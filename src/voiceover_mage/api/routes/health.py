# ABOUTME: Health check endpoints for API monitoring
# ABOUTME: Provides service status and database connectivity checks

from fastapi import APIRouter, Depends

from voiceover_mage.api.dependencies import get_db_manager
from voiceover_mage.api.models import HealthResponse
from voiceover_mage.persistence.manager import DatabaseManager

router = APIRouter()


@router.get(
    "/health",
    response_model=HealthResponse,
    summary="Health check",
    description="Check API service status and database connectivity",
)
async def health_check(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> HealthResponse:
    """Health check endpoint.

    Returns service status and database connectivity information.

    Args:
        db_manager: Database manager dependency

    Returns:
        HealthResponse with status information
    """
    # Test database connectivity
    db_status = "unknown"
    try:
        # Simple query to test connection
        async with db_manager.async_session() as session:
            await session.connection()
        db_status = "connected"
    except Exception:
        db_status = "disconnected"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "degraded",
        version="0.1.0",
        database=db_status,
    )
