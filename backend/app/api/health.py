import logging
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from app import db
from app.config import Settings, get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: Literal["ok", "unavailable", "not_configured"]


@router.get("/api/health")
async def health(
    response: Response, settings: Annotated[Settings, Depends(get_settings)]
) -> HealthResponse:
    if not settings.database_url:
        return HealthResponse(status="ok", db="not_configured")
    try:
        await db.ping(settings.database_url)
    except Exception:
        logger.exception("Database health check failed")
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return HealthResponse(status="degraded", db="unavailable")
    return HealthResponse(status="ok", db="ok")
