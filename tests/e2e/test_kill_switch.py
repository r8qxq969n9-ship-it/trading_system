"""E2E test: kill switch."""

import pytest
from packages.core.models import Control
from packages.ops.guards import check_kill_switch


def test_kill_switch_blocks_execution(db_session):
    """Test that kill switch blocks execution."""
    # Set kill switch ON
    control = Control(id=1, kill_switch=True, reason="Test kill switch")
    db_session.add(control)
    db_session.commit()

    # Try to check - should raise
    with pytest.raises(Exception):  # HTTPException
        check_kill_switch(db_session)

