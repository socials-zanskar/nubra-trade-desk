from __future__ import annotations

import sys
from pathlib import Path
import os

from dotenv import load_dotenv


def ensure_src_path() -> None:
    """Make the local src directory importable from multipage Streamlit files."""
    root = Path(__file__).resolve().parents[2]
    src = root / "src"
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))


def load_local_env() -> None:
    """Load local `.env` files when present for scripts and local Streamlit runs."""
    root = Path(__file__).resolve().parents[2]
    load_dotenv(root / ".env", override=False)
    load_dotenv(root / ".env.local", override=False)
