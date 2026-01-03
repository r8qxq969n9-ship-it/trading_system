"""Config page."""

import streamlit as st
from apps.ui.utils import api_get, api_post

def render():
    """Render config page."""
    st.title("Configuration")

    # Latest config
    config = api_get("/configs/latest")
    if "error" not in config:
        st.json(config)
    else:
        st.info("No config found. Create one below.")

    # Create config
    st.subheader("Create New Config")
    with st.form("create_config"):
        strategy_name = st.text_input("Strategy Name", value="dual_momentum")
        mode = st.selectbox("Mode", ["SIMULATION", "PAPER", "LIVE"])
        created_by = st.text_input("Created By", value="user")
        if st.form_submit_button("Create"):
            data = {
                "mode": mode,
                "strategy_name": strategy_name,
                "strategy_params": {},
                "constraints": {},
                "created_by": created_by,
            }
            result = api_post("/configs", data)
            if "error" not in result:
                st.success("Config created!")
                st.rerun()
            else:
                st.error(f"Error: {result['error']}")

