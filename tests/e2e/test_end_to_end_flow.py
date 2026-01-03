"""E2E test: full flow from plan generation to execution completion."""

from datetime import datetime
from decimal import Decimal

import pytest

from packages.core.models import (
    ConfigVersion,
    DataSnapshot,
    Execution,
    ExecutionStatus,
    Fill,
    Order,
    OrderStatus,
    PlanItem,
    PlanStatus,
    PortfolioSnapshot,
    RebalancePlan,
    Run,
    RunKind,
    RunStatus,
    TradingMode,
)


@pytest.fixture
def setup_test_data(db_session):
    """Setup test data: config version, data snapshot, portfolio snapshot."""
    # Create config version
    config_version = ConfigVersion(
        mode=TradingMode.PAPER,
        strategy_name="dual_momentum",
        strategy_params={
            "lookback_months": 3,
            "us_top_n": 4,
            "kr_top_m": 2,
            "kr_us_split": [0.4, 0.6],
        },
        constraints={
            "max_positions": 20,
            "max_weight_per_name": 0.08,
            "kr_us_split": [0.4, 0.6],
        },
        created_by="test",
    )
    db_session.add(config_version)
    db_session.commit()
    db_session.refresh(config_version)

    # Create data snapshot
    data_snapshot = DataSnapshot(
        source="test",
        asof=datetime.utcnow(),
        meta={"test": True},
    )
    db_session.add(data_snapshot)
    db_session.commit()
    db_session.refresh(data_snapshot)

    # Create portfolio snapshot
    portfolio_snapshot = PortfolioSnapshot(
        asof=datetime.utcnow(),
        mode=TradingMode.PAPER,
        positions={"005930": 10, "AAPL": 5},  # Some initial positions
        cash=Decimal("1000000.0"),
        nav=Decimal("2000000.0"),
    )
    db_session.add(portfolio_snapshot)
    db_session.commit()
    db_session.refresh(portfolio_snapshot)

    return {
        "config_version_id": config_version.id,
        "data_snapshot_id": data_snapshot.id,
        "portfolio_snapshot_id": portfolio_snapshot.id,
    }


@pytest.mark.asyncio
async def test_end_to_end_flow(db_session, setup_test_data):
    """Test full E2E flow: generate → approve → execute → done."""
    config_version_id = setup_test_data["config_version_id"]
    data_snapshot_id = setup_test_data["data_snapshot_id"]

    # 1. Generate plan (direct function call)
    from apps.api.routers.plans import generate_plan
    from packages.core.schemas import PlanGenerateRequest

    request = PlanGenerateRequest(
        config_version_id=config_version_id,
        data_snapshot_id=data_snapshot_id,
    )
    plan_response = await generate_plan(request, db_session)
    plan_id = plan_response.id
    assert plan_response.status == PlanStatus.PROPOSED
    assert len(plan_response.items) > 0
    assert "summary" in plan_response.summary
    assert "kr_us_summary" in plan_response.summary

    # Verify plan in DB
    plan = db_session.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
    assert plan is not None
    assert plan.status == PlanStatus.PROPOSED

    # Verify plan items
    items = db_session.query(PlanItem).filter(PlanItem.plan_id == plan_id).all()
    assert len(items) > 0

    # Verify audit event
    from packages.core.models import AuditEvent

    audit_events = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.ref_id == plan_id,
            AuditEvent.event_type == "plan_created",
        )
        .all()
    )
    assert len(audit_events) > 0

    # 2. Approve plan
    from apps.api.routers.plans import approve_plan
    from packages.core.schemas import PlanApproveRequest

    approve_request = PlanApproveRequest(approved_by="test_user")
    approve_response = await approve_plan(plan_id, approve_request, db_session)
    assert approve_response["status"] == "approved"

    # Verify plan status
    db_session.refresh(plan)
    assert plan.status == PlanStatus.APPROVED
    assert plan.approved_by == "test_user"
    assert plan.approved_at is not None

    # Verify audit event
    audit_events = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.ref_id == plan_id,
            AuditEvent.event_type == "plan_approved",
        )
        .all()
    )
    assert len(audit_events) > 0

    # 3. Start execution
    from apps.api.routers.executions import start_execution
    from packages.core.schemas import ExecutionStartRequest

    execution_request = ExecutionStartRequest(policy={})
    execution_response = await start_execution(plan_id, execution_request, db_session)
    execution_id = execution_response.id
    assert execution_response.status == ExecutionStatus.DONE  # Paper mode: immediate completion

    # Verify execution in DB
    execution = db_session.query(Execution).filter(Execution.id == execution_id).first()
    assert execution is not None
    assert execution.status == ExecutionStatus.DONE
    assert execution.started_at is not None
    assert execution.ended_at is not None

    # Verify orders created
    orders = db_session.query(Order).filter(Order.execution_id == execution_id).all()
    assert len(orders) > 0

    # Verify fills created (Paper mode: immediate fill)
    for order in orders:
        if order.status == OrderStatus.FILLED:
            fills = db_session.query(Fill).filter(Fill.order_id == order.id).all()
            assert len(fills) > 0
            for fill in fills:
                assert fill.filled_qty > 0
                assert fill.filled_price > 0
                assert fill.filled_at is not None

    # Verify run created
    runs = db_session.query(Run).filter(Run.kind == RunKind.EXECUTE).all()
    assert len(runs) > 0
    execute_run = [r for r in runs if r.status == RunStatus.DONE]
    assert len(execute_run) > 0

    # Verify audit event
    audit_events = (
        db_session.query(AuditEvent)
        .filter(
            AuditEvent.ref_id == execution_id,
            AuditEvent.event_type == "execution_completed",
        )
        .all()
    )
    assert len(audit_events) > 0

    # 4. Verify execution is idempotent (can call again)
    execution_response2 = await start_execution(plan_id, execution_request, db_session)
    assert execution_response2.id == execution_id  # Same execution returned
