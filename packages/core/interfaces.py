"""Broker interface."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel


class Order(BaseModel):
    """Order model."""

    symbol: str
    side: str  # BUY or SELL
    qty: float
    order_type: str
    limit_price: float | None = None
    market: str  # KR or US


class Balance(BaseModel):
    """Balance model."""

    cash: float
    positions: dict[str, Any]


class Quote(BaseModel):
    """Quote model."""

    symbol: str
    price: float
    market: str


class IBroker(ABC):
    """Broker interface."""

    @abstractmethod
    def get_token(self) -> str:
        """Get access token."""
        pass

    @abstractmethod
    def refresh_token(self) -> str:
        """Refresh access token."""
        pass

    @abstractmethod
    def get_quotes(self, symbols: list[str]) -> list[Quote]:
        """Get quotes for symbols."""
        pass

    @abstractmethod
    def get_balance(self) -> Balance:
        """Get account balance."""
        pass

    @abstractmethod
    def place_order(self, order: Order) -> dict[str, Any]:
        """Place order. In Phase 1, this should raise exception if ENABLE_LIVE_TRADING=false."""
        pass

    @abstractmethod
    def get_orders(self, status: str | None = None) -> list[dict[str, Any]]:
        """Get orders."""
        pass

    @abstractmethod
    def get_fills(self, order_id: str | None = None) -> list[dict[str, Any]]:
        """Get fills."""
        pass

    @abstractmethod
    def cancel_order(self, order_id: str) -> dict[str, Any]:
        """Cancel order."""
        pass
