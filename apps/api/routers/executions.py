"""Executions router."""

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.main import get_db
from packages.core.models import Execution, ExecutionStatus
from packages.core.schemas import ExecutionResponse, ExecutionStartRequest
from packages.ops.guards import check_kill_switch, check_plan_approved

router = APIRouter()


@router.post("/{plan_id}/start", response_model=ExecutionResponse)
async def start_execution(
    plan_id: UUID,
    request: ExecutionStartRequest,
    db: Session = Depends(get_db),
):
    """Start execution (idempotent)."""
    # Check kill switch
    check_kill_switch(db)

    # Check plan approved (raises if not approved)
    check_plan_approved(db, str(plan_id))

    # Check if execution already exists (idempotency)
    existing = db.query(Execution).filter(Execution.plan_id == plan_id).first()
    if existing:
        return ExecutionResponse(
            id=existing.id,
            plan_id=existing.plan_id,
            status=existing.status,
            started_at=existing.started_at,
            ended_at=existing.ended_at,
            policy=existing.policy,
            error=existing.error,
        )

    # Create execution
    execution = Execution(
        plan_id=plan_id,
        status=ExecutionStatus.PENDING,
        policy=request.policy,
    )
    db.add(execution)
    db.commit()
    db.refresh(execution)

    return ExecutionResponse(
        id=execution.id,
        plan_id=execution.plan_id,
        status=execution.status,
        started_at=execution.started_at,
        ended_at=execution.ended_at,
        policy=execution.policy,
        error=execution.error,
    )


@router.get("", response_model=list[ExecutionResponse])
async def list_executions(
    status: ExecutionStatus | None = Query(None),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    db: Session = Depends(get_db),
):
    """List executions."""
    query = db.query(Execution)
    if status:
        query = query.filter(Execution.status == status)
    # TODO: Add date filters
    executions = query.order_by(Execution.started_at.desc()).all()

    return [
        ExecutionResponse(
            id=e.id,
            plan_id=e.plan_id,
            status=e.status,
            started_at=e.started_at,
            ended_at=e.ended_at,
            policy=e.policy,
            error=e.error,
        )
        for e in executions
    ]


@router.get("/{execution_id}", response_model=ExecutionResponse)
async def get_execution(execution_id: UUID, db: Session = Depends(get_db)):
    """Get execution."""
    execution = db.query(Execution).filter(Execution.id == execution_id).first()
    if not execution:
        raise HTTPException(status_code=404, detail="Execution not found")

    return ExecutionResponse(
        id=execution.id,
        plan_id=execution.plan_id,
        status=execution.status,
        started_at=execution.started_at,
        ended_at=execution.ended_at,
        policy=execution.policy,
        error=execution.error,
    )
