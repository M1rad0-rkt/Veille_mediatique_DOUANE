import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import api_router
from app.core.config import settings
from app.core.limiter import limiter
from app.database.seed import seed, seed_sources
from app.database.session import SessionLocal

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(_: FastAPI):
    with SessionLocal() as db:
        seed(db)  # idempotent : rôles, catégories, premier admin
        seed_sources(db)
    yield


app = FastAPI(title=settings.app_name, version="0.5.0", lifespan=lifespan,
              docs_url="/api/docs" if settings.environment != "production" else None,
              redoc_url=None, openapi_url="/api/openapi.json" if settings.environment != "production" else None)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])

app.include_router(api_router)


@app.get("/api/health", tags=["health"])
def health():
    return {"status": "ok"}
