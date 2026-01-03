"""Plan expirer job."""

import logging
from datetime import datetime

from packages.core.database import get_session_factory
from packages.core.models import RebalancePlan, PlanStatus

logger = logging.getLogger(__name__)
SessionLocal = get_session_factory()


def run():
    """Expire old plans."""
    logger.info("Plan expirer job started")
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        expired = db.query(RebalancePlan).filter(
            RebalancePlan.status == PlanStatus.PROPOSED,
            RebalancePlan.expires_at < now,
        ).all()

        for plan in expired:
            plan.status = PlanStatus.EXPIRED
            logger.info(f"Expired plan {plan.id}")

        db.commit()
        logger.info(f"Expired {len(expired)} plans")
    except Exception as e:
        logger.error(f"Error in plan expirer: {e}")
        db.rollback()
    finally:
        db.close()

