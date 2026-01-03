"""Plans router."""

import random
from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from apps.api.dependencies import get_db
from packages.brokers import get_broker
from packages.core.constraints import ConstraintChecker
from packages.core.models import (
    AlertLevel,
    ConfigVersion,
    Market,
    PlanItem,
    PlanStatus,
    PortfolioSnapshot,
    RebalancePlan,
    Run,
    RunKind,
    RunStatus,
)
from packages.core.schemas import (
    PlanApproveRequest,
    PlanGenerateRequest,
    PlanItemResponse,
    PlanRejectRequest,
    PlanResponse,
)
from packages.core.strategy import DualMomentumStrategy
from packages.data import load_universe
from packages.ops.audit import record_audit_event
from packages.ops.slack import send

router = APIRouter()


@router.post("/generate", response_model=PlanResponse)
async def generate_plan(
    request: PlanGenerateRequest,
    db: Session = Depends(get_db),
):
    """Generate plan using Dual Momentum strategy."""
    # 1. Get config version
    if not request.config_version_id:
        raise HTTPException(status_code=400, detail="config_version_id is required")

    config_version = (
        db.query(ConfigVersion).filter(ConfigVersion.id == request.config_version_id).first()
    )
    if not config_version:
        raise HTTPException(status_code=404, detail="Config version not found")

    strategy_params = config_version.strategy_params
    constraints_config = config_version.constraints

    # 2. Load universe
    universe_kr = load_universe("KR")
    universe_us = load_universe("US")

    # 3. Get latest portfolio snapshot
    portfolio_snapshot = db.query(PortfolioSnapshot).order_by(PortfolioSnapshot.asof.desc()).first()

    if not portfolio_snapshot:
        raise HTTPException(
            status_code=404, detail="No portfolio snapshot found. Create one first."
        )

    # Convert positions to weight dict {symbol: weight}
    positions = portfolio_snapshot.positions or {}
    nav = float(portfolio_snapshot.nav)
    current_portfolio = {}
    for symbol, qty in positions.items():
        # For stub, assume price = 100 (will be replaced by actual quotes)
        current_portfolio[symbol] = float(qty) * 100.0 / nav if nav > 0 else 0.0

    # 4. Get price data (stub)
    broker = get_broker()
    all_symbols = universe_kr + universe_us
    quotes = broker.get_quotes(all_symbols)

    # Build prices dict: {symbol: {current: float, lookback: float}}
    prices = {}
    for quote in quotes:
        current_price = quote.price
        # Lookback price: current * (0.9 ~ 1.1) random
        lookback_price = current_price * random.uniform(0.9, 1.1)
        prices[quote.symbol] = {
            "current": current_price,
            "lookback": lookback_price,
        }

    # 5. Run strategy
    strategy = DualMomentumStrategy(
        lookback_months=strategy_params.get("lookback_months", 3),
        us_top_n=strategy_params.get("us_top_n", 4),
        kr_top_m=strategy_params.get("kr_top_m", 2),
        kr_us_split=tuple(strategy_params.get("kr_us_split", [0.4, 0.6])),
    )

    plan_items_dict = strategy.generate_plan(
        current_portfolio=current_portfolio,
        universe_kr=universe_kr,
        universe_us=universe_us,
        prices=prices,
    )

    # Add current_price to plan items for order builder
    for item in plan_items_dict:
        symbol = item["symbol"]
        if symbol in prices:
            item["current_price"] = prices[symbol]["current"]

    # 6. Apply constraints
    constraint_checker = ConstraintChecker(
        max_positions=constraints_config.get("max_positions", 20),
        max_weight_per_name=constraints_config.get("max_weight_per_name", 0.08),
        kr_us_split=tuple(constraints_config.get("kr_us_split", [0.4, 0.6])),
    )

    passed, errors = constraint_checker.check_all(plan_items_dict)
    if not passed:
        # Log warnings but don't fail (can be approved with warnings)
        pass

    # 7. Create Run
    run = Run(kind=RunKind.PLAN, status=RunStatus.STARTED)
    db.add(run)
    db.commit()

    # 8. Calculate summary
    kr_weight = sum(
        item["target_weight"] for item in plan_items_dict if item["market"] == Market.KR.value
    )
    us_weight = sum(
        item["target_weight"] for item in plan_items_dict if item["market"] == Market.US.value
    )

    current_kr_weight = sum(
        item["current_weight"] for item in plan_items_dict if item["market"] == Market.KR.value
    )
    current_us_weight = sum(
        item["current_weight"] for item in plan_items_dict if item["market"] == Market.US.value
    )

    # Top 3 changes by absolute delta_weight
    sorted_changes = sorted(
        plan_items_dict,
        key=lambda x: abs(x["delta_weight"]),
        reverse=True,
    )[:3]
    top_3_changes = [
        {
            "symbol": item["symbol"],
            "delta_weight": item["delta_weight"],
            "current_weight": item["current_weight"],
            "target_weight": item["target_weight"],
        }
        for item in sorted_changes
    ]

    summary = {
        "kr_us_summary": (
            f"KR {current_kr_weight:.1%} → {kr_weight:.1%}, "
            f"US {current_us_weight:.1%} → {us_weight:.1%}"
        ),
        "top_3_changes": top_3_changes,
        "constraint_checks": {
            "passed": passed,
            "errors": errors if not passed else [],
        },
    }

    # 9. Create Plan
    plan = RebalancePlan(
        run_id=run.id,
        config_version_id=request.config_version_id,
        data_snapshot_id=request.data_snapshot_id or UUID("00000000-0000-0000-0000-000000000001"),
        status=PlanStatus.PROPOSED,
        summary=summary,
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    # 10. Create PlanItems
    for item_dict in plan_items_dict:
        plan_item = PlanItem(
            plan_id=plan.id,
            symbol=item_dict["symbol"],
            market=Market(item_dict["market"]),
            current_weight=item_dict["current_weight"],
            target_weight=item_dict["target_weight"],
            delta_weight=item_dict["delta_weight"],
            reason=item_dict.get("reason", ""),
            checks={"constraint_errors": errors} if not passed else None,
        )
        db.add(plan_item)

    db.commit()

    # 11. Update Run status
    run.status = RunStatus.DONE
    db.commit()

    # 12. Record audit event
    record_audit_event(
        db=db,
        event_type="plan_created",
        actor="system",
        ref_type="plan",
        ref_id=plan.id,
        payload={"config_version_id": str(request.config_version_id)},
    )

    # 13. Send Slack notification
    send(
        level=AlertLevel.INFO,
        channel="dev",
        title="Plan 생성 완료",
        body_json={
            "plan_id": str(plan.id),
            "items_count": len(plan_items_dict),
            "kr_weight": f"{kr_weight:.1%}",
            "us_weight": f"{us_weight:.1%}",
            "constraint_passed": passed,
        },
    )

    # 14. Get items for response
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

    # Record audit event
    record_audit_event(
        db=db,
        event_type="plan_approved",
        actor=request.approved_by,
        ref_type="plan",
        ref_id=plan.id,
    )

    # Send Slack notification
    from packages.core.models import AlertLevel
    from packages.ops.slack import send

    send(
        level=AlertLevel.INFO,
        channel="dev",
        title="Plan 승인 완료",
        body_json={
            "plan_id": str(plan.id),
            "approved_by": request.approved_by,
        },
    )

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
