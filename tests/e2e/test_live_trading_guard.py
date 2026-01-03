"""E2E test: Live trading guard."""

import os

import pytest

from packages.brokers.kis_direct.adapter import KISDirectAdapter, LiveTradingDisabledError
from packages.core.interfaces import Order


def test_place_order_blocked_when_live_disabled():
    """Test that place_order is blocked when ENABLE_LIVE_TRADING=false."""
    os.environ["ENABLE_LIVE_TRADING"] = "false"

    adapter = KISDirectAdapter()
    order = Order(
        symbol="005930",
        side="BUY",
        qty=10,
        order_type="LIMIT",
        market="KR",
    )

    with pytest.raises(LiveTradingDisabledError):
        adapter.place_order(order)


def test_place_order_allowed_when_live_enabled():
    """Test that place_order is allowed when ENABLE_LIVE_TRADING=true."""
    os.environ["ENABLE_LIVE_TRADING"] = "true"

    adapter = KISDirectAdapter()
    order = Order(
        symbol="005930",
        side="BUY",
        qty=10,
        order_type="LIMIT",
        market="KR",
    )

    # Should not raise (stub implementation)
    result = adapter.place_order(order)
    assert result is not None
