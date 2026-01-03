"""Test Slack (no-op)."""

import os

from packages.core.models import AlertLevel
from packages.ops.slack import send


def test_slack_no_op():
    """Test Slack no-op when webhook not configured."""
    # Ensure no webhook is set
    os.environ.pop("SLACK_WEBHOOK_DEV", None)
    os.environ.pop("SLACK_WEBHOOK_ALERTS", None)
    os.environ.pop("SLACK_WEBHOOK_DECISIONS", None)

    # Should return False (no-op) but not raise
    result = send(AlertLevel.INFO, "dev", "Test", {})
    assert result is False
