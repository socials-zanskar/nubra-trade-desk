# Nubra Streamlit Dashboard Research

## Recommendation in one line

Build a `Signal Discovery Dashboard` rather than a generic data dashboard. The most useful product is a hosted Streamlit app that helps users find abnormal volume, confirm breakouts, and understand nearby OI support or resistance.

## What the Nubra packages give us

### `nubra-sdk`

Current PyPI version: `0.4.0` released March 4, 2026.

The SDK exposes:

- historical data
- quotes
- option chain
- websocket feeds
- instruments reference data
- portfolio data
- trading endpoints

This means the dashboard can start with the two scanner packages and still expand into richer drilldowns without needing a different data source.

### `nubra-oi-walls`

Current PyPI version: `0.1.1` released April 2, 2026.

Confirmed public functions:

- `run_wall_proximity_scan(...)`
- `run_multi_wall_proximity_scan(...)`

The single-wall DataFrame returns:

- `Stock`
- `LTP`
- `Wall Type`
- `Wall Strike`
- `Strength`
- `Proximity`
- `Bias`

The multi-wall DataFrame returns:

- `symbol`
- `ltp`
- `wall_side`
- `rank`
- `strike`
- `oi`
- `dist_pct`
- `selected`

Useful source-level notes:

- can reuse an existing `MarketData` client
- defaults to `UAT` if it creates its own client
- supports `PROD` through `NUBRA_OI_WALLS_ENV`
- resolves the nearest strong wall when `top_n > 1`

### `nubra-volume-breakout`

Current PyPI version: `0.1.1` released April 6, 2026.

Public output columns:

- `symbol`
- `candle_time`
- `current_volume`
- `average_volume`
- `volume_ratio`

Useful source-level notes:

- intraday volume is derived from cumulative volume
- supports `same_slot` and `rolling` baseline modes
- internally computes richer metrics like breakout percent, z-score, and signal flags even though the public output is lean

## What is actually meaningful for users

A useful volume tracker should not just show the highest absolute volume. It should answer:

- which symbols are trading unusually high volume versus their own baseline
- whether the spike is happening in the current time slot versus prior sessions
- whether price is also breaking a recent high
- whether the move is running into a call wall or sitting above a put wall
- which watchlist names deserve attention right now

That leads to a much better product:

- `Volume Spike Tracker`: identifies abnormal participation
- `Breakout Confirmation`: checks if price is also confirming the move
- `OI Context`: tells whether options positioning supports or resists the move

## Recommended product concept

### Product name

`Nubra Signal Discovery Dashboard`

### What it should feel like

- premium, dark, high-signal UI
- large metric cards
- dense but readable tables
- clear color semantics:
  - cyan and green for bullish / momentum
  - amber for caution / clustering
  - red for resistance / bearish pressure
- one plain-English insight card on every major screen

This should feel like a polished product showcase, not just a notebook wrapped in Streamlit.

## Recommended pages

### 1. Home

Purpose:

- explain the app quickly
- choose demo mode vs user credentials
- show headline metrics

### 2. Market Pulse

Purpose:

- summarize the strongest live signals
- show top breakout names and nearest walls

### 3. Volume Spike Tracker

Purpose:

- rank symbols by `volume_ratio`
- filter for the most abnormal activity

### 4. Breakout Confirmation

Purpose:

- combine volume spike with recent price breakout logic
- separate strong continuation candidates from noise

### 5. OI Walls Summary

Purpose:

- expose the package output clearly
- rank support / resistance proximity

### 6. Multi-Wall Explorer

Purpose:

- explain wall clustering
- make `top_n > 1` useful to the user

### 7. Symbol Drilldown

Purpose:

- combine price, volume, and wall context on one page
- most impressive page for demos

### 8. Watchlist and Alerts

Purpose:

- let users track chosen symbols
- define simple high-value alert rules

### 9. Comparison Lab

Purpose:

- compare multiple names across breakout strength and wall distance

### 10. Hosting and Access

Purpose:

- explain deployment mode
- show how demo, BYO credentials, and app login would work

## Can this be hosted on Streamlit with little or no backend

Yes.

For v1, Streamlit is enough if we keep the app read-only and mostly stateless apart from session data.

Use:

- `st.session_state` for current selections and temporary watchlists
- `st.cache_data` and `st.cache_resource` for performance
- Streamlit secrets for demo credentials
- multipage navigation for product structure

You do not need a separate FastAPI backend for the first version.

## Best hosting choice

### Best first choice

`Streamlit Community Cloud`

Why:

- fastest deployment path
- built for Streamlit apps
- supports secrets
- easy to share with users

What to validate:

- Nubra packages install cleanly on Linux
- hosted auth flow works as expected
- caching is enough for expected concurrency

### Good fallback choices

- Render
- Railway
- small cloud VM

Use those if you later need tighter networking, more process control, or predictable always-on performance.

## Credential strategy

### Option A: shared demo mode

- owner credentials in Streamlit secrets
- all users get read-only access
- best for demos and phase 1

### Option B: bring your own Nubra credentials

- user enters credentials for that session
- no persistence to disk
- better for real user ownership

### Option C: app login with OIDC

- use Streamlit authentication to gate the app
- separate concern from Nubra account access
- useful for internal or partner-only portals

## Strong recommendation

Ship phase 1 like this:

- Streamlit-hosted
- shared demo mode first
- read-only
- curated watchlists
- volume spike tracker
- breakout confirmation
- OI walls summary
- symbol drilldown

That gives you the highest chance of delivering something:

- useful
- easy to explain
- visually strong
- easy to host

## Sources

- [nubra-sdk on PyPI](https://pypi.org/project/nubra-sdk/)
- [nubra-oi-walls on PyPI](https://pypi.org/project/nubra-oi-walls/)
- [nubra-volume-breakout on PyPI](https://pypi.org/project/nubra-volume-breakout/)
- [Streamlit app dependencies docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/app-dependencies)
- [Streamlit secrets docs](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)
- [Streamlit authentication docs](https://docs.streamlit.io/develop/concepts/connections/authentication)
- [Streamlit multipage overview](https://docs.streamlit.io/develop/concepts/multipage-apps/overview)
