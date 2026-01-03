"""Guards: kill switch, live trading, plan approval checks."""

import os
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from packages.core.models import Control, PlanStatus, RebalancePlan


class GuardError(Exception):
    """Guard error."""

    pass


def check_kill_switch(db: Session) -> None:
    """Check kill switch. Raises HTTPException if ON."""
    control = db.query(Control).filter(Control.id == 1).first()
    if not control:
        # Initialize if not exists
        control = Control(id=1, kill_switch=False)
        db.add(control)
        db.commit()
        return

    if control.kill_switch:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "KILL_SWITCH_ON",
                "message": "Kill switch is ON. Trading operations are disabled.",
                "reason": control.reason,
            },
        )


def check_live_trading_enabled() -> None:
    """Check if live trading is enabled. Raises HTTPException if disabled."""
    enable_live = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
    if not enable_live:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "LIVE_TRADING_DISABLED",
                "message": "Live trading is disabled in Phase 1. ENABLE_LIVE_TRADING must be true.",
            },
        )


def check_plan_approved(db: Session, plan_id: str) -> RebalancePlan:
    """Check if plan is approved. Raises HTTPException if not."""
    from uuid import UUID

    plan = db.query(RebalancePlan).filter(RebalancePlan.id == UUID(plan_id)).first()
    if not plan:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLAN_NOT_FOUND", "message": f"Plan {plan_id} not found"},
        )

    if plan.status != PlanStatus.APPROVED:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "PLAN_NOT_APPROVED",
                "message": f"Plan {plan_id} is not approved. Current status: {plan.status.value}",
            },
        )

    return plan


def check_trading_mode(mode: str) -> None:
    """Check trading mode. Raises HTTPException if LIVE and not enabled."""
    if mode.upper() == "LIVE":
        check_live_trading_enabled()

