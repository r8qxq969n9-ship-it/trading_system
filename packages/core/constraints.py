"""Constraint checking logic."""

from packages.core.models import Market


class ConstraintViolationError(Exception):
    """Constraint violation exception."""

    def __init__(self, message: str, details: dict | None = None):
        super().__init__(message)
        self.details = details or {}


class ConstraintChecker:
    """Constraint checker."""

    def __init__(
        self,
        max_positions: int = 20,
        max_weight_per_name: float = 0.08,
        kr_us_split: tuple[float, float] = (0.4, 0.6),
        split_tolerance: float = 0.01,
    ):
        self.max_positions = max_positions
        self.max_weight_per_name = max_weight_per_name
        self.kr_us_split = kr_us_split
        self.split_tolerance = split_tolerance

    def check_positions(self, items: list[dict]) -> tuple[bool, str | None]:
        """Check positions count."""
        if len(items) > self.max_positions:
            return False, f"Positions count {len(items)} exceeds max {self.max_positions}"
        return True, None

    def check_weight_per_name(self, items: list[dict]) -> tuple[bool, str | None]:
        """Check weight per name."""
        violations = []
        for item in items:
            weight = float(item.get("target_weight", 0))
            if weight > self.max_weight_per_name:
                violations.append(
                    f"{item.get('symbol')}: {weight:.2%} > {self.max_weight_per_name:.2%}"
                )
        if violations:
            return False, "; ".join(violations)
        return True, None

    def check_kr_us_split(self, items: list[dict]) -> tuple[bool, str | None]:
        """Check KR/US split."""
        kr_weight = sum(
            float(item.get("target_weight", 0))
            for item in items
            if item.get("market") == Market.KR.value
        )
        us_weight = sum(
            float(item.get("target_weight", 0))
            for item in items
            if item.get("market") == Market.US.value
        )
        total_weight = kr_weight + us_weight

        if total_weight == 0:
            return True, None

        kr_ratio = kr_weight / total_weight
        us_ratio = us_weight / total_weight

        expected_kr, expected_us = self.kr_us_split
        kr_diff = abs(kr_ratio - expected_kr)
        us_diff = abs(us_ratio - expected_us)

        if kr_diff > self.split_tolerance or us_diff > self.split_tolerance:
            return (
                False,
                f"KR: {kr_ratio:.2%} (expected {expected_kr:.2%}), US: {us_ratio:.2%} (expected {expected_us:.2%})",
            )
        return True, None

    def check_data_quality(self, items: list[dict]) -> tuple[bool, str | None]:
        """Check data quality (missing/outlier detection)."""
        issues = []
        for item in items:
            price = item.get("current_price")
            if price is None or price == 0:
                issues.append(f"{item.get('symbol')}: missing or zero price")
            elif price < 0:
                issues.append(f"{item.get('symbol')}: negative price")
        if issues:
            return False, "; ".join(issues)
        return True, None

    def check_all(self, items: list[dict]) -> tuple[bool, list[str]]:
        """Check all constraints."""
        errors = []
        checks = [
            ("positions", self.check_positions),
            ("weight_per_name", self.check_weight_per_name),
            ("kr_us_split", self.check_kr_us_split),
            ("data_quality", self.check_data_quality),
        ]
        for name, check_func in checks:
            passed, error = check_func(items)
            if not passed:
                errors.append(f"{name}: {error}")
        return len(errors) == 0, errors
