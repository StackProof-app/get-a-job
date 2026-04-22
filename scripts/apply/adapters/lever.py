"""Lever deterministic adapter.

jobs.lever.co applications expose stable `name=` attributes on every
identity field across the 3 boards catalogued 2026-04-21 (Palantir,
Whoop, FORM). We fill those by CSS selector without calling the LLM,
record anything else as skipped, and stop before submit.

Selector strategy chosen in Task 2 of Plan 13-01: name-based. URL fields
carry `name=` but no `data-qa=`, which would silently skip URL entries
under a data-qa-first strategy. Selector rationale lives in
.paul/phases/13-lever-adapter/13-01-RESEARCH.md.

Lever uses a single `name` field (no first/last split), matching Ashby.
Custom questions render under `cards[<uuid>][fieldN]` bracket notation
and fall through to skipped_fields for the Phase 14 screener LLM. File
uploads (resume) land in skipped_fields so the pre-submit screenshot
surfaces them for the human.
"""

from __future__ import annotations

import re
from pathlib import Path

from ..adapter import FillResult, JobRef, UploadResult
from ..pdf_resolver import PDFBundle
from ..profile import Profile


SUBMIT_PATTERN = re.compile(r"submit|apply|send", re.IGNORECASE)
BANNED_TYPES = {"submit", "button", "reset", "image", "hidden"}

# Lever standard resume input (verified Metabase + AMT 2026-04-22,
# Palantir/Whoop/FORM 2026-04-21). Cover letter on Lever is usually a
# free-text or cards[UUID][field0] textarea; no stable selector exists
# for a separate cover-letter file input, so the pattern chooser at the
# gate routes to combined or text when cover letter matters.
RESUME_SELECTORS: tuple[str, ...] = (
    'input[type="file"]#resume-upload-input',
    'input[type="file"][name="resume"]',
)
COVER_LETTER_SELECTORS: tuple[str, ...] = (
    'input[type="file"][name="cover_letter"]',
    'input[type="file"][name="coverLetter"]',
)


class LeverAdapter:
    """Deterministic adapter for jobs.lever.co applications."""

    name: str = "lever"

    def matches(self, url: str) -> bool:
        lowered = (url or "").lower()
        return "jobs.lever.co" in lowered

    def fill(self, page, profile: Profile, job: JobRef) -> FillResult:
        field_map: list[tuple[str, str, str]] = [
            ('input[name="name"]', "identity.full_name", profile.identity.full_name),
            ('input[name="email"]', "identity.email", profile.identity.email),
            ('input[name="phone"]', "identity.phone", profile.identity.phone),
        ]
        if profile.identity.linkedin_url:
            field_map.append(
                (
                    'input[name="urls[LinkedIn]"]',
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
        """Attach PDFs to Lever file inputs per the chosen pattern.

        Cover letter rarely exposed as a file input on Lever; the caller
        handles paste-back via the text pattern in that case.
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
