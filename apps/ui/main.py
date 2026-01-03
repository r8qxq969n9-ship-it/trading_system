"""Streamlit main application."""

import streamlit as st

st.set_page_config(
    page_title="Trading System",
    page_icon="📈",
    layout="wide",
)

# Sidebar navigation
st.sidebar.title("Trading System")
page = st.sidebar.selectbox(
    "Navigation",
    [
        "Dashboard",
        "Config",
        "Proposals",
        "Proposal Detail",
        "Executions",
        "Positions",
        "Audit",
        "Controls",
    ],
)

# Route to pages
if page == "Dashboard":
    from apps.ui.pages.dashboard import render
    render()
elif page == "Config":
    from apps.ui.pages.config import render
    render()
elif page == "Proposals":
    from apps.ui.pages.proposals import render
    render()
elif page == "Proposal Detail":
    from apps.ui.pages.proposal_detail import render
    render()
elif page == "Executions":
    from apps.ui.pages.executions import render
    render()
elif page == "Positions":
    from apps.ui.pages.positions import render
    render()
elif page == "Audit":
    from apps.ui.pages.audit import render
    render()
elif page == "Controls":
    from apps.ui.pages.controls import render
    render()

