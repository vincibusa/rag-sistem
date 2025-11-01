from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import protected_router, public_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, logger


def create_application() -> FastAPI:
    configure_logging()

    app = FastAPI(
        title=settings.project_name,
        debug=settings.debug,
        version="0.1.0",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(public_router, prefix=settings.api_v1_prefix)
    app.include_router(protected_router, prefix=settings.api_v1_prefix)

    register_exception_handlers(app)

    @app.on_event("startup")
    async def on_startup() -> None:
        logger.info("Application startup complete", extra={"environment": settings.environment})

    @app.on_event("shutdown")
    async def on_shutdown() -> None:
        logger.info("Application shutdown")

    return app


app = create_application()
