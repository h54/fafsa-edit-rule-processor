from fastapi import APIRouter

router = APIRouter(tags=["core"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}
