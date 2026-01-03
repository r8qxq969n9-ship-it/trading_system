"""Stub price provider: seed-based deterministic price generation."""

import hashlib
import os


class StubPriceProvider:
    """Stub price provider with seed-based deterministic pricing."""

    def __init__(self, seed: int | None = None):
        """Initialize stub price provider.

        Args:
            seed: Random seed for price generation. If None, uses STUB_PRICE_SEED env var or 42.
        """
        if seed is None:
            seed = int(os.getenv("STUB_PRICE_SEED", "42"))
        self.seed = seed

    def _get_price_hash(self, symbol: str, price_type: str = "current") -> float:
        """Get deterministic price based on symbol and seed.

        Args:
            symbol: Stock symbol
            price_type: "current" or "lookback"

        Returns:
            Deterministic price value
        """
        # Create hash from symbol + seed + price_type
        hash_input = f"{symbol}_{self.seed}_{price_type}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        
        # Normalize to 0-1 range
        normalized = (hash_value % 1000000) / 1000000.0
        
        # Map to price range: $10 - $500
        base_price = 10.0 + (normalized * 490.0)
        
        return round(base_price, 2)

    def get_current_price(self, symbol: str) -> float:
        """Get current price for symbol.

        Args:
            symbol: Stock symbol

        Returns:
            Current price
        """
        return self._get_price_hash(symbol, "current")

    def get_lookback_price(self, symbol: str, months: int = 3) -> float:
        """Get lookback price for symbol.

        Args:
            symbol: Stock symbol
            months: Number of months to look back (default: 3)

        Returns:
            Lookback price
        """
        # Use months in hash to get different but deterministic price
        hash_input = f"{symbol}_{self.seed}_lookback_{months}".encode()
        hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
        normalized = (hash_value % 1000000) / 1000000.0
        
        # Map to price range: $8 - $550 (slightly wider range for lookback)
        base_price = 8.0 + (normalized * 542.0)
        
        return round(base_price, 2)

    def get_price_pair(self, symbol: str, months: int = 3) -> tuple[float, float]:
        """Get both current and lookback price.

        Args:
            symbol: Stock symbol
            months: Number of months to look back

        Returns:
            Tuple of (current_price, lookback_price)
        """
        return (self.get_current_price(symbol), self.get_lookback_price(symbol, months))

