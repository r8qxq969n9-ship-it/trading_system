"""KIS Direct adapter."""

import logging
import os
from typing import Any

from packages.brokers.kis_direct.spec_loader import SpecLoader
from packages.core.interfaces import Balance, IBroker, Order, Quote
from packages.data.stub_price_provider import StubPriceProvider

logger = logging.getLogger(__name__)


class LiveTradingDisabledError(Exception):
    """Live trading disabled error."""

    def __init__(self):
        super().__init__(
            "Live trading is disabled. ENABLE_LIVE_TRADING must be true to place orders."
        )


class KISDirectAdapter(IBroker):
    """KIS Direct adapter."""

    def __init__(self, api_docs_dir: str | None = None):
        """Initialize KIS Direct adapter."""
        self.spec_loader = SpecLoader(api_docs_dir)
        self._token: str | None = None
        self._token_expires_at: float | None = None
        # Initialize stub price provider if enabled
        use_stub_prices = os.getenv("USE_STUB_PRICES", "false").lower() == "true"
        self._stub_provider = StubPriceProvider() if use_stub_prices else None
        if use_stub_prices:
            logger.info("StubPriceProvider enabled for deterministic pricing")

    def get_token(self) -> str:
        """Get access token (stub)."""
        # TODO: Implement actual token retrieval from KIS API
        if (
            self._token
            and self._token_expires_at
            and self._token_expires_at > __import__("time").time()
        ):
            return self._token
        # Stub: return placeholder
        return "stub_token"

    def refresh_token(self) -> str:
        """Refresh access token (stub)."""
        # TODO: Implement actual token refresh
        self._token = "stub_token_refreshed"
        self._token_expires_at = __import__("time").time() + 86400  # 24 hours
        return self._token

    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for symbols."""
        # Use StubPriceProvider if enabled
        if self._stub_provider:
            quotes = []
            for symbol in symbols:
                # Determine market based on symbol format
                # KR: 6-digit numeric, US: 1-5 letter ticker
                if symbol.isdigit() and len(symbol) == 6:
                    market = "KR"
                else:
                    market = "US"
                price = self._stub_provider.get_current_price(symbol)
                quotes.append(Quote(symbol=symbol, price=price, market=market))
            return quotes
        
        # TODO: Implement using spec_loader to find appropriate API and call it
        # For now, return stub data
        logger.warning("get_quotes is not yet implemented, returning stub data")
        return [Quote(symbol=s, price=100.0, market="KR") for s in symbols]

    def get_balance(self) -> Balance:
        """Get account balance (stub)."""
        # TODO: Implement using spec_loader
        logger.warning("get_balance is not yet implemented, returning stub data")
        return Balance(cash=1000000.0, positions={})

    def place_order(self, order: Order) -> dict[str, Any]:
        """Place order. Raises LiveTradingDisabledError if ENABLE_LIVE_TRADING=false."""
        enable_live = os.getenv("ENABLE_LIVE_TRADING", "false").lower() == "true"
        if not enable_live:
            error_msg = (
                "Live trading is disabled. ENABLE_LIVE_TRADING must be true to place orders."
            )
            logger.error(f"place_order blocked: {error_msg}")
            # Record in audit (would be done by caller)
            raise LiveTradingDisabledError()

        # TODO: Implement actual order placement using spec_loader
        logger.warning("place_order is not yet implemented (stub)")
        return {
            "order_id": "stub_order_id",
            "status": "SENT",
        }

    def get_orders(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get orders (stub)."""
        # TODO: Implement using spec_loader
        logger.warning("get_orders is not yet implemented, returning stub data")
        return []

    def get_fills(self, order_id: str | None = None) -> list[dict[str, Any]]:
        """Get fills (stub)."""
        # TODO: Implement using spec_loader
        logger.warning("get_fills is not yet implemented, returning stub data")
        return []

    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel order (stub)."""
        # TODO: Implement using spec_loader
        logger.warning("cancel_order is not yet implemented (stub)")
        return {"status": "CANCELED"}
