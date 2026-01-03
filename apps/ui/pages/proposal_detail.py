"""Proposal detail page."""

import streamlit as st
from apps.ui.utils import api_get, api_post

def render():
    """Render proposal detail page."""
    st.title("Proposal Detail")

    plan_id = st.text_input("Plan ID")
    if not plan_id:
        st.info("Enter a Plan ID to view details")
        return

    plan = api_get(f"/plans/{plan_id}")
    if "error" in plan:
        st.error(f"Error: {plan['error']}")
        return

    st.subheader(f"Plan {plan_id[:8]}")
    st.write(f"Status: {plan['status']}")

    # Summary 3 lines (as per PRD)
    summary = plan.get("summary", {})
    st.write("**1. KR/US 비중 변화 요약**")
    st.write(summary.get("kr_us_summary", "N/A"))
    st.write("**2. Top 3 매매 변화**")
    st.write(summary.get("top_3_changes", "N/A"))
    st.write("**3. 제약/리스크 체크 결과**")
    st.write(summary.get("constraint_checks", "N/A"))

    # Items
    if plan.get("items"):
        st.subheader("Plan Items")
        st.dataframe(plan["items"])

    # Actions
    if plan["status"] == "PROPOSED":
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve"):
                result = api_post(f"/plans/{plan_id}/approve", {"approved_by": "user"})
                if "error" not in result:
                    st.success("Plan approved!")
                    st.rerun()
        with col2:
            if st.button("Reject"):
                result = api_post(f"/plans/{plan_id}/reject", {"rejected_by": "user"})
                if "error" not in result:
                    st.success("Plan rejected!")
                    st.rerun()

