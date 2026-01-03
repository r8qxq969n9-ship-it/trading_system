"""Executions page."""

import streamlit as st

from apps.ui.utils import api_get


def render():
    """Render executions page."""
    st.title("Executions")

    executions = api_get("/executions")
    if "error" in executions:
        st.error(f"Error: {executions['error']}")
        return

    if not executions:
        st.info("No executions found")
        return

    for execution in executions:
        with st.expander(f"Execution {execution['id'][:8]} - {execution['status']}"):
            st.json(execution)
