from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import OperationalError

from backend.core.config import get_settings
from backend.db.base import Base
from backend.db import models  # noqa: F401


def main():
    settings = get_settings()
    url = make_url(settings.database_url)
    engine = create_engine(settings.database_url, pool_pre_ping=True)

    try:
        Base.metadata.create_all(bind=engine)
        _apply_minimal_migrations(engine)
        print("Database tables created/verified.")
        return
    except OperationalError as e:
        message = str(e).lower()
        if "does not exist" not in message or not url.database:
            raise

    db_name = url.database
    admin_url = url.set(database="postgres")
    admin_engine = create_engine(admin_url, pool_pre_ping=True)

    with admin_engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text(f'CREATE DATABASE "{db_name}"'))

    Base.metadata.create_all(bind=engine)
    _apply_minimal_migrations(engine)
    print(f"Database '{db_name}' created and tables initialized.")


def _apply_minimal_migrations(engine) -> None:
    """Best-effort schema upgrades for early dev iterations.

    For production, replace this with Alembic migrations.
    """

    # These columns were added after initial scaffold.
    statements = [
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS password_hash TEXT;",
        "ALTER TABLE IF EXISTS users ADD COLUMN IF NOT EXISTS email_verified_at TIMESTAMPTZ;",
        "ALTER TABLE IF EXISTS project_profiles ADD COLUMN IF NOT EXISTS monitoring_active BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE IF EXISTS project_profiles ADD COLUMN IF NOT EXISTS include_validation BOOLEAN DEFAULT TRUE;",
        "ALTER TABLE IF EXISTS project_profiles ADD COLUMN IF NOT EXISTS last_checked_at TIMESTAMPTZ;",
        "ALTER TABLE IF EXISTS project_profiles ADD COLUMN IF NOT EXISTS ai_revision_tab_id VARCHAR(255);",
        "ALTER TABLE IF EXISTS project_profiles ADD COLUMN IF NOT EXISTS ai_revision_tab_title VARCHAR(200);",
        "ALTER TABLE IF EXISTS monitoring_jobs ADD COLUMN IF NOT EXISTS project_id UUID;",
        "ALTER TABLE IF EXISTS findings ADD COLUMN IF NOT EXISTS project_id UUID;",
    ]

    with engine.connect() as conn:
        conn = conn.execution_options(isolation_level="AUTOCOMMIT")
        for stmt in statements:
            conn.execute(text(stmt))

        # Backfill monitoring_active for existing rows that may have NULL.
        try:
            conn.execute(text("UPDATE project_profiles SET monitoring_active = TRUE WHERE monitoring_active IS NULL;"))
        except Exception:
            pass

        try:
            conn.execute(text("UPDATE project_profiles SET include_validation = TRUE WHERE include_validation IS NULL;"))
        except Exception:
            pass

        # Best-effort NOT NULL (ignore if it fails)
        try:
            conn.execute(text("ALTER TABLE project_profiles ALTER COLUMN monitoring_active SET NOT NULL;"))
        except Exception:
            pass

        try:
            conn.execute(text("ALTER TABLE project_profiles ALTER COLUMN include_validation SET NOT NULL;"))
        except Exception:
            pass

        # Best-effort foreign keys (ignore if already exist)
        try:
            conn.execute(
                text(
                    "ALTER TABLE monitoring_jobs ADD CONSTRAINT monitoring_jobs_project_id_fkey "
                    "FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;"
                )
            )
        except Exception:
            pass

        try:
            conn.execute(
                text(
                    "ALTER TABLE findings ADD CONSTRAINT findings_project_id_fkey "
                    "FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE;"
                )
            )
        except Exception:
            pass


if __name__ == "__main__":
    main()
