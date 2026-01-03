"""Dashboard page."""

import streamlit as st

from apps.ui.utils import api_get


def render():
    """Render dashboard."""
    st.title("Dashboard")

    # Health check
    health = api_get("/health")
    if "error" not in health:
        st.success("API is healthy")
    else:
        st.error(f"API error: {health['error']}")

    # Latest portfolio
    st.subheader("Latest Portfolio")
    portfolio = api_get("/portfolio/latest")
    if "error" not in portfolio:
        col1, col2, col3 = st.columns(3)
        col1.metric("NAV", f"${portfolio.get('nav', 0):,.2f}")
        col2.metric("Cash", f"${portfolio.get('cash', 0):,.2f}")
        col3.metric("Positions", len(portfolio.get("positions", {})))
    else:
        st.warning("No portfolio data available")

    # Recent plans
    st.subheader("Recent Plans")
    plans = api_get("/plans")
    if "error" not in plans and plans:
        for plan in plans[:5]:
            st.write(f"Plan {plan['id'][:8]} - {plan['status']}")
