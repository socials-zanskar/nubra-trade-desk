"""Nubra SDK session helpers with graceful fallback."""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from ..config import AuthConfig
from ..models import AuthSession


def _import_sdk() -> tuple[Any, Any]:
    try:
        from nubra_python_sdk.start_sdk import InitNubraSdk, NubraEnv
    except Exception as exc:  # pragma: no cover - import fallback
        raise RuntimeError(
            "nubra-sdk is not installed or could not be imported. "
            "Install nubra-sdk to enable live dashboard sessions."
        ) from exc
    return InitNubraSdk, NubraEnv


def create_session(auth: AuthConfig) -> AuthSession:
    """Create a Nubra session or return a safe unavailable state."""
    try:
        init_sdk, nubra_env = _import_sdk()
        env_name = auth.resolved_environment()
        env_value = getattr(nubra_env, env_name, None)
        if env_value is None:
            raise ValueError(f"Unsupported Nubra environment: {env_name}")

        if auth.use_env_creds:
            client = init_sdk(env_value, env_creds=True)
        else:
            sdk_kwargs = {key: value for key, value in auth.extra.items() if value}
            if auth.username:
                sdk_kwargs.setdefault("username", auth.username)
            if auth.password:
                sdk_kwargs.setdefault("password", auth.password)
            if auth.api_key:
                sdk_kwargs.setdefault("api_key", auth.api_key)
            if auth.api_secret:
                sdk_kwargs.setdefault("api_secret", auth.api_secret)
            if auth.access_token:
                sdk_kwargs.setdefault("access_token", auth.access_token)
            client = init_sdk(env_value, env_creds=False, **sdk_kwargs)

        market_data, market_data_error = _resolve_market_data_client(client)
        return AuthSession(
            mode=auth.mode,
            environment=env_name,
            client=client,
            market_data=market_data,
            is_available=market_data is not None,
            error=market_data_error,
        )
    except Exception as exc:
        return AuthSession(
            mode=auth.mode,
            environment=auth.resolved_environment(),
            is_available=False,
            error=str(exc),
        )


def load_auth_session(auth: AuthConfig) -> AuthSession:
    """Alias used by the future UI and tests."""
    return create_session(auth)


def _resolve_market_data_client(client: Any) -> tuple[Any, str | None]:
    try:
        from nubra_python_sdk.marketdata.market_data import MarketData
    except Exception as exc:
        return None, f"Failed to import MarketData: {exc}"

    try:
        return MarketData(client), None
    except Exception as exc:
        return None, f"Failed to initialize MarketData: {exc}"


def with_environment(auth: AuthConfig, environment: str) -> AuthConfig:
    """Helper for future UI flow when users switch environments."""
    return replace(auth, environment=environment)
