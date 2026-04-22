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

from ..adapter import FillResult, JobRef, UploadResult
from ..pdf_resolver import PDFBundle
from ..profile import Profile


SUBMIT_PATTERN = re.compile(r"submit|apply|send", re.IGNORECASE)
BANNED_TYPES = {"submit", "button", "reset", "image", "hidden"}

# Greenhouse has two renderings in the wild. New React boards use id=resume
# with no name; legacy embed boards use name="job_application[resume]".
# Both selector chains verified against live fetches 2026-04-22 (see
# 14-01-RESEARCH.md).
RESUME_SELECTORS: tuple[str, ...] = (
    'input[type="file"]#resume',
    'input[type="file"][name="job_application[resume]"]',
)
COVER_LETTER_SELECTORS: tuple[str, ...] = (
    'input[type="file"]#cover_letter',
    'input[type="file"][name="job_application[cover_letter]"]',
)


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

    def upload_pdfs(self, page, bundle: PDFBundle, pattern: str) -> UploadResult:
        """Attach resume / cover-letter PDFs to the matching file inputs.

        pattern="separate": resume input gets bundle.resume, cover letter input
          gets bundle.cover_letter (both must be present in the bundle).
        pattern="combined": resume input gets bundle.combined; cover letter
          input (if present on page) is left untouched.
        pattern="text": resume input gets bundle.resume; caller handles
          cover letter paste-back separately.

        Never clicks anything. Hidden file inputs are fine; Playwright's
        set_input_files works on visually-hidden inputs.
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
    """Try each selector in order; set_input_files on the first match.

    Records the label in uploaded_fields on success, or appends a
    skip reason to skipped_uploads on miss. Never raises into the caller.
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
