#!/usr/bin/env python3
"""Minimal .env loader for local scripts.

Loads key/value pairs from a .env file located next to this module,
without overriding variables already present in the process environment.
"""

import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent


def load_env_file(filename: str = ".env") -> None:
    env_path = BASE_DIR / filename
    if not env_path.exists() or not env_path.is_file():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("export "):
            line = line[7:].strip()

        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        if not key:
            continue

        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]

        os.environ.setdefault(key, value)


def resolve_session_name(session_name: str) -> str:
    raw = (session_name or "").strip()
    if not raw:
        raw = "tgseed_session"

    expanded = Path(raw).expanduser()
    if expanded.is_absolute() or str(expanded.parent) != ".":
        return str(expanded)

    return str(BASE_DIR / expanded)


def session_file_exists(session_name: str) -> bool:
    base = Path(resolve_session_name(session_name))
    session_file = base if base.suffix == ".session" else Path(f"{base}.session")
    return session_file.exists()
