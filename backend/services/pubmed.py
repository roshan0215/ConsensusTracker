from __future__ import annotations

from datetime import date
import re
import xml.etree.ElementTree as ET

import httpx

from backend.core.config import get_settings


EUTILS_BASE = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"


def search_pubmed(query: str, date_after: date | None = None, max_results: int = 50) -> list[dict]:
    settings = get_settings()

    if not settings.ncbi_email:
        raise RuntimeError("NCBI_EMAIL is required")

    search_term = query
    if date_after:
        search_term += f' AND ("{date_after.isoformat()}"[Date - Publication] : "3000"[Date - Publication])'

    params = {
        "db": "pubmed",
        "term": search_term,
        "retmax": str(max_results),
        "retmode": "json",
        "sort": "relevance",
        "tool": "consensustracker",
        "email": settings.ncbi_email,
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key

    with httpx.Client(timeout=30) as client:
        res = client.get(f"{EUTILS_BASE}/esearch.fcgi", params=params)
        res.raise_for_status()
        data = res.json()
        id_list = data.get("esearchresult", {}).get("idlist", [])
        if not id_list:
            return []

        fetch_params = {
            "db": "pubmed",
            "id": ",".join(id_list),
            "rettype": "abstract",
            "retmode": "xml",
            "tool": "consensustracker",
            "email": settings.ncbi_email,
        }
        if settings.ncbi_api_key:
            fetch_params["api_key"] = settings.ncbi_api_key
        fetch = client.get(f"{EUTILS_BASE}/efetch.fcgi", params=fetch_params)
        fetch.raise_for_status()
        papers = _parse_pubmed_efetch_xml(fetch.text)

        # Best-effort: enrich a few papers with open full text from PMC.
        full_text_attempts = 0
        for paper in papers:
            if full_text_attempts >= 5:
                break
            pmcid = paper.get("pmcid")
            if not pmcid:
                continue
            full_text_attempts += 1
            try:
                full_text = _fetch_pmc_full_text(client, pmcid=pmcid, settings=settings)
            except Exception:
                full_text = None
            if full_text:
                paper["full_text"] = full_text

        for paper in papers:
            if paper.get("full_text"):
                paper["content"] = paper["full_text"]
                paper["content_source"] = "full_text"
            else:
                paper["content"] = paper.get("abstract") or ""
                paper["content_source"] = "abstract"

        return papers


def _parse_pubmed_efetch_xml(xml_text: str) -> list[dict]:
    root = ET.fromstring(xml_text)
    papers: list[dict] = []
    for article in root.findall(".//PubmedArticle"):
        pmid = (article.findtext(".//PMID") or "").strip()
        title = (article.findtext(".//ArticleTitle") or "").strip()
        abstract_parts: list[str] = []
        for block in article.findall(".//AbstractText"):
            text = "".join(block.itertext()).strip()
            if text:
                abstract_parts.append(text)
        abstract = "\n".join(abstract_parts).strip()

        doi = None
        pmcid = None
        for aid in article.findall(".//ArticleId"):
            aid_text = (aid.text or "").strip()
            aid_type = (aid.attrib.get("IdType") or "").lower()
            if not aid_text:
                continue
            if aid_type == "doi" and doi is None:
                doi = aid_text
            if aid_type == "pmc" and pmcid is None:
                pmcid = aid_text if aid_text.lower().startswith("pmc") else f"PMC{aid_text}"

        # Extract authors: "Last I, Last I, et al." (cap at 6 before et al.)
        author_parts: list[str] = []
        for author in article.findall(".//Author"):
            last = (author.findtext("LastName") or "").strip()
            initials = (author.findtext("Initials") or "").strip()
            if last:
                author_parts.append(f"{last} {initials}".strip() if initials else last)
        if len(author_parts) > 6:
            authors_str = ", ".join(author_parts[:6]) + ", et al."
        elif author_parts:
            authors_str = ", ".join(author_parts)
        else:
            authors_str = None

        year = None
        pub_date = article.find(".//PubDate")
        if pub_date is not None:
            year = (pub_date.findtext("Year") or "").strip() or None

        papers.append(
            {
                "pmid": pmid,
                "pmcid": pmcid,
                "doi": doi,
                "title": title,
                "abstract": abstract,
                "authors": authors_str,
                "year": year,
            }
        )
    return papers


_WS_RE = re.compile(r"\s+")


def _fetch_pmc_full_text(client: httpx.Client, *, pmcid: str, settings) -> str | None:
    params = {
        "db": "pmc",
        "id": pmcid,
        "retmode": "xml",
        "tool": "consensustracker",
        "email": settings.ncbi_email,
    }
    if settings.ncbi_api_key:
        params["api_key"] = settings.ncbi_api_key

    res = client.get(f"{EUTILS_BASE}/efetch.fcgi", params=params)
    if res.status_code >= 400:
        return None

    root = ET.fromstring(res.text)
    paras: list[str] = []
    for p in root.findall(".//body//p"):
        txt = "".join(p.itertext()).strip()
        if not txt:
            continue
        txt = _WS_RE.sub(" ", txt)
        if txt:
            paras.append(txt)

    if not paras:
        return None

    # Keep payload sizes bounded for LLM prompts.
    full_text = "\n\n".join(paras)
    return full_text[:18000]
