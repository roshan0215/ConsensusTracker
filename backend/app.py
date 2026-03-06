from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.core.config import get_settings
from backend.routes.dashboard import router as dashboard_router
from backend.routes.auth import router as auth_router
from backend.routes.oauth import router as oauth_router
from backend.routes.cron import router as cron_router
from backend.routes.health import router as health_router
from backend.routes.monitoring import router as monitoring_router
from backend.routes.onboarding import router as onboarding_router
from backend.routes.projects import router as projects_router


def create_app() -> FastAPI:
    settings = get_settings()
    if settings.environment in {"staging", "production"} and not settings.secret_key:
        raise RuntimeError("SECRET_KEY must be set in staging/production")
    app = FastAPI(title=settings.app_name)

    if settings.environment == "development":
        # Completely permissive CORS for local dev to avoid browser blocks.
        # NOTE: allow_credentials must be False when allow_origins is '*'.
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    else:
        origins = [o.strip() for o in settings.cors_allow_origins.split(",") if o.strip()]
        app.add_middleware(
            CORSMiddleware,
            allow_origins=origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(oauth_router)
    app.include_router(cron_router)
    app.include_router(onboarding_router)
    app.include_router(dashboard_router)
    app.include_router(monitoring_router)
    app.include_router(projects_router)
    return app


app = create_app()
