"""Proposals page."""

import streamlit as st
from apps.ui.utils import api_get

def render():
    """Render proposals page."""
    st.title("Proposals")

    plans = api_get("/plans")
    if "error" in plans:
        st.error(f"Error: {plans['error']}")
        return

    if not plans:
        st.info("No plans found")
        return

    for plan in plans:
        with st.expander(f"Plan {plan['id'][:8]} - {plan['status']}"):
            st.json(plan)
            if plan["status"] == "PROPOSED":
                st.button(f"View Details", key=f"view_{plan['id']}")

