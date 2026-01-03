"""Strategy: Monthly Dual Momentum (skeleton)."""

from packages.core.models import Market


class DualMomentumStrategy:
    """Monthly Dual Momentum strategy."""

    def __init__(
        self,
        lookback_months: int = 3,
        us_top_n: int = 4,
        kr_top_m: int = 2,
        kr_us_split: tuple = (0.4, 0.6),
    ):
        self.lookback_months = lookback_months
        self.us_top_n = us_top_n
        self.kr_top_m = kr_top_m
        self.kr_us_split = kr_us_split

    def calculate_momentum_score(self, current_price: float, lookback_price: float) -> float:
        """Calculate momentum score: (current / lookback) - 1."""
        if lookback_price == 0:
            return 0.0
        return (current_price / lookback_price) - 1.0

    def select_universe(
        self,
        universe_kr: list[dict],
        universe_us: list[dict],
        prices: dict[str, dict[str, float]],  # {symbol: {current: float, lookback: float}}
    ) -> list[dict]:
        """Select top momentum stocks from universe."""
        selected = []

        # Calculate scores for KR
        kr_scores = []
        for symbol in universe_kr:
            if symbol not in prices:
                continue
            price_data = prices[symbol]
            score = self.calculate_momentum_score(
                price_data.get("current", 0),
                price_data.get("lookback", 0),
            )
            kr_scores.append(
                {
                    "symbol": symbol,
                    "market": Market.KR.value,
                    "score": score,
                }
            )

        # Calculate scores for US
        us_scores = []
        for symbol in universe_us:
            if symbol not in prices:
                continue
            price_data = prices[symbol]
            score = self.calculate_momentum_score(
                price_data.get("current", 0),
                price_data.get("lookback", 0),
            )
            us_scores.append(
                {
                    "symbol": symbol,
                    "market": Market.US.value,
                    "score": score,
                }
            )

        # Select top N
        kr_scores.sort(key=lambda x: x["score"], reverse=True)
        us_scores.sort(key=lambda x: x["score"], reverse=True)

        selected_kr = kr_scores[: self.kr_top_m]
        selected_us = us_scores[: self.us_top_n]

        # Equal weight allocation within each bucket
        kr_weight_per = self.kr_us_split[0] / len(selected_kr) if selected_kr else 0
        us_weight_per = self.kr_us_split[1] / len(selected_us) if selected_us else 0

        for item in selected_kr:
            item["target_weight"] = kr_weight_per
            selected.append(item)

        for item in selected_us:
            item["target_weight"] = us_weight_per
            selected.append(item)

        return selected

    def generate_plan(
        self,
        current_portfolio: dict[str, float],  # {symbol: weight}
        universe_kr: list[str],
        universe_us: list[str],
        prices: dict[str, dict[str, float]],
    ) -> list[dict]:
        """Generate rebalance plan (skeleton)."""
        # This is a skeleton - actual implementation will be in Phase 1 Plan generation
        selected = self.select_universe(universe_kr, universe_us, prices)

        plan_items = []
        for item in selected:
            symbol = item["symbol"]
            current_weight = current_portfolio.get(symbol, 0.0)
            target_weight = item["target_weight"]
            delta_weight = target_weight - current_weight

            plan_items.append(
                {
                    "symbol": symbol,
                    "market": item["market"],
                    "current_weight": current_weight,
                    "target_weight": target_weight,
                    "delta_weight": delta_weight,
                    "reason": f"Momentum score: {item['score']:.2%}",
                }
            )

        return plan_items
