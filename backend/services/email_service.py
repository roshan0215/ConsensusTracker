from __future__ import annotations

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.core.config import get_settings


def send_email(to: str, subject: str, html_body: str) -> None:
    settings = get_settings()

    if not settings.gmail_user or not settings.gmail_app_password:
        raise RuntimeError("GMAIL_USER and GMAIL_APP_PASSWORD are required")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.gmail_user
    msg["To"] = to
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(settings.gmail_user, settings.gmail_app_password)
        smtp.send_message(msg)


def render_contradiction_email(findings: list[dict]) -> str:
    items = "".join(
        f"<li><b>{f.get('paper_title','')}</b> — {f.get('severity','')} ({f.get('finding_kind') or f.get('contradiction_type','')})</li>"
        for f in findings
    )
    return f"<h2>ConsensusTracker Alert</h2><p>New findings identified:</p><ul>{items}</ul>"
