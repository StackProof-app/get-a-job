"""GAJ ATS autofill subpackage.

Python owns the browser (Scrapling is Python-native). TypeScript owns the
DB (pipeline-cli.ts is the single write surface). They meet via
`scripts/apply/cli_shim.py` subprocess calls.
"""

from __future__ import annotations

__all__ = [
    "Profile",
    "ProfileValidationError",
    "load_profile",
    "resolve_profile_path",
    "validate_profile",
    "ATSAdapter",
    "FillResult",
    "JobRef",
]


_PROFILE_EXPORTS = {
    "Profile",
    "ProfileValidationError",
    "load_profile",
    "resolve_profile_path",
    "validate_profile",
}

_ADAPTER_EXPORTS = {"ATSAdapter", "FillResult", "JobRef"}


def __getattr__(name: str):
    if name in _PROFILE_EXPORTS:
        from . import profile as _profile

        return getattr(_profile, name)
    if name in _ADAPTER_EXPORTS:
        from . import adapter as _adapter

        return getattr(_adapter, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
