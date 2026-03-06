# ConsensusTracker

**AI-powered research monitoring that watches PubMed 24/7, detects when new papers contradict or extend your literature review, and suggests updates directly in your Google Doc.**

---

## What it does

1. You link a Google Doc containing your literature review
2. The AI reads it and extracts your research topic and keywords
3. Every day (or on demand), it searches PubMed for new papers on your topic
4. An AI agent compares each paper against your existing claims and flags:
   - **Contradictions** — new evidence that conflicts with something you wrote
   - **Additions** — new evidence that fills a gap in your review
   - **Confirmations** — new evidence that supports your existing claims
5. Findings are posted as comments directly in your Google Doc, with author info and DOI links
6. You can optionally generate a full AI revision draft written into a separate tab in the same doc

---

## Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 18, Tailwind CSS 3 |
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| AI agents | DigitalOcean Gradient AI (managed LLM agents + knowledge bases) |
| Paper search | NCBI PubMed E-utilities API |
| Document integration | Google Docs API (service account) |
| Email alerts | Gmail SMTP |
| Auth | Magic-link email login |

---

## Project structure

```
ConsensusTracker/
├── backend/
│   ├── core/           # Config, settings
│   ├── db/             # SQLAlchemy models, session, migrations
│   ├── jobs/           # Background monitoring job runner
│   ├── routes/         # FastAPI route handlers (auth, projects, monitoring, etc.)
│   ├── schemas/        # Pydantic request/response schemas
│   └── services/       # PubMed, Google Docs, Gradient AI, email
├── frontend/
│   ├── components/     # Layout, Nav
│   ├── lib/            # API fetch helper
│   ├── pages/          # Next.js pages (index, projects, project, signin, register)
│   └── styles/         # Tailwind globals + design tokens
├── scripts/
│   └── init_db.py      # Database initialisation script
├── docker-compose.yml
└── .env.example
```

---

## Local setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- A Google Cloud service account with the Google Docs API enabled
- A DigitalOcean account with Gradient AI agents provisioned
- An NCBI account (free) for PubMed API access

### 1. Clone and create environment files

```bash
git clone <repo-url>
cd ConsensusTracker
cp .env.example .env
```

Fill in `.env` — see the [Environment variables](#environment-variables) section below.

### 2. Backend

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS/Linux
source .venv/bin/activate

pip install -r backend/requirements.txt
python scripts/init_db.py        # creates tables
uvicorn backend.main:app --reload --port 8000
```

### 3. Frontend

```bash
cd frontend
npm install
npm run dev                      # http://localhost:3000
```

---

## Environment variables

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Random secret for signing auth tokens |
| `DATABASE_URL` | PostgreSQL connection string |
| `CORS_ALLOW_ORIGINS` | Comma-separated allowed origins (e.g. `http://localhost:3000`) |
| `NCBI_EMAIL` | Your email address, required by NCBI for API access |
| `NCBI_API_KEY` | Optional — increases PubMed rate limits |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full JSON string of the service account credentials |
| `GMAIL_USER` | Gmail address for sending alert emails |
| `GMAIL_APP_PASSWORD` | Gmail app password (not your account password) |
| `DIGITALOCEAN_API_TOKEN` | DigitalOcean API token for Gradient AI management |
| `DIGITALOCEAN_PROJECT_ID` | DigitalOcean project to create knowledge bases under |
| `EXTRACTION_AGENT_ENDPOINT` | Chat endpoint URL for the extraction agent |
| `EXTRACTION_AGENT_ACCESS_KEY` | Access key for the extraction agent |
| `ROUTER_AGENT_ENDPOINT` | Chat endpoint URL for the monitoring/router agent |
| `ROUTER_AGENT_ACCESS_KEY` | Access key for the monitoring agent |
| `ROUTER_AGENT_UUID` | UUID of the router agent (for attaching knowledge bases) |
| `ANALYSIS_AGENT_UUID` | UUID of the analysis agent |
| `CRON_TOKEN` | Bearer token required to hit the `/api/cron/daily-run` endpoint |
| `NEXT_PUBLIC_API_BASE_URL` | Backend URL as seen by the browser (e.g. `http://localhost:8000`) |

### Google service account setup

1. Create a service account in Google Cloud Console with the **Google Docs API** enabled
2. Download the JSON key file
3. Set `GOOGLE_SERVICE_ACCOUNT_JSON` to the full contents of that file (as a single-line JSON string)
4. When linking a Google Doc in the app, share it with the service account email address shown in the UI

---

## Key API endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/auth/magic-link` | Send magic login link |
| `GET` | `/api/projects` | List user's projects |
| `POST` | `/api/projects` | Create a project |
| `GET` | `/api/projects/{id}` | Get project detail + findings |
| `POST` | `/api/projects/{id}/link-google-doc` | Link doc, extract profile, create KB |
| `POST` | `/api/projects/{id}/run-check` | Trigger a manual monitoring run |
| `PATCH` | `/api/projects/{id}/findings/{fid}` | Update finding status (resolved/dismissed/pending) |
| `POST` | `/api/projects/{id}/generate-ai-revision` | Generate AI revision draft into Google Doc |
| `GET` | `/api/projects/service-account-email` | Return the service account email to share docs with |
| `GET` | `/api/cron/daily-run` | Daily cron trigger (requires `CRON_TOKEN`) |
| `GET` | `/api/stats` | Public stats (researcher count, findings, etc.) |

---

## Running daily monitoring in production

The daily job is triggered by a GET request to `/api/cron/daily-run` with the header `Authorization: Bearer <CRON_TOKEN>`. Set this up as a cron job on your server or use a service like [cron-job.org](https://cron-job.org) to hit the endpoint once a day.

---

## Docker (optional)

A `docker-compose.yml` is provided that starts a local PostgreSQL instance:

```bash
docker-compose up -d    # starts postgres on port 5432
python scripts/init_db.py
```

Then run the backend and frontend as described above.
