from __future__ import annotations

import json
import re
from datetime import date

import httpx

from backend.core.config import get_settings


DO_GENAI_BASE = "https://api.digitalocean.com/v2/gen-ai"


def _require(value: str | None, name: str) -> str:
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def _extract_json_object(text: str) -> dict:
    """Best-effort JSON extraction for agent responses."""
    text = text.strip()
    try:
        return json.loads(text)
    except Exception:
        pass

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
    if fenced:
        return json.loads(fenced.group(1))

    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise ValueError("Agent response did not contain valid JSON")


def _recover_partial_findings(text: str) -> dict | None:
    """
    When a large agent response is truncated mid-JSON, extract every complete
    finding object that was produced before the cut-off.
    Returns a dict with 'findings' and 'papers_checked', or None if nothing useful found.
    """
    # Find the start of the findings array
    array_start = text.find('"findings"')
    if array_start == -1:
        return None
    bracket = text.find("[", array_start)
    if bracket == -1:
        return None

    findings = []
    i = bracket + 1
    depth = 0
    obj_start = None
    while i < len(text):
        c = text[i]
        if c == "{":
            if depth == 0:
                obj_start = i
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0 and obj_start is not None:
                try:
                    obj = json.loads(text[obj_start : i + 1])
                    findings.append(obj)
                except Exception:
                    pass
                obj_start = None
        i += 1

    if not findings:
        return None

    # Best-effort papers_checked
    pc_match = re.search(r'"papers_checked"\s*:\s*(\d+)', text)
    papers_checked = int(pc_match.group(1)) if pc_match else len(findings)
    return {"papers_checked": papers_checked, "findings": findings, "_truncated": True}


def agent_chat(*, endpoint: str, access_key: str, prompt: str, max_tokens: int = 4000) -> str:
    url = endpoint.rstrip("/") + "/api/v1/chat/completions"
    with httpx.Client(timeout=60) as client:
        res = client.post(
            url,
            headers={"Authorization": f"Bearer {access_key}", "Content-Type": "application/json"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "include_retrieval_info": True,
                "include_functions_info": True,
            },
        )
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"]


def _get_embedding_model_uuid(token: str, model_id: str) -> str:
    """Resolve an embedding model ID (e.g. 'qwen3-embedding-0.6b') to its DO UUID."""
    with httpx.Client(timeout=15) as client:
        res = client.get(
            f"{DO_GENAI_BASE}/models",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()
        for m in res.json().get("models", []):
            if m.get("id") == model_id:
                return m["uuid"]
    raise RuntimeError(f"Embedding model '{model_id}' not found in DO GenAI models")


def create_knowledge_base(*, name: str, description: str) -> str:
    settings = get_settings()
    token = _require(settings.digitalocean_api_token, "DIGITALOCEAN_API_TOKEN")
    project_id = _require(settings.digitalocean_project_id, "DIGITALOCEAN_PROJECT_ID")

    with httpx.Client(timeout=60) as client:
        embedding_uuid = _get_embedding_model_uuid(token, settings.gradient_embedding_model)
        res = client.post(
            f"{DO_GENAI_BASE}/knowledge_bases",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={
                "name": name,
                "description": description,
                "embedding_model_uuid": embedding_uuid,
                "region": settings.gradient_region,
                "project_id": project_id,
            },
        )
        if res.status_code >= 400:
            detail = res.text
            try:
                body = res.json()
                detail = body.get("message") or body.get("id") or detail
            except Exception:
                pass
            raise RuntimeError(f"Failed to create knowledge base: {detail}")
        payload = res.json()
        kb_uuid = payload.get("knowledge_base_uuid") or payload.get("knowledge_base", {}).get("uuid")
        if not kb_uuid:
            raise RuntimeError("Could not read knowledge base UUID from response")
        return kb_uuid


def knowledge_base_add_text_source(*, kb_uuid: str, filename: str, content: str) -> str:
    settings = get_settings()
    token = _require(settings.digitalocean_api_token, "DIGITALOCEAN_API_TOKEN")

    files = {"file": (filename, content.encode("utf-8"), "text/plain")}
    with httpx.Client(timeout=120) as client:
        res = client.post(
            f"{DO_GENAI_BASE}/knowledge_bases/{kb_uuid}/data_sources",
            headers={"Authorization": f"Bearer {token}"},
            files=files,
        )
        res.raise_for_status()
        payload = res.json()
        ds_uuid = payload.get("data_source_uuid") or payload.get("data_source", {}).get("uuid")
        return ds_uuid or ""


def knowledge_base_index(*, kb_uuid: str) -> None:
    settings = get_settings()
    token = _require(settings.digitalocean_api_token, "DIGITALOCEAN_API_TOKEN")
    with httpx.Client(timeout=120) as client:
        res = client.post(
            f"{DO_GENAI_BASE}/knowledge_bases/{kb_uuid}/index",
            headers={"Authorization": f"Bearer {token}"},
        )
        res.raise_for_status()


def attach_kb_to_agent(*, agent_uuid: str, kb_uuid: str) -> None:
    settings = get_settings()
    token = _require(settings.digitalocean_api_token, "DIGITALOCEAN_API_TOKEN")
    with httpx.Client(timeout=60) as client:
        res = client.post(
            f"{DO_GENAI_BASE}/agents/{agent_uuid}/knowledge_bases",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
            json={"knowledge_base_uuids": [kb_uuid]},
        )
        res.raise_for_status()


def extract_research_profile(lit_review_text: str) -> dict:
    settings = get_settings()
    endpoint = _require(settings.extraction_agent_endpoint, "EXTRACTION_AGENT_ENDPOINT")
    access_key = _require(settings.extraction_agent_access_key, "EXTRACTION_AGENT_ACCESS_KEY")

    prompt = (
        "Analyze this literature review and extract:\n"
        "1) Main research topic (1 sentence)\n"
        "2) Key keywords (5-10 terms)\n"
        "3) Research methodology\n"
        "4) Key research questions\n\n"
        "Respond with JSON ONLY using this schema:\n"
        "{\"topic\": string, \"keywords\": string[], \"methodology\": string|null, \"key_questions\": string[]}\n\n"
        f"LITERATURE REVIEW:\n{lit_review_text}\n"
    )
    content = agent_chat(endpoint=endpoint, access_key=access_key, prompt=prompt, max_tokens=2000)
    return _extract_json_object(content)


def run_router_monitoring(
    *,
    user_id: str,
    topic: str,
    keywords: list[str],
    date_after: str,
    kb_uuid: str,
    papers: list[dict],
    lit_review_text: str | None = None,
) -> dict:
    settings = get_settings()
    endpoint = _require(settings.router_agent_endpoint, "ROUTER_AGENT_ENDPOINT")
    access_key = _require(settings.router_agent_access_key, "ROUTER_AGENT_ACCESS_KEY")

    papers_payload = json.dumps(papers, ensure_ascii=False)

    # Truncate lit review to ~12 000 chars to stay well within context limits
    lit_review_snippet = ""
    if lit_review_text and lit_review_text.strip():
        truncated = lit_review_text.strip()[:12000]
        lit_review_snippet = f"""

LITERATURE REVIEW TEXT (use this as the reference document for comparison):
\"\"\"
{truncated}
\"\"\"
"""

    prompt = f"""
Monitor research topic for user {user_id}.

Topic: {topic}
Keywords: {', '.join(keywords)}
Date filter: Papers after {date_after}
Knowledge base UUID: {kb_uuid}
{lit_review_snippet}
PubMed papers to analyze (JSON):
{papers_payload}

Instructions:
1) Use ONLY the provided PubMed papers JSON as the candidate paper set
2) Compare each paper against the LITERATURE REVIEW TEXT provided above (or the attached knowledge base if available)
3) Generate findings in three categories:
     - contradiction: new evidence conflicts with an existing claim in the literature review
     - confirmation: new evidence supports an existing claim
     - addition: new evidence adds relevant information not currently covered
4) For each finding, include citations (PMID/DOI or title references) and a suggested update sentence
4a) Also include concise but specific evidence reasoning:
    - why this paper supports/conflicts/adds to the claim
    - practical implication for what the author should change
5) For paper_authors: copy the "authors" field verbatim from the matching paper in the JSON above. Never invent author names.
6) For paper_date: use the "year" field from the matching paper if available.
7) If no findings, return an empty findings array

Return JSON ONLY with schema:
{{
  "papers_checked": number,
    "findings": [
    {{
            "finding_kind": "contradiction"|"confirmation"|"addition",
      "paper_title": string,
      "paper_doi": string|null,
      "paper_authors": string|null,
      "paper_date": string|null,
            "contradiction_type": "direct"|"methodological"|"population"|"statistical"|"confirmation"|"addition"|string,
      "severity": "high"|"medium"|"low"|string,
      "user_section": string|null,
      "user_claim": string|null,
      "new_finding": string|null,
    "implication": string|null,
      "explanation": string,
      "suggested_update": string,
            "location": string|null,
            "citations": string[]
    }}
  ]
}}
"""

    content = agent_chat(endpoint=endpoint, access_key=access_key, prompt=prompt, max_tokens=50000)
    try:
        return _extract_json_object(content)
    except (ValueError, Exception):
        # Response was truncated mid-JSON — recover whatever complete findings were produced.
        partial = _recover_partial_findings(content)
        if partial is not None:
            return partial
        raise ValueError(f"Agent response was not valid JSON. Raw response (first 500 chars):\n{content[:500]}")


def generate_ai_revision_draft(
    *,
    topic: str,
    citation_style: str,
    source_text: str,
    findings: list[dict],
) -> dict:
    settings = get_settings()
    endpoint = _require(settings.router_agent_endpoint, "ROUTER_AGENT_ENDPOINT")
    access_key = _require(settings.router_agent_access_key, "ROUTER_AGENT_ACCESS_KEY")

    findings_payload = json.dumps(findings, ensure_ascii=False)

    prompt = f"""
You are revising a research paper draft using only explicitly provided evidence.

Topic: {topic}
Requested citation style: {citation_style}

Original draft text:
{source_text}

Evidence findings JSON (use only this evidence):
{findings_payload}

Hard rules:
1) Do not invent facts, citations, authors, dates, or claims.
2) Use only information present in the original draft text and the findings JSON.
3) If evidence is insufficient for a claim, omit the claim.
4) Preserve the original intent where possible while integrating supported updates.
5) For in-text citations and the references section, use the "paper_authors", "paper_date", "paper_title", and "paper_doi" fields from each finding. Format them in {citation_style} style. Never invent author names — if paper_authors is null, cite by title only.
6) If a citation field is incomplete, keep it minimal and clearly bounded to known fields only.

Return JSON only in this schema:
{{
  "revised_draft": string,
  "references": [string],
  "notes": [string]
}}
"""

    content = agent_chat(endpoint=endpoint, access_key=access_key, prompt=prompt, max_tokens=6000)
    parsed = _extract_json_object(content)
    revised_draft = str(parsed.get("revised_draft") or "").strip()
    references = parsed.get("references") or []
    notes = parsed.get("notes") or []

    if not isinstance(references, list):
        references = [str(references)]
    if not isinstance(notes, list):
        notes = [str(notes)]

    return {
        "revised_draft": revised_draft,
        "references": [str(r).strip() for r in references if str(r).strip()],
        "notes": [str(n).strip() for n in notes if str(n).strip()],
    }

