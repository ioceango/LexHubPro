from fastapi import APIRouter, HTTPException, status

from services.database import check_database_health

router = APIRouter(tags=["health"])


@router.get("/api/v1/health")
async def app_health():
    """就绪检查：进程已起来且数据库可连。供 compose healthcheck 使用。"""
    is_healthy = await check_database_health()
    if not is_healthy:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        )
    return {"status": "healthy", "database": "ok", "service": "lexhubpro"}


@router.get("/database/health")
async def database_health_check():
    """Check database connection health"""
    is_healthy = await check_database_health()
    return {"status": "healthy" if is_healthy else "unhealthy", "service": "database"}
