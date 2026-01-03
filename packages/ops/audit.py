"""Audit event utilities."""

import logging
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from packages.core.models import AuditEvent

logger = logging.getLogger(__name__)


def record_audit_event(
    db: Session,
    event_type: str,
    actor: str,
    ref_type: str | None = None,
    ref_id: UUID | None = None,
    payload: dict[str, Any] | None = None,
) -> AuditEvent:
    """Record an audit event.
    
    Args:
        db: Database session
        event_type: Event type (e.g., 'plan_created', 'plan_approved', 'execution_started')
        actor: Actor who performed the action
        ref_type: Reference type (e.g., 'plan', 'execution')
        ref_id: Reference ID (UUID)
        payload: Additional payload data
        
    Returns:
        Created AuditEvent
    """
    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        ref_type=ref_type,
        ref_id=ref_id,
        payload=payload or {},
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    
    logger.info(f"Audit event recorded: {event_type} by {actor} (ref: {ref_type}/{ref_id})")
    
    return event

