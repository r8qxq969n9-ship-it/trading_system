"""KIS MCP adapter (skeleton)."""

import logging
from typing import Any

from packages.core.interfaces import Balance, IBroker, Order, Quote

logger = logging.getLogger(__name__)


class KISMCPAdapter(IBroker):
    """KIS MCP adapter (skeleton)."""

    def __init__(self):
        """Initialize KIS MCP adapter."""
        # TODO: Initialize MCP connection
        pass

    def get_token(self) -> str:
        """Get access token (stub)."""
        # TODO: Implement MCP token retrieval
        return "stub_mcp_token"

    def refresh_token(self) -> str:
        """Refresh access token (stub)."""
        # TODO: Implement MCP token refresh
        return "stub_mcp_token_refreshed"

    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for symbols (stub)."""
        # TODO: Implement MCP quote retrieval
        logger.warning("get_quotes is not yet implemented (MCP), returning stub data")
        return [Quote(symbol=s, price=100.0, market="KR") for s in symbols]

    def get_balance(self) -> Balance:
        """Get account balance (stub)."""
        # TODO: Implement MCP balance retrieval
        logger.warning("get_balance is not yet implemented (MCP), returning stub data")
        return Balance(cash=1000000.0, positions={})

    def place_order(self, order: Order) -> dict[str, Any]:
        """Place order (stub)."""
        # TODO: Implement MCP order placement
        # Note: Same LiveTradingDisabledError check should be applied by caller
        logger.warning("place_order is not yet implemented (MCP stub)")
        return {
            "order_id": "stub_mcp_order_id",
            "status": "SENT",
        }

    def get_orders(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get orders (stub)."""
        # TODO: Implement MCP order retrieval
        logger.warning("get_orders is not yet implemented (MCP), returning stub data")
        return []

    def get_fills(self, order_id: str | None = None) -> list[dict[str, Any]]:
        """Get fills (stub)."""
        # TODO: Implement MCP fill retrieval
        logger.warning("get_fills is not yet implemented (MCP), returning stub data")
        return []

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel order (stub)."""
        # TODO: Implement MCP order cancellation
        logger.warning("cancel_order is not yet implemented (MCP stub)")
        return {"status": "CANCELED"}
