from __future__ import annotations

import logging
import os
import sys
import builtins
from dataclasses import replace
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
LOG_DIR = ROOT / "logs"
LOG_FILE = LOG_DIR / "local_probe.log"


def ensure_src_path() -> None:
    if str(SRC) not in sys.path:
        sys.path.insert(0, str(SRC))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip("'").strip('"'))


def configure_logging() -> logging.Logger:
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger("nubra_probe")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)
    return logger


def install_prompt_overrides(logger: logging.Logger) -> None:
    """Supply OTP or MPIN from env when the SDK prompts interactively."""
    original_input = builtins.input

    def patched_input(prompt: str = "") -> str:
        prompt_text = str(prompt)
        if "OTP" in prompt_text.upper():
            otp = os.getenv("NUBRA_TEST_OTP", "").strip()
            if otp:
                logger.info("Using OTP from environment for local probe.")
                return otp
        if "MPIN" in prompt_text.upper():
            mpin = os.getenv("MPIN", "").strip()
            if mpin:
                logger.info("Using MPIN from environment for local probe.")
                return mpin
        return original_input(prompt)

    builtins.input = patched_input


def main() -> int:
    load_env_file(ROOT / ".env.local")
    load_env_file(ROOT / ".env")
    ensure_src_path()
    logger = configure_logging()
    install_prompt_overrides(logger)

    from nubra_dash.config import load_app_config
    from nubra_dash.services.auth import load_auth_session
    from nubra_dash.services.oi_walls import run_multi_wall_scan, run_oi_walls_scan
    from nubra_dash.services.volume_breakout import run_volume_breakout_scan

    config = load_app_config()
    config = replace(
        config,
        demo_mode=False,
        auth=replace(config.auth, mode="user", environment="PROD", use_env_creds=True),
    )
    logger.info("Loaded config | env=%s | demo_mode=%s | exchange=%s", config.auth.environment, config.demo_mode, config.scans.exchange)
    logger.info("Symbols | %s", ", ".join(config.scans.demo_symbols))

    if not os.getenv("PHONE_NO") or not os.getenv("MPIN"):
        logger.error("Missing PHONE_NO or MPIN in .env.local. Fill them before running the local probe.")
        return 1

    auth = load_auth_session(config.auth)
    if not auth.is_available or auth.market_data is None:
        logger.error("Auth failed | %s", auth.error)
        logger.info("Check your `.env.local` values and Nubra SDK environment expectations.")
        return 1

    logger.info("Auth succeeded | environment=%s", auth.environment)

    volume_batch = run_volume_breakout_scan(
        auth.market_data,
        config.scans.demo_symbols,
        lookback_days=config.scans.lookback_days,
        interval=config.scans.volume_interval,
        rank=min(config.scans.breakout_rank, len(config.scans.demo_symbols)),
        exchange=config.scans.exchange,
    )
    logger.info("Volume batch | ok=%s | rows=%s | errors=%s", volume_batch.ok, len(volume_batch.rows), len(volume_batch.errors))
    for error in volume_batch.errors:
        logger.error("Volume error | %s", error)
    for row in volume_batch.rows[:5]:
        logger.info("Volume row | %s", getattr(row, "to_dict", lambda: row)())

    wall_batch = run_oi_walls_scan(
        auth.market_data,
        config.scans.demo_symbols,
        exchange=config.scans.exchange,
    )
    logger.info("Wall batch | ok=%s | rows=%s | errors=%s", wall_batch.ok, len(wall_batch.rows), len(wall_batch.errors))
    for error in wall_batch.errors:
        logger.error("Wall error | %s", error)
    for row in wall_batch.rows[:5]:
        logger.info("Wall row | %s", getattr(row, "to_dict", lambda: row)())

    multi_wall_batch = run_multi_wall_scan(
        auth.market_data,
        config.scans.demo_symbols,
        top_n=config.scans.multi_wall_top_n,
        exchange=config.scans.exchange,
    )
    logger.info("Multi-wall batch | ok=%s | rows=%s | errors=%s", multi_wall_batch.ok, len(multi_wall_batch.rows), len(multi_wall_batch.errors))
    for error in multi_wall_batch.errors:
        logger.error("Multi-wall error | %s", error)
    for row in multi_wall_batch.rows[:5]:
        logger.info("Multi-wall row | %s", getattr(row, "to_dict", lambda: row)())

    logger.info("Probe complete | log_file=%s", LOG_FILE)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
