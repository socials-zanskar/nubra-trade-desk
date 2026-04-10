from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.ui.mission_control import render_mission_control_home
from nubra_dash.ui.runtime import load_snapshot_with_feedback, render_refresh_bar
from nubra_dash.ui.shell import get_runtime_app_config, get_selected_symbols, render_sidebar
from nubra_dash.ui.theme import inject_css


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

render_mission_control_home(
    app_config=config,
    snapshot=snapshot,
    selected_symbols=selected_symbols,
    used_cache=used_cache,
)
