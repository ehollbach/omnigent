"""Tests for ACP executor timeout configuration."""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

_TIMEOUT_ENV = "HARNESS_ACP_PROMPT_TIMEOUT_S"
_PRINT_TIMEOUT = (
    "from omnigent.inner.acp_executor import _PROMPT_TIMEOUT_SECONDS; "
    "print(_PROMPT_TIMEOUT_SECONDS)"
)


def _subprocess_env(value: str | None) -> dict[str, str]:
    env = os.environ.copy()
    if value is None:
        env.pop(_TIMEOUT_ENV, None)
    else:
        env[_TIMEOUT_ENV] = value
    return env


def test_prompt_timeout_defaults_and_override() -> None:
    assert (
        subprocess.check_output(
            [sys.executable, "-c", _PRINT_TIMEOUT],
            env=_subprocess_env(None),
            text=True,
        ).strip()
        == "300.0"
    )
    assert (
        subprocess.check_output(
            [sys.executable, "-c", _PRINT_TIMEOUT],
            env=_subprocess_env("7200"),
            text=True,
        ).strip()
        == "7200.0"
    )


def test_prompt_timeout_malformed_value_fails_loud() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PRINT_TIMEOUT],
        env=_subprocess_env("not-a-number"),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert _TIMEOUT_ENV in result.stderr.strip().splitlines()[-1]


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf"])
def test_prompt_timeout_rejects_non_positive_or_non_finite_values(value: str) -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PRINT_TIMEOUT],
        env=_subprocess_env(value),
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert _TIMEOUT_ENV in result.stderr.strip().splitlines()[-1]


def test_acp_and_qwen_prompt_timeouts_honor_post_import_env_and_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from omnigent.inner import acp_executor, qwen_executor

    monkeypatch.delenv("HARNESS_ACP_PROMPT_TIMEOUT_S", raising=False)
    monkeypatch.delenv("HARNESS_QWEN_PROMPT_TIMEOUT_S", raising=False)
    assert acp_executor._prompt_timeout_seconds() == 300.0
    assert qwen_executor._prompt_timeout_seconds() == 300.0

    monkeypatch.setenv("HARNESS_ACP_PROMPT_TIMEOUT_S", "420")
    assert acp_executor._prompt_timeout_seconds() == 420.0
    assert qwen_executor._prompt_timeout_seconds() == 420.0

    monkeypatch.setenv("HARNESS_QWEN_PROMPT_TIMEOUT_S", "510")
    assert qwen_executor._prompt_timeout_seconds() == 510.0

    # Monkeypatching the module attribute still wins for tests.
    monkeypatch.setattr(qwen_executor, "_PROMPT_TIMEOUT_SECONDS", 12.5)
    assert qwen_executor._prompt_timeout_seconds() == 12.5


@pytest.mark.parametrize(
    ("code", "env_name", "value"),
    [
        ("import omnigent.inner.acp_executor", "HARNESS_ACP_INIT_TIMEOUT_S", "0"),
        ("import omnigent.inner.acp_executor", "HARNESS_ACP_INIT_TIMEOUT_S", "nan"),
        ("import omnigent.inner.qwen_executor", "HARNESS_QWEN_PROMPT_TIMEOUT_S", "-5"),
        ("import omnigent.inner.qwen_executor", "HARNESS_ACP_PROMPT_TIMEOUT_S", "inf"),
    ],
)
def test_timeout_imports_reject_invalid_env_values(code: str, env_name: str, value: str) -> None:
    env = os.environ.copy()
    env[env_name] = value
    result = subprocess.run(
        [sys.executable, "-c", code],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode != 0
    assert env_name in result.stderr.strip().splitlines()[-1]
