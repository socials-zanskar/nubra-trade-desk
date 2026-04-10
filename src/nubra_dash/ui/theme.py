from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Palette:
    bg: str = "#08131f"
    panel: str = "#10263a"
    panel_alt: str = "#143149"
    line: str = "#234a68"
    text: str = "#e8f1f8"
    muted: str = "#88a3bb"
    cyan: str = "#2ed3b7"
    blue: str = "#57b6ff"
    amber: str = "#f8b84e"
    red: str = "#ff6b6b"
    green: str = "#24c48e"


PALETTE = Palette()


def inject_css() -> None:
    import streamlit as st

    st.markdown(
        f"""
        <style>
          :root {{
            --bg: {PALETTE.bg};
            --panel: {PALETTE.panel};
            --panel-alt: {PALETTE.panel_alt};
            --line: {PALETTE.line};
            --text: {PALETTE.text};
            --muted: {PALETTE.muted};
            --cyan: {PALETTE.cyan};
            --blue: {PALETTE.blue};
            --amber: {PALETTE.amber};
            --red: {PALETTE.red};
            --green: {PALETTE.green};
          }}

          .stApp {{
            background:
              radial-gradient(circle at top right, rgba(46, 211, 183, 0.12), transparent 32%),
              radial-gradient(circle at bottom left, rgba(87, 182, 255, 0.10), transparent 28%),
              linear-gradient(180deg, #08131f 0%, #0b1825 100%);
            color: var(--text);
          }}

          html, body, [class*="css"] {{
            font-family: Inter, "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
          }}

          section.main > div {{
            padding-top: 1.2rem;
            padding-bottom: 2rem;
            max-width: none;
            width: 100%;
          }}

          .block-container,
          div[data-testid="stMainBlockContainer"],
          section.main .block-container {{
            max-width: 100% !important;
            width: 100% !important;
            padding-left: 1.1rem !important;
            padding-right: 1.1rem !important;
          }}

          div[data-testid="stSidebar"] {{
            display: none;
          }}

          button[kind="header"],
          div[data-testid="collapsedControl"] {{
            display: none;
          }}

          .nubra-hero {{
            background: linear-gradient(135deg, rgba(16, 38, 58, 0.98), rgba(13, 108, 115, 0.60));
            border: 1px solid rgba(35, 74, 104, 0.95);
            border-radius: 18px;
            padding: 22px 24px;
            box-shadow: 0 24px 50px rgba(2, 10, 18, 0.28);
          }}

          .nubra-hero-title {{
            margin: 0 0 0.45rem 0;
            font-size: 2.05rem;
            line-height: 1.05;
          }}

          .nubra-hero-copy {{
            max-width: 56rem;
            margin: 0 0 0.85rem 0;
          }}

          .nubra-subtle {{
            color: var(--muted);
            font-size: 0.96rem;
            line-height: 1.55;
          }}

          .nubra-kicker {{
            color: var(--cyan);
            font-size: 0.72rem;
            letter-spacing: 0.14em;
            text-transform: uppercase;
            font-weight: 800;
            margin-bottom: 0.35rem;
          }}

          .nubra-card {{
            background: rgba(16, 38, 58, 0.96);
            border: 1px solid rgba(35, 74, 104, 0.95);
            border-radius: 16px;
            padding: 14px 14px 12px 14px;
          }}

          .nubra-card h4 {{
            margin: 0 0 0.45rem 0;
            color: var(--text);
          }}

          .nubra-pill {{
            display: inline-flex;
            align-items: center;
            min-height: 1.4rem;
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            background: rgba(46, 211, 183, 0.12);
            color: var(--cyan);
            border: 1px solid rgba(46, 211, 183, 0.24);
            font-size: 0.68rem;
            font-weight: 700;
            margin-right: 0.3rem;
            margin-bottom: 0.3rem;
          }}

          .nubra-chip-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.3rem;
          }}

          .nubra-chip {{
            display: inline-flex;
            align-items: center;
            min-height: 1.4rem;
            padding: 0.1rem 0.55rem;
            border-radius: 999px;
            border: 1px solid rgba(255,255,255,0.08);
            background: rgba(255,255,255,0.03);
            color: var(--text);
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.02em;
          }}

          .nubra-chip.tone-green {{ color: var(--green); }}
          .nubra-chip.tone-blue {{ color: var(--blue); }}
          .nubra-chip.tone-amber {{ color: var(--amber); }}
          .nubra-chip.tone-red {{ color: var(--red); }}
          .nubra-chip.tone-cyan {{ color: var(--cyan); }}
          .nubra-chip.tone-purple {{ color: #b48cff; }}

          .nubra-callout {{
            padding: 0.72rem 0.8rem;
            border-radius: 14px;
            background: rgba(20, 49, 73, 0.85);
            border: 1px solid rgba(35, 74, 104, 0.95);
          }}

          .nubra-callout-title {{
            color: var(--text);
            font-weight: 700;
            margin-bottom: 0.2rem;
            font-size: 0.88rem;
          }}

          .nubra-mission {{
            border-radius: 10px;
            padding: 0.75rem 0.9rem;
            background:
              linear-gradient(135deg, rgba(16, 38, 58, 0.98), rgba(11, 24, 37, 0.92)),
              radial-gradient(circle at top right, rgba(46, 211, 183, 0.12), transparent 24%);
            border: 1px solid rgba(35, 74, 104, 0.95);
            box-shadow: 0 12px 30px rgba(2, 10, 18, 0.2);
          }}

          .nubra-mission-grid {{
            display: grid;
            grid-template-columns: minmax(0, 1fr) auto;
            gap: 1rem;
            align-items: end;
          }}

          .nubra-mission-title {{
            margin: 0;
            font-size: 1.06rem;
            line-height: 1.05;
            letter-spacing: -0.03em;
          }}

          .nubra-mission-copy {{
            margin: 0.25rem 0 0 0;
            max-width: 64rem;
            font-size: 0.74rem;
          }}

          .nubra-mission-tags {{
            display: flex;
            gap: 0.3rem;
            flex-wrap: wrap;
            justify-content: flex-end;
          }}

          .nubra-grid {{
            display: grid;
            gap: 0.9rem;
          }}

          .nubra-grid.cols-4 {{
            grid-template-columns: repeat(4, minmax(0, 1fr));
          }}

          .nubra-grid.cols-3 {{
            grid-template-columns: repeat(3, minmax(0, 1fr));
          }}

          .nubra-feed {{
            display: grid;
            gap: 0.65rem;
          }}

          .nubra-feed-item {{
            border-radius: 14px;
            border: 1px solid rgba(35, 74, 104, 0.95);
            background: rgba(16, 38, 58, 0.82);
            padding: 0.7rem 0.8rem;
          }}

          .nubra-feed-item strong {{
            display: block;
            color: var(--text);
            margin-bottom: 0.12rem;
          }}

          .nubra-feed-item span {{
            color: var(--muted);
            font-size: 0.85rem;
            line-height: 1.45;
          }}

          .nubra-flag {{
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            border: 1px solid rgba(35, 74, 104, 0.95);
            padding: 0.16rem 0.6rem;
            color: var(--text);
            background: rgba(20, 49, 73, 0.8);
            font-size: 0.72rem;
            font-weight: 700;
            letter-spacing: 0.02em;
          }}

          .nubra-flag.green {{ color: var(--green); }}
          .nubra-flag.blue {{ color: var(--blue); }}
          .nubra-flag.amber {{ color: var(--amber); }}

          .nubra-topbar {{
            position: fixed;
            top: 0.45rem;
            left: 1.25rem;
            right: 1.25rem;
            z-index: 999;
            backdrop-filter: blur(16px);
            background:
              linear-gradient(180deg, rgba(8, 34, 53, 0.97), rgba(11, 57, 72, 0.93)),
              radial-gradient(circle at top right, rgba(46, 211, 183, 0.18), transparent 24%);
            border: 1px solid rgba(46, 211, 183, 0.42);
            border-radius: 12px;
            padding: 0.3rem 0.52rem 0.34rem 0.52rem;
            box-shadow:
              0 14px 28px rgba(2, 10, 18, 0.28),
              0 0 0 1px rgba(87, 182, 255, 0.12);
          }}

          .nubra-topbar-brand {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
            margin-bottom: 0.2rem;
          }}

          .nubra-topbar-kicker {{
            color: var(--cyan);
            font-size: 0.58rem;
            text-transform: uppercase;
            letter-spacing: 0.16em;
            font-weight: 800;
            margin-bottom: 0.08rem;
          }}

          .nubra-topbar-title {{
            margin: 0;
            color: var(--text);
            font-size: 0.8rem;
            font-weight: 800;
            letter-spacing: -0.02em;
          }}

          .nubra-nav-hint {{
            color: var(--cyan);
            font-size: 0.62rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.08em;
          }}

          .nubra-nav-banner {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            border-radius: 999px;
            padding: 0.08rem 0.42rem;
            background: rgba(46, 211, 183, 0.12);
            border: 1px solid rgba(46, 211, 183, 0.28);
            color: var(--cyan);
            font-size: 0.58rem;
            font-weight: 700;
          }}

          .nubra-nav-row {{
            display: grid;
            grid-template-columns: repeat(8, minmax(0, 1fr));
            gap: 0.28rem;
          }}

          .nubra-topbar-spacer {{
            height: 2.85rem;
          }}

          .nubra-nav-link {{
            display: inline-flex;
            justify-content: center;
            align-items: center;
            min-height: 1.62rem;
            padding: 0.04rem 0.32rem;
            border-radius: 8px;
            border: 1px solid rgba(87, 182, 255, 0.18);
            background: linear-gradient(180deg, rgba(15, 42, 62, 0.96), rgba(10, 28, 45, 0.94));
            color: var(--text) !important;
            text-decoration: none !important;
            font-weight: 700;
            font-size: 0.7rem;
            box-shadow: inset 0 1px 0 rgba(255,255,255,0.03);
            transition: all 0.18s ease;
            text-align: center;
          }}

          .nubra-nav-link:hover {{
            border-color: rgba(46, 211, 183, 0.55);
            background: linear-gradient(180deg, rgba(17, 66, 83, 0.98), rgba(12, 39, 56, 0.96));
            color: var(--cyan) !important;
            transform: translateY(-1px);
            box-shadow: 0 10px 22px rgba(2, 10, 18, 0.28);
          }}

          .nubra-toolbar {{
            border-top: 1px solid rgba(255,255,255,0.05);
            border-bottom: 1px solid rgba(255,255,255,0.05);
            background: rgba(255,255,255,0.01);
            padding: 0.34rem 0;
            margin-bottom: 0.6rem;
          }}

          .trader-strip {{
            margin-top: 0.15rem;
          }}

          .nubra-toolbar strong {{
            color: var(--text);
            font-size: 0.75rem;
          }}

          .nubra-toolbar span {{
            color: var(--muted);
          }}

          .nubra-toolbar-row {{
            display: flex;
            align-items: center;
            gap: 0.45rem;
            flex-wrap: wrap;
          }}

          .nubra-toolbar-label {{
            color: var(--muted);
            font-size: 0.67rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 700;
          }}

          .nubra-toolbar-sep {{
            width: 1px;
            height: 0.8rem;
            background: rgba(255,255,255,0.08);
          }}

          .nubra-inline-note {{
            color: var(--muted);
            font-size: 0.75rem;
            line-height: 1.35;
            padding-top: 0.25rem;
          }}

          .nubra-inline-metric {{
            display: flex;
            flex-direction: column;
            justify-content: center;
            min-height: 2.5rem;
            border-bottom: 1px solid rgba(255,255,255,0.06);
            padding: 0.08rem 0;
          }}

          .nubra-inline-metric strong {{
            color: var(--text);
            font-size: 0.82rem;
            font-weight: 800;
            line-height: 1.2;
          }}

          .nubra-inline-metric span {{
            color: var(--muted);
            font-size: 0.69rem;
            line-height: 1.25;
          }}

          .nubra-metric-card,
          .nubra-stat-card {{
            display: flex;
            flex-direction: column;
            gap: 0.4rem;
            transition: transform 0.18s ease, box-shadow 0.18s ease, border-color 0.18s ease;
          }}

          .nubra-metric-card:hover,
          .nubra-stat-card:hover {{
            transform: scale(1.01);
            box-shadow: 0 14px 28px rgba(2, 10, 18, 0.26);
            border-color: rgba(46, 211, 183, 0.28);
          }}

          .nubra-metric-head,
          .nubra-stat-top {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.65rem;
          }}

          .nubra-metric-label,
          .nubra-stat-label {{
            color: var(--muted);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 0.08em;
            font-weight: 800;
          }}

          .nubra-metric-meta,
          .nubra-stat-meta {{
            display: flex;
            gap: 0.25rem;
            flex-wrap: wrap;
            justify-content: flex-end;
          }}

          .nubra-metric-body,
          .nubra-stat-main {{
            display: flex;
            justify-content: space-between;
            gap: 0.65rem;
            align-items: flex-end;
          }}

          .nubra-metric-value,
          .nubra-stat-value {{
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 1.65rem;
            line-height: 1;
            font-weight: 800;
            letter-spacing: -0.03em;
            text-align: right;
          }}

          .nubra-metric-spark,
          .nubra-stat-spark {{
            width: 110px;
            min-width: 110px;
            opacity: 0.95;
          }}

          .nubra-sparkline {{
            width: 100%;
            height: 26px;
            filter: drop-shadow(0 0 6px rgba(46, 211, 183, 0.12));
          }}

          .nubra-trend {{
            display: inline-flex;
            align-items: center;
            min-height: 1.28rem;
            padding: 0.05rem 0.38rem;
            border-radius: 999px;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
            font-size: 0.68rem;
            font-weight: 800;
            border: 1px solid rgba(255,255,255,0.06);
          }}

          .nubra-trend.tone-green {{ color: var(--green); }}
          .nubra-trend.tone-blue {{ color: var(--blue); }}
          .nubra-trend.tone-amber {{ color: var(--amber); }}
          .nubra-trend.tone-red {{ color: var(--red); }}

          .nubra-feed-title-row {{
            display: flex;
            justify-content: space-between;
            gap: 0.5rem;
            align-items: baseline;
            margin-bottom: 0.2rem;
          }}

          .nubra-feed-title-row strong {{
            display: inline-flex;
            align-items: center;
            gap: 0.45rem;
            color: var(--text);
            font-size: 0.85rem;
          }}

          .nubra-feed-icon {{
            color: var(--cyan);
            font-size: 0.8rem;
          }}

          .nubra-feed-time {{
            color: var(--muted);
            font-size: 0.66rem;
            font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
          }}

          .nubra-feed-body {{
            color: var(--muted);
            font-size: 0.8rem;
            line-height: 1.4;
          }}

          .nubra-desk-hero {{
            border-radius: 18px;
            padding: 1.2rem 1.25rem;
            background:
              radial-gradient(circle at top right, rgba(46, 211, 183, 0.12), transparent 22%),
              linear-gradient(135deg, rgba(16, 38, 58, 0.98), rgba(10, 31, 46, 0.96));
            border: 1px solid rgba(35, 74, 104, 0.95);
            box-shadow: 0 18px 34px rgba(2, 10, 18, 0.24);
          }}

          .nubra-desk-title {{
            margin: 0;
            font-size: 2.35rem;
            line-height: 0.96;
            letter-spacing: -0.05em;
            color: var(--text);
          }}

          .nubra-desk-copy {{
            margin: 0.45rem 0 0 0;
            max-width: 54rem;
            color: var(--muted);
            font-size: 0.95rem;
            line-height: 1.5;
          }}

          @media (max-width: 1100px) {{
            .nubra-grid.cols-4,
            .nubra-grid.cols-3 {{
              grid-template-columns: 1fr;
            }}

            .nubra-mission-title {{
              font-size: 1.2rem;
            }}

            .nubra-topbar {{
              left: 0.75rem;
              right: 0.75rem;
            }}

            .nubra-nav-row {{
              grid-template-columns: repeat(2, minmax(0, 1fr));
            }}

            .nubra-topbar-spacer {{
              height: 5rem;
            }}
          }}
        </style>
        """,
        unsafe_allow_html=True,
    )
