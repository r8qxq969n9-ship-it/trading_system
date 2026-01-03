"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from packages.core.models import (
    AlertLevel,
    ExecutionStatus,
    Market,
    OrderSide,
    OrderStatus,
    PlanStatus,
    RunKind,
    RunStatus,
    TradingMode,
)


# Common
class ErrorDetail(BaseModel):
    """Error detail."""

    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
    hint: Optional[str] = None


class ErrorResponse(BaseModel):
    """Error response."""

    error: ErrorDetail
    request_id: Optional[str] = None
    run_id: Optional[str] = None


class SuccessResponse(BaseModel):
    """Success response."""

    request_id: Optional[str] = None
    run_id: Optional[str] = None


# Config
class ConfigVersionCreate(BaseModel):
    """Config version create request."""

    mode: TradingMode
    strategy_name: str
    strategy_params: Dict[str, Any]
    constraints: Dict[str, Any]
    created_by: str


class ConfigVersionResponse(BaseModel):
    """Config version response."""

    id: UUID
    mode: TradingMode
    strategy_name: str
    strategy_params: Dict[str, Any]
    constraints: Dict[str, Any]
    created_at: datetime
    created_by: str


# Plan
class PlanGenerateRequest(BaseModel):
    """Plan generate request."""

    config_version_id: Optional[UUID] = None
    data_snapshot_id: Optional[UUID] = None


class PlanItemResponse(BaseModel):
    """Plan item response."""

    id: UUID
    symbol: str
    market: Market
    current_weight: float
    target_weight: float
    delta_weight: float
    reason: Optional[str] = None
    checks: Optional[Dict[str, Any]] = None


class PlanResponse(BaseModel):
    """Plan response."""

    id: UUID
    run_id: UUID
    config_version_id: UUID
    data_snapshot_id: UUID
    status: PlanStatus
    summary: Dict[str, Any]
    created_at: datetime
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    rejected_at: Optional[datetime] = None
    rejected_by: Optional[str] = None
    expires_at: Optional[datetime] = None
    items: List[PlanItemResponse] = []


class PlanApproveRequest(BaseModel):
    """Plan approve request."""

    approved_by: str


class PlanRejectRequest(BaseModel):
    """Plan reject request."""

    rejected_by: str
    reason: Optional[str] = None


# Execution
class ExecutionStartRequest(BaseModel):
    """Execution start request."""

    policy: Optional[Dict[str, Any]] = None


class ExecutionResponse(BaseModel):
    """Execution response."""

    id: UUID
    plan_id: UUID
    status: ExecutionStatus
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    policy: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


# Order
class OrderResponse(BaseModel):
    """Order response."""

    id: UUID
    plan_id: UUID
    execution_id: Optional[UUID] = None
    symbol: str
    side: OrderSide
    qty: float
    order_type: str
    limit_price: Optional[float] = None
    status: OrderStatus
    broker_order_id: Optional[str] = None
    error: Optional[str] = None
    created_at: datetime


# Controls
class KillSwitchRequest(BaseModel):
    """Kill switch request."""

    on: bool = Field(..., alias="on")
    reason: Optional[str] = None


class ControlResponse(BaseModel):
    """Control response."""

    kill_switch: bool
    reason: Optional[str] = None
    updated_at: datetime


# Portfolio
class PortfolioSnapshotResponse(BaseModel):
    """Portfolio snapshot response."""

    id: UUID
    asof: datetime
    mode: TradingMode
    positions: Dict[str, Any]
    cash: float
    nav: float
    created_at: datetime


# Data
class DataSnapshotCreate(BaseModel):
    """Data snapshot create request."""

    source: str
    asof: datetime
    meta: Optional[Dict[str, Any]] = None


class DataSnapshotResponse(BaseModel):
    """Data snapshot response."""

    id: UUID
    source: str
    asof: datetime
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

