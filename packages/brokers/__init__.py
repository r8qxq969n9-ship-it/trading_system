"""Broker factory."""

import os
import logging
from typing import Optional

from packages.core.interfaces import IBroker
from packages.brokers.kis_direct.adapter import KISDirectAdapter
from packages.brokers.kis_mcp.adapter import KISMCPAdapter

logger = logging.getLogger(__name__)


def get_broker(api_docs_dir: Optional[str] = None) -> IBroker:
    """Get broker instance based on BROKER_MODE environment variable."""
    broker_mode = os.getenv("BROKER_MODE", "direct").lower()

    if broker_mode == "mcp":
        logger.info("Using KIS MCP adapter")
        return KISMCPAdapter()
    else:
        logger.info("Using KIS Direct adapter")
        return KISDirectAdapter(api_docs_dir)
