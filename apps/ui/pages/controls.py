"""Controls page."""

import streamlit as st

from apps.ui.utils import api_get, api_post


def render():
    """Render controls page."""
    st.title("Controls")

    controls = api_get("/controls")
    if "error" in controls:
        st.error(f"Error: {controls['error']}")
        return

    st.subheader("Kill Switch")
    st.write(f"Status: {'ON' if controls.get('kill_switch') else 'OFF'}")
    if controls.get("reason"):
        st.write(f"Reason: {controls['reason']}")

    # Toggle kill switch
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Turn ON"):
            result = api_post("/controls/kill-switch", {"on": True, "reason": "Manual toggle"})
            if "error" not in result:
                st.success("Kill switch turned ON")
                st.rerun()
    with col2:
        if st.button("Turn OFF"):
            result = api_post("/controls/kill-switch", {"on": False, "reason": "Manual toggle"})
            if "error" not in result:
                st.success("Kill switch turned OFF")
                st.rerun()
