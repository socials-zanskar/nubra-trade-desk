from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ThemeSpec:
    mode: str
    bg: str
    bg_alt: str
    surface: str
    surface_alt: str
    surface_soft: str
    border: str
    border_strong: str
    text: str
    muted: str
    accent: str
    accent_2: str
    accent_soft: str
    success: str
    warning: str
    danger: str
    purple: str
    shadow: str
    glow: str
    chart_grid: str
    input_bg: str
    overlay: str


DARK_THEME = ThemeSpec(
    mode="dark",
    bg="#0a0913",
    bg_alt="#131221",
    surface="#11121c",
    surface_alt="#171827",
    surface_soft="#1d1f31",
    border="#292b43",
    border_strong="#3a3d5f",
    text="#f4f3ff",
    muted="#a3abc2",
    accent="#8b6cff",
    accent_2="#5d7dff",
    accent_soft="#19152c",
    success="#35d6a0",
    warning="#ffbd5a",
    danger="#ff7393",
    purple="#b49cff",
    shadow="0 22px 55px rgba(3, 4, 11, 0.42)",
    glow="rgba(139, 108, 255, 0.24)",
    chart_grid="rgba(255, 255, 255, 0.08)",
    input_bg="#141625",
    overlay="rgba(10, 10, 18, 0.82)",
)

LIGHT_THEME = ThemeSpec(
    mode="light",
    bg="#f6f4ff",
    bg_alt="#f0eefb",
    surface="#ffffff",
    surface_alt="#faf8ff",
    surface_soft="#f2effc",
    border="#dfd9f5",
    border_strong="#c9c0eb",
    text="#151829",
    muted="#69738b",
    accent="#7a63ef",
    accent_2="#4e74ff",
    accent_soft="#f0ebff",
    success="#1ea46b",
    warning="#c88819",
    danger="#d94f70",
    purple="#8b74f7",
    shadow="0 24px 60px rgba(125, 111, 175, 0.18)",
    glow="rgba(122, 99, 239, 0.14)",
    chart_grid="rgba(21, 24, 41, 0.08)",
    input_bg="#fbfaff",
    overlay="rgba(246, 244, 255, 0.9)",
)


PALETTE = DARK_THEME


def get_theme_mode() -> str:
    import streamlit as st

    return str(st.session_state.get("nubra_theme", "dark")).lower()


def get_active_theme() -> ThemeSpec:
    return LIGHT_THEME if get_theme_mode() == "light" else DARK_THEME


def resolve_semantic_color(name: str) -> str:
    theme = get_active_theme()
    return {
        "accent": theme.accent,
        "info": theme.accent_2,
        "success": theme.success,
        "warning": theme.warning,
        "danger": theme.danger,
        "purple": theme.purple,
        "muted": theme.muted,
        "text": theme.text,
    }.get(name, name)


def get_plotly_palette() -> dict[str, str]:
    theme = get_active_theme()
    return {
        "bg": "rgba(0,0,0,0)",
        "panel": "rgba(17,18,28,0.72)" if theme.mode == "dark" else "rgba(255,255,255,0.76)",
        "grid": theme.chart_grid,
        "zero": theme.border_strong,
        "text": theme.text,
        "muted": theme.muted,
        "accent": theme.accent,
        "accent_2": theme.accent_2,
        "success": theme.success,
        "warning": theme.warning,
        "danger": theme.danger,
        "purple": theme.purple,
    }


def inject_css() -> None:
    import streamlit as st

    theme = get_active_theme()
    is_dark = theme.mode == "dark"
    background = (
        "radial-gradient(circle at top left, rgba(139, 108, 255, 0.18), transparent 28%),"
        "radial-gradient(circle at top right, rgba(93, 125, 255, 0.14), transparent 24%),"
        "linear-gradient(180deg, #0a0913 0%, #10111d 100%)"
        if is_dark
        else "radial-gradient(circle at top left, rgba(139, 108, 255, 0.10), transparent 26%),"
        "radial-gradient(circle at top right, rgba(93, 125, 255, 0.08), transparent 22%),"
        "linear-gradient(180deg, #f7f5ff 0%, #f2f3fb 100%)"
    )
    text_on_accent = "#ffffff" if not is_dark else "#f7f5ff"
    primary_button_text = "#f7f5ff" if is_dark else "#ffffff"

    st.markdown(
        f"""
        <style>
          :root {{
            --color-bg: {theme.bg};
            --color-bg-alt: {theme.bg_alt};
            --color-surface: {theme.surface};
            --color-surface-alt: {theme.surface_alt};
            --color-surface-soft: {theme.surface_soft};
            --color-border: {theme.border};
            --color-border-strong: {theme.border_strong};
            --color-text: {theme.text};
            --color-muted: {theme.muted};
            --color-accent: {theme.accent};
            --color-accent-2: {theme.accent_2};
            --color-accent-soft: {theme.accent_soft};
            --color-success: {theme.success};
            --color-warning: {theme.warning};
            --color-danger: {theme.danger};
            --color-purple: {theme.purple};
            --color-shadow: {theme.shadow};
            --color-glow: {theme.glow};
            --color-grid: {theme.chart_grid};
            --color-input: {theme.input_bg};
            --color-overlay: {theme.overlay};
            --color-text-on-accent: {text_on_accent};
            --bg: {theme.bg};
            --panel: {theme.surface};
            --panel-alt: {theme.surface_alt};
            --line: {theme.border};
            --text: {theme.text};
            --muted: {theme.muted};
            --cyan: {theme.accent};
            --blue: {theme.accent_2};
            --amber: {theme.warning};
            --red: {theme.danger};
            --green: {theme.success};
          }}

          .stApp {{
            background: {background};
            color: var(--color-text);
          }}

          html, body, [class*="css"] {{
            font-family: "Segoe UI", "Aptos", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          }}

          section.main > div {{
            padding-top: 1rem;
            padding-bottom: 1.8rem;
            max-width: none;
            width: 100%;
          }}

          .block-container,
          div[data-testid="stMainBlockContainer"],
          section.main .block-container {{
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 1rem !important;
            padding-right: 1rem !important;
          }}

          div[data-testid="stSidebar"] {{
            display: none;
          }}

          button[kind="header"],
          div[data-testid="collapsedControl"] {{
            display: none;
          }}

          .nubra-topbar {{
            position: fixed;
            top: 0.7rem;
            left: 1rem;
            right: 1rem;
            z-index: 10000;
            padding: 0.55rem 0.65rem;
            border-radius: 1.25rem;
            border: 1px solid var(--color-border);
            background:
              linear-gradient(180deg, color-mix(in srgb, {theme.overlay} 96%, var(--color-bg-alt)), rgba(255,255,255,0.02)),
              linear-gradient(120deg, var(--color-accent-soft), transparent 58%);
            box-shadow: var(--color-shadow);
            backdrop-filter: blur(18px);
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
          }}

          .nubra-topbar-brand {{
            display: flex;
            justify-content: flex-start;
            gap: 0.8rem;
            align-items: center;
          }}

          .nubra-brand-lockup {{
            display: flex;
            align-items: center;
            gap: 0.75rem;
          }}

          .nubra-brand-mark {{
            width: 2.1rem;
            height: 2.1rem;
            border-radius: 0.8rem;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            background: linear-gradient(135deg, var(--color-accent), var(--color-accent-2));
            color: var(--color-text-on-accent);
            font-weight: 900;
            box-shadow: 0 10px 22px var(--color-glow);
          }}

          .nubra-topbar-kicker {{
            color: var(--color-muted);
            font-size: 0.66rem;
            text-transform: uppercase;
            letter-spacing: 0.14em;
            font-weight: 800;
            margin-bottom: 0.06rem;
          }}

          .nubra-topbar-title {{
            margin: 0;
            color: var(--color-text);
            font-size: 1.2rem;
            font-weight: 800;
            letter-spacing: -0.03em;
          }}

          .nubra-topbar-meta {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
            justify-content: flex-end;
          }}

          .nubra-nav-banner {{
            display: inline-flex;
            align-items: center;
            gap: 0.3rem;
            border-radius: 999px;
            padding: 0.24rem 0.7rem;
            background: var(--color-accent-soft);
            color: var(--color-accent);
            border: 1px solid var(--color-border);
            font-size: 0.72rem;
            font-weight: 700;
          }}

          .nubra-nav-hint {{
            color: var(--color-muted);
            font-size: 0.72rem;
            font-weight: 700;
          }}

          .nubra-nav-row {{
            display: flex;
            gap: 0.4rem;
            justify-content: flex-end;
            flex-wrap: wrap;
          }}

          .nubra-topbar-spacer {{
            height: 4.4rem;
          }}

          .nubra-nav-link {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            min-height: 2.2rem;
            padding: 0.1rem 0.75rem;
            border-radius: 0.95rem;
            border: 1px solid var(--color-border);
            background: var(--color-surface-alt);
            color: var(--color-text) !important;
            text-decoration: none !important;
            font-weight: 700;
            font-size: 0.78rem;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease, background 0.18s ease;
            text-align: center;
          }}

          .nubra-nav-link:hover {{
            transform: translateY(-1px);
            border-color: var(--color-border-strong);
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.08);
          }}

          .nubra-nav-link.is-active {{
            background: linear-gradient(135deg, var(--color-accent), var(--color-accent-2));
            border-color: transparent;
            box-shadow: 0 10px 22px var(--color-glow);
            color: var(--color-text-on-accent) !important;
          }}

          .trader-strip {{
            margin-top: 0.1rem;
          }}

          .nubra-refresh-bar {{
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: center;
            margin: 0.05rem 0 0.35rem 0;
            padding: 0.3rem 0.1rem 0.35rem 0.1rem;
            border-bottom: 1px solid rgba(255,255,255,0.05);
          }}

          .nubra-refresh-cluster {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
            min-width: 0;
          }}

          .nubra-status-dot {{
            width: 0.5rem;
            height: 0.5rem;
            border-radius: 999px;
            background: linear-gradient(135deg, var(--color-accent), var(--color-accent-2));
            box-shadow: 0 0 14px var(--color-glow);
            flex: 0 0 auto;
          }}

          .nubra-refresh-strong {{
            color: var(--color-text);
            font-size: 0.82rem;
            font-weight: 800;
            letter-spacing: -0.01em;
          }}

          .nubra-refresh-chip {{
            display: inline-flex;
            align-items: center;
            padding: 0.15rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--color-border);
            background: var(--color-surface-alt);
            color: var(--color-accent);
            font-size: 0.66rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }}

          .nubra-refresh-meta,
          .nubra-refresh-side {{
            color: var(--color-muted);
            font-size: 0.74rem;
            font-weight: 600;
          }}

          .nubra-refresh-side {{
            max-width: 14rem;
            text-align: right;
            line-height: 1.3;
          }}

          .nubra-inline-note {{
            color: var(--color-muted);
            font-size: 0.74rem;
            line-height: 1.35;
            padding-top: 0.05rem;
          }}

          .nubra-card,
          .nubra-callout,
          .nubra-control-note,
          .nubra-control-summary,
          .nubra-inline-metric {{
            background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-surface-alt) 100%);
            border: 1px solid var(--color-border);
            border-radius: 1.05rem;
            box-shadow: 0 10px 24px rgba(0, 0, 0, 0.04);
          }}

          .nubra-card {{
            padding: 0.9rem 0.95rem 0.85rem 0.95rem;
          }}

          .nubra-callout {{
            padding: 0.8rem 0.9rem;
          }}

          .nubra-control-note,
          .nubra-control-summary,
          .nubra-inline-metric {{
            min-height: 3.4rem;
            padding: 0.68rem 0.82rem;
          }}

          .nubra-control-summary-top {{
            display: flex;
            gap: 0.35rem;
            flex-wrap: wrap;
            align-items: center;
          }}

          .nubra-control-summary strong,
          .nubra-inline-metric strong {{
            color: var(--color-text);
            font-size: 0.88rem;
            line-height: 1.2;
            font-weight: 800;
          }}

          .nubra-control-summary span,
          .nubra-inline-metric span,
          .nubra-control-note {{
            color: var(--color-muted);
            font-size: 0.74rem;
            line-height: 1.35;
          }}

          .nubra-kicker {{
            color: var(--color-accent);
            font-size: 0.68rem;
            letter-spacing: 0.16em;
            text-transform: uppercase;
            font-weight: 800;
            margin-bottom: 0.2rem;
          }}

          .nubra-desk-hero,
          .nubra-hero,
          .nubra-mission {{
            border-radius: 1.2rem;
            padding: 1rem 1.15rem;
            border: 1px solid var(--color-border);
            background:
              linear-gradient(180deg, var(--color-surface) 0%, var(--color-surface-alt) 100%),
              linear-gradient(135deg, var(--color-accent-soft), transparent 70%);
            box-shadow: var(--color-shadow);
          }}

          .nubra-desk-title,
          .nubra-hero-title,
          .nubra-mission-title {{
            margin: 0;
            color: var(--color-text);
            font-size: 1.9rem;
            line-height: 0.98;
            letter-spacing: -0.05em;
          }}

          .nubra-desk-copy,
          .nubra-hero-copy,
          .nubra-mission-copy,
          .nubra-subtle {{
            color: var(--color-muted);
            font-size: 0.9rem;
            line-height: 1.5;
          }}

          .nubra-mission-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 0.75rem;
            align-items: end;
          }}

          .nubra-chip-row,
          .nubra-mission-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
          }}

          .nubra-chip,
          .nubra-pill,
          .nubra-trend {{
            display: inline-flex;
            align-items: center;
            min-height: 1.55rem;
            padding: 0.12rem 0.55rem;
            border-radius: 999px;
            border: 1px solid var(--color-border);
            background: var(--color-surface-soft);
            color: var(--color-text);
            font-size: 0.68rem;
            font-weight: 800;
            letter-spacing: 0.03em;
          }}

          .nubra-chip.tone-green,
          .nubra-pill,
          .nubra-trend.tone-green,
          .nubra-flag.green {{
            color: var(--color-success);
          }}

          .nubra-chip.tone-blue,
          .nubra-trend.tone-blue,
          .nubra-flag.blue {{
            color: var(--color-accent-2);
          }}

          .nubra-chip.tone-amber,
          .nubra-trend.tone-amber,
          .nubra-flag.amber {{
            color: var(--color-warning);
          }}

          .nubra-chip.tone-red,
          .nubra-trend.tone-red {{
            color: var(--color-danger);
          }}

          .nubra-chip.tone-cyan {{
            color: var(--color-accent);
          }}

          .nubra-chip.tone-purple {{
            color: var(--color-purple);
          }}

          .nubra-grid {{
            display: grid;
            gap: 0.8rem;
          }}

          .nubra-grid.cols-4 {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }}

          .nubra-grid.cols-3 {{
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }}

          .nubra-metric-card,
          .nubra-stat-card {{
            display: flex;
            flex-direction: column;
            gap: 0.35rem;
            min-height: 7rem;
            transition: transform 0.18s ease, border-color 0.18s ease, box-shadow 0.18s ease;
          }}

          .nubra-metric-card:hover,
          .nubra-stat-card:hover,
          .nubra-nav-link:hover {{
            border-color: var(--color-border-strong);
          }}

          .nubra-metric-head,
          .nubra-stat-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.5rem;
          }}

          .nubra-metric-label,
          .nubra-stat-label {{
            color: var(--color-muted);
            font-size: 0.68rem;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            font-weight: 800;
          }}

          .nubra-metric-body,
          .nubra-stat-main {{
            display: flex;
            justify-content: space-between;
            gap: 0.6rem;
            align-items: flex-end;
          }}

          .nubra-metric-value,
          .nubra-stat-value {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 1.65rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.04em;
          }}

          .nubra-metric-spark,
          .nubra-stat-spark {{
            width: 96px;
            min-width: 96px;
            opacity: 0.9;
          }}

          .nubra-sparkline {{
            width: 100%;
            height: 24px;
          }}

          .nubra-feed {{
            display: grid;
            gap: 0.6rem;
          }}

          .nubra-feed-item {{
            border-radius: 1rem;
            border: 1px solid var(--color-border);
            background: linear-gradient(180deg, var(--color-surface) 0%, var(--color-surface-alt) 100%);
            padding: 0.72rem 0.82rem;
          }}

          .nubra-feed-title-row {{
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            align-items: baseline;
            margin-bottom: 0.2rem;
          }}

          .nubra-feed-title-row strong,
          .nubra-callout-title {{
            color: var(--color-text);
            font-size: 0.87rem;
            font-weight: 800;
          }}

          .nubra-feed-time,
          .nubra-feed-body {{
            color: var(--color-muted);
          }}

          .nubra-feed-body {{
            font-size: 0.8rem;
            line-height: 1.45;
          }}

          .nubra-feed-icon {{
            color: var(--color-accent);
          }}

          div[data-testid="stSelectbox"] > div,
          div[data-testid="stTextInput"] > div,
          div[data-testid="stMultiSelect"] > div {{
            border-radius: 1rem;
          }}

          div[data-testid="stSelectbox"] [data-baseweb="select"] > div,
          div[data-testid="stTextInput"] input,
          div[data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
            background: var(--color-input) !important;
            border: 1px solid var(--color-border) !important;
            color: var(--color-text) !important;
            border-radius: 1rem !important;
            min-height: 3rem !important;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.05);
          }}

          div[data-testid="stTextInput"] input::placeholder {{
            color: color-mix(in srgb, var(--color-muted) 78%, transparent);
          }}

          div[data-testid="stSelectbox"] label,
          div[data-testid="stTextInput"] label,
          div[data-testid="stMultiSelect"] label,
          div[data-testid="stRadio"] label {{
            color: var(--color-muted) !important;
          }}

          div[data-testid="stRadio"] > div {{
            gap: 0.4rem;
          }}

          div[data-testid="stRadio"] label[data-baseweb="radio"] {{
            border: 1px solid var(--color-border);
            background: var(--color-surface-alt);
            border-radius: 999px;
            padding: 0.24rem 0.7rem;
          }}

          div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{
            background: var(--color-accent-soft);
            border-color: rgba(139, 108, 255, 0.36);
            box-shadow: 0 10px 20px var(--color-glow);
          }}

          div[data-testid="stRadio"] label[data-baseweb="radio"] span {{
            color: var(--color-text) !important;
            font-size: 0.8rem;
            font-weight: 700;
          }}

          div[data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) span {{
            color: var(--color-accent) !important;
          }}

          div.stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, var(--color-accent), var(--color-accent-2));
            color: {primary_button_text};
            border: 1px solid transparent;
            font-weight: 800;
            box-shadow: 0 12px 26px var(--color-glow);
          }}

          div.stButton > button {{
            border-radius: 0.95rem;
            border: 1px solid var(--color-border);
            background: var(--color-surface-alt);
            color: var(--color-text);
            min-height: 2.7rem;
          }}

          div.stButton > button:hover {{
            border-color: var(--color-border-strong);
            color: var(--color-text);
          }}

          div[data-testid="stDataFrame"] {{
            border: 1px solid var(--color-border);
            border-radius: 1rem;
            overflow: hidden;
            box-shadow: 0 10px 22px rgba(0, 0, 0, 0.04);
          }}

          @media (max-width: 1100px) {{
            .nubra-grid.cols-4,
            .nubra-grid.cols-3 {{
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .nubra-topbar {{
              left: 0.7rem;
              right: 0.7rem;
            }}

            .nubra-topbar-spacer {{
              height: 7.25rem;
            }}

            .nubra-refresh-bar {{
              flex-direction: column;
              align-items: flex-start;
            }}

            .nubra-refresh-side {{
              max-width: none;
              text-align: left;
            }}

            .nubra-mission-grid {{
              grid-template-columns: 1fr;
            }}

            .nubra-desk-title,
            .nubra-hero-title,
            .nubra-mission-title {{
              font-size: 1.55rem;
            }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )
