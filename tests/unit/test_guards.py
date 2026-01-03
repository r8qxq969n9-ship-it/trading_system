"""Test guards."""

import pytest
from packages.core.models import Control
from packages.ops.guards import check_kill_switch, check_live_trading_enabled
import os


def test_check_kill_switch_off(db_session):
    """Test kill switch check when OFF."""
    control = Control(id=1, kill_switch=False)
    db_session.add(control)
    db_session.commit()
    # Should not raise
    check_kill_switch(db_session)


def test_check_kill_switch_on(db_session):
    """Test kill switch check when ON."""
    control = Control(id=1, kill_switch=True, reason="Test")
    db_session.add(control)
    db_session.commit()
    with pytest.raises(Exception):  # HTTPException
        check_kill_switch(db_session)


def test_check_live_trading_enabled():
    """Test live trading enabled check."""
    os.environ["ENABLE_LIVE_TRADING"] = "false"
    with pytest.raises(Exception):  # HTTPException
        check_live_trading_enabled()

