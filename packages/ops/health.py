"""Health check logic."""

from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


def check_health(db: Session) -> dict[str, Any]:
    """Check system health."""
    health = {
        "status": "healthy",
        "checks": {},
    }

    # DB check
    try:
        db.execute(text("SELECT 1"))
        health["checks"]["database"] = "ok"
    except Exception as e:
        health["status"] = "unhealthy"
        health["checks"]["database"] = f"error: {str(e)}"

    return health
