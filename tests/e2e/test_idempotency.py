"""E2E test: idempotency."""

import pytest
from uuid import uuid4
from packages.core.models import RebalancePlan, PlanStatus, Execution, ExecutionStatus, Run, RunKind, RunStatus


def test_execution_idempotency(db_session):
    """Test that execution is idempotent (same plan_id can only be executed once)."""
    # Create an APPROVED plan
    run = Run(kind=RunKind.PLAN, status=RunStatus.STARTED)
    db_session.add(run)
    db_session.commit()

    plan = RebalancePlan(
        run_id=run.id,
        config_version_id=uuid4(),
        data_snapshot_id=uuid4(),
        status=PlanStatus.APPROVED,
        summary={},
    )
    db_session.add(plan)
    db_session.commit()

    # Create first execution
    execution1 = Execution(
        plan_id=plan.id,
        status=ExecutionStatus.PENDING,
    )
    db_session.add(execution1)
    db_session.commit()

    # Try to create second execution - should fail due to UNIQUE constraint
    execution2 = Execution(
        plan_id=plan.id,  # Same plan_id
        status=ExecutionStatus.PENDING,
    )
    db_session.add(execution2)
    with pytest.raises(Exception):  # IntegrityError
        db_session.commit()

