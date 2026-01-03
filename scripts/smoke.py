"""Smoke test script: full E2E flow validation."""

import os
import sys
import traceback
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func

from apps.api.main import app
from packages.core.database import get_session_factory
from packages.core.models import (
    AlertLevel,
    AuditEvent,
    Execution,
    ExecutionStatus,
    Fill,
    Order,
    PlanItem,
    PlanStatus,
    PortfolioSnapshot,
    RebalancePlan,
    TradingMode,
)
from packages.ops.slack import send

# Enable stub prices for deterministic testing
os.environ["USE_STUB_PRICES"] = "true"
os.environ["STUB_PRICE_SEED"] = "42"

client = TestClient(app)


def send_error_alert(error_msg: str):
    """Send error alert to Slack."""
    error_snippet = error_msg[-500:] if len(error_msg) > 500 else error_msg
    send(
        level=AlertLevel.ERROR,
        channel="alerts",
        title="Smoke Test 실패",
        body_json={
            "error": error_snippet,
            "timestamp": datetime.utcnow().isoformat(),
        },
    )


def print_db_row_counts():
    """Print database row counts for key tables."""
    try:
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            plans_count = db.query(func.count(RebalancePlan.id)).scalar()
            executions_count = db.query(func.count(Execution.id)).scalar()
            orders_count = db.query(func.count(Order.id)).scalar()
            fills_count = db.query(func.count(Fill.id)).scalar()
            audit_events_count = db.query(func.count(AuditEvent.id)).scalar()
            portfolio_snapshots_count = db.query(func.count(PortfolioSnapshot.id)).scalar()

            print("\n" + "=" * 50)
            print("Database Row Counts:")
            print("=" * 50)
            print(f"  rebalance_plans:        {plans_count}")
            print(f"  executions:             {executions_count}")
            print(f"  orders:                 {orders_count}")
            print(f"  fills:                  {fills_count}")
            print(f"  audit_events:           {audit_events_count}")
            print(f"  portfolio_snapshots:   {portfolio_snapshots_count}")
            print("=" * 50)
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: Failed to get DB row counts: {e}")


def verify_ui_data():
    """Verify that UI can display proposals and executions (at least 1 each)."""
    try:
        # Check plans via API
        plans_response = client.get("/plans")
        if plans_response.status_code == 200:
            plans = plans_response.json()
            plans_count = len(plans) if isinstance(plans, list) else 0
            print(f"\n✓ UI Proposals check: {plans_count} plan(s) available")
            if plans_count == 0:
                print("  WARNING: No plans found for UI display")
        else:
            print(f"\n⚠ UI Proposals check: API returned {plans_response.status_code}")

        # Check executions via API
        executions_response = client.get("/executions")
        if executions_response.status_code == 200:
            executions = executions_response.json()
            executions_count = len(executions) if isinstance(executions, list) else 0
            print(f"✓ UI Executions check: {executions_count} execution(s) available")
            if executions_count == 0:
                print("  WARNING: No executions found for UI display")
        else:
            print(f"⚠ UI Executions check: API returned {executions_response.status_code}")

        return plans_count > 0 and executions_count > 0
    except Exception as e:
        print(f"Warning: Failed to verify UI data: {e}")
        return False


def send_completion_summary(plan_id: str, execution_id: str):
    """Send G1 completion summary to Slack (once only, spam prevention)."""
    try:
        SessionLocal = get_session_factory()
        db = SessionLocal()
        try:
            # Get counts
            plans_count = db.query(func.count(RebalancePlan.id)).scalar()
            executions_count = db.query(func.count(Execution.id)).scalar()
            orders_count = db.query(func.count(Order.id)).scalar()
            fills_count = db.query(func.count(Fill.id)).scalar()

            # Get plan summary
            plan = db.query(RebalancePlan).filter(RebalancePlan.id == plan_id).first()
            plan_items_count = (
                db.query(func.count(PlanItem.id)).filter(PlanItem.plan_id == plan_id).scalar()
            )

            # Check if we already sent a completion summary (spam prevention)
            # Look for recent "G1 POC E2E 완주 완료" alerts in the last hour
            from datetime import timedelta

            cutoff_time = datetime.utcnow() - timedelta(hours=1)
            recent_alerts = (
                db.query(AuditEvent)
                .filter(
                    AuditEvent.event_type == "g1_completion_summary_sent",
                    AuditEvent.created_at >= cutoff_time,
                )
                .count()
            )

            if recent_alerts > 0:
                print("  (Skipping Slack notification - already sent recently)")
                return

            # Send summary
            sent = send(
                level=AlertLevel.INFO,
                channel="dev",
                title="G1 POC E2E 완주 완료",
                body_json={
                    "status": "success",
                    "plan_id": plan_id,
                    "execution_id": execution_id,
                    "plan_items": plan_items_count,
                    "summary": {
                        "total_plans": plans_count,
                        "total_executions": executions_count,
                        "total_orders": orders_count,
                        "total_fills": fills_count,
                    },
                    "timestamp": datetime.utcnow().isoformat(),
                },
            )

            if sent:
                # Record that we sent the summary (for spam prevention)
                from packages.ops.audit import record_audit_event

                record_audit_event(
                    db=db,
                    event_type="g1_completion_summary_sent",
                    actor="smoke_test",
                    ref_type="execution",
                    ref_id=execution_id,
                    payload={"plan_id": plan_id},
                )
                db.commit()
        finally:
            db.close()
    except Exception as e:
        print(f"Warning: Failed to send completion summary: {e}")


def main():
    """Run smoke test."""
    try:
        # 1. Create config version
        print("Step 1: Creating config version...")
        config_response = client.post(
            "/configs",
            json={
                "mode": TradingMode.PAPER.value,
                "strategy_name": "dual_momentum",
                "strategy_params": {
                    "lookback_months": 3,
                    "us_top_n": 4,
                    "kr_top_m": 2,
                    "kr_us_split": [0.4, 0.6],
                },
                "constraints": {
                    "max_positions": 20,
                    "max_weight_per_name": 0.08,
                    "kr_us_split": [0.4, 0.6],
                },
                "created_by": "smoke_test",
            },
        )
        if config_response.status_code != 200:
            error_msg = f"Config creation failed: {config_response.status_code} - {config_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        config_id = config_response.json()["id"]
        print(f"✓ Config created: {config_id}")

        # 2. Create data snapshot
        print("Step 2: Creating data snapshot...")
        data_response = client.post(
            "/data/snapshot",
            json={
                "source": "smoke_test",
                "asof": datetime.now(timezone.utc).isoformat(),
                "meta": {"test": True},
            },
        )
        if data_response.status_code != 200:
            error_msg = f"Data snapshot creation failed: {data_response.status_code} - {data_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        data_snapshot_id = data_response.json()["id"]
        print(f"✓ Data snapshot created: {data_snapshot_id}")

        # 3. Create portfolio snapshot
        print("Step 3: Creating portfolio snapshot...")
        portfolio_response = client.post(
            "/portfolio",
            json={
                "asof": datetime.now(timezone.utc).isoformat(),
                "mode": TradingMode.PAPER.value,
                "positions": {"005930": 10, "AAPL": 5},
                "cash": 1000000.0,
                "nav": 2000000.0,
            },
        )
        if portfolio_response.status_code != 200:
            error_msg = f"Portfolio snapshot creation failed: {portfolio_response.status_code} - {portfolio_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        portfolio_id = portfolio_response.json()["id"]
        print(f"✓ Portfolio snapshot created: {portfolio_id}")

        # 4. Generate plan
        print("Step 4: Generating plan...")
        plan_response = client.post(
            "/plans/generate",
            json={
                "config_version_id": config_id,
                "data_snapshot_id": data_snapshot_id,
            },
        )
        if plan_response.status_code != 200:
            error_msg = f"Plan generation failed: {plan_response.status_code} - {plan_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        plan_data = plan_response.json()
        plan_id = plan_data["id"]
        if plan_data["status"] != PlanStatus.PROPOSED.value:
            error_msg = f"Plan status is not PROPOSED: {plan_data['status']}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        if len(plan_data["items"]) == 0:
            error_msg = "Plan has no items"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        print(f"✓ Plan generated: {plan_id} ({len(plan_data['items'])} items)")

        # 5. Approve plan
        print("Step 5: Approving plan...")
        approve_response = client.post(
            f"/plans/{plan_id}/approve",
            json={"approved_by": "smoke_test"},
        )
        if approve_response.status_code != 200:
            error_msg = f"Plan approval failed: {approve_response.status_code} - {approve_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        print(f"✓ Plan approved: {plan_id}")

        # 6. Start execution
        print("Step 6: Starting execution...")
        execution_response = client.post(
            f"/executions/{plan_id}/start",
            json={"policy": {}},
        )
        if execution_response.status_code != 200:
            error_msg = f"Execution start failed: {execution_response.status_code} - {execution_response.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        execution_data = execution_response.json()
        execution_id = execution_data["id"]
        if execution_data["status"] != ExecutionStatus.DONE.value:
            error_msg = f"Execution status is not DONE: {execution_data['status']}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        print(f"✓ Execution completed: {execution_id}")

        # 7. Verify execution details
        print("Step 7: Verifying execution details...")
        execution_get = client.get(f"/executions/{execution_id}")
        if execution_get.status_code != 200:
            error_msg = f"Execution retrieval failed: {execution_get.status_code} - {execution_get.text}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        execution_detail = execution_get.json()
        if execution_detail["status"] != ExecutionStatus.DONE.value:
            error_msg = f"Execution status verification failed: {execution_detail['status']}"
            print(f"ERROR: {error_msg}")
            send_error_alert(error_msg)
            sys.exit(1)
        print(f"✓ Execution verified: {execution_id}")

        # 8. Print DB row counts
        print_db_row_counts()

        # 9. Verify UI data availability
        ui_verified = verify_ui_data()
        if not ui_verified:
            print("\n⚠ WARNING: UI may not display proposals/executions correctly")
            print("  Please verify manually: streamlit run apps/ui/main.py")
            print("  Navigate to 'Proposals' and 'Executions' pages")

        # 10. Send completion summary to Slack (once only, spam prevention)
        send_completion_summary(plan_id, execution_id)

        print("\n✅ Smoke test PASSED!")
        print("\nNext steps:")
        print("  1. Check artifacts/smoke.log for full execution log")
        print("  2. Verify UI: streamlit run apps/ui/main.py")
        print("  3. Check Slack for completion summary")
        sys.exit(0)

    except Exception as e:
        error_msg = f"Smoke test failed with exception: {str(e)}\n{traceback.format_exc()}"
        print(f"ERROR: {error_msg}")
        send_error_alert(error_msg)
        sys.exit(1)


if __name__ == "__main__":
    main()

