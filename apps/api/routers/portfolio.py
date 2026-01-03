"""Portfolio router."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.core.models import PortfolioSnapshot
from packages.core.schemas import PortfolioSnapshotResponse

router = APIRouter()


@router.get("/latest", response_model=PortfolioSnapshotResponse)
async def get_latest_portfolio(db: Session = Depends(get_db)):
    """Get latest portfolio snapshot."""
    snapshot = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.asof.desc()).first()
    if not snapshot:
        raise HTTPException(status_code=404, detail="No portfolio snapshot found")
    return PortfolioSnapshotResponse(
        id=snapshot.id,
        asof=snapshot.asof,
        mode=snapshot.mode,
        positions=snapshot.positions,
        cash=float(snapshot.cash),
        nav=float(snapshot.nav),
        created_at=snapshot.created_at,
    )

