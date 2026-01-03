"""Test constraints."""

import pytest
from packages.core.constraints import ConstraintChecker


def test_check_positions():
    """Test positions count check."""
    checker = ConstraintChecker(max_positions=20)
    items = [{"symbol": f"STOCK{i}"} for i in range(10)]
    passed, error = checker.check_positions(items)
    assert passed
    assert error is None

    items = [{"symbol": f"STOCK{i}"} for i in range(25)]
    passed, error = checker.check_positions(items)
    assert not passed
    assert error is not None


def test_check_weight_per_name():
    """Test weight per name check."""
    checker = ConstraintChecker(max_weight_per_name=0.08)
    items = [
        {"symbol": "STOCK1", "target_weight": 0.05},
        {"symbol": "STOCK2", "target_weight": 0.07},
    ]
    passed, error = checker.check_weight_per_name(items)
    assert passed

    items = [
        {"symbol": "STOCK1", "target_weight": 0.10},  # Exceeds 8%
    ]
    passed, error = checker.check_weight_per_name(items)
    assert not passed


def test_check_kr_us_split():
    """Test KR/US split check."""
    checker = ConstraintChecker(kr_us_split=(0.4, 0.6), split_tolerance=0.01)
    items = [
        {"symbol": "KR1", "market": "KR", "target_weight": 0.2},
        {"symbol": "KR2", "market": "KR", "target_weight": 0.2},
        {"symbol": "US1", "market": "US", "target_weight": 0.3},
        {"symbol": "US2", "market": "US", "target_weight": 0.3},
    ]
    passed, error = checker.check_kr_us_split(items)
    assert passed

