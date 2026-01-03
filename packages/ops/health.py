"""Health check logic."""

from typing import Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text


def check_health(db: Session) -> Dict[str, Any]:
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

