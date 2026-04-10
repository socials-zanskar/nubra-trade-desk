from __future__ import annotations

import streamlit as st

from nubra_dash.config import LIQUID_STOCKS_SYMBOLS, TOP_FNO_SYMBOLS, get_basket_options, load_app_config, resolve_symbols_for_basket


PAGES = [
    ("Home", "app.py"),
    ("Market Pulse", "pages/1_Market_Pulse.py"),
    ("Volume Tracker", "pages/2_Volume_Tracker.py"),
    ("Breakout Confirmation", "pages/4_Breakout_Confirmation.py"),
    ("OI Walls", "pages/3_OI_Walls.py"),
    ("Multi-Wall Explorer", "pages/5_Multi_Wall_Explorer.py"),
    ("Symbol Drilldown", "pages/6_Symbol_Drilldown.py"),
    ("Watchlist + Alerts", "pages/7_Watchlist_Alerts.py"),
]

NAV_LINKS = [
    ("Home", "/"),
    ("Market Pulse", "/Market_Pulse"),
    ("Volume Tracker", "/Volume_Tracker"),
    ("Breakout Confirmation", "/Breakout_Confirmation"),
    ("OI Walls", "/OI_Walls"),
    ("Multi-Wall Explorer", "/Multi_Wall_Explorer"),
    ("Symbol Drilldown", "/Symbol_Drilldown"),
    ("Watchlist + Alerts", "/Watchlist_Alerts"),
]


def render_sidebar() -> None:
    config = load_app_config()
    basket_options = get_basket_options()
    selected_basket = st.session_state.get("nubra_selected_basket", config.scans.default_basket)
    if selected_basket not in basket_options:
        selected_basket = config.scans.default_basket
    custom_symbols = st.session_state.get("nubra_custom_symbols", "")
    custom_symbol_values = [item.strip().upper() for item in custom_symbols.split(",") if item.strip()]
    searchable_custom_pool = tuple(dict.fromkeys((*TOP_FNO_SYMBOLS, *LIQUID_STOCKS_SYMBOLS)))

    nav_html = "".join(
        f'<a class="nubra-nav-link" href="{href}" target="_self">{label}</a>'
        for label, href in NAV_LINKS
    )
    st.markdown(
        f"""
        <div class="nubra-topbar">
          <div class="nubra-topbar-brand">
            <div>
              <div class="nubra-topbar-kicker">Trader workspace</div>
              <div class="nubra-topbar-title">Nubra Trading Desk</div>
            </div>
            <div style="display:flex; align-items:center; gap:0.5rem;">
              <div class="nubra-nav-hint">Scanner | Regime | Workbench</div>
              <div class="nubra-nav-banner">Switch views</div>
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

    controls = st.columns([0.18, 0.36, 0.1, 0.16, 0.2], gap="small")
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
        st.caption("CUSTOM LIST")
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
            st.text_input(
                "Custom symbols",
                value="Use Custom universe to pick symbols",
                disabled=True,
                label_visibility="collapsed",
            )

    selected_symbols = resolve_symbols_for_basket(selected_basket, custom_symbols)
    st.session_state["nubra_custom_symbols"] = custom_symbols
    st.session_state["nubra_selected_basket"] = selected_basket
    st.session_state["nubra_selected_symbols"] = selected_symbols

    with controls[2]:
        st.caption("NAMES")
        st.markdown(
            f"""
            <div class="nubra-inline-metric">
              <strong>{len(selected_symbols)}</strong>
              <span>In play</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with controls[3]:
        st.caption("FOCUS")
        st.markdown(
            f"""
            <div class="nubra-inline-metric">
              <strong>{selected_basket}</strong>
              <span>Current universe</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with controls[4]:
        st.caption("PREVIEW")
        symbol_preview = ", ".join(selected_symbols[:3]) if selected_symbols else "No symbols"
        more = f" +{len(selected_symbols) - 3}" if len(selected_symbols) > 3 else ""
        st.markdown(
            f"""
            <div class="nubra-inline-metric">
              <strong>{symbol_preview}</strong>
              <span>{more if more else "Universe preview"}</span>
            </div>
            """,
            unsafe_allow_html=True,
        )
def get_selected_symbols() -> tuple[str, ...]:
    config = load_app_config()
    if "nubra_selected_symbols" in st.session_state and st.session_state["nubra_selected_symbols"]:
        return tuple(st.session_state["nubra_selected_symbols"])
    return resolve_symbols_for_basket(config.scans.default_basket)


def get_runtime_app_config():
    return load_app_config()
