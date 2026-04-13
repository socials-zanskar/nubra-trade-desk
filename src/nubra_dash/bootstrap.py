from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
except Exception:  # pragma: no cover - optional in hosted environments
    load_dotenv = None


def ensure_src_path() -> None:
    """Make the local src directory importable from multipage Streamlit files."""
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def load_local_env() -> None:
    """Load local `.env` files and Streamlit secrets when present."""
    root = Path(__file__).resolve().parents[2]
    if load_dotenv is not None:
        load_dotenv(root / ".env", override=False)
        load_dotenv(root / ".env.local", override=False)
    _load_streamlit_secrets()


def _load_streamlit_secrets() -> None:
    try:
        import streamlit as st
    except Exception:
        return

    try:
        secrets = st.secrets
    except Exception:
        return

    for key, value in secrets.items():
        if isinstance(value, (str, int, float, bool)):
            os.environ.setdefault(key, str(value))
