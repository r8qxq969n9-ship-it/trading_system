"""Health check router."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.ops.health import check_health

router = APIRouter()


@router.get("")
async def health_check(db: Session = Depends(get_db)):
    """Health check endpoint."""
    health_data = check_health(db)
    return health_data
