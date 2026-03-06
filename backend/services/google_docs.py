from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend.core.config import get_settings


_DOC_ID_RE = re.compile(r"/d/([a-zA-Z0-9_-]+)")
_DOC_ID_ALT_RE = re.compile(r"[?&]id=([a-zA-Z0-9_-]+)")


def _make_creds(user_id: str | None, scopes: list[str]):
    """Return Google credentials.

    Tries the user's stored OAuth tokens first (if user_id given and tokens
    exist). Falls back to the service account.
    """
    settings = get_settings()

    if user_id and settings.google_oauth_client_id and settings.google_oauth_client_secret:
        try:
            from backend.db.models import User as _User
            from backend.db.session import db_session as _db_session
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials

            with _db_session() as _session:
                u = _session.query(_User).filter(_User.id == user_id).one_or_none()
                if u and u.google_refresh_token:
                    needs_refresh = (
                        not u.google_access_token
                        or (
                            u.google_token_expires_at is not None
                            and u.google_token_expires_at < datetime.now(tz=timezone.utc) + timedelta(seconds=60)
                        )
                    )
                    creds = Credentials(
                        token=u.google_access_token,
                        refresh_token=u.google_refresh_token,
                        token_uri="https://oauth2.googleapis.com/token",
                        client_id=settings.google_oauth_client_id,
                        client_secret=settings.google_oauth_client_secret,
                        scopes=scopes,
                    )
                    if needs_refresh:
                        creds.refresh(Request())
                        u.google_access_token = creds.token
                        if creds.expiry:
                            u.google_token_expires_at = creds.expiry.replace(tzinfo=timezone.utc)
                    return creds
        except Exception:
            pass  # fall through to service account

    # Service account fallback
    if not settings.google_service_account_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON is required (or user must connect Google)")
    sa_path = _resolve_path_from_repo_root(settings.google_service_account_json)
    if not sa_path.exists():
        raise RuntimeError(f"GOOGLE_SERVICE_ACCOUNT_JSON file not found: {sa_path}")
    from google.oauth2 import service_account
    return service_account.Credentials.from_service_account_file(str(sa_path), scopes=scopes)


def extract_google_doc_id(url: str) -> str | None:
    match = _DOC_ID_RE.search(url)
    if match:
        return match.group(1)
    match = _DOC_ID_ALT_RE.search(url)
    if match:
        return match.group(1)
    return None


@dataclass
class GoogleDocContent:
    doc_id: str
    text: str


@dataclass
class GoogleDocTab:
    tab_id: str
    title: str


def download_google_doc_as_text(google_doc_url: str, user_id: str | None = None) -> GoogleDocContent:
    doc_id = extract_google_doc_id(google_doc_url)
    if not doc_id:
        raise ValueError("Could not parse Google Doc ID from URL")

    from googleapiclient.discovery import build
    creds = _make_creds(user_id, [
        "https://www.googleapis.com/auth/documents.readonly",
        "https://www.googleapis.com/auth/drive",
    ])
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = docs_service.documents().get(documentId=doc_id).execute()

    text_parts: list[str] = []
    for element in doc.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for pe in paragraph.get("elements", []):
            tr = pe.get("textRun")
            if tr and "content" in tr:
                text_parts.append(tr["content"])

    return GoogleDocContent(doc_id=doc_id, text="".join(text_parts))


def get_google_doc_tab_by_title(doc_id: str, title: str, user_id: str | None = None) -> GoogleDocTab | None:
    from googleapiclient.discovery import build
    creds = _make_creds(user_id, ["https://www.googleapis.com/auth/documents.readonly"])
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)
    doc = docs_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()

    target = title.strip()
    for tab in _flatten_tabs(doc):
        props = (tab or {}).get("tabProperties") or {}
        if (props.get("title") or "").strip() == target:
            tab_id = props.get("tabId")
            if tab_id:
                return GoogleDocTab(tab_id=tab_id, title=props.get("title") or target)
    return None


def ensure_google_doc_tab(doc_id: str, title: str, user_id: str | None = None) -> GoogleDocTab:
    from googleapiclient.discovery import build
    normalized_title = title.strip() or "AI-Revision"
    creds = _make_creds(user_id, ["https://www.googleapis.com/auth/documents"])
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)

    before_doc = docs_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
    existing = _find_tab_by_title(before_doc, normalized_title)
    if existing:
        return existing

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "addDocumentTab": {
                        "tabProperties": {
                            "title": normalized_title,
                        }
                    }
                }
            ]
        },
    ).execute()

    after_doc = docs_service.documents().get(documentId=doc_id, includeTabsContent=True).execute()
    created = _find_tab_by_title(after_doc, normalized_title)
    if created:
        return created
    raise RuntimeError("Created tab but could not resolve tab ID")


def add_google_doc_comment(doc_id: str, comment_text: str, location: str | None = None, user_id: str | None = None) -> None:
    full_comment = comment_text if not location else f"[{location}]\n{comment_text}"

    from googleapiclient.discovery import build
    creds = _make_creds(user_id, ["https://www.googleapis.com/auth/drive"])
    drive_service = build("drive", "v3", credentials=creds, cache_discovery=False)

    drive_service.comments().create(
        fileId=doc_id,
        body={"content": full_comment},
        fields="id",
    ).execute()


def append_google_doc_ai_references(doc_id: str, references: list[str], run_label: str | None = None, user_id: str | None = None) -> None:
    if not references:
        return

    from googleapiclient.discovery import build
    creds = _make_creds(user_id, ["https://www.googleapis.com/auth/documents"])
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)

    doc = docs_service.documents().get(documentId=doc_id).execute()
    end_index = doc.get("body", {}).get("content", [])[-1].get("endIndex", 1)
    insert_at = max(1, end_index - 1)

    label = f" ({run_label})" if run_label else ""
    heading = f"[AI-ADDED REFERENCES]{label}"
    refs_text = "\n".join(f"- {ref}" for ref in references)
    block = f"\n\n{heading}\n{refs_text}\n"

    start_index = insert_at
    end_block_index = start_index + len(block)
    heading_start = start_index + 2  # skip leading \n\n
    heading_end = heading_start + len(heading)

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "location": {"index": start_index},
                        "text": block,
                    }
                },
                {
                    "updateTextStyle": {
                        "range": {"startIndex": heading_start, "endIndex": heading_end},
                        "textStyle": {"bold": True},
                        "fields": "bold",
                    }
                },
                {
                    "updateTextStyle": {
                        "range": {"startIndex": heading_start, "endIndex": end_block_index},
                        "textStyle": {
                            "backgroundColor": {
                                "color": {
                                    "rgbColor": {
                                        "red": 1.0,
                                        "green": 0.97,
                                        "blue": 0.75,
                                    }
                                }
                            }
                        },
                        "fields": "backgroundColor",
                    }
                },
            ]
        },
    ).execute()


def append_text_to_google_doc_tab(doc_id: str, tab_id: str, text: str, user_id: str | None = None) -> None:
    if not text:
        return

    from googleapiclient.discovery import build
    creds = _make_creds(user_id, ["https://www.googleapis.com/auth/documents"])
    docs_service = build("docs", "v1", credentials=creds, cache_discovery=False)

    docs_service.documents().batchUpdate(
        documentId=doc_id,
        body={
            "requests": [
                {
                    "insertText": {
                        "text": text,
                        "endOfSegmentLocation": {
                            "tabId": tab_id,
                        },
                    }
                }
            ]
        },
    ).execute()


def _resolve_path_from_repo_root(path_str: str) -> Path:
    """Resolve relative paths from the project root (folder containing backend/).

    This lets `.env` set GOOGLE_SERVICE_ACCOUNT_JSON to just a filename when the
    key JSON is placed in the repo root.
    """

    p = Path(path_str)
    if p.is_absolute():
        return p
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / p


def _flatten_tabs(document_payload: dict[str, Any]) -> list[dict[str, Any]]:
    tabs = document_payload.get("tabs") or []
    flat: list[dict[str, Any]] = []
    for tab in tabs:
        _append_tab_recursive(tab, flat)
    return flat


def _append_tab_recursive(tab: dict[str, Any], output: list[dict[str, Any]]) -> None:
    output.append(tab)
    for child in (tab or {}).get("childTabs") or []:
        _append_tab_recursive(child, output)


def _find_tab_by_title(document_payload: dict[str, Any], title: str) -> GoogleDocTab | None:
    target = (title or "").strip()
    for tab in _flatten_tabs(document_payload):
        props = (tab or {}).get("tabProperties") or {}
        tab_title = (props.get("title") or "").strip()
        if tab_title != target:
            continue
        tab_id = props.get("tabId")
        if tab_id:
            return GoogleDocTab(tab_id=tab_id, title=props.get("title") or target)
    return None
