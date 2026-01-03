"""Plans router."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.core.models import PlanItem, PlanStatus, RebalancePlan, Run, RunKind, RunStatus
from packages.core.schemas import (
    PlanApproveRequest,
    PlanGenerateRequest,
    PlanItemResponse,
    PlanRejectRequest,
    PlanResponse,
)

router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate plan (stub)."""
    # TODO: Implement actual plan generation
    # For now, create a stub plan
    run = Run(kind=RunKind.PLAN, status=RunStatus.STARTED)
    db.add(run)
    db.commit()

    plan = RebalancePlan(
        run_id=run.id,
        config_version_id=request.config_version_id or UUID("00000000-0000-0000-0000-000000000001"),
        data_snapshot_id=request.data_snapshot_id or UUID("00000000-0000-0000-0000-000000000001"),
        status=PlanStatus.PROPOSED,
        summary={"stub": True},
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return PlanResponse(
        id=plan.id,
        run_id=plan.run_id,
        config_version_id=plan.config_version_id,
        data_snapshot_id=plan.data_snapshot_id,
        status=plan.status,
        summary=plan.summary,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        approved_by=plan.approved_by,
        rejected_at=plan.rejected_at,
        rejected_by=plan.rejected_by,
        expires_at=plan.expires_at,
        items=[],
    )


@router.get("", response_model=list[PlanResponse])
async def list_plans(
    status: PlanStatus | None = Query(None),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """List plans."""
    query = db.query(RebalancePlan)
    if status:
        query = query.filter(RebalancePlan.status == status)
    if from_date:
        query = query.filter(RebalancePlan.created_at >= from_date)
    if to_date:
        query = query.filter(RebalancePlan.created_at <= to_date)
    plans = query.order_by(RebalancePlan.created_at.desc()).all()

    result = []
    for plan in plans:
        items = db.query(PlanItem).filter(PlanItem.plan_id == plan.id).all()
        result.append(
            PlanResponse(
                id=plan.id,
                run_id=plan.run_id,
                config_version_id=plan.config_version_id,
                data_snapshot_id=plan.data_snapshot_id,
                status=plan.status,
                summary=plan.summary,
                created_at=plan.created_at,
                approved_at=plan.approved_at,
                approved_by=plan.approved_by,
                rejected_at=plan.rejected_at,
                rejected_by=plan.rejected_by,
                expires_at=plan.expires_at,
                items=[
                    PlanItemResponse(
                        id=item.id,
                        symbol=item.symbol,
                        market=item.market,
                        current_weight=float(item.current_weight),
                        target_weight=float(item.target_weight),
                        delta_weight=float(item.delta_weight),
                        reason=item.reason,
                        checks=item.checks,
                    )
                    for item in items
                ],
            )
        )
    return result


@router.get("/{plan_id}", response_model=PlanResponse)
async def get_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Get plan."""
    plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    items = db.query(PlanItem).filter(PlanItem.plan_id == plan.id).all()
    return PlanResponse(
        id=plan.id,
        run_id=plan.run_id,
        config_version_id=plan.config_version_id,
        data_snapshot_id=plan.data_snapshot_id,
        status=plan.status,
        summary=plan.summary,
        created_at=plan.created_at,
        approved_at=plan.approved_at,
        approved_by=plan.approved_by,
        rejected_at=plan.rejected_at,
        rejected_by=plan.rejected_by,
        expires_at=plan.expires_at,
        items=[
            PlanItemResponse(
                id=item.id,
                symbol=item.symbol,
                market=item.market,
                current_weight=float(item.current_weight),
                target_weight=float(item.target_weight),
                delta_weight=float(item.delta_weight),
                reason=item.reason,
                checks=item.checks,
            )
            for item in items
        ],
    )


@router.post("/{plan_id}/approve")
async def approve_plan(
    plan_id: UUID,
    request: PlanApproveRequest,
    db: Session = Depends(get_db),
):
    """Approve plan."""
    plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")
    if plan.status != PlanStatus.PROPOSED:
        raise HTTPException(
            status_code=400, detail=f"Plan is not PROPOSED (current: {plan.status.value})"
        )

    plan.status = PlanStatus.APPROVED
    plan.approved_at = datetime.utcnow()
    plan.approved_by = request.approved_by
    db.commit()

    return {"status": "approved", "plan_id": str(plan_id)}


@router.post("/{plan_id}/reject")
async def reject_plan(
    plan_id: UUID,
    request: PlanRejectRequest,
    db: Session = Depends(get_db),
):
    """Reject plan."""
    plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = PlanStatus.REJECTED
    plan.rejected_at = datetime.utcnow()
    plan.rejected_by = request.rejected_by
    db.commit()

    return {"status": "rejected", "plan_id": str(plan_id)}


@router.post("/{plan_id}/expire")
async def expire_plan(plan_id: UUID, db: Session = Depends(get_db)):
    """Expire plan."""
    plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    plan.status = PlanStatus.EXPIRED
    db.commit()

    return {"status": "expired", "plan_id": str(plan_id)}
