"""SQLAlchemy models for trading system."""

import enum
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Column,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SQLEnum,
)
from sqlalchemy.dialects.postgresql import JSONB, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


# Enums
class TradingMode(str, enum.Enum):
    """Trading mode."""

    SIMULATION = "SIMULATION"
    PAPER = "PAPER"
    LIVE = "LIVE"


class PlanStatus(str, enum.Enum):
    """Rebalance plan status."""

    PROPOSED = "PROPOSED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class ExecutionStatus(str, enum.Enum):
    """Execution status."""

    PENDING = "PENDING"
    RUNNING = "RUNNING"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELED = "CANCELED"


class RunKind(str, enum.Enum):
    """Run kind."""

    SIMULATION = "SIMULATION"
    PAPER = "PAPER"
    PLAN = "PLAN"
    EXECUTE = "EXECUTE"


class RunStatus(str, enum.Enum):
    """Run status."""

    STARTED = "STARTED"
    DONE = "DONE"
    FAILED = "FAILED"


class Market(str, enum.Enum):
    """Market."""

    KR = "KR"
    US = "US"


class OrderSide(str, enum.Enum):
    """Order side."""

    BUY = "BUY"
    SELL = "SELL"


class OrderStatus(str, enum.Enum):
    """Order status."""

    CREATED = "CREATED"
    SENT = "SENT"
    PARTIAL = "PARTIAL"
    FILLED = "FILLED"
    CANCELED = "CANCELED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"


class AlertLevel(str, enum.Enum):
    """Alert level."""

    INFO = "INFO"
    WARN = "WARN"
    ERROR = "ERROR"
    DECISION_REQUIRED = "DECISION_REQUIRED"


# Models
class ConfigVersion(Base):
    """Configuration version."""

    __tablename__ = "config_versions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    mode = Column(SQLEnum(TradingMode), nullable=False)
    strategy_name = Column(Text, nullable=False)
    strategy_params = Column(JSONB, nullable=False)
    constraints = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    created_by = Column(Text, nullable=False)


class DataSnapshot(Base):
    """Data snapshot."""

    __tablename__ = "data_snapshots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    source = Column(Text, nullable=False)
    asof = Column(TIMESTAMP(timezone=True), nullable=False)
    meta = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class PortfolioSnapshot(Base):
    """Portfolio snapshot."""

    __tablename__ = "portfolio_snapshots"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    asof = Column(TIMESTAMP(timezone=True), nullable=False)
    mode = Column(SQLEnum(TradingMode), nullable=False)
    positions = Column(JSONB, nullable=False)
    cash = Column(Numeric, nullable=False)
    nav = Column(Numeric, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class Run(Base):
    """Run record."""

    __tablename__ = "runs"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    kind = Column(SQLEnum(RunKind), nullable=False)
    status = Column(SQLEnum(RunStatus), nullable=False)
    started_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    meta = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)


class RebalancePlan(Base):
    """Rebalance plan."""

    __tablename__ = "rebalance_plans"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    run_id = Column(PGUUID(as_uuid=True), ForeignKey("runs.id"), nullable=False)
    config_version_id = Column(
        PGUUID(as_uuid=True), ForeignKey("config_versions.id"), nullable=False
    )
    data_snapshot_id = Column(PGUUID(as_uuid=True), ForeignKey("data_snapshots.id"), nullable=False)
    status = Column(SQLEnum(PlanStatus), nullable=False, default=PlanStatus.PROPOSED)
    summary = Column(JSONB, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    approved_at = Column(TIMESTAMP(timezone=True), nullable=True)
    approved_by = Column(Text, nullable=True)
    rejected_at = Column(TIMESTAMP(timezone=True), nullable=True)
    rejected_by = Column(Text, nullable=True)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=True)

    # Relationships
    items = relationship("PlanItem", back_populates="plan", cascade="all, delete-orphan")
    execution = relationship("Execution", back_populates="plan", uselist=False)

    __table_args__ = (Index("idx_rebalance_plans_status_created_at", "status", "created_at"),)


class PlanItem(Base):
    """Plan item."""

    __tablename__ = "plan_items"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id = Column(PGUUID(as_uuid=True), ForeignKey("rebalance_plans.id"), nullable=False)
    symbol = Column(Text, nullable=False)
    market = Column(SQLEnum(Market), nullable=False)
    current_weight = Column(Numeric, nullable=False)
    target_weight = Column(Numeric, nullable=False)
    delta_weight = Column(Numeric, nullable=False)
    reason = Column(Text, nullable=True)
    checks = Column(JSONB, nullable=True)

    # Relationships
    plan = relationship("RebalancePlan", back_populates="items")


class Execution(Base):
    """Execution."""

    __tablename__ = "executions"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id = Column(
        PGUUID(as_uuid=True), ForeignKey("rebalance_plans.id"), nullable=False, unique=True
    )
    status = Column(SQLEnum(ExecutionStatus), nullable=False, default=ExecutionStatus.PENDING)
    started_at = Column(TIMESTAMP(timezone=True), nullable=True)
    ended_at = Column(TIMESTAMP(timezone=True), nullable=True)
    policy = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)

    # Relationships
    plan = relationship("RebalancePlan", back_populates="execution")
    orders = relationship("Order", back_populates="execution")


class Order(Base):
    """Order."""

    __tablename__ = "orders"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    plan_id = Column(PGUUID(as_uuid=True), ForeignKey("rebalance_plans.id"), nullable=False)
    execution_id = Column(PGUUID(as_uuid=True), ForeignKey("executions.id"), nullable=True)
    symbol = Column(Text, nullable=False)
    side = Column(SQLEnum(OrderSide), nullable=False)
    qty = Column(Numeric, nullable=False)
    order_type = Column(Text, nullable=False)
    limit_price = Column(Numeric, nullable=True)
    status = Column(SQLEnum(OrderStatus), nullable=False, default=OrderStatus.CREATED)
    broker_order_id = Column(Text, nullable=True)
    error = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())

    # Relationships
    execution = relationship("Execution", back_populates="orders")
    fills = relationship("Fill", back_populates="order", cascade="all, delete-orphan")

    __table_args__ = (Index("idx_orders_plan_id_status", "plan_id", "status"),)


class Fill(Base):
    """Fill."""

    __tablename__ = "fills"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    order_id = Column(PGUUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    filled_qty = Column(Numeric, nullable=False)
    filled_price = Column(Numeric, nullable=False)
    filled_at = Column(TIMESTAMP(timezone=True), nullable=False)
    raw = Column(JSONB, nullable=True)

    # Relationships
    order = relationship("Order", back_populates="fills")


class AuditEvent(Base):
    """Audit event."""

    __tablename__ = "audit_events"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_type = Column(Text, nullable=False)
    actor = Column(Text, nullable=False)
    ref_type = Column(Text, nullable=True)
    ref_id = Column(PGUUID(as_uuid=True), nullable=True)
    payload = Column(JSONB, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class AlertSent(Base):
    """Alert sent."""

    __tablename__ = "alerts_sent"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    level = Column(SQLEnum(AlertLevel), nullable=False)
    channel = Column(Text, nullable=False)
    title = Column(Text, nullable=False)
    body = Column(JSONB, nullable=False)
    sent_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())


class Control(Base):
    """Control (kill switch)."""

    __tablename__ = "controls"

    id = Column(Integer, primary_key=True, default=1)
    kill_switch = Column(Boolean, nullable=False, default=False)
    reason = Column(Text, nullable=True)
    updated_at = Column(
        TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )
