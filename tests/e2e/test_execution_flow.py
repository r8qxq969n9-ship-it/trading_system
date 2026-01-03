"""E2E test: execution flow (approval required)."""

import pytest
from uuid import uuid4
from packages.core.models import RebalancePlan, PlanStatus, Run, RunKind, RunStatus


def test_execution_requires_approval(db_session):
    """Test that execution requires plan approval."""
    # Create a PROPOSED plan
    run = Run(kind=RunKind.PLAN, status=RunStatus.STARTED)
    db_session.add(run)
    db_session.commit()

    plan = RebalancePlan(
        run_id=run.id,
        config_version_id=uuid4(),
        data_snapshot_id=uuid4(),
        status=PlanStatus.PROPOSED,  # Not approved
        summary={},
    )
    db_session.add(plan)
    db_session.commit()

    # Try to start execution - should fail
    from packages.ops.guards import check_plan_approved
    with pytest.raises(Exception):  # HTTPException
        check_plan_approved(db_session, str(plan.id))

