"""Positions page."""

import streamlit as st
from apps.ui.utils import api_get

def render():
    """Render positions page."""
    st.title("Positions")

    portfolio = api_get("/portfolio/latest")
    if "error" in portfolio:
        st.error(f"Error: {portfolio['error']}")
        return

    st.metric("NAV", f"${portfolio.get('nav', 0):,.2f}")
    st.metric("Cash", f"${portfolio.get('cash', 0):,.2f}")

    positions = portfolio.get("positions", {})
    if positions:
        st.dataframe(positions)
    else:
        st.info("No positions")

