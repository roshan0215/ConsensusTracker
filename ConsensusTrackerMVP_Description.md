# ConsensusTracker - Complete MVP Specification

## 🎯 One-Sentence Pitch

**AI agent that monitors your research topic 24/7, detects contradictions in new papers, and automatically suggests updates to your Google Doc literature review.**

---

## 📋 Core Features (MVP)

### What We're Building ✅

- User uploads literature review (Google Doc link or file)
- AI extracts research topic & keywords
- User reviews/edits the extracted profile
- User specifies when review was last updated
- Optional one-time backfill scan for missed papers
- Daily automatic monitoring of PubMed
- AI detects contradictions with user's work
- Adds suggestions as Google Doc comments
- Sends email alerts to user
- Dashboard showing activity & settings

### What We're NOT Building (Post-MVP) ❌

- Multiple document types (just Google Docs for MVP)
- Team collaboration features
- Slack/Discord integration (email only)
- Multiple database sources (just PubMed for MVP)
- Mobile app (web only)
- Payment processing (all free for hackathon)

---

## 🏗️ Technical Architecture

### Stack Overview

```
┌─────────────────────────────────────────────┐
│              USER'S BROWSER                  │
│  (Next.js/React Frontend)                   │
└────────────┬────────────────────────────────┘
             │ HTTPS
             ↓
┌─────────────────────────────────────────────┐
│         BACKEND API SERVER                   │
│  (Python Flask or FastAPI)                  │
│  Hosted on: DigitalOcean App Platform       │
│                                             │
│  Routes:                                    │
│  • POST /api/onboard                        │
│  • POST /api/extract-topic                  │
│  • GET  /api/dashboard                      │
│  • POST /api/trigger-backfill               │
│  • POST /api/manual-check                   │
└────────┬─────────────┬──────────────────────┘
         │             │
         │             ↓
         │    ┌─────────────────────┐
         │    │   PostgreSQL DB     │
         │    │  (User profiles,    │
         │    │   settings, logs)   │
         │    └─────────────────────┘
         ↓
┌─────────────────────────────────────────────┐
│    DIGITALOCEAN GRADIENT AI PLATFORM        │
│         (Managed Service)                   │
│                                             │
│  Multi-Agent System:                        │
│  ├─ MONITOR AGENT (searches PubMed daily)   │
│  ├─ ANALYSIS AGENT (detects contradictions) │
│  ├─ SUGGESTION AGENT (generates updates)    │
│  └─ ROUTER AGENT (orchestrates workflow)    │
│                                             │
│  Knowledge Bases (per user):                │
│  └─ User's uploaded literature review       │
│                                             │
│  Functions (Tool Calling):                  │
│  ├─ search_pubmed(query, date_filter)       │
│  ├─ add_google_doc_comment(doc_id, text)    │
│  └─ send_email(to, subject, body)           │
└─────────────────────────────────────────────┘
```

---

## 🤖 DigitalOcean Gradient AI Implementation

### Agent Architecture

We'll use multi-agent routing with 4 specialized agents:

#### 1. MONITOR AGENT

```python
monitor_agent = gradient.create_agent(
    name="MonitorAgent",
    instructions="""
    You are a research monitoring agent.
    
    YOUR TASK:
    1. Search PubMed for papers matching user's keywords
    2. Filter papers published after user's last review date
    3. Assess relevance to user's research topic
    4. Return list of relevant papers with metadata
    
    RULES:
    - Only return papers highly relevant to the topic
    - Include DOI, title, abstract, authors, date
    - Rank by relevance score
    """,
    functions=[
        search_pubmed_function,
        fetch_paper_metadata_function
    ],
    model="claude-sonnet-4-5"  # Fast and efficient
)
```

#### 2. ANALYSIS AGENT

```python
analysis_agent = gradient.create_agent(
    name="AnalysisAgent",
    instructions="""
    You are a research analysis specialist.
    
    YOUR TASK:
    1. Read new paper abstract and findings
    2. Compare to user's literature review (in knowledge base)
    3. Identify contradictions, supporting evidence, or novel findings
    4. Provide detailed analysis with specific quotes
    
    CONTRADICTION TYPES:
    - Direct contradiction (opposite findings)
    - Methodological conflict (different approaches, different results)
    - Population differences (different cohorts)
    - Statistical significance changes
    
    OUTPUT FORMAT (JSON):
    {
      "contradiction_found": true/false,
      "type": "direct|methodological|population|statistical",
      "severity": "high|medium|low",
      "user_section": "Section 3.2",
      "user_claim": "quote from user's review",
      "new_finding": "quote from new paper",
      "explanation": "why this is a contradiction"
    }
    """,
    knowledge_base_enabled=True,  # User's lit review stored here
    model="claude-opus-4-5"  # Most capable for deep analysis
)
```

#### 3. SUGGESTION AGENT

```python
suggestion_agent = gradient.create_agent(
    name="SuggestionAgent",
    instructions="""
    You are an academic writing assistant.
    
    YOUR TASK:
    Generate a suggested update to user's literature review based on
    contradiction analysis.
    
    REQUIREMENTS:
    - Write in academic tone
    - Include proper citation (Author, Year)
    - Preserve user's original argument flow
    - Add nuance, don't delete content
    - Suggest placement in user's document
    
    OUTPUT FORMAT:
    {
      "suggested_text": "Full paragraph with citation",
      "location": "Section 3.2, after paragraph 2",
      "reasoning": "Why this update is needed",
      "citation": "Smith et al., 2025, DOI: 10.xxx"
    }
    """,
    model="claude-sonnet-4-5"
)
```

#### 4. ROUTER AGENT (Master Orchestrator)

```python
router_agent = gradient.create_agent(
    name="RouterAgent", 
    instructions="""
    You orchestrate the research monitoring workflow.
    
    WORKFLOW:
    1. Receive trigger (daily schedule or manual)
    2. Route to MonitorAgent → get new papers
    3. For each relevant paper:
       a. Route to AnalysisAgent → check for contradictions
       b. If contradiction found → Route to SuggestionAgent
       c. Compile results
    4. Return summary of findings
    
    DECISION LOGIC:
    - Skip papers with relevance score < 0.7
    - Prioritize high severity contradictions
    - Batch multiple findings per email (don't spam user)
    """,
    agent_routing_enabled=True,
    sub_agents=[monitor_agent, analysis_agent, suggestion_agent],
    model="claude-sonnet-4-5"
)
```

---

### Knowledge Base Setup

```python
def create_user_knowledge_base(user_id, lit_review_file):
    """
    Create isolated knowledge base for user's documents
    """
    
    kb = gradient.create_knowledge_base(
        name=f"user_{user_id}_literature",
        description="User's literature review and key papers"
    )
    
    # Upload user's literature review
    kb.add_document(
        file=lit_review_file,
        metadata={
            "type": "literature_review",
            "user_id": user_id,
            "uploaded_at": datetime.now()
        }
    )
    
    # Attach to analysis agent
    analysis_agent.attach_knowledge_base(kb.id)
    
    return kb.id
```

---

### Function Calling (Tool Use)

#### Function 1: Search PubMed

```python
def search_pubmed_function():
    return {
        "name": "search_pubmed",
        "description": "Search PubMed for academic papers",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query with keywords"
                },
                "date_after": {
                    "type": "string", 
                    "description": "Only papers after this date (YYYY-MM-DD)"
                },
                "max_results": {
                    "type": "integer",
                    "description": "Max papers to return (default 50)"
                }
            },
            "required": ["query"]
        },
        "implementation": search_pubmed_api
    }

def search_pubmed_api(query, date_after=None, max_results=50):
    """
    Actual implementation that gets called by agent
    """
    from Bio import Entrez
    
    Entrez.email = "consensustracker@gmail.com"
    
    # Build query
    search_term = query
    if date_after:
        search_term += f' AND ("{date_after}"[Date - Publication] : "3000"[Date - Publication])'
    
    # Search
    handle = Entrez.esearch(
        db="pubmed",
        term=search_term,
        retmax=max_results,
        sort="relevance"
    )
    
    results = Entrez.read(handle)
    paper_ids = results["IdList"]
    
    # Fetch details
    handle = Entrez.efetch(
        db="pubmed",
        id=paper_ids,
        rettype="xml"
    )
    
    papers = parse_pubmed_xml(handle)
    
    return {
        "papers": papers,
        "count": len(papers)
    }
```

#### Function 2: Add Google Doc Comment

```python
def add_google_doc_comment_function():
    return {
        "name": "add_google_doc_comment",
        "description": "Add a comment/suggestion to user's Google Doc",
        "parameters": {
            "type": "object",
            "properties": {
                "doc_id": {
                    "type": "string",
                    "description": "Google Doc ID"
                },
                "comment_text": {
                    "type": "string",
                    "description": "Comment content to add"
                },
                "location": {
                    "type": "string",
                    "description": "Where to place comment (section name)"
                }
            },
            "required": ["doc_id", "comment_text"]
        },
        "implementation": add_comment_to_google_doc
    }

def add_comment_to_google_doc(doc_id, comment_text, location=None):
    """
    Use Google Docs API to add comment
    """
    from googleapiclient.discovery import build
    from google.oauth2 import service_account
    
    creds = service_account.Credentials.from_service_account_file(
        'google_service_account.json',
        scopes=['https://www.googleapis.com/auth/documents']
    )
    
    service = build('docs', 'v1', credentials=creds)
    
    # Get document
    doc = service.documents().get(documentId=doc_id).execute()
    
    # Find location (simplified - search for section header)
    insert_index = find_section_index(doc, location) if location else len(doc['body']['content'])
    
    # Create comment using Google Docs API
    requests = [{
        'createComment': {
            'textRange': {
                'startIndex': insert_index,
                'endIndex': insert_index + 1
            },
            'comment': {
                'content': comment_text
            }
        }
    }]
    
    service.documents().batchUpdate(
        documentId=doc_id,
        body={'requests': requests}
    ).execute()
    
    return {"status": "success", "comment_added": True}
```

#### Function 3: Send Email

```python
def send_email_function():
    return {
        "name": "send_email",
        "description": "Send email notification to user",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        },
        "implementation": send_email_via_gmail
    }

def send_email_via_gmail(to, subject, body):
    """
    Send email using Gmail SMTP
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = os.getenv('GMAIL_USER')
    msg['To'] = to
    
    html_part = MIMEText(body, 'html')
    msg.attach(html_part)
    
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login(
            os.getenv('GMAIL_USER'),
            os.getenv('GMAIL_APP_PASSWORD')
        )
        smtp.send_message(msg)
    
    return {"status": "sent"}
```

---

## 💾 Database Schema

```sql
-- PostgreSQL Database

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    google_doc_id VARCHAR(255),
    google_doc_url TEXT,
    monitoring_active BOOLEAN DEFAULT TRUE
);

-- Research profiles table
CREATE TABLE research_profiles (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    topic TEXT NOT NULL,
    keywords TEXT[], -- Array of keywords
    methodology VARCHAR(100),
    review_last_updated DATE,
    review_coverage_notes TEXT,
    gradient_kb_id VARCHAR(255), -- Knowledge base ID in Gradient AI
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- Monitoring jobs table
CREATE TABLE monitoring_jobs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_type VARCHAR(50), -- 'daily', 'backfill', 'manual'
    status VARCHAR(50), -- 'pending', 'running', 'completed', 'failed'
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    papers_found INTEGER,
    contradictions_found INTEGER,
    error_message TEXT
);

-- Findings table (contradictions detected)
CREATE TABLE findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    job_id UUID REFERENCES monitoring_jobs(id),
    paper_title TEXT NOT NULL,
    paper_doi VARCHAR(255),
    paper_authors TEXT,
    paper_date DATE,
    contradiction_type VARCHAR(50), -- 'direct', 'methodological', etc.
    severity VARCHAR(20), -- 'high', 'medium', 'low'
    user_section VARCHAR(100),
    user_claim TEXT,
    new_finding TEXT,
    explanation TEXT,
    suggested_update TEXT,
    status VARCHAR(50), -- 'pending', 'accepted', 'rejected', 'ignored'
    created_at TIMESTAMP DEFAULT NOW()
);

-- Activity log
CREATE TABLE activity_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    action VARCHAR(100), -- 'onboarded', 'backfill_completed', 'finding_accepted', etc.
    details JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_findings_user_status ON findings(user_id, status);
CREATE INDEX idx_monitoring_jobs_user ON monitoring_jobs(user_id);
```

---

## 🔄 Core Workflows

### Workflow 1: User Onboarding

```python
# File: backend/routes/onboarding.py
from flask import Blueprint, request, jsonify
from gradientai import Gradient
import os

onboarding_bp = Blueprint('onboarding', __name__)

@onboarding_bp.route('/api/onboard', methods=['POST'])
def onboard_user():
    """
    Complete onboarding flow
    """
    
    # Step 1: Get user input
    data = request.json
    email = data['email']
    google_doc_url = data['google_doc_url']
    review_last_updated = data['review_last_updated']  # "2025-01"
    
    # Step 2: Download Google Doc content
    doc_content = download_google_doc(google_doc_url)
    
    # Step 3: Extract research profile using Gradient AI
    gradient = Gradient(api_key=os.getenv('DIGITALOCEAN_API_KEY'))
    
    extraction_result = gradient.agents.chat(
        agent_id=os.getenv('EXTRACTION_AGENT_ID'),
        message=f"""
        Analyze this literature review and extract:
        1. Main research topic (1 sentence)
        2. Key keywords (5-10 terms)
        3. Research methodology
        4. Key research questions
        
        Literature review:
        {doc_content}
        
        Respond in JSON format.
        """
    )
    
    profile = json.loads(extraction_result.content)
    
    # Step 4: Create user in database
    user = create_user(
        email=email,
        google_doc_url=google_doc_url
    )
    
    # Step 5: Create knowledge base in Gradient AI
    kb = gradient.knowledge_bases.create(
        name=f"user_{user.id}_literature",
        description=f"Literature review for {profile['topic']}"
    )
    
    # Upload document to knowledge base
    kb.add_document(
        content=doc_content,
        metadata={
            "type": "literature_review",
            "user_id": str(user.id)
        }
    )
    
    # Step 6: Save research profile
    save_research_profile(
        user_id=user.id,
        topic=profile['topic'],
        keywords=profile['keywords'],
        review_last_updated=review_last_updated,
        gradient_kb_id=kb.id
    )
    
    # Step 7: Offer backfill
    months_old = calculate_months_old(review_last_updated)
    
    if months_old > 1:
        # Queue backfill job
        job = create_monitoring_job(
            user_id=user.id,
            job_type='backfill',
            status='pending'
        )
        
        # Trigger async backfill
        trigger_background_job('backfill', user.id, job.id)
    
    # Step 8: Start daily monitoring
    schedule_daily_monitoring(user.id)
    
    # Step 9: Send welcome email
    send_welcome_email(
        to=email,
        topic=profile['topic'],
        backfill_pending=(months_old > 1)
    )
    
    return jsonify({
        "status": "success",
        "user_id": str(user.id),
        "profile": profile,
        "backfill_queued": months_old > 1
    })
```

---

### Workflow 2: Daily Monitoring (Automated)

```python
# File: backend/jobs/daily_monitor.py
from gradientai import Gradient
import os

def run_daily_monitoring():
    """
    Runs every day at 9 AM EST
    Triggered by cron job or DigitalOcean App Platform scheduled job
    """
    
    # Get all active users
    active_users = get_active_users()
    
    for user in active_users:
        try:
            # Create monitoring job record
            job = create_monitoring_job(
                user_id=user.id,
                job_type='daily',
                status='running'
            )
            
            # Get user's research profile
            profile = get_research_profile(user.id)
            
            # Use Router Agent to orchestrate workflow
            gradient = Gradient(api_key=os.getenv('DIGITALOCEAN_API_KEY'))
            
            result = gradient.agents.chat(
                agent_id=os.getenv('ROUTER_AGENT_ID'),
                message=f"""
                TASK: Daily monitoring for user research
                
                USER PROFILE:
                - Topic: {profile.topic}
                - Keywords: {', '.join(profile.keywords)}
                - Last review date: {profile.review_last_updated}
                - Knowledge base ID: {profile.gradient_kb_id}
                
                INSTRUCTIONS:
                1. Search PubMed for papers published in last 24 hours
                2. Filter for relevance to user's topic
                3. For each relevant paper, analyze against user's literature review
                4. Identify contradictions
                5. Generate suggestions for contradictions found
                
                Return JSON with findings.
                """,
                context={
                    "user_id": str(user.id),
                    "kb_id": profile.gradient_kb_id
                }
            )
            
            findings = json.loads(result.content)
            
            # Save findings to database
            for finding in findings.get('contradictions', []):
                save_finding(
                    user_id=user.id,
                    job_id=job.id,
                    **finding
                )
                
                # Add comment to Google Doc
                add_google_doc_comment(
                    doc_id=user.google_doc_id,
                    comment_text=format_suggestion_comment(finding),
                    location=finding.get('section')
                )
            
            # Update job status
            update_job_status(
                job.id,
                status='completed',
                papers_found=findings.get('papers_checked', 0),
                contradictions_found=len(findings.get('contradictions', []))
            )
            
            # Send email if contradictions found
            if findings.get('contradictions'):
                send_contradiction_alert_email(
                    user=user,
                    findings=findings['contradictions']
                )
            
        except Exception as e:
            # Log error
            update_job_status(job.id, status='failed', error_message=str(e))
            send_error_email(user.email, str(e))
```

---

### Workflow 3: Backfill Scan

```python
# File: backend/jobs/backfill.py
def run_backfill(user_id, job_id):
    """
    One-time scan for papers since user's last review
    Runs in background
    """
    
    user = get_user(user_id)
    profile = get_research_profile(user_id)
    
    # Calculate date range
    start_date = profile.review_last_updated
    end_date = datetime.now()
    
    # Use Monitor Agent to search
    gradient = Gradient(api_key=os.getenv('DIGITALOCEAN_API_KEY'))
    
    # Search in batches (avoid timeout)
    all_papers = []
    current_date = start_date
    
    while current_date < end_date:
        batch_end = min(current_date + timedelta(days=30), end_date)
        
        result = gradient.agents.chat(
            agent_id=os.getenv('MONITOR_AGENT_ID'),
            message=f"""
            Search PubMed for papers on: {profile.topic}
            Keywords: {', '.join(profile.keywords)}
            Date range: {current_date} to {batch_end}
            Max results: 50
            
            Return relevant papers only.
            """
        )
        
        papers = json.loads(result.content).get('papers', [])
        all_papers.extend(papers)
        
        current_date = batch_end
    
    # Analyze each paper
    contradictions = []
    
    for paper in all_papers:
        # Use Analysis Agent
        analysis = gradient.agents.chat(
            agent_id=os.getenv('ANALYSIS_AGENT_ID'),
            message=f"""
            Analyze this paper against user's literature review.
            
            Paper:
            Title: {paper['title']}
            Abstract: {paper['abstract']}
            Date: {paper['date']}
            
            Knowledge base: {profile.gradient_kb_id}
            
            Find contradictions and return JSON.
            """
        )
        
        result = json.loads(analysis.content)
        
        if result.get('contradiction_found'):
            contradictions.append({
                **paper,
                **result
            })
    
    # Save findings
    for finding in contradictions:
        save_finding(user_id=user_id, job_id=job_id, **finding)
        add_google_doc_comment(
            doc_id=user.google_doc_id,
            comment_text=format_suggestion_comment(finding)
        )
    
    # Update job
    update_job_status(
        job_id,
        status='completed',
        papers_found=len(all_papers),
        contradictions_found=len(contradictions)
    )
    
    # Send summary email
    send_backfill_complete_email(
        user=user,
        total_papers=len(all_papers),
        contradictions=contradictions
    )
```

---

## 🎨 Frontend (Simplified)

```javascript
// File: frontend/pages/onboarding.jsx
import { useState } from 'react';

export default function Onboarding() {
  const [step, setStep] = useState(1);
  const [formData, setFormData] = useState({
    email: '',
    googleDocUrl: '',
    reviewLastUpdated: '',
  });
  const [aiProfile, setAiProfile] = useState(null);

  const handleUpload = async () => {
    // Call backend to extract profile
    const response = await fetch('/api/extract-topic', {
      method: 'POST',
      body: JSON.stringify({
        google_doc_url: formData.googleDocUrl
      })
    });
    
    const profile = await response.json();
    setAiProfile(profile);
    setStep(2);
  };

  const handleConfirm = async () => {
    // Finalize onboarding
    await fetch('/api/onboard', {
      method: 'POST',
      body: JSON.stringify({
        ...formData,
        profile: aiProfile
      })
    });
    
    window.location.href = '/dashboard';
  };

  return (
    <div className="max-w-2xl mx-auto p-8">
      {step === 1 && (
        <div>
          <h1>Upload Your Literature Review</h1>
          
          <input
            type="email"
            placeholder="Your email"
            value={formData.email}
            onChange={(e) => setFormData({...formData, email: e.target.value})}
          />
          
          <input
            type="url"
            placeholder="Google Doc URL"
            value={formData.googleDocUrl}
            onChange={(e) => setFormData({...formData, googleDocUrl: e.target.value})}
          />
          
          <select
            value={formData.reviewLastUpdated}
            onChange={(e) => setFormData({...formData, reviewLastUpdated: e.target.value})}
          >
            <option>When was this last updated?</option>
            <option value="2025-02">February 2025</option>
            <option value="2025-01">January 2025</option>
            <option value="2024-12">December 2024</option>
          </select>
          
          <button onClick={handleUpload}>
            Analyze My Review
          </button>
        </div>
      )}
      
      {step === 2 && aiProfile && (
        <div>
          <h2>Review AI's Understanding</h2>
          
          <div>
            <label>Research Topic:</label>
            <input
              value={aiProfile.topic}
              onChange={(e) => setAiProfile({...aiProfile, topic: e.target.value})}
            />
          </div>
          
          <div>
            <label>Keywords:</label>
            {aiProfile.keywords.map((kw, i) => (
              <div key={i}>
                <input value={kw} />
                <button>Remove</button>
              </div>
            ))}
          </div>
          
          <button onClick={handleConfirm}>
            Start Monitoring!
          </button>
        </div>
      )}
    </div>
  );
}
```

---

## 🚀 Deployment Plan

### Services to Deploy

1. **Backend API**
   - Platform: DigitalOcean App Platform
   - Framework: Python Flask/FastAPI
   - Auto-deploys from GitHub

2. **Frontend**
   - Platform: DigitalOcean App Platform (static site)
   - Framework: Next.js build
   - Or Vercel (free tier)

3. **Database**
   - DigitalOcean Managed PostgreSQL
   - $15/month (or use free tier initially)

4. **Cron Jobs** (Daily Monitoring)
   - DigitalOcean App Platform scheduled jobs
   - Or GitHub Actions (free)

5. **Gradient AI Agents**
   - Already managed by DigitalOcean
   - Pay-per-use from $200 credits

---

## 💰 Cost Estimate (MVP)

### DigitalOcean Services

- App Platform (Backend): **$5/month** (Basic)
- PostgreSQL Database: **$15/month** (or $0 with free tier initially)
- Static Site (Frontend): **$0** (can use Vercel free)
- **Total Infrastructure: ~$20/month**

### Gradient AI (From $200 credits)

- Onboarding (per user): ~$0.50
- Daily monitoring (per user): ~$0.05/day
- 20 demo users × 30 days: ~$40
- **Well within $200 budget ✅**

### External APIs

- PubMed: **Free**
- Google Docs API: **Free** (quotas sufficient)
- Gmail SMTP: **Free**
- **Total: $0**

### **TOTAL FOR HACKATHON: ~$20 + usage from credits**

---

## 📅 Development Timeline (Pre-Hackathon)

### Week 1: Setup & Core Infrastructure

- **Day 1-2**: Setup DigitalOcean accounts, Gradient AI
- **Day 3-4**: Create agent architecture
- **Day 5-7**: Build database schema, basic backend

### Week 2: Core Features

- **Day 8-10**: Onboarding flow
- **Day 11-12**: Daily monitoring logic
- **Day 13-14**: Google Docs integration

### Week 3: Polish & Demo

- **Day 15-17**: Frontend dashboard
- **Day 18-19**: Email templates
- **Day 20-21**: Demo video, testing

### During Hackathon (35 days)

- Submit project
- Gather user feedback
- Fix bugs
- Improve demo

---

## 🎬 Demo Script (3 Minutes)

**0:00-0:30 → THE PROBLEM**
> "I'm Dr. Sarah, cancer researcher. I wrote this lit review in January. It's now March. I have NO IDEA if my conclusions are still valid. Manually checking would take 20+ hours."

**0:30-1:00 → THE SOLUTION**
> "Meet ConsensusTracker. I upload my review, tell it when I last updated it. AI extracts my research topic."

**1:00-1:30 → THE MAGIC**
> [Screen recording]
> "It scans PubMed... Found 3 new papers. One contradicts my Section 3! Look - it's already added a suggestion to my Google Doc."

**1:30-2:00 → THE RESULT**
> [Show Google Doc with comment]
> "Here's the contradiction, with full citation and reasoning. I click 'Accept' and my review updates automatically."

**2:00-2:30 → THE VALUE**
> "This runs DAILY. Every morning, it checks for new papers, finds contradictions, updates my doc. I saved 20 hours and my research stays current."

**2:30-3:00 → CLOSING**
> "ConsensusTracker: Your literature review, but it updates itself. Built with DigitalOcean Gradient AI. Try it at consensustracker.com"

---

## ✅ MVP Checklist

### Backend ✓
- [ ] User registration & authentication
- [ ] Google Doc upload/linking
- [ ] AI topic extraction
- [ ] Knowledge base creation
- [ ] Daily monitoring cron
- [ ] Backfill scan
- [ ] Email notifications
- [ ] Dashboard API

### Gradient AI ✓
- [ ] 4 agents created (Monitor, Analysis, Suggestion, Router)
- [ ] Knowledge base per user
- [ ] Function calling (PubMed, Google Docs, Email)
- [ ] Multi-agent routing

### Frontend ✓
- [ ] Onboarding flow
- [ ] Dashboard (view findings)
- [ ] Settings page
- [ ] Privacy policy

### Testing ✓
- [ ] End-to-end onboarding
- [ ] Daily monitoring job
- [ ] Google Docs commenting
- [ ] Email delivery

### Documentation ✓
- [ ] README with setup instructions
- [ ] Demo video
- [ ] Privacy policy
- [ ] Open source license

---

## 🔐 Environment Variables

```bash
# .env file (NEVER commit to GitHub)

# DigitalOcean Gradient AI
DIGITALOCEAN_API_KEY=dop_v1_xxxxxxxxxxxxx
ROUTER_AGENT_ID=agent_xxxxx
MONITOR_AGENT_ID=agent_xxxxx
ANALYSIS_AGENT_ID=agent_xxxxx
SUGGESTION_AGENT_ID=agent_xxxxx

# Database
DATABASE_URL=postgresql://user:pass@host:5432/consensustracker

# Email
GMAIL_USER=consensustracker@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx

# Google Docs API
GOOGLE_SERVICE_ACCOUNT_JSON=path/to/service-account.json

# App
SECRET_KEY=your-secret-key-here
FRONTEND_URL=https://consensustracker.com
```

---

## 📦 File Structure

```
consensustracker/
├── backend/
│   ├── app.py                 # Flask/FastAPI main
│   ├── routes/
│   │   ├── onboarding.py
│   │   ├── dashboard.py
│   │   └── monitoring.py
│   ├── jobs/
│   │   ├── daily_monitor.py
│   │   └── backfill.py
│   ├── services/
│   │   ├── gradient_ai.py     # Gradient AI wrapper
│   │   ├── google_docs.py
│   │   ├── pubmed.py
│   │   └── email.py
│   ├── models/
│   │   └── database.py        # SQLAlchemy models
│   └── requirements.txt
│
├── frontend/
│   ├── pages/
│   │   ├── index.jsx
│   │   ├── onboarding.jsx
│   │   └── dashboard.jsx
│   ├── components/
│   │   ├── Header.jsx
│   │   └── FindingCard.jsx
│   └── package.json
│
├── scripts/
│   ├── setup_agents.py        # Create Gradient AI agents
│   ├── init_db.py             # Initialize database
│   └── seed_demo_data.py
│
├── .env.example
├── .gitignore
├── README.md
└── docker-compose.yml
```

---

## 🎯 Success Metrics

**MVP is successful if:**

- ✅ Users can upload their Google Doc
- ✅ AI correctly extracts research topic
- ✅ Daily monitoring finds new papers
- ✅ Contradictions are detected accurately
- ✅ Comments appear in Google Doc
- ✅ Email notifications are sent
- ✅ Dashboard shows activity

**Stretch Goals:**

- 🎯 10+ demo users during hackathon
- 🎯 95%+ accuracy in contradiction detection
- 🎯 <30 second onboarding time
- 🎯 Professional demo video

---

## 📝 License

MIT License - Open Source

---

**Built with ❤️ for researchers who deserve tools that actually help.**
