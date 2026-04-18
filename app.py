from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css

load_local_env()


st.set_page_config(
    page_title="Nubra Signal Discovery",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar()

config = get_runtime_app_config()
selected_symbols = get_selected_symbols()
render_refresh_bar("home", config, selected_symbols, live_auth=False, prefer_database=True)
snapshot, used_cache = load_snapshot_with_feedback(
    "Loading trading desk...",
    config,
    selected_symbols,
    live_auth=False,
    prefer_database=True,
)

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Welcome</div>
      <h1 class="nubra-desk-title">Nubra APIs Trading Desk</h1>
      <p class="nubra-desk-copy">
        Discover the power of Nubra APIs through our focused applications. 
        Select an option from the sidebar to begin.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown("### :bar_chart: <a href='/Volume_Tracker' target='_self' style='color:var(--color-text); text-decoration:none;'>Volume Dashboard</a>", unsafe_allow_html=True)
    st.caption("Identify abnormal volume participation using real-time data.")
    st.markdown("Track massive volume spikes against a baseline to discover strong directional moves. Nubra APIs provide robust volume signals.")
    
with col2:
    st.markdown("### :building_construction: <a href='/OI_Walls' target='_self' style='color:var(--color-text); text-decoration:none;'>Options Section</a>", unsafe_allow_html=True)
    st.caption("Track Open Interest structures and key resistance limits.")
    st.markdown("Visualize live options data to find critical OI walls and structure breakdowns, powered reliably by Nubra API integrations.")
