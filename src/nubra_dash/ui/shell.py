from __future__ import annotations

import streamlit as st

from nubra_dash.config import (
    LIQUID_STOCKS_SYMBOLS,
    MARKET_300_SYMBOLS,
    TOP_FNO_SYMBOLS,
    get_basket_options,
    load_app_config,
    resolve_symbols_for_basket,
)


PAGES = [
    ("Home", "app.py"),
    ("Market Pulse", "pages/1_Market_Pulse.py"),
    ("Volume Tracker", "pages/2_Volume_Tracker.py"),
    ("Breakout Confirmation", "pages/4_Breakout_Confirmation.py"),
    ("OI Walls", "pages/3_OI_Walls.py"),
    ("Multi-Wall Explorer", "pages/5_Multi_Wall_Explorer.py"),
    ("Symbol Drilldown", "pages/6_Symbol_Drilldown.py"),
]

NAV_LINKS = [
    ("Home", "/"),
    ("Market Pulse", "/Market_Pulse"),
    ("Volume Tracker", "/Volume_Tracker"),
    ("Breakout Confirmation", "/Breakout_Confirmation"),
    ("OI Walls", "/OI_Walls"),
    ("Multi-Wall Explorer", "/Multi_Wall_Explorer"),
    ("Symbol Drilldown", "/Symbol_Drilldown"),
]


def render_sidebar() -> None:
    config = load_app_config()
    basket_options = get_basket_options()
    active_theme = str(st.session_state.get("nubra_theme", "dark")).lower()
    selected_basket = st.session_state.get("nubra_selected_basket", config.scans.default_basket)
    if selected_basket not in basket_options:
        selected_basket = config.scans.default_basket
    custom_symbols = st.session_state.get("nubra_custom_symbols", "")
    custom_symbol_values = [item.strip().upper() for item in custom_symbols.split(",") if item.strip()]
    searchable_custom_pool = tuple(dict.fromkeys((*TOP_FNO_SYMBOLS, *LIQUID_STOCKS_SYMBOLS, *MARKET_300_SYMBOLS)))

    nav_html = "".join(
        f'<a class="nubra-nav-link" href="{href}" target="_self">{label}</a>'
        for label, href in NAV_LINKS
    )
    st.markdown(
        f"""
        <div class="nubra-topbar">
          <div class="nubra-topbar-brand">
            <div class="nubra-brand-lockup">
              <div class="nubra-brand-mark">N</div>
              <div>
                <div class="nubra-topbar-kicker">Launch workspace</div>
                <div class="nubra-topbar-title">Nubra APIs Trading Desk</div>
              </div>
            </div>
            <div class="nubra-topbar-meta">
              <div class="nubra-nav-banner">Sandbox desk</div>
              <div class="nubra-nav-hint">Volume scanners | OI structure | Symbol reads</div>
            </div>
          </div>
          <div class="nubra-nav-row">
            {nav_html}
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown('<div class="nubra-topbar-spacer"></div>', unsafe_allow_html=True)

    controls = st.columns([0.21, 0.39, 0.24, 0.16], gap="small")
    with controls[0]:
        st.caption("UNIVERSE")
        selected_basket = st.selectbox(
            "Scan universe",
            basket_options,
            index=basket_options.index(selected_basket),
            label_visibility="collapsed",
            help="This changes the symbol set used by the stock-signal pages.",
        )
    with controls[1]:
        st.caption("SYMBOL SET")
        if selected_basket == "Custom":
            selected_custom = st.multiselect(
                "Custom symbols",
                options=searchable_custom_pool,
                default=[item for item in custom_symbol_values if item in searchable_custom_pool],
                label_visibility="collapsed",
                placeholder="Search and add symbols",
                help="Choose from the curated liquid universe for faster custom scans.",
            )
            manual_symbols = st.text_input(
                "Additional symbols",
                value=",".join(item for item in custom_symbol_values if item not in searchable_custom_pool),
                placeholder="Optional extra symbols, comma separated",
                label_visibility="collapsed",
                help="Add symbols not present in the curated picker.",
            )
            combined_custom = list(selected_custom)
            combined_custom.extend(item.strip().upper() for item in manual_symbols.split(",") if item.strip())
            custom_symbols = ",".join(dict.fromkeys(combined_custom))
        else:
            st.markdown(
                """
                <div class="nubra-control-note">
                  Switch to <strong>Custom</strong> when you want to choose names manually.
                </div>
                """,
                unsafe_allow_html=True,
            )

    selected_symbols = resolve_symbols_for_basket(selected_basket, custom_symbols)
    st.session_state["nubra_custom_symbols"] = custom_symbols
    st.session_state["nubra_selected_basket"] = selected_basket
    st.session_state["nubra_selected_symbols"] = selected_symbols

    with controls[2]:
        st.caption("DESK SUMMARY")
        symbol_preview = ", ".join(selected_symbols[:3]) if selected_symbols else "No symbols"
        more = f"+{len(selected_symbols) - 3} more" if len(selected_symbols) > 3 else "Focused basket"
        st.markdown(
            f"""
            <div class="nubra-control-summary">
              <div class="nubra-control-summary-top">
                <span class="nubra-chip tone-cyan">{len(selected_symbols)} names</span>
                <span class="nubra-chip tone-purple">{selected_basket}</span>
              </div>
              <strong>{symbol_preview}</strong>
              <span>{more}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with controls[3]:
        st.caption("APPEARANCE")
        theme_choice = st.radio(
            "Appearance",
            options=["Dark", "Light"],
            index=0 if active_theme == "dark" else 1,
            horizontal=True,
            label_visibility="collapsed",
        )
        st.session_state["nubra_theme"] = theme_choice.lower()


def get_selected_symbols() -> tuple[str, ...]:
    config = load_app_config()
    if "nubra_selected_symbols" in st.session_state and st.session_state["nubra_selected_symbols"]:
        return tuple(st.session_state["nubra_selected_symbols"])
    return resolve_symbols_for_basket(config.scans.default_basket)


def get_runtime_app_config():
    return load_app_config()
