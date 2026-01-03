"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from packages.core.models import (
    ExecutionStatus,
    Market,
    OrderSide,
    OrderStatus,
    PlanStatus,
    TradingMode,
)


# Common
class ErrorDetail(BaseModel):
    """Error detail."""

    code: str
    message: str
    details: dict[str, Any] | None = None
    hint: str | None = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: ErrorDetail
    request_id: str | None = None
    run_id: str | None = None


class SuccessResponse(BaseModel):
    """Success response."""

    request_id: str | None = None
    run_id: str | None = None


# Config
class ConfigVersionCreate(BaseModel):
    """Config version create request."""

    mode: TradingMode
    strategy_name: str
    strategy_params: dict[str, Any]
    constraints: dict[str, Any]
    created_by: str


class ConfigVersionResponse(BaseModel):
    """Config version response."""

    id: UUID
    mode: TradingMode
    strategy_name: str
    strategy_params: dict[str, Any]
    constraints: dict[str, Any]
    created_at: datetime
    created_by: str


# Plan
class PlanGenerateRequest(BaseModel):
    """Plan generate request."""

    config_version_id: UUID | None = None
    data_snapshot_id: UUID | None = None


class PlanItemResponse(BaseModel):
    """Plan item response."""

    id: UUID
    symbol: str
    market: Market
    current_weight: float
    target_weight: float
    delta_weight: float
    reason: str | None = None
    checks: dict[str, Any] | None = None


class PlanResponse(BaseModel):
    """Plan response."""

    id: UUID
    run_id: UUID
    config_version_id: UUID
    data_snapshot_id: UUID
    status: PlanStatus
    summary: dict[str, Any]
    created_at: datetime
    approved_at: datetime | None = None
    approved_by: str | None = None
    rejected_at: datetime | None = None
    rejected_by: str | None = None
    expires_at: datetime | None = None
    items: list[PlanItemResponse] = []


class PlanApproveRequest(BaseModel):
    """Plan approve request."""

    approved_by: str


class PlanRejectRequest(BaseModel):
    """Plan reject request."""

    rejected_by: str
    reason: str | None = None


# Execution
class ExecutionStartRequest(BaseModel):
    """Execution start request."""

    policy: dict[str, Any] | None = None


class ExecutionResponse(BaseModel):
    """Execution response."""

    id: UUID
    plan_id: UUID
    status: ExecutionStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    policy: dict[str, Any] | None = None
    error: str | None = None


# Order
class OrderResponse(BaseModel):
    """Order response."""

    id: UUID
    plan_id: UUID
    execution_id: UUID | None = None
    symbol: str
    side: OrderSide
    qty: float
    order_type: str
    limit_price: float | None = None
    status: OrderStatus
    broker_order_id: str | None = None
    error: str | None = None
    created_at: datetime


# Controls
class KillSwitchRequest(BaseModel):
    """Kill switch request."""

    on: bool = Field(..., alias="on")
    reason: str | None = None


class ControlResponse(BaseModel):
    """Control response."""

    kill_switch: bool
    reason: str | None = None
    updated_at: datetime


# Portfolio
class PortfolioSnapshotCreate(BaseModel):
    """Portfolio snapshot create request."""

    asof: datetime
    mode: TradingMode
    positions: dict[str, Any]
    cash: float
    nav: float


class PortfolioSnapshotResponse(BaseModel):
    """Portfolio snapshot response."""

    id: UUID
    asof: datetime
    mode: TradingMode
    positions: dict[str, Any]
    cash: float
    nav: float
    created_at: datetime


# Data
class DataSnapshotCreate(BaseModel):
    """Data snapshot create request."""

    source: str
    asof: datetime
    meta: dict[str, Any] | None = None


class DataSnapshotResponse(BaseModel):
    """Data snapshot response."""

    id: UUID
    source: str
    asof: datetime
    meta: dict[str, Any] | None = None
    created_at: datetime
