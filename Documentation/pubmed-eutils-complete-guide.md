# PubMed E-utilities API - Complete Implementation Guide

## Table of Contents
1. [Overview](#overview)
2. [Key Concepts](#key-concepts)
3. [E-utilities Toolset](#e-utilities-toolset)
4. [Authentication & Setup](#authentication--setup)
5. [Using Biopython](#using-biopython)
6. [Advanced Search Syntax](#advanced-search-syntax)
7. [Complete Code Examples](#complete-code-examples)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

### What is PubMed E-utilities?

**PubMed E-utilities** (Entrez Programming Utilities) is a free REST API for accessing the National Library of Medicine's databases, including:
- **PubMed**: 35+ million biomedical citations
- **PMC** (PubMed Central): 7+ million full-text articles
- **MedGen, ClinVar, Gene, Protein**, and more

**Key Features:**
- ✅ Completely free (no API key required, but recommended)
- ✅ Programmatic access to MEDLINE/PubMed
- ✅ Search, retrieve, analyze citations
- ✅ Get abstracts, DOIs, authors, dates, MeSH terms
- ✅ XML and JSON output formats

---

## Key Concepts

### 1. Databases

Each Entrez database has a short name:
- `pubmed` - Biomedical literature citations
- `pmc` - Full-text articles
- `gene` - Gene information
- `protein` - Protein sequences

**For ConsensusTracker, use `pubmed`.**

### 2. UIDs (Unique Identifiers)

Every record has a unique ID:
- **PMID** (PubMed ID): e.g., `12345678`
- **PMCID** (PMC ID): e.g., `PMC1234567`
- **DOI**: e.g., `10.1038/nature12345`

### 3. E-utilities Functions

8 core utilities:
1. **ESearch** - Search and retrieve UIDs
2. **EFetch** - Retrieve full records
3. **ESummary** - Get document summaries
4. **ELink** - Find related records
5. **EInfo** - Get database statistics
6. **EPost** - Upload UIDs to server
7. **ESpell** - Get spelling suggestions
8. **ECitMatch** - Retrieve PMIDs from citations

**Most common workflow: ESearch → EFetch**

### 4. Search Fields

Restrict searches to specific fields:
- `[Title]` - Article title only
- `[Author]` - Author names
- `[Journal]` - Journal name
- `[Date - Publication]` - Publication date
- `[MeSH Terms]` - Medical Subject Headings (controlled vocabulary)
- `[TIAB]` - Title/Abstract

---

## E-utilities Toolset

### Base URL

All E-utilities requests use:
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/
```

### ESearch - Search for Papers

**Purpose:** Search PubMed, get list of PMIDs

**Endpoint:** `esearch.fcgi`

**Parameters:**
- `db` - Database (e.g., `pubmed`)
- `term` - Search query
- `retmax` - Max results (default 20, max 10,000)
- `retmode` - Format (`xml` or `json`)
- `sort` - Sort order (`relevance`, `pub_date`)
- `mindate`, `maxdate` - Date filters (YYYY/MM/DD)
- `api_key` - Your API key (optional but recommended)

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi?db=pubmed&term=cancer+immunotherapy&retmax=10&retmode=json
```

**Response (JSON):**
```json
{
  "esearchresult": {
    "count": "45632",
    "retmax": "10",
    "idlist": ["37654321", "37654320", ...],
    "querytranslation": "\"neoplasms\"[MeSH Terms] AND \"immunotherapy\"[MeSH Terms]"
  }
}
```

---

### EFetch - Retrieve Full Records

**Purpose:** Get detailed paper information (title, abstract, authors, DOI)

**Endpoint:** `efetch.fcgi`

**Parameters:**
- `db` - Database (`pubmed`)
- `id` - PMIDs (comma-separated)
- `rettype` - Return type (`abstract`, `xml`, `medline`)
- `retmode` - Format (`xml`, `text`)

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi?db=pubmed&id=12345678,12345679&rettype=abstract&retmode=xml
```

**Response:** XML with full article metadata

---

### ESummary - Get Summaries

**Purpose:** Get brief summaries (lighter than EFetch)

**Endpoint:** `esummary.fcgi`

**Example:**
```
https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=12345678&retmode=json
```

---

## Authentication & Setup

### Option 1: No API Key (Rate Limited)

**Rate limit:** 3 requests/second

**Usage:**
```python
from Bio import Entrez

Entrez.email = "your.email@example.com"  # REQUIRED

# Make requests
handle = Entrez.esearch(db="pubmed", term="cancer")
```

**⚠️ You MUST set `Entrez.email`** - NCBI will block your IP if you don't.

---

### Option 2: With API Key (Recommended)

**Rate limit:** 10 requests/second

**Get API key:**
1. Create NCBI account: https://www.ncbi.nlm.nih.gov/account/
2. Go to Settings → API Key Management
3. Click "Create an API Key"
4. Copy key (e.g., `abcdef123456789...`)

**Usage:**
```python
from Bio import Entrez

Entrez.email = "your.email@example.com"
Entrez.api_key = "abcdef123456789..."  # Your API key

# Now you get 10 req/s instead of 3
```

**Environment variable approach:**
```bash
# .bashrc or .zshrc
export NCBI_API_KEY="abcdef123456789..."
export NCBI_EMAIL="your.email@example.com"
```

```python
import os
from Bio import Entrez

Entrez.email = os.getenv("NCBI_EMAIL")
Entrez.api_key = os.getenv("NCBI_API_KEY")
```

---

## Using Biopython

### Installation

```bash
pip install biopython
```

### Basic Search

```python
from Bio import Entrez

Entrez.email = "your.email@example.com"

def search_pubmed(query, max_results=20):
    """
    Search PubMed and return list of PMIDs.
    
    Args:
        query: Search terms
        max_results: Max papers to return
    
    Returns:
        List of PMIDs
    """
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        sort="relevance"
    )
    
    results = Entrez.read(handle)
    handle.close()
    
    return results["IdList"]

# Usage
pmids = search_pubmed("cancer immunotherapy", max_results=10)
print(f"Found {len(pmids)} papers")
print(pmids)
# ['37654321', '37654320', ...]
```

---

### Fetch Paper Details

```python
def fetch_paper_details(pmid_list):
    """
    Fetch full details for papers.
    
    Args:
        pmid_list: List of PMIDs
    
    Returns:
        List of paper dictionaries
    """
    # Join PMIDs with commas
    ids = ",".join(pmid_list)
    
    handle = Entrez.efetch(
        db="pubmed",
        id=ids,
        rettype="xml",
        retmode="xml"
    )
    
    records = Entrez.read(handle)
    handle.close()
    
    papers = []
    
    for article in records['PubmedArticle']:
        medline = article['MedlineCitation']
        article_data = medline['Article']
        
        # Extract abstract
        abstract = ""
        if 'Abstract' in article_data:
            abstract_parts = article_data['Abstract']['AbstractText']
            if isinstance(abstract_parts, list):
                abstract = " ".join(str(p) for p in abstract_parts)
            else:
                abstract = str(abstract_parts)
        
        # Extract authors
        authors = []
        if 'AuthorList' in article_data:
            for author in article_data['AuthorList']:
                last = author.get('LastName', '')
                first = author.get('ForeName', '')
                if last:
                    authors.append(f"{first} {last}".strip())
        
        # Extract DOI
        doi = ""
        if 'ELocationID' in article_data:
            for eloc in article_data['ELocationID']:
                if eloc.attributes.get('EIdType') == 'doi':
                    doi = str(eloc)
        
        # Extract publication date
        pub_date = article_data['Journal']['JournalIssue']['PubDate']
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')
        
        # Build paper object
        paper = {
            'pmid': str(medline['PMID']),
            'doi': doi,
            'title': str(article_data['ArticleTitle']),
            'authors': authors,
            'journal': str(article_data['Journal']['Title']),
            'pub_date': f"{year}-{month}-{day}",
            'abstract': abstract
        }
        
        papers.append(paper)
    
    return papers

# Usage
pmids = search_pubmed("CRISPR", max_results=5)
papers = fetch_paper_details(pmids)

for paper in papers:
    print(f"Title: {paper['title']}")
    print(f"Authors: {', '.join(paper['authors'][:3])}")
    print(f"DOI: {paper['doi']}")
    print(f"Date: {paper['pub_date']}")
    print("---")
```

---

### Date Filtering

```python
def search_with_date_filter(query, date_after, max_results=50):
    """
    Search PubMed for papers published after a specific date.
    
    Args:
        query: Search terms
        date_after: Date string (YYYY/MM/DD or YYYY)
        max_results: Max results
    
    Returns:
        List of PMIDs
    """
    
    # Build date filter
    # Format: ("date_after"[Date - Publication] : "3000"[Date - Publication])
    search_term = f'{query} AND ("{date_after}"[Date - Publication] : "3000"[Date - Publication])'
    
    handle = Entrez.esearch(
        db="pubmed",
        term=search_term,
        retmax=max_results,
        sort="pub_date",  # Sort by publication date (newest first)
        retmode="xml"
    )
    
    results = Entrez.read(handle)
    handle.close()
    
    return results["IdList"]

# Usage - Papers on immunotherapy since Jan 2025
pmids = search_with_date_filter(
    query="cancer immunotherapy",
    date_after="2025/01/01",
    max_results=20
)
print(f"Found {len(pmids)} papers since 2025-01-01")
```

---

### Alternative Date Filtering (Using Parameters)

```python
def search_date_range(query, min_date, max_date, max_results=50):
    """
    Search with date range using API parameters.
    
    Args:
        min_date: Start date (YYYY/MM/DD)
        max_date: End date (YYYY/MM/DD)
    """
    
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=max_results,
        mindate=min_date,
        maxdate=max_date,
        datetype="pdat",  # Publication date
        sort="relevance"
    )
    
    results = Entrez.read(handle)
    handle.close()
    
    return results["IdList"]

# Usage
pmids = search_date_range(
    query="COVID-19 vaccine",
    min_date="2024/01/01",
    max_date="2024/12/31",
    max_results=100
)
```

---

## Advanced Search Syntax

### Boolean Operators

```python
# AND (both terms must be present)
"cancer AND immunotherapy"

# OR (either term)
"cancer OR tumor OR neoplasm"

# NOT (exclude term)
"cancer NOT lung"

# Grouping with parentheses
"(breast OR ovarian) AND cancer AND BRCA1"
```

---

### Field Tags

Restrict search to specific fields:

```python
# Title only
"CRISPR[Title]"

# Author
"Smith J[Author]"

# Journal
"Nature[Journal]"

# Title or Abstract
"immunotherapy[TIAB]"

# MeSH terms (controlled vocabulary)
'"Neoplasms"[MeSH Terms]'

# Publication type
"Review[Publication Type]"

# Multiple fields
"cancer[Title] AND immunotherapy[TIAB]"
```

---

### Date Filters

```python
# Last 5 years
"cancer AND 2020:2025[Date - Publication]"

# Specific year
"cancer AND 2024[Date - Publication]"

# Date range
"cancer AND 2023/01/01:2024/12/31[Date - Publication]"

# Last 30 days (using reldate parameter)
handle = Entrez.esearch(
    db="pubmed",
    term="cancer",
    reldate=30,  # Last 30 days
    datetype="pdat"
)
```

---

### MeSH Terms (Medical Subject Headings)

MeSH = Controlled vocabulary for indexing biomedical literature

```python
# Search using MeSH
'"Breast Neoplasms"[MeSH Terms]'

# MeSH with subheadings
'"Diabetes Mellitus"[MeSH Terms] AND "drug therapy"[Subheading]'

# Find MeSH term for a concept
'"Neoplasms"[MeSH Terms]'  # More precise than "cancer"
```

**Pro tip:** Use [MeSH Browser](https://meshb.nlm.nih.gov/) to find correct terms.

---

### Publication Types

```python
# Randomized Controlled Trials only
"cancer AND Randomized Controlled Trial[Publication Type]"

# Reviews only
"immunotherapy AND Review[Publication Type]"

# Systematic Reviews
"COVID-19 AND Systematic Review[Publication Type]"

# Clinical Trials
"diabetes AND Clinical Trial[Publication Type]"

# Exclude specific types
"cancer NOT Review[Publication Type]"
```

---

### Complex Query Example

```python
# Advanced search: RCTs on breast cancer drug therapy from 2020-2024
query = """
    ("Breast Neoplasms"[MeSH Terms] OR "breast cancer"[TIAB])
    AND ("drug therapy"[Subheading] OR "chemotherapy"[TIAB])
    AND Randomized Controlled Trial[Publication Type]
    AND 2020:2024[Date - Publication]
    AND English[Language]
    AND humans[MeSH Terms]
"""

pmids = search_pubmed(query, max_results=100)
```

---

## Complete Code Examples

### Full Workflow: Search + Fetch + Parse

```python
# complete_pubmed_workflow.py

from Bio import Entrez
import os
from datetime import datetime

# Configuration
Entrez.email = os.getenv("NCBI_EMAIL", "your.email@example.com")
Entrez.api_key = os.getenv("NCBI_API_KEY")  # Optional but recommended

def search_papers(keywords, date_after=None, max_results=50):
    """
    Search PubMed with date filtering.
    
    Args:
        keywords: List of keywords or single query string
        date_after: Date in YYYY/MM/DD format (optional)
        max_results: Max papers to return
    
    Returns:
        List of PMIDs
    """
    
    # Build query
    if isinstance(keywords, list):
        query = " AND ".join(keywords)
    else:
        query = keywords
    
    # Add date filter if provided
    if date_after:
        query += f' AND ("{date_after}"[Date - Publication] : "3000"[Date - Publication])'
    
    print(f"Searching PubMed: {query}")
    
    try:
        handle = Entrez.esearch(
            db="pubmed",
            term=query,
            retmax=max_results,
            sort="relevance",
            retmode="xml"
        )
        
        results = Entrez.read(handle)
        handle.close()
        
        pmids = results["IdList"]
        count = results["Count"]
        
        print(f"Found {count} total papers, returning {len(pmids)}")
        return pmids
    
    except Exception as e:
        print(f"Search error: {e}")
        return []

def fetch_papers(pmid_list, batch_size=200):
    """
    Fetch paper details in batches.
    
    Args:
        pmid_list: List of PMIDs
        batch_size: Papers per batch (max 200 recommended)
    
    Returns:
        List of paper dictionaries
    """
    
    all_papers = []
    
    # Process in batches to avoid timeout
    for i in range(0, len(pmid_list), batch_size):
        batch = pmid_list[i:i + batch_size]
        ids = ",".join(batch)
        
        print(f"Fetching batch {i//batch_size + 1} ({len(batch)} papers)...")
        
        try:
            handle = Entrez.efetch(
                db="pubmed",
                id=ids,
                rettype="xml",
                retmode="xml"
            )
            
            records = Entrez.read(handle)
            handle.close()
            
            # Parse each article
            for article in records.get('PubmedArticle', []):
                paper = parse_article(article)
                if paper:
                    all_papers.append(paper)
        
        except Exception as e:
            print(f"Fetch error for batch: {e}")
            continue
    
    return all_papers

def parse_article(article):
    """
    Parse PubMed article XML into structured dict.
    
    Returns:
        {
            'pmid': str,
            'doi': str,
            'title': str,
            'authors': list,
            'journal': str,
            'pub_date': str,
            'abstract': str,
            'mesh_terms': list,
            'publication_types': list
        }
    """
    
    try:
        medline = article['MedlineCitation']
        article_data = medline['Article']
        
        # Extract abstract
        abstract = ""
        if 'Abstract' in article_data:
            abstract_parts = article_data['Abstract']['AbstractText']
            if isinstance(abstract_parts, list):
                # Handle structured abstracts
                abstract_sections = []
                for part in abstract_parts:
                    if hasattr(part, 'attributes') and 'Label' in part.attributes:
                        label = part.attributes['Label']
                        abstract_sections.append(f"{label}: {str(part)}")
                    else:
                        abstract_sections.append(str(part))
                abstract = " ".join(abstract_sections)
            else:
                abstract = str(abstract_parts)
        
        # Extract authors
        authors = []
        if 'AuthorList' in article_data:
            for author in article_data['AuthorList']:
                last = author.get('LastName', '')
                first = author.get('ForeName', '')
                initials = author.get('Initials', '')
                
                if last:
                    if first:
                        authors.append(f"{first} {last}")
                    elif initials:
                        authors.append(f"{initials} {last}")
                    else:
                        authors.append(last)
        
        # Extract DOI
        doi = ""
        if 'ELocationID' in article_data:
            for eloc in article_data['ELocationID']:
                if eloc.attributes.get('EIdType') == 'doi':
                    doi = str(eloc)
                    break
        
        # Extract publication date
        pub_date = article_data['Journal']['JournalIssue']['PubDate']
        year = pub_date.get('Year', '')
        month = pub_date.get('Month', '01')
        day = pub_date.get('Day', '01')
        
        # Convert month name to number if needed
        if month and not month.isdigit():
            month_map = {
                'Jan': '01', 'Feb': '02', 'Mar': '03', 'Apr': '04',
                'May': '05', 'Jun': '06', 'Jul': '07', 'Aug': '08',
                'Sep': '09', 'Oct': '10', 'Nov': '11', 'Dec': '12'
            }
            month = month_map.get(month[:3], '01')
        
        date_str = f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        # Extract MeSH terms
        mesh_terms = []
        if 'MeshHeadingList' in medline:
            for mesh in medline['MeshHeadingList']:
                descriptor = mesh['DescriptorName']
                mesh_terms.append(str(descriptor))
        
        # Extract publication types
        pub_types = []
        if 'PublicationTypeList' in article_data:
            for pub_type in article_data['PublicationTypeList']:
                pub_types.append(str(pub_type))
        
        return {
            'pmid': str(medline['PMID']),
            'doi': doi,
            'title': str(article_data['ArticleTitle']),
            'authors': authors,
            'journal': str(article_data['Journal']['Title']),
            'pub_date': date_str,
            'abstract': abstract,
            'mesh_terms': mesh_terms,
            'publication_types': pub_types
        }
    
    except Exception as e:
        print(f"Parse error: {e}")
        return None

def assess_relevance(paper, topic_keywords):
    """
    Simple relevance scoring (0-1).
    
    Args:
        paper: Paper dictionary
        topic_keywords: List of important keywords
    
    Returns:
        float: Relevance score
    """
    
    # Combine title + abstract
    text = f"{paper['title']} {paper['abstract']}".lower()
    
    # Count keyword matches
    matches = sum(1 for kw in topic_keywords if kw.lower() in text)
    
    # Normalize
    score = min(matches / len(topic_keywords), 1.0)
    
    # Boost if in title
    title_matches = sum(1 for kw in topic_keywords if kw.lower() in paper['title'].lower())
    if title_matches > 0:
        score = min(score + 0.2, 1.0)
    
    return round(score, 2)

# MAIN WORKFLOW
if __name__ == '__main__':
    
    # Step 1: Search
    pmids = search_papers(
        keywords=["cancer", "immunotherapy", "PD-1"],
        date_after="2024/01/01",
        max_results=50
    )
    
    if not pmids:
        print("No papers found")
        exit()
    
    # Step 2: Fetch details
    papers = fetch_papers(pmids)
    
    print(f"\nFetched {len(papers)} papers")
    
    # Step 3: Score relevance
    topic_keywords = ["cancer", "immunotherapy", "PD-1", "checkpoint inhibitor"]
    
    for paper in papers:
        paper['relevance_score'] = assess_relevance(paper, topic_keywords)
    
    # Step 4: Filter and sort
    relevant_papers = [p for p in papers if p['relevance_score'] > 0.5]
    relevant_papers.sort(key=lambda x: x['relevance_score'], reverse=True)
    
    print(f"\nRelevant papers (score > 0.5): {len(relevant_papers)}")
    
    # Step 5: Display top results
    print("\n" + "="*80)
    print("TOP 5 MOST RELEVANT PAPERS:")
    print("="*80)
    
    for i, paper in enumerate(relevant_papers[:5], 1):
        print(f"\n{i}. {paper['title']}")
        print(f"   Authors: {', '.join(paper['authors'][:3])}...")
        print(f"   Journal: {paper['journal']}")
        print(f"   Date: {paper['pub_date']}")
        print(f"   PMID: {paper['pmid']}")
        print(f"   DOI: {paper['doi']}")
        print(f"   Relevance: {paper['relevance_score']}")
        print(f"   Abstract: {paper['abstract'][:200]}...")
        print(f"   MeSH: {', '.join(paper['mesh_terms'][:5])}")
```

---

## Best Practices

### 1. Rate Limiting

```python
import time

def search_with_rate_limit(queries, delay=0.34):
    """
    Execute multiple searches with rate limiting.
    
    Args:
        queries: List of search queries
        delay: Seconds between requests (0.34 = ~3 req/s)
    """
    
    results = []
    
    for i, query in enumerate(queries):
        pmids = search_pubmed(query)
        results.append(pmids)
        
        # Rate limit
        if i < len(queries) - 1:
            time.sleep(delay)
    
    return results

# With API key: delay=0.1 (10 req/s)
# Without API key: delay=0.34 (3 req/s)
```

---

### 2. Error Handling

```python
from urllib.error import HTTPError
from http.client import IncompleteRead

def robust_search(query, max_retries=3):
    """Search with retry logic."""
    
    for attempt in range(max_retries):
        try:
            handle = Entrez.esearch(
                db="pubmed",
                term=query,
                retmax=50
            )
            results = Entrez.read(handle)
            handle.close()
            return results["IdList"]
        
        except HTTPError as e:
            if e.code == 429:  # Too Many Requests
                wait_time = 2 ** attempt  # Exponential backoff
                print(f"Rate limited. Waiting {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"HTTP error: {e}")
                break
        
        except IncompleteRead as e:
            print(f"Incomplete read. Retrying...")
            time.sleep(1)
        
        except Exception as e:
            print(f"Error: {e}")
            break
    
    return []
```

---

### 3. Batch Processing

```python
def fetch_large_dataset(query, total_needed=1000, batch_size=100):
    """
    Fetch large numbers of papers efficiently.
    
    Uses EPost + History server for better performance.
    """
    
    all_pmids = []
    
    # Search
    handle = Entrez.esearch(
        db="pubmed",
        term=query,
        retmax=total_needed,
        usehistory="y"  # Use history server
    )
    
    search_results = Entrez.read(handle)
    handle.close()
    
    count = int(search_results["Count"])
    webenv = search_results["WebEnv"]
    query_key = search_results["QueryKey"]
    
    print(f"Found {count} papers total")
    
    # Fetch in batches
    for start in range(0, min(count, total_needed), batch_size):
        end = min(start + batch_size, total_needed)
        
        print(f"Fetching papers {start+1}-{end}...")
        
        try:
            fetch_handle = Entrez.efetch(
                db="pubmed",
                rettype="xml",
                retmode="xml",
                retstart=start,
                retmax=batch_size,
                webenv=webenv,
                query_key=query_key
            )
            
            data = Entrez.read(fetch_handle)
            fetch_handle.close()
            
            # Process batch
            for article in data['PubmedArticle']:
                paper = parse_article(article)
                if paper:
                    all_pmids.append(paper)
            
            # Rate limit
            time.sleep(0.34)
        
        except Exception as e:
            print(f"Batch error: {e}")
            continue
    
    return all_pmids
```

---

### 4. Caching Results

```python
import json
import hashlib

def cached_search(query, cache_dir='cache'):
    """
    Search with caching to avoid redundant API calls.
    """
    
    os.makedirs(cache_dir, exist_ok=True)
    
    # Generate cache key from query
    cache_key = hashlib.md5(query.encode()).hexdigest()
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    
    # Check cache
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as f:
            print("Using cached results")
            return json.load(f)
    
    # Search
    pmids = search_pubmed(query)
    papers = fetch_papers(pmids)
    
    # Cache
    with open(cache_file, 'w') as f:
        json.dump(papers, f)
    
    return papers
```

---

## Troubleshooting

### Common Errors

**1. `HTTP Error 429: Too Many Requests`**

**Cause:** Exceeded rate limit

**Solution:**
```python
# Get an API key (10 req/s instead of 3)
Entrez.api_key = "your_api_key"

# Add delays
time.sleep(0.34)  # ~3 requests/second

# Implement exponential backoff
```

---

**2. `RuntimeError: Email parameter not set`**

**Cause:** Forgot to set `Entrez.email`

**Solution:**
```python
Entrez.email = "your.email@example.com"  # ALWAYS required
```

---

**3. Empty results but papers should exist**

**Cause:** Query syntax error or too restrictive

**Solution:**
```python
# Check what NCBI actually searched
handle = Entrez.esearch(db="pubmed", term="cancer AND immuntherapy")
results = Entrez.read(handle)
print(results.get("QueryTranslation"))
# Shows: "cancer[All Fields] AND immuntherapy[All Fields]"
# Typo: "immuntherapy" instead of "immunotherapy"
```

---

**4. XML parsing errors**

**Cause:** Unexpected XML structure

**Solution:**
```python
# Pretty-print XML to inspect structure
import json
from xml.etree import ElementTree

handle = Entrez.efetch(db="pubmed", id="12345678", rettype="xml")
tree = ElementTree.parse(handle)
root = tree.getroot()

# Print XML
ElementTree.dump(root)
```

---

**5. Missing abstracts**

**Cause:** Not all papers have abstracts

**Solution:**
```python
# Always check if abstract exists
abstract = ""
if 'Abstract' in article_data:
    abstract = article_data['Abstract']['AbstractText']
else:
    abstract = "[No abstract available]"
```

---

### Debugging Tips

**1. Test queries in PubMed website first**

Go to https://pubmed.ncbi.nlm.nih.gov/ and test your query manually.

**2. Use `retmode='json'` for debugging**

JSON is easier to inspect than XML:
```python
handle = Entrez.esearch(db="pubmed", term="cancer", retmode="json")
import json
data = json.load(handle)
print(json.dumps(data, indent=2))
```

**3. Inspect QueryTranslation**

See how NCBI interpreted your query:
```python
results = Entrez.read(Entrez.esearch(db="pubmed", term="breast ca"))
print(results["QueryTranslation"])
# "breast"[All Fields] AND "ca"[All Fields]
# (Not what you wanted! Use "breast cancer" or MeSH terms)
```

---

## Summary

**Key Takeaways:**

✅ **ESearch → EFetch** is the standard workflow
✅ **Always set `Entrez.email`** (required by NCBI)
✅ **Get API key** for 10 req/s (vs 3 without)
✅ **Use Biopython** - easier than raw HTTP
✅ **Date filtering** essential for monitoring new papers
✅ **MeSH terms** improve precision
✅ **Batch requests** for large datasets
✅ **Cache results** to avoid redundant calls

**For ConsensusTracker:**
- Search daily for papers after user's last review date
- Use `("2025/01/01"[Date - Publication] : "3000"[Date - Publication])` syntax
- Fetch full details (title, abstract, authors, DOI)
- Parse abstracts for contradiction detection
- Implement rate limiting (0.1s delay with API key)
- Cache paper metadata to avoid re-fetching

**Rate Limits:**
- No API key: 3 requests/second
- With API key: 10 requests/second
- Recommended: 0.1-0.34 second delay between requests

**Next Steps:**
1. Get NCBI API key
2. Test search with date filtering
3. Build parsing function for paper metadata
4. Implement relevance scoring
5. Integrate with Gradient AI agents

Good luck with your research monitoring! 🔬📚
