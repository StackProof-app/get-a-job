"""Greenhouse deterministic adapter.

boards.greenhouse.io applications expose a stable input naming scheme
(`job_application[first_name]`, `[last_name]`, `[email]`, `[phone]`,
`[urls][LinkedIn]`). We fill those by CSS selector without calling the
LLM, record anything else as skipped, and stop before submit.

File uploads (resume, cover letter attachments) are recorded as skipped
so the pre-submit screenshot surfaces them for the human to handle.
Custom questions are unmapped by design and fall through to the same
skipped bucket; Phase 14 revisits screener drafting.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..adapter import FillResult, JobRef
from ..profile import Profile


SUBMIT_PATTERN = re.compile(r"submit|apply|send", re.IGNORECASE)
BANNED_TYPES = {"submit", "button", "reset", "image", "hidden"}


def _split_name(full_name: str) -> tuple[str, str]:
    """Split identity.full_name into first/last halves.

    Single-word names produce (name, "") so the last-name locator records
    a skip rather than filling an empty string on a required field.
    """
    stripped = (full_name or "").strip()
    if not stripped:
        return "", ""
    parts = stripped.split(" ", 1)
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], parts[1].strip()


class GreenhouseAdapter:
    """Deterministic adapter for boards.greenhouse.io applications."""

    name: str = "greenhouse"

    def matches(self, url: str) -> bool:
        lowered = (url or "").lower()
        return (
            "boards.greenhouse.io" in lowered
            or "greenhouse.io/embed/job_app" in lowered
        )

    def fill(self, page, profile: Profile, job: JobRef) -> FillResult:
        first, last = _split_name(profile.identity.full_name)

        field_map: list[tuple[str, str, str]] = [
            ('input[name="job_application[first_name]"]', "identity.full_name", first),
            ('input[name="job_application[last_name]"]', "identity.full_name", last),
            ('input[name="job_application[email]"]', "identity.email", profile.identity.email),
            ('input[name="job_application[phone]"]', "identity.phone", profile.identity.phone),
        ]
        if profile.identity.linkedin_url:
            field_map.append(
                (
                    'input[name="job_application[urls][LinkedIn]"]',
                    "identity.linkedin_url",
                    profile.identity.linkedin_url,
                )
            )

        filled_paths: set[str] = set()
        skipped_paths: list[str] = []

        for selector, profile_path, value in field_map:
            if not value:
                skipped_paths.append(profile_path)
                continue
            try:
                locator = page.locator(selector).first
                if locator.count() == 0:
                    skipped_paths.append(profile_path)
                    continue
                el_type = (locator.get_attribute("type") or "").lower()
                if el_type in BANNED_TYPES:
                    skipped_paths.append(profile_path)
                    continue
                if el_type == "file":
                    skipped_paths.append(profile_path)
                    continue
                locator.fill(str(value))
                filled_paths.add(profile_path)
            except Exception:  # noqa: BLE001
                skipped_paths.append(profile_path)

        try:
            file_locators = page.locator('input[type="file"]').all()
        except Exception:  # noqa: BLE001
            file_locators = []
        for loc in file_locators:
            try:
                attr_name = loc.get_attribute("name") or "unknown_file_field"
            except Exception:  # noqa: BLE001
                attr_name = "unknown_file_field"
            if attr_name not in skipped_paths:
                skipped_paths.append(attr_name)

        screenshot_path = self._capture_screenshot(page, job.id)

        return FillResult(
            filled_fields=sorted(filled_paths),
            skipped_fields=skipped_paths,
            screenshot_path=screenshot_path,
        )

    def _capture_screenshot(self, page, job_id: str) -> str:
        target_dir = Path.home() / "gaj" / "applications" / job_id
        target_dir.mkdir(parents=True, exist_ok=True)
        path = target_dir / "pre_submit.png"
        try:
            page.screenshot(path=str(path), full_page=True)
        except TypeError:
            page.screenshot(path=str(path))
        return str(path)
