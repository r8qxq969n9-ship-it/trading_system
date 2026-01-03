"""Data router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.core.models import DataSnapshot
from packages.core.schemas import DataSnapshotCreate, DataSnapshotResponse

router = APIRouter()


@router.post("/snapshot", response_model=DataSnapshotResponse)
async def create_snapshot(
    request: DataSnapshotCreate,
    db: Session = Depends(get_db),
):
    """Create data snapshot."""
    snapshot = DataSnapshot(
        source=request.source,
        asof=request.asof,
        meta=request.meta,
    )
    db.add(snapshot)
    db.commit()
    db.refresh(snapshot)
    return DataSnapshotResponse(
        id=snapshot.id,
        source=snapshot.source,
        asof=snapshot.asof,
        meta=snapshot.meta,
        created_at=snapshot.created_at,
    )

