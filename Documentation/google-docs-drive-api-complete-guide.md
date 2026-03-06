# Google Docs & Drive API - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Key Concepts](#key-concepts)
3. [Authentication Setup](#authentication-setup)
4. [Google Docs API](#google-docs-api)
5. [Google Drive API](#google-drive-api)
6. [Adding Comments](#adding-comments)
7. [Complete Code Examples](#complete-code-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What Are These APIs?

**Google Docs API:**
- Read document content and structure
- Create new documents
- Modify existing documents (insert/delete text, format)
- **CANNOT** directly add comments

**Google Drive API:**
- Manage file permissions
- **Add/edit/delete comments** (yes, comments use Drive API!)
- List files and folders
- Upload/download files

### Important Distinction

**📌 CRITICAL:** Comments on Google Docs are managed through the **Drive API**, NOT the Docs API!

```
Google Docs API → Reading/writing document content
Google Drive API → Comments, permissions, file metadata
```

---

## Key Concepts

### Document Structure

Google Docs are structured as:
```
Document
├─ Body
│  └─ Content (array of StructuralElements)
│     ├─ Paragraph
│     │  └─ Elements (text, inline objects)
│     ├─ Table
│     ├─ SectionBreak
│     └─ TableOfContents
└─ DocumentStyle
```

### Character Indices

**Every character has an index** (0-based):
```
"Hello World"
 012345678910
```

To insert text at position 6: Insert at index 6
To select "World": startIndex=6, endIndex=11

### Scopes (Permissions)

OAuth scopes determine what your app can access:

| Scope | Access Level |
|-------|--------------|
| `https://www.googleapis.com/auth/documents` | Full read/write docs |
| `https://www.googleapis.com/auth/documents.readonly` | Read-only docs |
| `https://www.googleapis.com/auth/drive` | Full read/write Drive (includes comments) |
| `https://www.googleapis.com/auth/drive.file` | Access only files created by app |
| `https://www.googleapis.com/auth/drive.comments` | Comments only |

**For ConsensusTracker, you need:**
```python
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',  # Read doc content
    'https://www.googleapis.com/auth/drive.comments'       # Add comments
]
```

---

## Authentication Setup

### Two Authentication Methods

1. **OAuth 2.0 User Flow** - User grants access to their docs
2. **Service Account** - App acts on its own behalf (recommended for backend)

---

### Method 1: Service Account (Recommended for ConsensusTracker)

**Use when:**
- Backend service (no human interaction)
- Server-to-server authentication
- Accessing shared documents

**Setup Steps:**

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click **Select a Project** → **New Project**
3. Name: `ConsensusTracker`
4. Click **Create**

#### Step 2: Enable APIs

1. Navigate to **APIs & Services** → **Library**
2. Search "Google Docs API" → Click → **Enable**
3. Search "Google Drive API" → Click → **Enable**

#### Step 3: Create Service Account

1. **APIs & Services** → **Credentials**
2. **Create Credentials** → **Service Account**
3. Fill in:
   - Name: `consensustracker-bot`
   - Description: `Service account for adding comments to user docs`
4. Click **Create and Continue**
5. **Grant this service account access to project** (optional) → Skip
6. Click **Done**

#### Step 4: Generate Key File

1. Click on newly created service account email (e.g., `consensustracker-bot@project-id.iam.gserviceaccount.com`)
2. Go to **Keys** tab
3. **Add Key** → **Create New Key**
4. Choose **JSON**
5. Click **Create**
6. **Save this file securely!** (e.g., `service-account-credentials.json`)

**⚠️ NEVER commit this file to Git!**

```bash
# Add to .gitignore
echo "service-account-credentials.json" >> .gitignore
```

#### Step 5: Share Documents with Service Account

**CRITICAL STEP:** User must share their Google Doc with the service account email.

**Programmatically:**
```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

creds = service_account.Credentials.from_service_account_file(
    'service-account-credentials.json'
)

drive_service = build('drive', 'v3', credentials=creds)

# Grant service account write access to document
permission = {
    'type': 'user',
    'role': 'writer',
    'emailAddress': 'consensustracker-bot@project-id.iam.gserviceaccount.com'
}

drive_service.permissions().create(
    fileId='DOCUMENT_ID',
    body=permission,
    fields='id'
).execute()
```

**User Flow in ConsensusTracker:**
1. User provides Google Doc URL during onboarding
2. App extracts document ID
3. App displays: "Please share this doc with `consensustracker-bot@...` and grant edit access"
4. User shares via Google Docs UI
5. App tests access by attempting to read doc

---

### Method 2: OAuth 2.0 User Flow

**Use when:**
- User is granting access to their own documents
- Web app with frontend

**Setup:**

#### Step 1: Configure OAuth Consent Screen

1. **APIs & Services** → **OAuth consent screen**
2. **User Type**: External (for public) or Internal (for Google Workspace orgs)
3. **App name**: ConsensusTracker
4. **User support email**: Your email
5. **Developer contact**: Your email
6. **Scopes**: Add scopes listed above
7. **Test users**: Add your email for testing
8. **Save**

#### Step 2: Create OAuth Client ID

1. **Credentials** → **Create Credentials** → **OAuth Client ID**
2. **Application type**: Desktop app (for Python scripts) or Web application (for web apps)
3. **Name**: ConsensusTracker OAuth Client
4. **Authorized redirect URIs** (for web apps): `http://localhost:5000/oauth2callback`
5. Click **Create**
6. Download **client_secret.json**

#### Step 3: Python Authentication Code

```python
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
import os

SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.comments'
]

def get_credentials():
    """Get or create OAuth credentials."""
    creds = None
    
    # Token file stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If no valid credentials, let user log in
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'client_secret.json', SCOPES
            )
            creds = flow.run_local_server(port=0)
        
        # Save credentials for next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    
    return creds

# Usage
creds = get_credentials()
```

**First run:**
- Browser opens
- User logs in with Google
- User grants permissions
- `token.json` created (contains access token)

**Subsequent runs:**
- `token.json` loaded
- No user interaction needed

---

## Google Docs API

### Reading Document Content

```python
from googleapiclient.discovery import build
from google.oauth2 import service_account

# Authenticate
creds = service_account.Credentials.from_service_account_file(
    'service-account-credentials.json',
    scopes=['https://www.googleapis.com/auth/documents.readonly']
)

docs_service = build('docs', 'v1', credentials=creds)

# Get document
DOCUMENT_ID = '1abcdefghijklmnopqrstuvwxyz'  # From URL
document = docs_service.documents().get(documentId=DOCUMENT_ID).execute()

# Extract title
title = document.get('title')
print(f"Title: {title}")

# Extract text content
def get_text(document):
    """Extract all text from document."""
    content = document.get('body').get('content')
    text_parts = []
    
    for element in content:
        if 'paragraph' in element:
            for elem in element.get('paragraph').get('elements', []):
                if 'textRun' in elem:
                    text_parts.append(elem.get('textRun').get('content'))
    
    return ''.join(text_parts)

full_text = get_text(document)
print(full_text)
```

---

### Finding Specific Text

```python
def find_text_positions(document, search_text):
    """
    Find all occurrences of text and return their indices.
    
    Returns: [(start_index, end_index), ...]
    """
    content = document.get('body').get('content')
    positions = []
    current_index = 1  # Docs are 1-indexed
    
    for element in content:
        if 'paragraph' in element:
            paragraph = element.get('paragraph')
            for elem in paragraph.get('elements', []):
                if 'textRun' in elem:
                    text_run = elem.get('textRun')
                    text = text_run.get('content')
                    start = text_run.get('startIndex')
                    end = text_run.get('endIndex')
                    
                    # Search for text
                    if search_text in text:
                        offset = text.index(search_text)
                        match_start = start + offset
                        match_end = match_start + len(search_text)
                        positions.append((match_start, match_end))
    
    return positions

# Example: Find "Section 3.2"
positions = find_text_positions(document, "Section 3.2")
print(f"Found at positions: {positions}")
```

---

### Finding Sections by Headers

```python
def find_sections(document):
    """
    Find all section headers and their positions.
    
    Returns: {
        "Introduction": (start_idx, end_idx),
        "Methods": (start_idx, end_idx),
        ...
    }
    """
    content = document.get('body').get('content')
    sections = {}
    
    for element in content:
        if 'paragraph' in element:
            paragraph = element.get('paragraph')
            
            # Check if paragraph style indicates heading
            style = paragraph.get('paragraphStyle', {})
            named_style = style.get('namedStyleType', '')
            
            if 'HEADING' in named_style:  # HEADING_1, HEADING_2, etc.
                # Extract heading text
                text = ''
                start_idx = None
                end_idx = None
                
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text_run = elem.get('textRun')
                        text += text_run.get('content', '')
                        if start_idx is None:
                            start_idx = text_run.get('startIndex')
                        end_idx = text_run.get('endIndex')
                
                sections[text.strip()] = (start_idx, end_idx)
    
    return sections

sections = find_sections(document)
# {'Introduction': (42, 56), 'Methods': (156, 164), ...}
```

---

### Creating a New Document

```python
def create_document(title, content):
    """Create a new Google Doc."""
    
    docs_service = build('docs', 'v1', credentials=creds)
    
    # Create empty doc
    document = docs_service.documents().create(body={'title': title}).execute()
    doc_id = document.get('documentId')
    
    # Add content
    requests = [
        {
            'insertText': {
                'location': {'index': 1},
                'text': content
            }
        }
    ]
    
    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()
    
    return doc_id

# Usage
new_doc_id = create_document(
    title="Literature Review",
    content="This is my literature review..."
)
print(f"Created: https://docs.google.com/document/d/{new_doc_id}/edit")
```

---

## Google Drive API

### Listing Files

```python
from googleapiclient.discovery import build

drive_service = build('drive', 'v3', credentials=creds)

# List all docs
results = drive_service.files().list(
    q="mimeType='application/vnd.google-apps.document'",
    pageSize=10,
    fields="files(id, name, modifiedTime)"
).execute()

files = results.get('files', [])
for file in files:
    print(f"{file['name']} (ID: {file['id']})")
```

---

### Getting File Metadata

```python
file = drive_service.files().get(
    fileId='DOCUMENT_ID',
    fields='id, name, mimeType, owners, permissions'
).execute()

print(f"Name: {file['name']}")
print(f"Owners: {[owner['emailAddress'] for owner in file['owners']]}")
```

---

## Adding Comments

### Understanding Comment Anchoring

Comments can be:
1. **Unanchored** - Attached to document (no specific location)
2. **Anchored** - Attached to specific text range

**For Google Docs, anchoring is tricky:**
- Anchors use `{"r": "head"}` for latest revision
- For sheets: Anchors use cell references
- **The anchor format for Docs is NOT well documented**

---

### Adding an Anchored Comment (Line-based)

```python
def add_comment_at_line(file_id, comment_text, line_number):
    """
    Add comment anchored to a specific line in a Google Doc.
    
    Note: Line numbers are approximate and depend on revision.
    """
    
    drive_service = build('drive', 'v3', credentials=creds)
    
    # Define anchor
    anchor = {
        'r': 'head',  # Latest revision
        'a': [{
            'line': {
                'line': line_number,
                'length': 1
            }
        }]
    }
    
    # Create comment
    comment_body = {
        'content': comment_text,
        'anchor': json.dumps(anchor)
    }
    
    comment = drive_service.comments().create(
        fileId=file_id,
        body=comment_body,
        fields='id,content,anchor'
    ).execute()
    
    print(f"Comment added: {comment['id']}")
    return comment

# Usage
add_comment_at_line(
    file_id='DOCUMENT_ID',
    comment_text='This contradicts recent findings by Smith et al. (2025).',
    line_number=42
)
```

---

### Adding Unanchored Comment (Simpler, Recommended)

```python
def add_unanchored_comment(file_id, comment_text):
    """
    Add comment to document (not anchored to specific location).
    
    This is more reliable than anchored comments.
    """
    
    drive_service = build('drive', 'v3', credentials=creds)
    
    comment_body = {
        'content': comment_text
    }
    
    comment = drive_service.comments().create(
        fileId=file_id,
        body=comment_body,
        fields='id,content,createdTime'
    ).execute()
    
    return comment

# Usage
comment = add_unanchored_comment(
    file_id='DOCUMENT_ID',
    comment_text="""
    CONTRADICTION DETECTED in Section 3.2:
    
    Your claim: "Treatment X shows 80% efficacy"
    New finding: Smith et al. (2025) found only 45% efficacy in larger cohort
    
    Suggested update: Add nuance about patient population differences.
    """
)
```

---

### Alternative: Using Suggestions (Track Changes)

```python
def add_suggestion(document_id, start_index, end_index, suggested_text):
    """
    Add suggested edit (like Track Changes in Word).
    
    This creates a pending change that user can accept/reject.
    """
    
    docs_service = build('docs', 'v1', credentials=creds)
    
    requests = [
        {
            'replaceAllText': {
                'containsText': {
                    'text': 'old_text',
                    'matchCase': True
                },
                'replaceText': suggested_text,
                'tabsCriteria': {
                    'all': True
                }
            }
        }
    ]
    
    # Actually, Google Docs API doesn't support suggestions directly
    # You must use Drive API comments instead
```

**❌ Limitation:** Google Docs API doesn't support creating suggestions programmatically. Use comments instead.

---

### Practical Workaround: Comments with Section References

Since anchored comments are unreliable, use this pattern:

```python
def add_comment_with_reference(file_id, section, original_text, new_finding):
    """
    Add comment that references section explicitly in text.
    """
    
    comment_text = f"""
    📍 LOCATION: {section}
    
    ⚠️ CONTRADICTION DETECTED:
    
    Your original text:
    "{original_text}"
    
    New finding contradicts this:
    {new_finding}
    
    🔗 Citation: [Full citation here]
    
    ✏️ SUGGESTED UPDATE:
    [Your suggested revised text here]
    
    ---
    Generated by ConsensusTracker
    """
    
    return add_unanchored_comment(file_id, comment_text)

# Usage
add_comment_with_reference(
    file_id='DOCUMENT_ID',
    section='Section 3.2, Paragraph starting with "Treatment efficacy..."',
    original_text='Treatment X shows 80% efficacy in all patient populations',
    new_finding='Smith et al. (2025, DOI: 10.1234/xyz) found only 45% efficacy in cohort of 500 patients with comorbidities'
)
```

**Advantages:**
- ✅ Reliable (always works)
- ✅ Clear location reference in comment text
- ✅ User can easily find relevant section
- ✅ Professional formatting

---

## Complete Code Examples

### Full Workflow: Read Doc + Add Comment

```python
# complete_example.py
from googleapiclient.discovery import build
from google.oauth2 import service_account
import json

# Configuration
SERVICE_ACCOUNT_FILE = 'service-account-credentials.json'
SCOPES = [
    'https://www.googleapis.com/auth/documents.readonly',
    'https://www.googleapis.com/auth/drive.comments'
]

def get_services():
    """Initialize Docs and Drive API services."""
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=SCOPES
    )
    
    docs_service = build('docs', 'v1', credentials=creds)
    drive_service = build('drive', 'v3', credentials=creds)
    
    return docs_service, drive_service

def extract_document_content(docs_service, document_id):
    """
    Extract full text content from Google Doc.
    
    Returns: str
    """
    document = docs_service.documents().get(documentId=document_id).execute()
    
    content_parts = []
    body = document.get('body', {}).get('content', [])
    
    for element in body:
        if 'paragraph' in element:
            for text_elem in element['paragraph'].get('elements', []):
                if 'textRun' in text_elem:
                    content_parts.append(text_elem['textRun']['content'])
    
    return ''.join(content_parts)

def find_section_by_keyword(docs_service, document_id, keyword):
    """
    Find section containing keyword.
    
    Returns: {
        'section_name': str,
        'text': str,
        'start_index': int,
        'end_index': int
    } or None
    """
    document = docs_service.documents().get(documentId=document_id).execute()
    body = document.get('body', {}).get('content', [])
    
    current_section = None
    
    for element in body:
        if 'paragraph' in element:
            paragraph = element['paragraph']
            style = paragraph.get('paragraphStyle', {})
            
            # Check if heading
            if 'HEADING' in style.get('namedStyleType', ''):
                # Extract heading text
                text = ''
                for elem in paragraph.get('elements', []):
                    if 'textRun' in elem:
                        text += elem['textRun']['content']
                current_section = text.strip()
            
            # Check for keyword in paragraph
            for elem in paragraph.get('elements', []):
                if 'textRun' in elem:
                    text_run = elem['textRun']
                    if keyword.lower() in text_run['content'].lower():
                        return {
                            'section_name': current_section or 'Unknown Section',
                            'text': text_run['content'],
                            'start_index': text_run.get('startIndex'),
                            'end_index': text_run.get('endIndex')
                        }
    
    return None

def add_contradiction_comment(drive_service, file_id, contradiction_data):
    """
    Add formatted contradiction comment to document.
    
    Args:
        contradiction_data: {
            'section': str,
            'user_claim': str,
            'new_finding': str,
            'paper_title': str,
            'paper_authors': str,
            'paper_doi': str,
            'severity': 'high'|'medium'|'low',
            'suggested_update': str
        }
    """
    
    severity_emoji = {
        'high': '🚨',
        'medium': '⚠️',
        'low': 'ℹ️'
    }
    
    comment_text = f"""
    {severity_emoji.get(contradiction_data['severity'], '📍')} CONTRADICTION DETECTED
    
    📍 LOCATION: {contradiction_data['section']}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    YOUR ORIGINAL CLAIM:
    "{contradiction_data['user_claim']}"
    
    NEW FINDING:
    {contradiction_data['new_finding']}
    
    📄 SOURCE:
    {contradiction_data['paper_title']}
    Authors: {contradiction_data['paper_authors']}
    DOI: {contradiction_data['paper_doi']}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    ✏️ SUGGESTED UPDATE:
    {contradiction_data['suggested_update']}
    
    ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    
    🤖 Generated by ConsensusTracker
    """
    
    comment_body = {'content': comment_text.strip()}
    
    comment = drive_service.comments().create(
        fileId=file_id,
        body=comment_body,
        fields='id,content,createdTime,author'
    ).execute()
    
    return comment

# MAIN WORKFLOW
if __name__ == '__main__':
    # Setup
    DOCUMENT_ID = '1abcdefghijklmnopqrstuvwxyz'
    docs_service, drive_service = get_services()
    
    # Step 1: Extract document content
    print("Extracting document content...")
    content = extract_document_content(docs_service, DOCUMENT_ID)
    print(f"Extracted {len(content)} characters")
    
    # Step 2: Search for specific claim
    print("Searching for relevant section...")
    section_info = find_section_by_keyword(docs_service, DOCUMENT_ID, "efficacy")
    
    if section_info:
        print(f"Found in: {section_info['section_name']}")
        
        # Step 3: Add contradiction comment
        print("Adding comment...")
        comment = add_contradiction_comment(
            drive_service,
            DOCUMENT_ID,
            {
                'section': section_info['section_name'],
                'user_claim': 'Treatment X shows 80% efficacy',
                'new_finding': 'Smith et al. found only 45% efficacy in larger cohort (n=500)',
                'paper_title': 'Reassessing Treatment X Efficacy in Diverse Populations',
                'paper_authors': 'Smith J, Jones A, Williams B',
                'paper_doi': '10.1234/example.2025.001',
                'severity': 'high',
                'suggested_update': 'While early studies suggested 80% efficacy, recent large-scale research (Smith et al., 2025) found 45% efficacy, highlighting the importance of patient population characteristics in treatment outcomes.'
            }
        )
        
        print(f"✓ Comment added successfully (ID: {comment['id']})")
    else:
        print("Section not found")
```

---

## Best Practices

### 1. Error Handling

```python
from googleapiclient.errors import HttpError

def safe_add_comment(drive_service, file_id, comment_text):
    """Add comment with error handling."""
    try:
        comment = drive_service.comments().create(
            fileId=file_id,
            body={'content': comment_text},
            fields='id'
        ).execute()
        return {'success': True, 'comment_id': comment['id']}
    
    except HttpError as error:
        error_reason = error.resp.get('reason', 'Unknown')
        
        if error.resp.status == 403:
            return {
                'success': False,
                'error': 'Permission denied. Service account needs edit access.'
            }
        elif error.resp.status == 404:
            return {
                'success': False,
                'error': 'Document not found. Check document ID.'
            }
        else:
            return {
                'success': False,
                'error': f'API error: {error_reason}'
            }
    
    except Exception as e:
        return {
            'success': False,
            'error': f'Unexpected error: {str(e)}'
        }
```

---

### 2. Rate Limiting

Google APIs have quotas:
- **Docs API**: 300 requests/minute per user
- **Drive API**: 1000 requests/100 seconds per user

```python
import time

def add_comments_batch(drive_service, file_id, comments_list):
    """Add multiple comments with rate limiting."""
    results = []
    
    for i, comment_text in enumerate(comments_list):
        result = safe_add_comment(drive_service, file_id, comment_text)
        results.append(result)
        
        # Rate limit: Max 10 requests/second
        if i > 0 and i % 10 == 0:
            time.sleep(1)
    
    return results
```

---

### 3. Caching Document Content

```python
import hashlib
import json
import os

def get_cached_document(docs_service, document_id, cache_dir='cache'):
    """
    Get document content, using cache if available.
    
    Cache invalidation: Checks if doc modified since last cache.
    """
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, f"{document_id}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            cached = json.load(f)
        
        # Verify not stale (check last modified)
        doc_meta = drive_service.files().get(
            fileId=document_id,
            fields='modifiedTime'
        ).execute()
        
        if doc_meta['modifiedTime'] == cached['modified_time']:
            print("Using cached content")
            return cached['content']
    
    # Fetch fresh
    document = docs_service.documents().get(documentId=document_id).execute()
    content = extract_document_content_from_doc(document)
    
    # Cache
    with open(cache_file, 'w') as f:
        json.dump({
            'content': content,
            'modified_time': doc_meta['modifiedTime']
        }, f)
    
    return content
```

---

### 4. Security Best Practices

**DO:**
- ✅ Store service account credentials as environment variables or secrets manager
- ✅ Use least-privilege scopes
- ✅ Validate document IDs before accessing
- ✅ Log all API operations for audit
- ✅ Implement retry logic with exponential backoff

**DON'T:**
- ❌ Commit credentials to Git
- ❌ Request broader scopes than needed
- ❌ Store credentials in frontend code
- ❌ Share service account keys publicly

---

## Troubleshooting

### Common Errors

**1. `403 Forbidden - Insufficient Permission`**

**Cause:** Service account doesn't have access to document.

**Solution:**
```python
# Check if service account has access
try:
    file = drive_service.files().get(fileId=document_id).execute()
    print("Access granted")
except HttpError as e:
    if e.resp.status == 403:
        print("User must share document with service account")
```

---

**2. `404 Not Found`**

**Cause:** Invalid document ID

**Solution:**
```python
def extract_doc_id_from_url(url):
    """Extract document ID from Google Docs URL."""
    # https://docs.google.com/document/d/DOCUMENT_ID/edit
    import re
    match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None

doc_id = extract_doc_id_from_url(user_provided_url)
```

---

**3. Comments not anchoring correctly**

**Cause:** Anchor format is complex and poorly documented.

**Solution:** Use unanchored comments with explicit section references (see earlier example).

---

**4. `401 Unauthorized`**

**Cause:** Invalid or expired credentials

**Solution:**
```python
# For service accounts: Regenerate key
# For OAuth: Delete token.json and re-authenticate

if os.path.exists('token.json'):
    os.remove('token.json')
    
creds = get_credentials()  # Re-authenticate
```

---

### Debugging Tips

**1. Inspect document structure:**

```python
import json

document = docs_service.documents().get(documentId=doc_id).execute()
print(json.dumps(document, indent=2))
```

**2. Test with public document first:**

Use a test doc that's "Anyone with link can edit"

**3. Enable API logging:**

```python
import logging

logging.basicConfig(level=logging.DEBUG)
```

---

## Summary

**Key Takeaways:**

✅ **Two APIs**: Docs API (content) + Drive API (comments)
✅ **Authentication**: Service account recommended for backend
✅ **Comments**: Use Drive API, not Docs API
✅ **Anchoring**: Unreliable – use unanchored with section references
✅ **Rate limits**: 300 req/min (Docs), 1000 req/100s (Drive)
✅ **Scopes**: Request minimum needed permissions

**For ConsensusTracker:**
- Use **service account** authentication
- Request user to share doc during onboarding
- Add **unanchored comments** with explicit section references
- Include paper citation + suggested update in comment text
- Handle errors gracefully (403, 404)
- Implement rate limiting for batch operations

**Next Steps:**
1. Create service account and download credentials
2. Test reading a sample Google Doc
3. Test adding an unanchored comment
4. Build comment formatting template
5. Integrate with your backend

Good luck! 📄✨
