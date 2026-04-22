"""Ashby deterministic adapter.

jobs.ashbyhq.com applications expose a stable ID-based naming scheme
(`_systemfield_name`, `_systemfield_email`, `_systemfield_phone`,
`_systemfield_linkedin`). We fill those by CSS selector without calling
the LLM, record anything else as skipped, and stop before submit.

Ashby uses a single `name` field (no first/last split). Custom
questions render with UUID-suffixed IDs (`_customfield_<uuid>`) that
are unmapped by design and fall through to skipped_fields for human
review or the Phase 14 screener LLM. File uploads (resume, attachments)
are recorded as skipped so the pre-submit screenshot surfaces them.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..adapter import FillResult, JobRef, UploadResult
from ..pdf_resolver import PDFBundle
from ..profile import Profile


SUBMIT_PATTERN = re.compile(r"submit|apply|send", re.IGNORECASE)
BANNED_TYPES = {"submit", "button", "reset", "image", "hidden"}

# Ashby standard resume input (verified Benchling + Replit 2026-04-22).
# Ashby does not expose a cover letter file input in the standard flow;
# cover letter either lives in a free-text field (text pattern) or gets
# swallowed by a board-specific _customfield_<uuid> upload.
RESUME_SELECTORS: tuple[str, ...] = (
    'input[type="file"]#_systemfield_resume',
)
COVER_LETTER_SELECTORS: tuple[str, ...] = (
    'input[type="file"]#_systemfield_coverLetter',
    'input[type="file"]#_systemfield_cover_letter',
)


class AshbyAdapter:
    """Deterministic adapter for jobs.ashbyhq.com applications."""

    name: str = "ashby"

    def matches(self, url: str) -> bool:
        lowered = (url or "").lower()
        return "jobs.ashbyhq.com" in lowered or (
            "ashbyhq.com/" in lowered and "/application" in lowered
        )

    def fill(self, page, profile: Profile, job: JobRef) -> FillResult:
        field_map: list[tuple[str, str, str]] = [
            ('input[id="_systemfield_name"]', "identity.full_name", profile.identity.full_name),
            ('input[id="_systemfield_email"]', "identity.email", profile.identity.email),
            ('input[id="_systemfield_phone"]', "identity.phone", profile.identity.phone),
        ]
        if profile.identity.linkedin_url:
            field_map.append(
                (
                    'input[id="_systemfield_linkedin"]',
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

    def upload_pdfs(self, page, bundle: PDFBundle, pattern: str) -> UploadResult:
        """Attach PDFs to Ashby file inputs per the chosen pattern.

        Cover letter rarely exposed as a file input on Ashby; when the
        pattern is "separate" and no cover letter input exists on the
        page, the miss is recorded and the caller falls back to paste-
        back outside upload_pdfs.
        """
        result = UploadResult()
        if pattern not in ("separate", "combined", "text"):
            result.error = f"unknown pattern: {pattern!r}"
            return result

        if pattern == "separate":
            _set_first(page, RESUME_SELECTORS, bundle.resume, "resume", result)
            _set_first(page, COVER_LETTER_SELECTORS, bundle.cover_letter, "cover_letter", result)
        elif pattern == "combined":
            _set_first(page, RESUME_SELECTORS, bundle.combined, "resume(combined)", result)
        else:  # text
            _set_first(page, RESUME_SELECTORS, bundle.resume, "resume", result)
        return result


def _set_first(page, selectors: tuple[str, ...], file_path, label: str, result: UploadResult) -> None:
    """See greenhouse._set_first. Duplicated per Phase 11 decision: each
    adapter independently auditable, cross-adapter coupling avoided.
    """
    if file_path is None:
        result.skipped_uploads.append(f"{label}:no-file-in-bundle")
        return
    for selector in selectors:
        try:
            locator = page.locator(selector).first
            if locator.count() == 0:
                continue
            locator.set_input_files(str(file_path))
            result.uploaded_fields.append(label)
            return
        except Exception as exc:  # noqa: BLE001
            result.skipped_uploads.append(f"{label}:selector-error:{selector}:{exc}")
            return
    result.skipped_uploads.append(f"{label}:no-input-on-page")
