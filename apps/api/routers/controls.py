"""Controls router."""

from datetime import datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.core.models import Control
from packages.core.schemas import ControlResponse, KillSwitchRequest

router = APIRouter()


@router.get("", response_model=ControlResponse)
async def get_controls(db: Session = Depends(get_db)):
    """Get controls."""
    control = db.query(Control).filter(Control.id == 1).first()
    if not control:
        # Initialize
        control = Control(id=1, kill_switch=False)
        db.add(control)
        db.commit()
        db.refresh(control)
    return ControlResponse(
        kill_switch=control.kill_switch,
        reason=control.reason,
        updated_at=control.updated_at,
    )


@router.post("/kill-switch")
async def set_kill_switch(
    request: KillSwitchRequest,
    db: Session = Depends(get_db),
):
    """Set kill switch."""
    control = db.query(Control).filter(Control.id == 1).first()
    if not control:
        control = Control(id=1, kill_switch=request.on, reason=request.reason)
        db.add(control)
    else:
        control.kill_switch = request.on
        control.reason = request.reason
        control.updated_at = datetime.utcnow()
    db.commit()
    return {"status": "ok", "kill_switch": control.kill_switch}
