from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.api.v1.health.schemas import LivenessResponse, ReadinessResponse
from app.common.dependencies import get_connection, get_object_storage

router = APIRouter(tags=["health"])


@router.get("/health/live", response_model=LivenessResponse)
def liveness() -> LivenessResponse:
    """Liveness probe: reports that the process is up."""
    return LivenessResponse(status="alive")


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessResponse, "description": "Database or object storage is unreachable."}},
)
async def readiness():
    """Readiness probe (NFR-013 AC-08).

    Reports ``ready`` only when both the primary database and the configured
    object-storage backend are reachable. A storage outage flips readiness to
    HTTP 503 so the pod is taken out of rotation until storage recovers.
    """
    conn = get_connection()
    db_ok = conn.is_connected()

    try:
        storage_status = await get_object_storage().health_check()
        storage_ok = bool(storage_status.get("ready"))
    except Exception:  # noqa: BLE001 — any storage failure means not-ready
        storage_ok = False

    overall_ok = db_ok and storage_ok
    body = {
        "status": "ready" if overall_ok else "not_ready",
        "database": db_ok,
        "object_storage": storage_ok,
    }
    if overall_ok:
        return body
    return JSONResponse(status_code=503, content=body)


@router.post("/falsification-probe-1404")
def _falsification_probe() -> dict[str, str]:
    """Ungated write route — this branch exists only to prove the lane blocks."""
    return {"ok": "never merged"}
