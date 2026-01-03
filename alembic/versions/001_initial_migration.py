"""Initial migration

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create enums
    op.execute("CREATE TYPE tradingmode AS ENUM ('SIMULATION', 'PAPER', 'LIVE')")
    op.execute("CREATE TYPE planstatus AS ENUM ('PROPOSED', 'APPROVED', 'REJECTED', 'EXPIRED')")
    op.execute("CREATE TYPE executionstatus AS ENUM ('PENDING', 'RUNNING', 'DONE', 'FAILED', 'CANCELED')")
    op.execute("CREATE TYPE runkind AS ENUM ('SIMULATION', 'PAPER', 'PLAN', 'EXECUTE')")
    op.execute("CREATE TYPE runstatus AS ENUM ('STARTED', 'DONE', 'FAILED')")
    op.execute("CREATE TYPE market AS ENUM ('KR', 'US')")
    op.execute("CREATE TYPE orderside AS ENUM ('BUY', 'SELL')")
    op.execute("CREATE TYPE orderstatus AS ENUM ('CREATED', 'SENT', 'PARTIAL', 'FILLED', 'CANCELED', 'FAILED', 'SKIPPED')")
    op.execute("CREATE TYPE alertlevel AS ENUM ('INFO', 'WARN', 'ERROR', 'DECISION_REQUIRED')")

    # config_versions
    op.create_table(
        'config_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('mode', postgresql.ENUM('SIMULATION', 'PAPER', 'LIVE', name='tradingmode'), nullable=False),
        sa.Column('strategy_name', sa.Text(), nullable=False),
        sa.Column('strategy_params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.Text(), nullable=False),
    )

    # data_snapshots
    op.create_table(
        'data_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('asof', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # portfolio_snapshots
    op.create_table(
        'portfolio_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('asof', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('mode', postgresql.ENUM('SIMULATION', 'PAPER', 'LIVE', name='tradingmode'), nullable=False),
        sa.Column('positions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('cash', sa.Numeric(), nullable=False),
        sa.Column('nav', sa.Numeric(), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # runs
    op.create_table(
        'runs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('kind', postgresql.ENUM('SIMULATION', 'PAPER', 'PLAN', 'EXECUTE', name='runkind'), nullable=False),
        sa.Column('status', postgresql.ENUM('STARTED', 'DONE', 'FAILED', name='runstatus'), nullable=False),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('meta', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
    )

    # rebalance_plans
    op.create_table(
        'rebalance_plans',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('runs.id'), nullable=False),
        sa.Column('config_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('config_versions.id'), nullable=False),
        sa.Column('data_snapshot_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('data_snapshots.id'), nullable=False),
        sa.Column('status', postgresql.ENUM('PROPOSED', 'APPROVED', 'REJECTED', 'EXPIRED', name='planstatus'), nullable=False, server_default='PROPOSED'),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('approved_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('approved_by', sa.Text(), nullable=True),
        sa.Column('rejected_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('rejected_by', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.TIMESTAMP(timezone=True), nullable=True),
    )
    op.create_index('idx_rebalance_plans_status_created_at', 'rebalance_plans', ['status', 'created_at'])

    # plan_items
    op.create_table(
        'plan_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rebalance_plans.id'), nullable=False),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('market', postgresql.ENUM('KR', 'US', name='market'), nullable=False),
        sa.Column('current_weight', sa.Numeric(), nullable=False),
        sa.Column('target_weight', sa.Numeric(), nullable=False),
        sa.Column('delta_weight', sa.Numeric(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('checks', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # executions
    op.create_table(
        'executions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rebalance_plans.id'), nullable=False),
        sa.Column('status', postgresql.ENUM('PENDING', 'RUNNING', 'DONE', 'FAILED', 'CANCELED', name='executionstatus'), nullable=False, server_default='PENDING'),
        sa.Column('started_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('ended_at', sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column('policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.UniqueConstraint('plan_id', name='uq_executions_plan_id'),
    )

    # orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('plan_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('rebalance_plans.id'), nullable=False),
        sa.Column('execution_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('executions.id'), nullable=True),
        sa.Column('symbol', sa.Text(), nullable=False),
        sa.Column('side', postgresql.ENUM('BUY', 'SELL', name='orderside'), nullable=False),
        sa.Column('qty', sa.Numeric(), nullable=False),
        sa.Column('order_type', sa.Text(), nullable=False),
        sa.Column('limit_price', sa.Numeric(), nullable=True),
        sa.Column('status', postgresql.ENUM('CREATED', 'SENT', 'PARTIAL', 'FILLED', 'CANCELED', 'FAILED', 'SKIPPED', name='orderstatus'), nullable=False, server_default='CREATED'),
        sa.Column('broker_order_id', sa.Text(), nullable=True),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    op.create_index('idx_orders_plan_id_status', 'orders', ['plan_id', 'status'])

    # fills
    op.create_table(
        'fills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('filled_qty', sa.Numeric(), nullable=False),
        sa.Column('filled_price', sa.Numeric(), nullable=False),
        sa.Column('filled_at', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )

    # audit_events
    op.create_table(
        'audit_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('event_type', sa.Text(), nullable=False),
        sa.Column('actor', sa.Text(), nullable=False),
        sa.Column('ref_type', sa.Text(), nullable=True),
        sa.Column('ref_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # alerts_sent
    op.create_table(
        'alerts_sent',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('level', postgresql.ENUM('INFO', 'WARN', 'ERROR', 'DECISION_REQUIRED', name='alertlevel'), nullable=False),
        sa.Column('channel', sa.Text(), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sent_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )

    # controls
    op.create_table(
        'controls',
        sa.Column('id', sa.Integer(), primary_key=True, server_default='1'),
        sa.Column('kill_switch', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('reason', sa.Text(), nullable=True),
        sa.Column('updated_at', sa.TIMESTAMP(timezone=True), server_default=sa.text('now()'), nullable=False),
    )
    # Insert initial control row
    op.execute("INSERT INTO controls (id, kill_switch) VALUES (1, false) ON CONFLICT (id) DO NOTHING")


def downgrade() -> None:
    op.drop_table('controls')
    op.drop_table('alerts_sent')
    op.drop_table('audit_events')
    op.drop_table('fills')
    op.drop_table('orders')
    op.drop_table('executions')
    op.drop_table('plan_items')
    op.drop_table('rebalance_plans')
    op.drop_table('runs')
    op.drop_table('portfolio_snapshots')
    op.drop_table('data_snapshots')
    op.drop_table('config_versions')
    
    op.execute("DROP TYPE alertlevel")
    op.execute("DROP TYPE orderstatus")
    op.execute("DROP TYPE orderside")
    op.execute("DROP TYPE market")
    op.execute("DROP TYPE runstatus")
    op.execute("DROP TYPE runkind")
    op.execute("DROP TYPE executionstatus")
    op.execute("DROP TYPE planstatus")
    op.execute("DROP TYPE tradingmode")

