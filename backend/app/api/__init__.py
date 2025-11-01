from fastapi import APIRouter, Depends

from app.core.security import verify_api_key

from .routes import documents, health, search

public_router = APIRouter()
public_router.include_router(health.router, prefix="/health")

protected_router = APIRouter(dependencies=[Depends(verify_api_key)])
protected_router.include_router(documents.router)
protected_router.include_router(search.router)
