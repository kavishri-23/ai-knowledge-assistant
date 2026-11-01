"""FastAPI application factory."""

import logging
import threading
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings, get_settings
from app.routers import ask, documents
from app.services.container import Services, build_services

log = logging.getLogger("app")


def create_app(settings: Settings | None = None, services: Services | None = None) -> FastAPI:
    """Build the app. Tests pass in their own settings and fake services."""
    settings = settings or get_settings()
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        svc = services or build_services(settings)
        svc.registry.fail_interrupted()
        app.state.services = svc
        if services is None:  # real run: load the embedding model in the background
            threading.Thread(target=svc.embedder.warm_up, daemon=True).start()
        yield

    app = FastAPI(title="AI Knowledge Assistant", version="2.0.0", lifespan=lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        request_id = uuid.uuid4().hex[:8]
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            log.exception("request=%s %s %s crashed", request_id, request.method, request.url.path)
            raise
        response.headers["X-Request-ID"] = request_id
        log.info(
            "request=%s %s %s -> %d in %.0f ms",
            request_id, request.method, request.url.path,
            response.status_code, (time.perf_counter() - started) * 1000,
        )
        return response

    app.include_router(documents.router)
    app.include_router(ask.router)

    @app.get("/health", tags=["meta"])
    def health(request: Request):
        llm = request.app.state.services.llm
        return {"status": "ok", "ollama_reachable": llm.ping()}

    return app


app = create_app()
