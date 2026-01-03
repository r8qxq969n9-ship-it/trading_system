"""Executions router."""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from packages.brokers import get_broker
from packages.core.models import (
    AlertLevel,
    Execution,
    ExecutionStatus,
    Fill,
    Order,
    OrderSide,
    OrderStatus,
    PlanItem,
    PortfolioSnapshot,
    RebalancePlan,
    Run,
    RunKind,
    RunStatus,
)
from packages.core.order_builder import OrderBuilder
from packages.core.schemas import ExecutionResponse, ExecutionStartRequest
from packages.ops.audit import record_audit_event
from packages.ops.guards import check_kill_switch, check_plan_approved
from packages.ops.slack import send

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
        # If already DONE, return as-is
        if existing.status == ExecutionStatus.DONE:
            return ExecutionResponse(
                id=existing.id,
                plan_id=existing.plan_id,
                status=existing.status,
                started_at=existing.started_at,
                ended_at=existing.ended_at,
                policy=existing.policy,
                error=existing.error,
            )
        # If RUNNING, continue execution (idempotent)
        execution = existing
    else:
        # Create execution
        execution = Execution(
            plan_id=plan_id,
            status=ExecutionStatus.PENDING,
            policy=request.policy,
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

    # Get plan
    plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found")

    # Get plan items
    plan_items = db.query(PlanItem).filter(PlanItem.plan_id == plan_id).all()
    if not plan_items:
        raise HTTPException(status_code=400, detail="Plan has no items")

    # 1. Create Run
    run = Run(kind=RunKind.EXECUTE, status=RunStatus.STARTED)
    db.add(run)
    db.commit()

    # 2. Update execution status
    execution.status = ExecutionStatus.RUNNING
    execution.started_at = datetime.utcnow()
    db.commit()

    # 3. Get latest portfolio snapshot
    portfolio_snapshot = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.asof.desc()).first()
    if not portfolio_snapshot:
        execution.status = ExecutionStatus.FAILED
        execution.error = "No portfolio snapshot found"
        execution.ended_at = datetime.utcnow()
        run.status = RunStatus.FAILED
        run.error = "No portfolio snapshot found"
        db.commit()
        raise HTTPException(status_code=404, detail="No portfolio snapshot found")

    cash_available = float(portfolio_snapshot.cash)
    nav = float(portfolio_snapshot.nav)

    # 4. Get broker for quotes
    broker = get_broker()

    # 5. Convert plan items to dict with current_price
    plan_items_dict = []
    symbols = [item.symbol for item in plan_items]
    quotes = broker.get_quotes(symbols)
    quote_map = {q.symbol: q.price for q in quotes}

    for item in plan_items:
        current_price = quote_map.get(item.symbol, 100.0)  # Default stub price
        plan_items_dict.append(
            {
                "symbol": item.symbol,
                "market": item.market.value,
                "current_weight": float(item.current_weight),
                "target_weight": float(item.target_weight),
                "delta_weight": float(item.delta_weight),
                "current_price": current_price,
            }
        )

    # 6. Build orders (SELL → BUY)
    order_dicts = OrderBuilder.build_orders(plan_items_dict, cash_available, nav)

    # 7. Execute orders (Paper mode: immediate fill)
    cash_remaining = cash_available
    positions = dict(portfolio_snapshot.positions or {})

    for order_dict in order_dicts:
        symbol = order_dict["symbol"]
        side = order_dict["side"]
        qty = float(order_dict["qty"])
        limit_price = float(order_dict.get("limit_price", 0))

        # Check if skipped
        if order_dict.get("status") == "SKIPPED":
            order = Order(
                plan_id=plan_id,
                execution_id=execution.id,
                symbol=symbol,
                side=OrderSide(side),
                qty=Decimal(str(qty)),
                order_type=order_dict.get("order_type", "LIMIT"),
                limit_price=Decimal(str(limit_price)) if limit_price else None,
                status=OrderStatus.SKIPPED,
                error=order_dict.get("error"),
            )
            db.add(order)
            continue

        # Create order
        order = Order(
            plan_id=plan_id,
            execution_id=execution.id,
            symbol=symbol,
            side=OrderSide(side),
            qty=Decimal(str(qty)),
            order_type=order_dict.get("order_type", "LIMIT"),
            limit_price=Decimal(str(limit_price)) if limit_price else None,
            status=OrderStatus.CREATED,
        )
        db.add(order)
        db.commit()
        db.refresh(order)

        # Paper mode: immediate fill
        filled_price = limit_price
        filled_qty = qty

        # Create fill
        fill = Fill(
            order_id=order.id,
            filled_qty=Decimal(str(filled_qty)),
            filled_price=Decimal(str(filled_price)),
            filled_at=datetime.utcnow(),
        )
        db.add(fill)

        # Update order status
        order.status = OrderStatus.FILLED
        order.broker_order_id = f"PAPER_{order.id}"

        # Update cash and positions
        if side == OrderSide.SELL.value:
            cash_remaining += filled_qty * filled_price
            current_qty = positions.get(symbol, 0)
            positions[symbol] = current_qty - filled_qty
            if positions[symbol] <= 0:
                positions.pop(symbol, None)
        else:  # BUY
            cost = filled_qty * filled_price
            cash_remaining -= cost
            current_qty = positions.get(symbol, 0)
            positions[symbol] = current_qty + filled_qty

        db.commit()

    # 8. Update execution status
    execution.status = ExecutionStatus.DONE
    execution.ended_at = datetime.utcnow()
    run.status = RunStatus.DONE
    run.ended_at = datetime.utcnow()
    db.commit()

    # 9. Record audit event
    record_audit_event(
        db=db,
        event_type="execution_completed",
        actor="system",
        ref_type="execution",
        ref_id=execution.id,
        payload={"plan_id": str(plan_id), "orders_count": len(order_dicts)},
    )

    # 10. Send Slack notification (spam prevention: only if execution just completed)
    if execution.status == ExecutionStatus.DONE:
        orders_count = db.query(Order).filter(Order.execution_id == execution.id).count()
        filled_count = (
            db.query(Order)
            .filter(Order.execution_id == execution.id, Order.status == OrderStatus.FILLED)
            .count()
        )
        skipped_count = (
            db.query(Order)
            .filter(Order.execution_id == execution.id, Order.status == OrderStatus.SKIPPED)
            .count()
        )

        send(
            level=AlertLevel.INFO,
            channel="dev",
            title="Execution 완료",
            body_json={
                "execution_id": str(execution.id),
                "plan_id": str(plan_id),
                "orders_total": orders_count,
                "orders_filled": filled_count,
                "orders_skipped": skipped_count,
            },
        )

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
