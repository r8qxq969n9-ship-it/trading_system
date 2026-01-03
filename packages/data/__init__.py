"""Data package: snapshots and market data pipeline."""

import csv
import os
from pathlib import Path
from typing import list


def load_universe(market: str) -> list[str]:
    """Load universe symbols from CSV file.
    
    Args:
        market: 'KR' or 'US'
        
    Returns:
        List of symbols (enabled only)
    """
    # Get project root (assuming this file is at packages/data/__init__.py)
    project_root = Path(__file__).resolve().parents[2]
    csv_path = project_root / "config" / f"universe_{market.lower()}.csv"
    
    if not csv_path.exists():
        raise FileNotFoundError(f"Universe file not found: {csv_path}")
    
    symbols = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # enabled defaults to true if not specified
            enabled = row.get("enabled", "true").lower() == "true"
            if enabled:
                symbols.append(row["symbol"])
    
    return symbols
