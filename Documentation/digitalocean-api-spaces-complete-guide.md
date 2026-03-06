# DigitalOcean API & Spaces - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [DigitalOcean Spaces (S3-Compatible Storage)](#digitalocean-spaces)
4. [DigitalOcean API (Droplets, Databases, Apps)](#digitalocean-api)
5. [App Platform Deployment](#app-platform-deployment)
6. [Complete Code Examples](#complete-code-examples)
7. [Best Practices](#best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Overview

### DigitalOcean Services Overview

**What you'll use for ConsensusTracker:**

1. **Spaces Object Storage** - Store user-uploaded files (literature reviews, PDFs)
   - S3-compatible API
   - Built-in CDN
   - $5/month for 250GB + 1TB bandwidth

2. **App Platform** - Deploy backend Flask/FastAPI app
   - Auto-deploy from GitHub
   - Free tier available ($0/month for static sites, $5+ for services)
   - Automatic SSL, scaling

3. **Managed PostgreSQL** - User data, monitoring logs
   - $15/month (Basic)
   - Automated backups, scaling

4. **Functions** - Serverless functions (optional, for PubMed searches)
   - Pay per execution
   - Node.js or Python

---

## Authentication

### Creating API Token

1. **Log in to DigitalOcean**: cloud.digitalocean.com
2. **API** → **Tokens/Keys** → **Generate New Token**
3. **Name**: `consensustracker-api-token`
4. **Scopes**: ✓ Read + ✓ Write
5. **Expiration**: Never (or custom)
6. **Generate Token** → Copy immediately (shown once)

**Token format:** `dop_v1_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

### Environment Variables

```bash
# Add to .bashrc or .zshrc
export DIGITALOCEAN_TOKEN="dop_v1_xxxxx"
export DIGITALOCEAN_API_TOKEN="$DIGITALOCEAN_TOKEN"  # Alias

# Or .env file for your app
echo "DIGITALOCEAN_TOKEN=dop_v1_xxxxx" >> .env
```

### Testing Authentication

```bash
# Test token
curl -X GET \
  -H "Authorization: Bearer $DIGITALOCEAN_TOKEN" \
  "https://api.digitalocean.com/v2/account"

# Should return your account info
```

---

## DigitalOcean Spaces

### What is Spaces?

**Spaces** = DigitalOcean's S3-compatible object storage
- Store files: PDFs, images, backups, static sites
- **S3-compatible**: Use boto3 (AWS SDK) to interact
- Built-in CDN (optional, free)
- Regions: NYC3, SFO3, AMS3, SGP1, FRA1

### Creating a Space

#### Via Control Panel:

1. **Create** → **Spaces Object Storage**
2. **Datacenter region**: NYC3 (or closest to you)
3. **Enable CDN**: ✓ Yes (free, improves performance)
4. **Choose a unique name**: `consensustracker-uploads` (globally unique like S3)
5. **Select a project**: Default or create new
6. **Restrict File Listing**: ✓ Yes (security best practice)
7. **Create Space**

**Your Space URL:**
```
https://consensustracker-uploads.nyc3.digitaloceanspaces.com
```

**CDN URL (if enabled):**
```
https://consensustracker-uploads.nyc3.cdn.digitaloceanspaces.com
```

---

### Creating Spaces Access Keys

**Why:** You need access keys (like AWS credentials) to use the Spaces API.

1. **Spaces** → **Manage Keys**
2. **Generate New Key**
3. **Name**: `consensustracker-app`
4. **Generate Key**

**You'll receive:**
- **Access Key ID**: e.g., `DO00ABC123XYZ456`
- **Secret Access Key**: e.g., `secretkey123456...` (SAVE THIS - shown once)

**Environment variables:**
```bash
export SPACES_ACCESS_KEY_ID="DO00ABC123XYZ456"
export SPACES_SECRET_ACCESS_KEY="secretkey123456..."
export SPACES_REGION="nyc3"
export SPACES_BUCKET_NAME="consensustracker-uploads"
```

---

### Using Spaces with Python (boto3)

#### Installation

```bash
pip install boto3
```

#### Basic Setup

```python
import boto3
import os

# Configuration
REGION = os.getenv("SPACES_REGION", "nyc3")
BUCKET_NAME = os.getenv("SPACES_BUCKET_NAME")
ACCESS_KEY = os.getenv("SPACES_ACCESS_KEY_ID")
SECRET_KEY = os.getenv("SPACES_SECRET_ACCESS_KEY")

# Create session
session = boto3.session.Session()

# Create S3 client
# IMPORTANT: Set endpoint_url to DigitalOcean Spaces
client = session.client(
    's3',
    region_name=REGION,
    endpoint_url=f'https://{REGION}.digitaloceanspaces.com',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

# Or use resource interface (higher-level)
s3 = session.resource(
    's3',
    region_name=REGION,
    endpoint_url=f'https://{REGION}.digitaloceanspaces.com',
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)
```

**⚠️ CRITICAL:** You MUST set `endpoint_url` to DigitalOcean Spaces endpoint, not AWS S3!

---

### Upload File to Spaces

```python
def upload_file(local_file_path, remote_file_name, make_public=False):
    """
    Upload file to DigitalOcean Spaces.
    
    Args:
        local_file_path: Path to local file (e.g., 'docs/review.pdf')
        remote_file_name: Key in Spaces (e.g., 'user_123/literature_review.pdf')
        make_public: Whether to make file publicly accessible
    
    Returns:
        dict: {'success': bool, 'url': str}
    """
    
    try:
        # Extra args for metadata and permissions
        extra_args = {}
        
        # Set ACL (Access Control List)
        if make_public:
            extra_args['ACL'] = 'public-read'
        else:
            extra_args['ACL'] = 'private'
        
        # Guess content type
        import mimetypes
        content_type, _ = mimetypes.guess_type(local_file_path)
        if content_type:
            extra_args['ContentType'] = content_type
        
        # Upload
        client.upload_file(
            Filename=local_file_path,
            Bucket=BUCKET_NAME,
            Key=remote_file_name,
            ExtraArgs=extra_args
        )
        
        # Generate URL
        if make_public:
            # Use CDN URL if enabled
            url = f"https://{BUCKET_NAME}.{REGION}.cdn.digitaloceanspaces.com/{remote_file_name}"
        else:
            # Private - need signed URL
            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': BUCKET_NAME, 'Key': remote_file_name},
                ExpiresIn=3600  # 1 hour
            )
        
        return {
            'success': True,
            'url': url,
            'key': remote_file_name
        }
    
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

# Usage
result = upload_file(
    local_file_path='uploads/user_123_review.pdf',
    remote_file_name='users/123/literature_review.pdf',
    make_public=False  # Keep private
)

if result['success']:
    print(f"Uploaded: {result['url']}")
else:
    print(f"Error: {result['error']}")
```

---

### Download File from Spaces

```python
def download_file(remote_file_name, local_file_path):
    """
    Download file from Spaces to local disk.
    
    Args:
        remote_file_name: Key in Spaces
        local_file_path: Where to save locally
    
    Returns:
        bool: Success status
    """
    
    try:
        client.download_file(
            Bucket=BUCKET_NAME,
            Key=remote_file_name,
            Filename=local_file_path
        )
        return True
    
    except Exception as e:
        print(f"Download error: {e}")
        return False

# Usage
success = download_file(
    remote_file_name='users/123/literature_review.pdf',
    local_file_path='/tmp/review.pdf'
)
```

---

### Download File to Memory (Without Saving to Disk)

```python
import io

def download_to_memory(remote_file_name):
    """
    Download file directly into memory (BytesIO buffer).
    Useful for processing without disk I/O.
    
    Args:
        remote_file_name: Key in Spaces
    
    Returns:
        io.BytesIO: File contents in memory
    """
    
    buffer = io.BytesIO()
    
    try:
        client.download_fileobj(
            Bucket=BUCKET_NAME,
            Key=remote_file_name,
            Fileobj=buffer
        )
        
        # Reset buffer position to beginning
        buffer.seek(0)
        
        return buffer
    
    except Exception as e:
        print(f"Error: {e}")
        return None

# Usage - Read PDF directly from Spaces
pdf_buffer = download_to_memory('users/123/review.pdf')

if pdf_buffer:
    # Process in memory
    from PyPDF2 import PdfReader
    reader = PdfReader(pdf_buffer)
    text = reader.pages[0].extract_text()
    print(text)
```

---

### List Files in Space

```python
def list_files(prefix=''):
    """
    List all files in Spaces (or with specific prefix).
    
    Args:
        prefix: Filter by prefix (e.g., 'users/123/')
    
    Returns:
        list: List of file keys
    """
    
    try:
        response = client.list_objects_v2(
            Bucket=BUCKET_NAME,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            return []
        
        files = [obj['Key'] for obj in response['Contents']]
        return files
    
    except Exception as e:
        print(f"Error: {e}")
        return []

# Usage
user_files = list_files(prefix='users/123/')
print(f"User has {len(user_files)} files")
for file in user_files:
    print(f"  - {file}")
```

---

### Delete File from Spaces

```python
def delete_file(remote_file_name):
    """Delete file from Spaces."""
    
    try:
        client.delete_object(
            Bucket=BUCKET_NAME,
            Key=remote_file_name
        )
        return True
    
    except Exception as e:
        print(f"Error: {e}")
        return False

# Usage
deleted = delete_file('users/123/old_review.pdf')
```

---

### Generate Signed URL (Temporary Access to Private Files)

```python
def generate_download_url(remote_file_name, expiration=3600):
    """
    Generate temporary signed URL for private file.
    
    Args:
        remote_file_name: Key in Spaces
        expiration: URL validity in seconds (default 1 hour)
    
    Returns:
        str: Signed URL
    """
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': BUCKET_NAME,
                'Key': remote_file_name
            },
            ExpiresIn=expiration
        )
        return url
    
    except Exception as e:
        print(f"Error: {e}")
        return None

# Usage
# User wants to download their literature review
download_url = generate_download_url(
    remote_file_name='users/123/literature_review.pdf',
    expiration=3600  # Valid for 1 hour
)

print(f"Download link (expires in 1 hour): {download_url}")
```

---

### Complete Spaces Helper Class

```python
# File: services/spaces_manager.py

import boto3
import os
import io
import mimetypes

class SpacesManager:
    """
    DigitalOcean Spaces helper for ConsensusTracker.
    """
    
    def __init__(self):
        self.region = os.getenv("SPACES_REGION", "nyc3")
        self.bucket = os.getenv("SPACES_BUCKET_NAME")
        self.access_key = os.getenv("SPACES_ACCESS_KEY_ID")
        self.secret_key = os.getenv("SPACES_SECRET_ACCESS_KEY")
        
        if not all([self.bucket, self.access_key, self.secret_key]):
            raise ValueError("Missing Spaces credentials in environment")
        
        # Create client
        session = boto3.session.Session()
        self.client = session.client(
            's3',
            region_name=self.region,
            endpoint_url=f'https://{self.region}.digitaloceanspaces.com',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key
        )
    
    def upload(self, local_path, remote_key, public=False):
        """Upload file to Spaces."""
        
        extra_args = {
            'ACL': 'public-read' if public else 'private'
        }
        
        # Auto-detect content type
        content_type, _ = mimetypes.guess_type(local_path)
        if content_type:
            extra_args['ContentType'] = content_type
        
        self.client.upload_file(
            Filename=local_path,
            Bucket=self.bucket,
            Key=remote_key,
            ExtraArgs=extra_args
        )
        
        return self.get_url(remote_key, public)
    
    def upload_fileobj(self, file_object, remote_key, public=False):
        """Upload file-like object to Spaces."""
        
        extra_args = {
            'ACL': 'public-read' if public else 'private'
        }
        
        self.client.upload_fileobj(
            Fileobj=file_object,
            Bucket=self.bucket,
            Key=remote_key,
            ExtraArgs=extra_args
        )
        
        return self.get_url(remote_key, public)
    
    def download(self, remote_key, local_path):
        """Download file to disk."""
        
        self.client.download_file(
            Bucket=self.bucket,
            Key=remote_key,
            Filename=local_path
        )
    
    def download_to_memory(self, remote_key):
        """Download file to memory buffer."""
        
        buffer = io.BytesIO()
        self.client.download_fileobj(
            Bucket=self.bucket,
            Key=remote_key,
            Fileobj=buffer
        )
        buffer.seek(0)
        return buffer
    
    def delete(self, remote_key):
        """Delete file from Spaces."""
        
        self.client.delete_object(
            Bucket=self.bucket,
            Key=remote_key
        )
    
    def list_files(self, prefix=''):
        """List files with optional prefix."""
        
        response = self.client.list_objects_v2(
            Bucket=self.bucket,
            Prefix=prefix
        )
        
        if 'Contents' not in response:
            return []
        
        return [obj['Key'] for obj in response['Contents']]
    
    def get_url(self, remote_key, public=False):
        """Get URL for file."""
        
        if public:
            # Public CDN URL
            return f"https://{self.bucket}.{self.region}.cdn.digitaloceanspaces.com/{remote_key}"
        else:
            # Generate signed URL (1 hour validity)
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': remote_key},
                ExpiresIn=3600
            )
    
    def file_exists(self, remote_key):
        """Check if file exists."""
        
        try:
            self.client.head_object(Bucket=self.bucket, Key=remote_key)
            return True
        except:
            return False

# Usage
spaces = SpacesManager()

# Upload user's literature review
url = spaces.upload(
    local_path='/tmp/user_upload.pdf',
    remote_key='users/123/literature_review.pdf',
    public=False
)
print(f"Uploaded to: {url}")

# Download for processing
buffer = spaces.download_to_memory('users/123/literature_review.pdf')
# Process buffer...

# Delete old file
spaces.delete('users/123/old_review.pdf')
```

---

## DigitalOcean API

### What is DigitalOcean API?

The **DigitalOcean API** lets you manage infrastructure programmatically:
- Droplets (VMs)
- Databases (PostgreSQL, MySQL, etc.)
- App Platform (deploy apps)
- Load Balancers, Firewalls, etc.

**Base URL:** `https://api.digitalocean.com/v2/`

**For ConsensusTracker, you'll likely use:**
- **App Platform API** - Deploy backend
- **Database API** - Manage PostgreSQL (optional)

---

### Python SDK (PyDo)

**PyDo** = Official DigitalOcean Python client

#### Installation

```bash
pip install pydo
```

#### Basic Usage

```python
import os
from pydo import Client

# Initialize client
client = Client(token=os.environ.get("DIGITALOCEAN_TOKEN"))

# Example: Get account info
account = client.account.get()
print(f"Account email: {account['account']['email']}")

# Example: List databases
databases = client.databases.list()
for db in databases['databases']:
    print(f"Database: {db['name']} ({db['engine']})")
```

---

### App Platform - Deploy Your Backend

#### Creating an App (From GitHub)

**Via Control Panel:**

1. **Create** → **Apps**
2. **Choose Source**: GitHub
3. **Authorize DigitalOcean** to access your repo
4. **Select repo**: `yourname/consensustracker`
5. **Branch**: `main`
6. **Auto-deploy**: ✓ (redeploys on git push)
7. **Resource Type**: Web Service
8. **Environment Variables**:
   ```
   DIGITALOCEAN_API_KEY=dop_v1_xxxxx
   SPACES_ACCESS_KEY_ID=DO00xxxxx
   SPACES_SECRET_ACCESS_KEY=secretxxxxx
   DATABASE_URL=${db.DATABASE_URL}  # Auto-injected if you add DB
   ```
9. **Build Command**: `pip install -r requirements.txt`
10. **Run Command**: `gunicorn app:app` (or `uvicorn main:app`)
11. **HTTP Port**: `8080`
12. **Choose plan**: Basic ($5/month) or Pro ($12/month)
13. **Create App**

**Your app will be live at:**
```
https://your-app-xyz123.ondigitalocean.app
```

---

#### Via API (Python)

```python
from pydo import Client
import os

client = Client(token=os.environ.get("DIGITALOCEAN_TOKEN"))

# App specification
app_spec = {
    "name": "consensustracker-backend",
    "region": "nyc",
    "services": [
        {
            "name": "api",
            "github": {
                "repo": "yourusername/consensustracker",
                "branch": "main",
                "deploy_on_push": True
            },
            "build_command": "pip install -r requirements.txt",
            "run_command": "gunicorn app:app",
            "http_port": 8080,
            "instance_count": 1,
            "instance_size_slug": "basic-xxs",  # $5/month
            "envs": [
                {
                    "key": "DIGITALOCEAN_API_KEY",
                    "value": "dop_v1_xxxxx",
                    "type": "SECRET"  # Encrypted
                },
                {
                    "key": "SPACES_BUCKET_NAME",
                    "value": "consensustracker-uploads"
                }
            ]
        }
    ]
}

# Create app
response = client.apps.create(body={"spec": app_spec})
app = response['app']

print(f"App created: {app['id']}")
print(f"Live URL: {app['live_url']}")
```

---

#### Getting App Logs

```python
# Get app ID
apps = client.apps.list()
app_id = apps['apps'][0]['id']

# Get latest deployment
deployments = client.apps.list_deployments(app_id=app_id)
latest_deployment = deployments['deployments'][0]
deployment_id = latest_deployment['id']

# Get logs
logs = client.apps.get_logs_aggregate(
    app_id=app_id,
    deployment_id=deployment_id,
    type='BUILD'  # or 'DEPLOY', 'RUN'
)

print(logs)
```

---

### Managing PostgreSQL Database

#### Creating Database

**Via Control Panel:**

1. **Create** → **Databases**
2. **Database engine**: PostgreSQL 16
3. **Datacenter**: NYC3 (same as app for low latency)
4. **Plan**: Basic ($15/month) - 1 vCPU, 1GB RAM, 10GB storage
5. **Database name**: `consensustracker`
6. **Create Database Cluster**

**Connection string (auto-generated):**
```
postgres://user:password@host:25060/defaultdb?sslmode=require
```

**Environment variable in App Platform:**
```
DATABASE_URL=${db.DATABASE_URL}
```

---

#### Via API

```python
# Create database
db_spec = {
    "name": "consensustracker-db",
    "engine": "pg",  # PostgreSQL
    "version": "16",
    "region": "nyc3",
    "size": "db-s-1vcpu-1gb",  # $15/month
    "num_nodes": 1
}

response = client.databases.create(body=db_spec)
database = response['database']

print(f"Database ID: {database['id']}")
print(f"Connection: {database['connection']}")
```

---

#### Connecting Database to App

**Via Control Panel:**

1. Open your app
2. **Settings** → **Database**
3. **Attach Database**
4. Select your database
5. **Attach**

**Result:** App Platform auto-injects `DATABASE_URL` environment variable.

---

#### Using Database in Python

```python
import os
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL
database_url = os.getenv("DATABASE_URL")
url = urlparse(database_url)

# Connect
conn = psycopg2.connect(
    host=url.hostname,
    port=url.port,
    user=url.username,
    password=url.password,
    database=url.path[1:],  # Remove leading '/'
    sslmode='require'
)

cursor = conn.cursor()

# Query
cursor.execute("SELECT version();")
version = cursor.fetchone()
print(f"PostgreSQL version: {version}")

cursor.close()
conn.close()
```

**Or use SQLAlchemy:**

```python
from sqlalchemy import create_engine
import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

# Use with SQLAlchemy ORM
from sqlalchemy.orm import sessionmaker

Session = sessionmaker(bind=engine)
session = Session()

# Your models/queries here
```

---

## App Platform Deployment

### Complete Deployment Workflow

**File Structure:**
```
consensustracker/
├── app.py                  # Flask/FastAPI app
├── requirements.txt        # Dependencies
├── runtime.txt             # Python version (optional)
├── .env.example            # Example env vars
├── Procfile               # App Platform run command (optional)
└── .gitignore
```

**requirements.txt:**
```
flask==3.0.0
gunicorn==21.2.0
psycopg2-binary==2.9.9
boto3==1.34.0
biopython==1.83
python-dotenv==1.0.0
```

**runtime.txt** (optional):
```
python-3.11
```

**Procfile** (optional, alternative to run command in UI):
```
web: gunicorn app:app --bind 0.0.0.0:8080
```

**app.py:**
```python
import os
from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/')
def index():
    return jsonify({
        'status': 'running',
        'app': 'ConsensusTracker'
    })

@app.route('/health')
def health():
    return jsonify({'status': 'healthy'})

if __name__ == '__main__':
    # For local dev only (App Platform uses Procfile/run command)
    app.run(host='0.0.0.0', port=8080)
```

**Deploy:**
```bash
git add .
git commit -m "Initial commit"
git push origin main
```

**App Platform automatically:**
1. Detects changes in GitHub
2. Pulls code
3. Runs `pip install -r requirements.txt`
4. Runs `gunicorn app:app`
5. Deploys to `https://your-app.ondigitalocean.app`

---

### Environment Variables in App Platform

**Set via Control Panel:**

1. Open app → **Settings** → **App-Level Environment Variables**
2. Add variables:
   - `DIGITALOCEAN_API_TOKEN` (SECRET)
   - `SPACES_ACCESS_KEY_ID` (SECRET)
   - `SPACES_SECRET_ACCESS_KEY` (SECRET)
   - `SPACES_BUCKET_NAME` (plain)
   - `FLASK_ENV` = `production`
3. **Save** → App redeploys

**Access in code:**
```python
import os

api_token = os.getenv("DIGITALOCEAN_API_TOKEN")
bucket = os.getenv("SPACES_BUCKET_NAME")
```

---

## Complete Code Examples

### Full Integration Example

```python
# File: app.py (Flask backend on App Platform)

import os
from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import boto3
from pydo import Client

app = Flask(__name__)

# Configuration
SPACES_REGION = os.getenv("SPACES_REGION", "nyc3")
SPACES_BUCKET = os.getenv("SPACES_BUCKET_NAME")
SPACES_ACCESS_KEY = os.getenv("SPACES_ACCESS_KEY_ID")
SPACES_SECRET = os.getenv("SPACES_SECRET_ACCESS_KEY")

DO_TOKEN = os.getenv("DIGITALOCEAN_TOKEN")

# Initialize Spaces client
session = boto3.session.Session()
spaces_client = session.client(
    's3',
    region_name=SPACES_REGION,
    endpoint_url=f'https://{SPACES_REGION}.digitaloceanspaces.com',
    aws_access_key_id=SPACES_ACCESS_KEY,
    aws_secret_access_key=SPACES_SECRET
)

# Initialize DigitalOcean API client
do_client = Client(token=DO_TOKEN)

@app.route('/')
def index():
    return jsonify({'status': 'running', 'app': 'ConsensusTracker'})

@app.route('/upload', methods=['POST'])
def upload_file():
    """
    Upload user's literature review to Spaces.
    
    POST /upload
    Body: multipart/form-data with 'file' field
    """
    
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'error': 'Empty filename'}), 400
    
    # Secure filename
    filename = secure_filename(file.filename)
    
    # Generate unique key
    user_id = request.form.get('user_id', 'default')
    remote_key = f"users/{user_id}/literature_reviews/{filename}"
    
    try:
        # Upload to Spaces
        spaces_client.upload_fileobj(
            Fileobj=file,
            Bucket=SPACES_BUCKET,
            Key=remote_key,
            ExtraArgs={'ACL': 'private'}
        )
        
        # Generate temporary download URL
        download_url = spaces_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': SPACES_BUCKET, 'Key': remote_key},
            ExpiresIn=3600
        )
        
        return jsonify({
            'success': True,
            'key': remote_key,
            'download_url': download_url
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download/<user_id>/<filename>')
def download_file(user_id, filename):
    """
    Generate signed download URL for user's file.
    
    GET /download/<user_id>/<filename>
    """
    
    remote_key = f"users/{user_id}/literature_reviews/{filename}"
    
    try:
        # Check if file exists
        spaces_client.head_object(Bucket=SPACES_BUCKET, Key=remote_key)
        
        # Generate signed URL (1 hour)
        url = spaces_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': SPACES_BUCKET, 'Key': remote_key},
            ExpiresIn=3600
        )
        
        return jsonify({
            'download_url': url,
            'expires_in': 3600
        })
    
    except Exception as e:
        return jsonify({'error': 'File not found'}), 404

@app.route('/list/<user_id>')
def list_user_files(user_id):
    """
    List all files for a user.
    
    GET /list/<user_id>
    """
    
    prefix = f"users/{user_id}/"
    
    try:
        response = spaces_client.list_objects_v2(
            Bucket=SPACES_BUCKET,
            Prefix=prefix
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                files.append({
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'].isoformat()
                })
        
        return jsonify({'files': files})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health')
def health():
    """Health check endpoint."""
    
    checks = {
        'spaces': False,
        'do_api': False
    }
    
    # Check Spaces connection
    try:
        spaces_client.list_buckets()
        checks['spaces'] = True
    except:
        pass
    
    # Check DO API connection
    try:
        do_client.account.get()
        checks['do_api'] = True
    except:
        pass
    
    healthy = all(checks.values())
    
    return jsonify({
        'status': 'healthy' if healthy else 'degraded',
        'checks': checks
    }), 200 if healthy else 503

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
```

---

## Best Practices

### 1. Security

**DO:**
- ✅ Use environment variables for secrets
- ✅ Mark sensitive env vars as SECRET in App Platform
- ✅ Keep Spaces files private by default
- ✅ Use signed URLs for temporary access
- ✅ Restrict file listing on Spaces buckets
- ✅ Use HTTPS for all API calls

**DON'T:**
- ❌ Commit credentials to Git
- ❌ Make all Spaces files public
- ❌ Use long-lived signed URLs (>24 hours)
- ❌ Store API tokens in frontend code

---

### 2. Cost Optimization

**Spaces:**
- $5/month for 250GB storage + 1TB bandwidth
- Additional storage: $0.02/GB/month
- Bandwidth overage: $0.01/GB

**Tips:**
- Enable CDN (free, reduces bandwidth)
- Delete old files regularly
- Compress files before upload
- Use lifecycle policies for auto-deletion

---

### 3. Error Handling

```python
def safe_upload(file_path, remote_key):
    """Upload with comprehensive error handling."""
    
    try:
        spaces_client.upload_file(
            Filename=file_path,
            Bucket=SPACES_BUCKET,
            Key=remote_key
        )
        return {'success': True}
    
    except spaces_client.exceptions.NoSuchBucket:
        return {'success': False, 'error': 'Bucket does not exist'}
    
    except spaces_client.exceptions.ClientError as e:
        error_code = e.response['Error']['Code']
        if error_code == 'AccessDenied':
            return {'success': False, 'error': 'Access denied - check credentials'}
        elif error_code == 'EntityTooLarge':
            return {'success': False, 'error': 'File too large'}
        else:
            return {'success': False, 'error': f'Client error: {error_code}'}
    
    except Exception as e:
        return {'success': False, 'error': str(e)}
```

---

## Troubleshooting

### Common Errors

**1. `EndpointConnectionError`**

**Cause:** Forgot to set `endpoint_url` or wrong region

**Solution:**
```python
# WRONG
client = boto3.client('s3', ...)

# RIGHT
client = boto3.client(
    's3',
    endpoint_url=f'https://{REGION}.digitaloceanspaces.com',
    ...
)
```

---

**2. `AccessDenied` when uploading**

**Cause:** Invalid access keys or insufficient permissions

**Solution:**
```bash
# Verify keys
echo $SPACES_ACCESS_KEY_ID
echo $SPACES_SECRET_ACCESS_KEY

# Regenerate keys if needed (Spaces → Manage Keys)
```

---

**3. App Platform build fails**

**Cause:** Missing dependencies or Python version mismatch

**Solution:**
```
# Check build logs in App Platform UI
# Ensure requirements.txt is complete
# Specify Python version in runtime.txt
```

---

**4. Environment variables not working**

**Cause:** Not saving/redeploying after adding env vars

**Solution:**
- Settings → Environment Variables → **Save**
- App Platform will auto-redeploy
- Or manually trigger redeploy

---

## Summary

**Key Takeaways:**

✅ **Spaces = S3-compatible** - Use boto3 with custom endpoint
✅ **Always set** `endpoint_url` to DigitalOcean Spaces
✅ **App Platform** deploys from GitHub automatically
✅ **Environment variables** stored securely in App Platform
✅ **Signed URLs** for temporary access to private files
✅ **PyDo** for DigitalOcean API operations

**For ConsensusTracker:**
- Store user literature reviews in **Spaces** (private)
- Deploy Flask backend on **App Platform** ($5/month)
- Use **PostgreSQL** for user data ($15/month)
- Generate signed URLs for file downloads
- Auto-deploy from GitHub on push

**Costs:**
- Spaces: $5/month (250GB + 1TB bandwidth)
- App Platform: $5/month (Basic service)
- PostgreSQL: $15/month (Basic)
- **Total: ~$25/month**

**Next Steps:**
1. Create Spaces bucket + access keys
2. Test upload/download with boto3
3. Deploy Flask app to App Platform
4. Add environment variables
5. Test end-to-end workflow

Good luck! 🚀
