"""Test order builder."""

from packages.core.order_builder import OrderBuilder


def test_build_orders_sell_first():
    """Test that SELL orders come before BUY orders."""
    items = [
        {"symbol": "STOCK1", "delta_weight": -0.1, "current_price": 100.0, "market": "KR"},
        {"symbol": "STOCK2", "delta_weight": 0.1, "current_price": 100.0, "market": "KR"},
    ]
    orders = OrderBuilder.build_orders(items, cash_available=10000.0)
    assert len(orders) >= 2
    # First order should be SELL
    assert orders[0]["side"] == "SELL"
