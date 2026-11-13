"""Shared positive-timeout env-var parsing and runtime resolution for ACP/Qwen executors."""

from __future__ import annotations

import math
import os

DEFAULT_PROMPT_TIMEOUT_SECONDS = 300.0
DEFAULT_INIT_TIMEOUT_SECONDS = 180.0


def parse_positive_timeout_seconds(
    env_var: str,
    *,
    default: float,
) -> float:
    """Parse a positive finite seconds value from *env_var*, failing loudly on invalid input.

    :param env_var: Environment variable name to read from ``os.environ``.
    :param default: Fallback seconds value when *env_var* is unset.
    :returns: Parsed positive finite timeout in seconds.
    :raises ValueError: When *env_var* is set to a non-numeric, non-positive, or non-finite value.
    """
    if env_var not in os.environ:
        return default
    err = f"{env_var} must be a positive finite number of seconds"
    try:
        value = float(os.environ[env_var])
    except ValueError as exc:
        raise ValueError(err) from exc
    if not math.isfinite(value) or value <= 0:
        raise ValueError(err)
    return value


def resolve_timeout_seconds(
    *env_vars: str,
    current_global: float,
    import_time_global: float,
    default: float,
) -> float:
    """Resolve an effective timeout in seconds, honoring runtime env changes and test patches.

    When a test monkeypatches a module's ``_PROMPT_TIMEOUT_SECONDS`` /
    ``_INIT_TIMEOUT_SECONDS`` attribute after import, *current_global* differs
    from *import_time_global* and wins. Otherwise the first set env var in
    *env_vars* is re-read from ``os.environ`` so post-import env updates take effect.

    :param env_vars: Candidate environment variable names in precedence order.
    :param current_global: Current value of the module-level constant.
    :param import_time_global: Value captured when the module was imported.
    :param default: Fallback seconds value when no candidate env var is set.
    :returns: Effective timeout in seconds.
    """
    if current_global != import_time_global:
        return current_global
    for env_var in env_vars:
        if env_var in os.environ:
            return parse_positive_timeout_seconds(env_var, default=default)
    return default
