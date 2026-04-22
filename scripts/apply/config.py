"""GAJ apply-side config resolver.

Mirrors the Phase 9 TypeScript db-path precedence pattern for the
applications folder path used by the PDF resolver:

    env GAJ_APPLICATIONS_PATH > ~/gaj/config.yaml (applications_path) > default

The default points at the canonical per-slug PDF folder on the author's
disk. Tests monkeypatch DEFAULT_APPLICATIONS_PATH to a tmp_path.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml


DEFAULT_GAJ_DIR = Path.home() / "gaj"
CONFIG_PATH = DEFAULT_GAJ_DIR / "config.yaml"
DEFAULT_APPLICATIONS_PATH = Path(
    "/Users/christianmartin/ANTIGRAVITY PROJECTS/OPERATION GETAJOB 2026/resume/applications"
)


class ConfigError(Exception):
    """Raised when a resolved config value points at a missing path."""


def _read_yaml_key(key: str) -> str | None:
    if not CONFIG_PATH.exists():
        return None
    try:
        parsed = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError:
        return None
    if not isinstance(parsed, dict):
        return None
    value = parsed.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def get_applications_path() -> Path:
    """Resolve the per-slug applications folder.

    Precedence: GAJ_APPLICATIONS_PATH env > ~/gaj/config.yaml applications_path
    key > DEFAULT_APPLICATIONS_PATH. Returns a Path that exists on disk;
    raises ConfigError otherwise.
    """
    env = os.environ.get("GAJ_APPLICATIONS_PATH", "").strip()
    if env:
        path = Path(env)
    else:
        configured = _read_yaml_key("applications_path")
        path = Path(configured) if configured else DEFAULT_APPLICATIONS_PATH

    if not path.is_dir():
        raise ConfigError(f"applications path does not exist or is not a directory: {path}")
    return path
