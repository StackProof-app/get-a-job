"""ATSAdapter Protocol + shared dataclasses.

Phase 11-13 adapters implement ATSAdapter. The runtime_checkable decorator
means they stay plain classes without subclassing an ABC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from .profile import Profile


@dataclass
class JobRef:
    id: str
    apply_url: str
    company: str
    title: str


@dataclass
class FillResult:
    filled_fields: list[str] = field(default_factory=list)
    skipped_fields: list[str] = field(default_factory=list)
    screenshot_path: str | None = None
    error: str | None = None


@runtime_checkable
class ATSAdapter(Protocol):
    """Interface every ATS adapter implements.

    `name` is a class attribute (the adapter's identity). `matches` is a
    cheap URL check. `fill` does the work against a Scrapling page handle
    and must never click a submit button.
    """

    name: str

    def matches(self, url: str) -> bool:
        ...

    def fill(self, page: object, profile: "Profile", job: JobRef) -> FillResult:
        ...
