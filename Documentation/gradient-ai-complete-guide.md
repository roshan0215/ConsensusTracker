# DigitalOcean Gradient AI Platform - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Core Concepts](#core-concepts)
3. [Authentication & Setup](#authentication--setup)
4. [Creating Agents](#creating-agents)
5. [Knowledge Bases](#knowledge-bases)
6. [Function Calling (Tool Use)](#function-calling-tool-use)
7. [Multi-Agent Routing](#multi-agent-routing)
8. [Agent Development Kit (ADK)](#agent-development-kit-adk)
9. [Best Practices](#best-practices)
10. [Code Examples](#code-examples)
11. [Troubleshooting](#troubleshooting)

---

## Overview

**What is DigitalOcean Gradient AI Platform?**

A fully-managed platform for building production-ready AI agents with:
- **Knowledge Bases** for RAG (Retrieval-Augmented Generation)
- **Multi-agent routing** for complex workflows
- **Function calling** to connect external APIs and data
- **Serverless inference** from OpenAI, Anthropic, Meta models
- **Built-in observability** (traces, logs, evaluations)

**Key Value Proposition:**
- No infrastructure management
- Single API key for all models
- Pay-per-use pricing
- Production-grade observability out of the box

---

## Core Concepts

### 1. Agents
An **agent** is a stateful AI application powered by an LLM with:
- Custom instructions (system prompt)
- Access to knowledge bases (your data)
- Ability to call functions (external tools/APIs)
- Conversational memory
- Routing to other agents

Think of agents as AI workers with specific roles and expertise.

### 2. Knowledge Bases
A **knowledge base** is a vector database containing your documents:
- PDFs, text files, web pages
- Automatically chunked and embedded
- Retrieved via semantic search (RAG)
- Can be attached to multiple agents

### 3. Agent Routes
**Agent routing** lets one agent delegate work to specialized sub-agents:
- Parent agent → Router/orchestrator
- Child agents → Domain experts
- Automatic routing based on user intent

### 4. Function Routes
**Function calling** (tool use) lets agents interact with external systems:
- Call APIs for real-time data
- Execute code
- Trigger workflows
- Query databases

### 5. Workspaces
**Workspaces** are organizational units for grouping related agents and resources.

---

## Authentication & Setup

### Step 1: Get API Credentials

1. **Create DigitalOcean Account**: Sign up at digitalocean.com
2. **Enable Gradient AI Platform**: Navigate to GenAI Platform in console
3. **Generate API Token**:
   - Go to API → Tokens
   - Click "Generate New Token"
   - Name: `consensustracker-token`
   - Scopes: Read + Write
   - Copy token immediately (won't be shown again)

### Step 2: Set Environment Variables

```bash
# ~/.bashrc or ~/.zshrc
export DIGITALOCEAN_API_TOKEN="dop_v1_xxxxxxxxxxxxxxxxxxxxx"
export DIGITALOCEAN_API_KEY="$DIGITALOCEAN_API_TOKEN"  # Alias for convenience
```

### Step 3: Verify Access

```bash
# Using curl
curl -X GET \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/models"
  
# Should return JSON with available models
```

### Step 4: Install Python SDK (Optional)

```bash
pip install digitalocean-gradient
```

**Note**: As of February 2025, DigitalOcean provides REST API access. The Python SDK is evolving. Check docs for latest info.

---

## Creating Agents

### Method 1: Using the Control Panel (Web UI)

**Best for:** Quick prototyping, testing instructions

1. Navigate to **GenAI Platform** → **Agents**
2. Click **Create Agent**
3. Choose **Custom Configuration** or **Template**
4. Fill in:
   - **Name**: `MonitorAgent`
   - **Instructions**: Your system prompt (see example below)
   - **Model**: `claude-sonnet-4-5` (fast, efficient)
   - **Workspace**: Select or create new
5. Optionally attach **Knowledge Base**
6. Click **Create Agent**

**Example Instructions:**
```
You are a research monitoring agent specializing in PubMed searches.

YOUR TASK:
- Search PubMed for papers matching user's keywords
- Filter papers published after a specific date
- Assess relevance to user's research topic (0-1 score)
- Return list of relevant papers with metadata

RULES:
- Only return papers highly relevant (score > 0.7)
- Include: DOI, title, abstract, authors, publication date
- Rank by relevance score (highest first)
- Skip review articles unless specifically requested

OUTPUT FORMAT:
Return JSON array:
[
  {
    "pmid": "12345678",
    "doi": "10.xxxx/xxxx",
    "title": "Paper title",
    "authors": ["Smith J", "Jones A"],
    "date": "2025-01-15",
    "abstract": "...",
    "relevance_score": 0.92
  }
]
```

---

### Method 2: Using the API

**Best for:** Automation, scripts, CI/CD

**Endpoint:** `POST /v2/gen-ai/agents`

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents" \
  -d '{
    "name": "MonitorAgent",
    "model": "claude-sonnet-4-5",
    "instructions": "You are a research monitoring agent...",
    "workspace_name": "consensustracker",
    "region": "tor1",
    "project_id": "your-project-uuid"
  }'
```

**Response:**
```json
{
  "agent": {
    "uuid": "1b418231-b7d6-11ef-bf8f-4e013e2ddde4",
    "name": "MonitorAgent",
    "endpoint": "https://agent-xyz.ondigitalocean.app",
    "access_key": "ak_xxxxxxxxxxxxx",
    "status": "active"
  }
}
```

**Save these values:**
- `uuid`: Agent ID for future API calls
- `endpoint`: URL to send chat requests
- `access_key`: Bearer token for endpoint authentication

---

### Method 3: Using Agent Development Kit (Python SDK)

**Best for:** Complex agents, local development

```python
# Install ADK
# pip install gradient-adk

from gradient_adk import Agent

# Define agent
@Agent(
    name="MonitorAgent",
    model="claude-sonnet-4-5",
    instructions="""
    You are a research monitoring agent specializing in PubMed searches.
    
    YOUR TASK:
    - Search PubMed for papers matching user's keywords
    - Filter papers published after a specific date
    - Assess relevance to user's research topic
    """
)
async def monitor_agent(input: dict):
    # Your agent logic here
    query = input.get("query")
    date_after = input.get("date_after")
    
    # Call search_pubmed function
    results = await search_pubmed(query, date_after)
    
    return {"papers": results}

# Deploy to DigitalOcean
# gradient agent deploy
```

---

## Knowledge Bases

### What is a Knowledge Base?

A knowledge base provides your agent with domain-specific context through RAG:
- **Stores** your documents (PDFs, text, web pages)
- **Chunks** them into retrievable segments
- **Embeds** chunks into vector space
- **Retrieves** relevant chunks when agent processes queries

### Creating a Knowledge Base

#### Via Control Panel:

1. **GenAI Platform** → **Knowledge Bases** → **Create Knowledge Base**
2. **Name**: `user_literature_reviews`
3. **Description**: `User-uploaded literature reviews for contradiction detection`
4. **Embedding Model**: `text-embedding-3-large` (OpenAI) - best quality
5. **Region**: `tor1` (same as agents for low latency)
6. **Database**: Create new OpenSearch cluster OR use existing
   - Size: ~2x your data size (for embeddings overhead)
   - Minimum: 1GB for small datasets
7. **Add Data Sources**:
   - **Upload Files**: PDFs, .txt, .docx
   - **Spaces Bucket**: Link to DigitalOcean Spaces folder
   - **Web Crawler**: Provide seed URLs
8. **Chunking Strategy** (important!):
   - **Section-based**: Best for structured docs (default)
   - **Fixed-size**: For unstructured text
   - **Hierarchical**: For complex documents with nested structure
9. **Enable Auto-Indexing** (optional): Re-index when sources update
10. Click **Create Knowledge Base**

#### Via API:

```bash
# Step 1: Create knowledge base
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/knowledge_bases" \
  -d '{
    "name": "user_123_literature",
    "description": "Literature review for user 123",
    "embedding_model": "text-embedding-3-large",
    "region": "tor1",
    "project_id": "your-project-uuid"
  }'

# Response includes: knowledge_base_uuid

# Step 2: Add data source (upload file)
curl -X POST \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  -F "file=@literature_review.pdf" \
  "https://api.digitalocean.com/v2/gen-ai/knowledge_bases/{kb_uuid}/data_sources"

# Step 3: Trigger indexing
curl -X POST \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/knowledge_bases/{kb_uuid}/index"
```

---

### Attaching Knowledge Base to Agent

#### Via Control Panel:

1. Navigate to your agent → **Resources** tab
2. Scroll to **Knowledge Bases** section
3. Click **Add Knowledge Bases**
4. Select knowledge base from dropdown
5. Click **Add**

*Note: Agent will redeploy automatically (takes ~30 seconds)*

#### Via API:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}/knowledge_bases" \
  -d '{
    "knowledge_base_uuids": [
      "kb-uuid-1",
      "kb-uuid-2"
    ]
  }'
```

**Multiple KBs:** You can attach multiple knowledge bases to one agent!

---

### Chunking Strategies (Advanced)

**Why chunking matters:** Large documents must be split for effective retrieval.

**Available Strategies:**

1. **Section-based** (default):
   - Splits on document structure (headings, paragraphs)
   - Best for: PDFs with clear sections, academic papers
   - Pros: Preserves logical units
   - Cons: Variable chunk sizes

2. **Fixed-size**:
   - Splits every N tokens (e.g., 512 tokens)
   - Best for: Unstructured text, novels, transcripts
   - Pros: Predictable sizes, fast
   - Cons: May split mid-sentence

3. **Hierarchical**:
   - Creates parent-child relationships
   - Retrieves small chunks + broader context
   - Best for: Complex documents with nested structure
   - Pros: Best context preservation
   - Cons: More storage, slower indexing

**How to configure:**

```bash
curl -X PATCH \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/knowledge_bases/{kb_uuid}/data_sources/{ds_uuid}" \
  -d '{
    "chunking_strategy": "section",
    "chunk_size": 1000,
    "chunk_overlap": 200
  }'
```

---

## Function Calling (Tool Use)

### Overview

**Function calling** lets your agent execute code and interact with external systems.

**Use cases:**
- Search PubMed for papers
- Add comments to Google Docs
- Send emails
- Query databases
- Call APIs (weather, stock prices, CRM data)

**How it works:**
1. Agent receives user request
2. Agent decides it needs external data/action
3. Agent calls function with structured parameters
4. Your code executes function
5. Result returns to agent
6. Agent uses result in response

---

### Creating Functions

Functions can be:
- **DigitalOcean Functions** (serverless, Python/Node.js)
- **External APIs** (any HTTP endpoint)
- **Custom serverless functions** (AWS Lambda, Vercel, etc.)

#### Option 1: DigitalOcean Functions (Recommended)

**Example: PubMed Search Function**

```python
# File: packages/pubmed-search/search/__main__.py

from Bio import Entrez
import json
import os

def main(args):
    """
    Search PubMed for papers.
    
    Expected input:
    {
      "query": "cancer immunotherapy",
      "date_after": "2025/01/01",
      "max_results": 50
    }
    """
    
    # Set Entrez email
    Entrez.email = os.getenv("ENTREZ_EMAIL", "consensustracker@gmail.com")
    
    # Extract parameters
    query = args.get("query", "")
    date_after = args.get("date_after")
    max_results = args.get("max_results", 50)
    
    # Build search term
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
    search_results = Entrez.read(handle)
    pmids = search_results["IdList"]
    
    # Fetch details
    if not pmids:
        return {"papers": []}
    
    handle = Entrez.efetch(
        db="pubmed",
        id=",".join(pmids),
        rettype="xml",
        retmode="xml"
    )
    papers_xml = Entrez.read(handle)
    
    # Parse papers
    papers = []
    for paper in papers_xml["PubmedArticle"]:
        article = paper["MedlineCitation"]["Article"]
        
        # Extract abstract
        abstract = ""
        if "Abstract" in article:
            abstract_parts = article["Abstract"]["AbstractText"]
            if isinstance(abstract_parts, list):
                abstract = " ".join([str(p) for p in abstract_parts])
            else:
                abstract = str(abstract_parts)
        
        # Extract authors
        authors = []
        if "AuthorList" in article:
            for author in article["AuthorList"]:
                last = author.get("LastName", "")
                first = author.get("ForeName", "")
                authors.append(f"{first} {last}".strip())
        
        # Extract DOI
        doi = ""
        if "ELocationID" in article:
            for eloc in article["ELocationID"]:
                if eloc.attributes.get("EIdType") == "doi":
                    doi = str(eloc)
        
        # Extract date
        pub_date = paper["MedlineCitation"]["Article"]["Journal"]["JournalIssue"]["PubDate"]
        date_str = f"{pub_date.get('Year', '')}-{pub_date.get('Month', '01')}-{pub_date.get('Day', '01')}"
        
        papers.append({
            "pmid": str(paper["MedlineCitation"]["PMID"]),
            "doi": doi,
            "title": str(article["ArticleTitle"]),
            "authors": authors,
            "date": date_str,
            "abstract": abstract
        })
    
    return {
        "papers": papers,
        "count": len(papers)
    }
```

**Deploy:**
```bash
# Create function namespace
doctl serverless namespaces create consensustracker-functions

# Deploy function
doctl serverless deploy ./packages --remote-build
```

**Get function endpoint:**
```bash
doctl serverless functions get pubmed-search/search --url
# Returns: https://faas-tor1-xxxxx.doserverless.co/api/v1/web/fn-xxxxx/pubmed-search/search
```

---

### Connecting Function to Agent

#### Via Control Panel:

1. Agent → **Resources** → **Function Routes**
2. Click **Add Function Route**
3. Fill in:
   - **Route Name**: `search_pubmed`
   - **Function Name**: `search`
   - **Namespace**: `fn-xxxxx` (from function settings)
   - **Instructions**: When to call this function
     ```
     Call this function when you need to search PubMed for scientific papers.
     Use when user asks about recent research, new studies, or literature on a topic.
     ```
   - **Input Schema** (JSON):
     ```json
     {
       "query": {
         "type": "string",
         "description": "Search query (keywords, topics, MeSH terms)",
         "required": true
       },
       "date_after": {
         "type": "string",
         "description": "Only papers after this date (YYYY/MM/DD format)",
         "required": false
       },
       "max_results": {
         "type": "integer",
         "description": "Maximum papers to return (default 50)",
         "required": false
       }
     }
     ```
   - **Output Schema** (JSON):
     ```json
     {
       "papers": {
         "type": "array",
         "description": "List of papers with metadata"
       },
       "count": {
         "type": "integer",
         "description": "Number of papers found"
       }
     }
     ```
4. Click **Add Function Route**

#### Via API:

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/{agent_uuid}/functions" \
  -d '{
    "function_name": "search_pubmed",
    "description": "Search PubMed for scientific papers",
    "faas_namespace": "fn-2014dc98-faa1-45f4-ba1f-59910cb3d399",
    "faas_name": "pubmed-search/search",
    "input_schema": {
      "query": {
        "type": "string",
        "description": "Search query",
        "required": true
      },
      "date_after": {
        "type": "string",
        "description": "YYYY/MM/DD",
        "required": false
      }
    },
    "output_schema": {
      "papers": {
        "type": "array",
        "description": "List of papers"
      }
    }
  }'
```

---

### Testing Function Calling

**Agent Playground:**

1. Navigate to agent in control panel
2. Open **Playground** tab
3. Type: "Search PubMed for papers on CRISPR published after January 2025"
4. Watch in **Traces** tab:
   - Agent decides to call `search_pubmed`
   - Function executes
   - Results return
   - Agent synthesizes answer

**Via API:**

```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $AGENT_ACCESS_KEY" \
  "$AGENT_ENDPOINT/api/v1/chat/completions" \
  -d '{
    "messages": [
      {
        "role": "user",
        "content": "Find papers on CRISPR from 2025"
      }
    ],
    "include_functions_info": true
  }'
```

**Response:**
```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "I found 23 papers on CRISPR from 2025..."
    }
  }],
  "functions": {
    "called_functions": ["search_pubmed"]
  }
}
```

---

## Multi-Agent Routing

### Concept

**Multi-agent routing** = One orchestrator delegates to specialized agents.

**Example: Research Monitoring System**

```
RouterAgent (orchestrator)
├─ MonitorAgent (searches PubMed)
├─ AnalysisAgent (detects contradictions)
└─ SuggestionAgent (generates updates)
```

**Workflow:**
1. User query → RouterAgent
2. RouterAgent analyzes intent
3. Routes to appropriate sub-agent
4. Sub-agent processes and returns
5. RouterAgent synthesizes final response

---

### Creating Multi-Agent System

**Step 1: Create Sub-Agents**

Create 3 agents (as shown in "Creating Agents" section):
- `MonitorAgent`
- `AnalysisAgent`
- `SuggestionAgent`

**Step 2: Create Router Agent**

```
Name: RouterAgent
Model: claude-sonnet-4-5
Instructions:
---
You orchestrate a research monitoring workflow.

AVAILABLE SUB-AGENTS:
1. MonitorAgent - Searches PubMed for new papers
2. AnalysisAgent - Analyzes papers for contradictions with user's work
3. SuggestionAgent - Generates suggested updates

WORKFLOW:
When user requests monitoring:
1. Route to MonitorAgent → get new papers
2. For each relevant paper:
   - Route to AnalysisAgent → check contradictions
   - If contradiction found → Route to SuggestionAgent
3. Compile results into summary

ROUTING LOGIC:
- "Search for papers..." → MonitorAgent
- "Analyze this paper..." → AnalysisAgent
- "Suggest an update..." → SuggestionAgent
- Complex workflow → Use all agents in sequence
---
```

**Step 3: Add Agent Routes**

#### Via Control Panel:

1. RouterAgent → **Resources** → **Agent Routes**
2. Click **Add Agent Route** (repeat for each sub-agent)
3. **Route to MonitorAgent:**
   - Route Name: `route_to_monitor`
   - Child Agent: `MonitorAgent`
   - If Case: `When user asks to search PubMed or find new papers on a topic`
4. **Route to AnalysisAgent:**
   - Route Name: `route_to_analysis`
   - Child Agent: `AnalysisAgent`
   - If Case: `When analyzing a paper for contradictions with user's literature review`
5. **Route to SuggestionAgent:**
   - Route Name: `route_to_suggestion`
   - Child Agent: `SuggestionAgent`
   - If Case: `When generating suggested text to update user's document`

#### Via API:

```bash
# Add MonitorAgent route
curl -X POST \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $DIGITALOCEAN_API_TOKEN" \
  "https://api.digitalocean.com/v2/gen-ai/agents/{router_uuid}/child_agents/{monitor_uuid}" \
  -d '{
    "parent_agent_uuid": "{router_uuid}",
    "child_agent_uuid": "{monitor_uuid}",
    "route_name": "route_to_monitor",
    "if_case": "When user asks to search PubMed or find new papers"
  }'

# Repeat for AnalysisAgent and SuggestionAgent
```

---

### Testing Multi-Agent Routing

**Playground Test:**

```
User: "Monitor my research topic 'cancer immunotherapy' for papers since January 2025, 
analyze for contradictions with my review, and suggest updates."

RouterAgent:
1. Routes to MonitorAgent
2. Receives paper list
3. For each paper, routes to AnalysisAgent
4. If contradictions, routes to SuggestionAgent
5. Compiles final report
```

**View Traces:**
- RouterAgent → Traces tab
- See full routing flow
- Function calls
- Sub-agent interactions

---

## Agent Development Kit (ADK)

### Overview

The **Gradient ADK** is a Python SDK for building agents locally and deploying to DigitalOcean.

**Features:**
- Write agents in Python
- Local testing
- One-command deploy
- Automatic tracing
- Built-in evaluations
- LangGraph integration

### Installation

```bash
pip install gradient-adk
```

### Quick Start

```python
# agent.py
from gradient_adk import entrypoint, RequestContext

@entrypoint
async def main(input: dict, context: RequestContext):
    """
    Simple agent that greets users.
    """
    user_name = input.get("name", "there")
    return {
        "greeting": f"Hello, {user_name}! How can I help you today?"
    }
```

**Deploy:**
```bash
export DIGITALOCEAN_API_TOKEN="dop_v1_xxxxx"

gradient agent deploy
```

**Test:**
```bash
gradient agent test --input '{"name": "Alice"}'
```

---

### Advanced Example: Multi-Agent with LangGraph

```python
# complex_agent.py
from gradient_adk import entrypoint, RequestContext
from langgraph.graph import StateGraph
from typing import TypedDict

class AgentState(TypedDict):
    input: str
    papers: list
    analysis: dict
    output: str

async def search_papers(state: AgentState) -> AgentState:
    """Call PubMed search"""
    # This automatically traces the LangGraph node
    papers = await search_pubmed(state["input"])
    state["papers"] = papers
    return state

async def analyze_papers(state: AgentState) -> AgentState:
    """Analyze for contradictions"""
    analysis = await detect_contradictions(state["papers"])
    state["analysis"] = analysis
    return state

async def generate_summary(state: AgentState) -> AgentState:
    """Create final summary"""
    summary = f"Found {len(state['papers'])} papers, {len(state['analysis']['contradictions'])} contradictions"
    state["output"] = summary
    return state

@entrypoint
async def main(input: dict, context: RequestContext):
    # Build graph
    graph = StateGraph(AgentState)
    graph.add_node("search", search_papers)
    graph.add_node("analyze", analyze_papers)
    graph.add_node("summarize", generate_summary)
    
    graph.set_entry_point("search")
    graph.add_edge("search", "analyze")
    graph.add_edge("analyze", "summarize")
    
    # Run
    compiled = graph.compile()
    result = await compiled.ainvoke({"input": input["query"]})
    
    return {"result": result["output"]}
```

**Deploy:**
```bash
gradient agent deploy --name "ResearchMonitor"
```

**Automatic Tracing:**
- Every LangGraph node automatically traced
- View in DigitalOcean console under Traces
- See state transitions, timing, errors

---

## Best Practices

### 1. Agent Instructions

**DO:**
- Be specific about agent's role
- Define clear objectives
- List available tools/functions
- Specify output format
- Include examples

**DON'T:**
- Make instructions too long (>2000 words)
- Be vague ("help users")
- Forget to define boundaries

**Good Example:**
```
You are a PubMed monitoring specialist.

TASK: Search for papers, assess relevance (0-1 score), return JSON list.

TOOLS:
- search_pubmed(query, date_after) - Search PubMed

RULES:
- Only papers with relevance > 0.7
- Skip review articles
- Return max 50 papers

OUTPUT:
[{"pmid": "...", "title": "...", "score": 0.9}]
```

---

### 2. Knowledge Base Optimization

**DO:**
- Use descriptive file names
- Clean documents before upload (remove headers/footers)
- Choose appropriate chunking strategy
- Test retrieval quality with sample queries
- Monitor indexing logs

**DON'T:**
- Upload duplicate content
- Mix languages without consideration
- Ignore chunking settings
- Upload extremely large files (>50MB) without splitting

**Chunking Guidelines:**
- **Academic papers**: Section-based
- **Transcripts**: Fixed-size (512 tokens)
- **Technical docs**: Hierarchical
- **General text**: Section-based with 200-token overlap

---

### 3. Function Calling

**DO:**
- Write clear function descriptions
- Define precise input/output schemas
- Handle errors gracefully
- Return structured data (JSON)
- Add logging

**DON'T:**
- Make functions do too much (break into smaller functions)
- Forget input validation
- Return unstructured text when JSON expected
- Ignore rate limits

**Function Template:**
```python
def my_function(args):
    """
    Clear one-line description.
    
    Args:
        param1: Description and type
        param2: Description and type
    
    Returns:
        dict: {
            "result": ...,
            "error": None or error message
        }
    """
    try:
        # Validate input
        if "required_param" not in args:
            return {"error": "Missing required_param"}
        
        # Process
        result = do_something(args)
        
        # Return structured
        return {
            "result": result,
            "error": None
        }
    except Exception as e:
        return {
            "result": None,
            "error": str(e)
        }
```

---

### 4. Multi-Agent Systems

**DO:**
- Keep agents specialized (single responsibility)
- Use descriptive agent names
- Define clear routing conditions
- Test routing logic thoroughly
- Monitor agent interactions

**DON'T:**
- Create circular routing (A→B→A)
- Make routing conditions overlap
- Nest more than 2 levels deep (Router → Agent → Sub-Agent)
- Forget to handle edge cases

---

### 5. Cost Optimization

**Model Selection:**
- **Haiku**: Simple tasks, high volume ($0.25/M tokens)
- **Sonnet**: Most tasks, good balance ($3/M tokens)
- **Opus**: Complex reasoning, high quality ($15/M tokens)

**Tips:**
- Use Haiku for simple routing decisions
- Use Sonnet for main work
- Use Opus only when necessary
- Cache knowledge base embeddings
- Limit `max_tokens` in responses

**Example Cost (1000 users, 30 days):**
```
Daily monitoring:
- 1000 users × 1 job/day × 30 days = 30,000 jobs
- Avg 5,000 tokens per job (input + output)
- 30,000 × 5,000 = 150M tokens
- Sonnet: 150M × $3/M = $450/month

Knowledge base:
- 1000 users × 50 docs × 10 pages = 500,000 pages
- Embedding: ~$50 one-time + $10/month re-indexing
- Storage: ~$15/month

TOTAL: ~$525/month for 1000 active users
```

---

## Code Examples

### Complete Research Monitoring Flow

```python
import os
import requests

# Environment
DIGITALOCEAN_TOKEN = os.getenv("DIGITALOCEAN_API_TOKEN")
ROUTER_AGENT_ENDPOINT = os.getenv("ROUTER_AGENT_ENDPOINT")
ROUTER_AGENT_KEY = os.getenv("ROUTER_AGENT_ACCESS_KEY")

def monitor_research(user_id, topic, keywords, date_after):
    """
    Complete monitoring workflow using RouterAgent.
    """
    
    # Build prompt for router
    prompt = f"""
    Monitor research topic for user {user_id}.
    
    Topic: {topic}
    Keywords: {', '.join(keywords)}
    Date filter: Papers after {date_after}
    
    Workflow:
    1. Search PubMed for relevant papers
    2. Analyze each paper for contradictions with user's literature review
    3. Generate suggested updates for any contradictions found
    4. Return comprehensive report
    """
    
    # Call RouterAgent
    response = requests.post(
        f"{ROUTER_AGENT_ENDPOINT}/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {ROUTER_AGENT_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 4000,
            "include_retrieval_info": True,
            "include_functions_info": True
        }
    )
    
    result = response.json()
    
    # Extract results
    report = result["choices"][0]["message"]["content"]
    functions_used = result.get("functions", {}).get("called_functions", [])
    
    return {
        "report": report,
        "functions_called": functions_used,
        "timestamp": datetime.now().isoformat()
    }
```

---

## Troubleshooting

### Common Issues

**1. Agent not using knowledge base**

**Symptoms:**
- Agent gives generic answers
- Doesn't reference uploaded documents

**Solutions:**
- Verify KB attached to agent (Resources tab)
- Check indexing completed (Activity tab)
- Improve agent instructions: "Always search the knowledge base first before answering"
- Test with explicit reference: "What does the knowledge base say about X?"

---

**2. Function not being called**

**Symptoms:**
- Agent ignores external data needs
- Doesn't call function even when appropriate

**Solutions:**
- Improve function description (make it very clear when to use)
- Add to agent instructions: "You have access to search_pubmed function - use it when users ask about research papers"
- Check input schema is valid JSON
- Test function independently first

---

**3. Knowledge base retrieval is slow**

**Symptoms:**
- Agent responses take >10 seconds
- Timeout errors

**Solutions:**
- Reduce chunk size (smaller chunks = faster retrieval)
- Limit KB size (<1GB per KB)
- Use same region for KB and agent (tor1)
- Consider splitting into multiple specialized KBs

---

**4. Agent responses inconsistent**

**Symptoms:**
- Same query gives different results
- Quality varies

**Solutions:**
- Lower temperature (0.3-0.5 for consistency)
- Add more examples to instructions
- Use structured output format (JSON)
- Add constraints: "Always include X, Y, Z in response"

---

**5. Rate limit errors**

**Symptoms:**
- 429 Too Many Requests
- "API rate limit exceeded"

**Solutions:**
- Get API key from NCBI (10 requests/second vs 3)
- Add delays between requests
- Implement exponential backoff
- Use batching (e.g., EPost → EFetch instead of individual fetches)

---

### Getting Help

**Documentation:**
- https://docs.digitalocean.com/products/gradient-ai-platform/
- https://docs.digitalocean.com/products/gradient-ai-platform/reference/

**Community:**
- DigitalOcean Community Forums
- Discord (check DigitalOcean blog for link)

**Support:**
- DigitalOcean Support Tickets (account holders)
- GitHub Issues (for ADK): https://github.com/digitalocean/gradient-adk

---

## Summary

**You now know:**
✅ How to create agents with custom instructions
✅ How to build and attach knowledge bases for RAG
✅ How to enable function calling for external APIs
✅ How to set up multi-agent routing
✅ How to deploy with the Agent Development Kit
✅ Best practices for production systems

**Next Steps:**
1. Create your first agent in the control panel
2. Attach a knowledge base with sample data
3. Add a simple function (e.g., weather API)
4. Test in playground
5. Deploy to production

**For ConsensusTracker specifically:**
- Create 4 agents (Router, Monitor, Analysis, Suggestion)
- Attach user literature reviews as KBs
- Add PubMed search + Google Docs functions
- Set up daily monitoring cron job
- Use RouterAgent to orchestrate workflow

Good luck building! 🚀
