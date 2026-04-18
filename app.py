from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from nubra_dash.bootstrap import load_local_env
from nubra_dash.ui.shell import render_sidebar
from nubra_dash.ui.theme import inject_css

load_local_env()


st.set_page_config(
    page_title="Nubra Signal Discovery",
    page_icon=":bar_chart:",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()
render_sidebar("Home")

st.markdown(
    """
    <div class="nubra-desk-hero">
      <div class="nubra-kicker">Focused desk</div>
      <h1 class="nubra-desk-title">Two fast surfaces. Volume first, options second.</h1>
      <p class="nubra-desk-copy">
        This build is intentionally narrow: one board for abnormal participation and one board for index option structure.
        It shows how Nubra APIs can power a trader-facing desk without burying the signal in extra screens.
      </p>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2 = st.columns(2, gap="large")
with col1:
    st.markdown(
        """
        <div class="nubra-card" style="min-height: 12rem;">
          <div class="nubra-kicker">Volume</div>
          <h2 style="margin:0 0 0.45rem 0;"><a href="/Volume_Tracker" target="_self" style="color:var(--color-text); text-decoration:none;">Participation board</a></h2>
          <p class="nubra-desk-copy" style="margin-bottom:0.9rem;">
            Rank names by abnormal participation, tighten the list with a ratio floor, and keep only what deserves setup review.
          </p>
          <span class="nubra-chip tone-cyan">Volume spikes</span>
          <span class="nubra-chip tone-green">Shortlist flow</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
with col2:
    st.markdown(
        """
        <div class="nubra-card" style="min-height: 12rem;">
          <div class="nubra-kicker">Options</div>
          <h2 style="margin:0 0 0.45rem 0;"><a href="/OI_Walls" target="_self" style="color:var(--color-text); text-decoration:none;">Index OI walls</a></h2>
          <p class="nubra-desk-copy" style="margin-bottom:0.9rem;">
            Read NIFTY and SENSEX ladders directly, overlay the dominant scanner wall, and see where structure is actually stacked.
          </p>
          <span class="nubra-chip tone-purple">Current expiry</span>
          <span class="nubra-chip tone-blue">Wall structure</span>
        </div>
        """,
        unsafe_allow_html=True,
    )
