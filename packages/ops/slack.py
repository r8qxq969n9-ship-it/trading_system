"""Slack notification (no-op if webhook not configured)."""

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx

from packages.core.models import AlertLevel

logger = logging.getLogger(__name__)


def send(
    level: AlertLevel,
    channel: str,
    title: str,
    body_json: Dict[str, Any],
) -> bool:
    """Send Slack notification. Returns True if sent, False if no-op."""
    webhook_url = None

    if channel == "dev":
        webhook_url = os.getenv("SLACK_WEBHOOK_DEV")
    elif channel == "alerts":
        webhook_url = os.getenv("SLACK_WEBHOOK_ALERTS")
    elif channel == "decisions":
        webhook_url = os.getenv("SLACK_WEBHOOK_DECISIONS")

    if not webhook_url:
        logger.info(f"Slack webhook not configured for channel '{channel}', skipping notification: {title}")
        return False

    # Format message
    color_map = {
        AlertLevel.INFO: "#36a64f",
        AlertLevel.WARN: "#ff9900",
        AlertLevel.ERROR: "#ff0000",
        AlertLevel.DECISION_REQUIRED: "#ff6b6b",
    }

    payload = {
        "attachments": [
            {
                "color": color_map.get(level, "#36a64f"),
                "title": f"[{level.value}][{os.getenv('APP_ENV', 'local')}] {title}",
                "text": json.dumps(body_json, indent=2, ensure_ascii=False),
                "footer": "Trading System",
                "ts": int(__import__("time").time()),
            }
        ]
    }

    try:
        response = httpx.post(webhook_url, json=payload, timeout=5.0)
        response.raise_for_status()
        logger.info(f"Slack notification sent: {title}")
        return True
    except Exception as e:
        logger.error(f"Failed to send Slack notification: {e}")
        return False

