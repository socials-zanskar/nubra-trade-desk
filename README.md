# Nubra Signal Discovery

Streamlit dashboard for:
- batch-scanned stock volume signals
- current-expiry NIFTY and SENSEX OI ladders
- watchlist and drilldown workflows

## Local setup

1. Copy [.env.example](C:\Users\Aryan\Desktop\projects\Strategies\StreamLitDashboards\.env.example) to `.env`
2. Fill in your Nubra credentials
3. Start the app:

```powershell
uv run --with-requirements requirements.txt py -m streamlit run app.py
```

## Current secret layout

Use `.env` locally for:
- Nubra auth
- future Supabase credentials
- future batch-sync settings

Use [.streamlit/secrets.toml.example](C:\Users\Aryan\Desktop\projects\Strategies\StreamLitDashboards\.streamlit\secrets.toml.example) when deploying to Streamlit Community Cloud.

## Product shape

- `Home`: mission-control view
- `Market Pulse`: stock signal shortlist
- `Volume Tracker`: broad stock volume scan
- `Breakout Confirmation`: narrower stock shortlist
- `OI Walls`: current-expiry NIFTY/SENSEX ladders
- `Multi-Wall Explorer`: focused index strike structure
- `Symbol Drilldown`: one-stock narrative view

## Next backend step

We are preparing to move broad stock scanning into:
- `Supabase Postgres` for stored snapshots
- `GitHub Actions` for scheduled refresh jobs
- `Streamlit` for fast DB-backed reads plus manual reloads
