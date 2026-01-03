"""Order builder (SELL → BUY order)."""

from packages.core.models import OrderSide


class OrderBuilder:
    """Order builder."""

    @staticmethod
    def build_orders(plan_items: list[dict], cash_available: float) -> list[dict]:
        """Build orders from plan items. SELL first, then BUY."""
        orders = []
        sell_orders = []
        buy_orders = []

        for item in plan_items:
            delta_weight = float(item.get("delta_weight", 0))
            symbol = item.get("symbol")
            market = item.get("market")
            current_price = float(item.get("current_price", 0))

            if delta_weight < 0:
                # SELL
                qty = abs(delta_weight) / current_price if current_price > 0 else 0
                sell_orders.append(
                    {
                        "symbol": symbol,
                        "side": OrderSide.SELL.value,
                        "qty": qty,
                        "order_type": "LIMIT",
                        "limit_price": current_price,
                        "market": market,
                    }
                )
            elif delta_weight > 0:
                # BUY
                qty = delta_weight / current_price if current_price > 0 else 0
                buy_orders.append(
                    {
                        "symbol": symbol,
                        "side": OrderSide.BUY.value,
                        "qty": qty,
                        "order_type": "LIMIT",
                        "limit_price": current_price,
                        "market": market,
                        "estimated_cost": delta_weight,
                    }
                )

        # Sort buy orders by estimated cost (rank order)
        buy_orders.sort(key=lambda x: x.get("estimated_cost", 0), reverse=True)

        # Filter buy orders by available cash
        cash_remaining = cash_available
        for buy_order in buy_orders:
            cost = buy_order.get("estimated_cost", 0)
            if cost <= cash_remaining:
                orders.append(buy_order)
                cash_remaining -= cost
            else:
                # Skip if insufficient cash
                buy_order["status"] = "SKIPPED"
                buy_order["error"] = f"Insufficient cash: need {cost}, have {cash_remaining}"
                orders.append(buy_order)

        # SELL first, then BUY
        return sell_orders + [o for o in orders if o.get("side") == OrderSide.BUY.value]
