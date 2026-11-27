from fastapi import APIRouter

from app.api import admin, agent, auth, categories, news, sources

api_router = APIRouter(prefix="/api")
for module in (auth, news, categories, sources, admin, agent):
    api_router.include_router(module.router)
