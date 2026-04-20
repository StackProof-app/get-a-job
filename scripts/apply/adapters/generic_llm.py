"""Generic LLM fallback adapter.

Scrapling opens the page. We extract labels, aria, placeholder, and name
attributes; ask a headless `claude -p` call to map profile fields to form
field ids; fill via the page's fill() API; screenshot; never click
submit, apply, or send.

The adapter's fill() assumes `page` is a Playwright sync Page (Scrapling's
DynamicFetcher exposes it via the page_action callback).
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path

from ..adapter import FillResult, JobRef
from ..profile import Profile


SUBMIT_PATTERN = re.compile(r"submit|apply|send", re.IGNORECASE)
BANNED_TYPES = {"submit", "button", "reset", "image", "hidden"}


_FIELD_EXTRACTION_JS = r"""
() => {
    const candidates = Array.from(document.querySelectorAll('input, textarea, select'));
    const banned = new Set(['submit', 'button', 'reset', 'image', 'hidden']);
    return candidates
        .filter(el => !banned.has((el.type || '').toLowerCase()))
        .map(el => {
            const id = el.id || '';
            const name = el.name || '';
            let labelText = '';
            if (id) {
                const lab = document.querySelector('label[for="' + id.replace(/"/g, '\\"') + '"]');
                if (lab) labelText = (lab.textContent || '').trim();
            }
            return {
                id: id,
                name: name,
                type: (el.type || el.tagName || '').toLowerCase(),
                required: !!el.required,
                label: labelText,
                aria_label: el.getAttribute('aria-label') || '',
                placeholder: el.getAttribute('placeholder') || '',
                tag: el.tagName.toLowerCase(),
            };
        });
}
"""


def _profile_relevant_fields(profile: Profile) -> dict:
    """Serialize the subset of the profile that an ATS form typically asks for."""
    return {
        "identity": asdict(profile.identity),
        "address": asdict(profile.address),
        "work_auth": asdict(profile.work_auth),
        "relocation": asdict(profile.relocation),
        "employment": asdict(profile.employment),
        "eeoc_voluntary": asdict(profile.eeoc_voluntary),
    }


def _build_mapping_prompt(fields: list[dict], profile: Profile) -> str:
    profile_obj = _profile_relevant_fields(profile)
    instructions = (
        "You map ATS form fields to a candidate profile. Return STRICT JSON ONLY. "
        "No prose. No markdown fences.\n"
        "Shape: "
        '{"mappings": [{"field_id": "<id-or-name>", "profile_path": "<dotted.path>", '
        '"value": "<string>"}], '
        '"skipped": [{"field_id": "<id-or-name>", "reason": "<why>"}]}\n'
        "Rules:\n"
        "- Use the field id if present; otherwise its name attribute.\n"
        "- If a form asks for first/last name separately, split identity.full_name by space; "
        "both halves share profile_path identity.full_name.\n"
        "- Skip file/upload fields with reason \"file upload\".\n"
        "- Skip any field whose purpose is unclear with a short reason.\n"
        "- For EEOC voluntary sections, use the provided decline_to_state defaults.\n"
    )
    payload = {"fields": fields, "profile": profile_obj}
    return instructions + "\nPAYLOAD:\n" + json.dumps(payload)


def _strip_json_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        first_newline = stripped.find("\n")
        if first_newline != -1:
            stripped = stripped[first_newline + 1 :]
        if stripped.endswith("```"):
            stripped = stripped[: -3]
    return stripped.strip()


def _call_claude_map(prompt: str) -> dict:
    """Invoke `claude -p` with json output, return the parsed assistant JSON."""
    completed = subprocess.run(
        [
            "claude",
            "-p",
            "--model",
            "claude-haiku-4-5",
            "--output-format",
            "json",
            "--dangerously-skip-permissions",
        ],
        input=prompt,
        capture_output=True,
        text=True,
        timeout=60,
        check=True,
    )
    envelope = json.loads(completed.stdout)
    assistant_text = envelope.get("result", "") if isinstance(envelope, dict) else ""
    if not assistant_text:
        raise ValueError("claude envelope missing 'result' field")
    inner = _strip_json_fences(assistant_text)
    return json.loads(inner)


class GenericLLMAdapter:
    """Fallback adapter: label extraction plus headless Claude mapping."""

    name: str = "generic"

    def matches(self, url: str) -> bool:  # noqa: ARG002
        return True

    def fill(self, page, profile: Profile, job: JobRef) -> FillResult:
        try:
            fields = page.evaluate(_FIELD_EXTRACTION_JS) or []
        except Exception as exc:  # noqa: BLE001
            return FillResult(error=f"field extraction failed: {exc}")

        if not fields:
            return FillResult(error="no fillable fields found")

        prompt = _build_mapping_prompt(fields, profile)
        try:
            mapping = _call_claude_map(prompt)
        except subprocess.CalledProcessError as exc:
            return FillResult(error=f"claude cli failed: {exc.stderr or exc}")
        except subprocess.TimeoutExpired:
            return FillResult(error="claude cli timed out after 60s")
        except (ValueError, json.JSONDecodeError) as exc:
            return FillResult(error=f"claude response not JSON: {exc}")

        filled_paths: set[str] = set()
        skipped_paths: list[str] = []

        for entry in mapping.get("mappings", []):
            if not isinstance(entry, dict):
                continue
            field_id = str(entry.get("field_id") or "").strip()
            profile_path = str(entry.get("profile_path") or "").strip()
            value = entry.get("value")
            if not field_id or value is None:
                continue
            if SUBMIT_PATTERN.search(field_id):
                skipped_paths.append(profile_path or field_id)
                continue
            selector_candidates = [
                f'[id="{field_id}"]',
                f'[name="{field_id}"]',
            ]
            filled_here = False
            for sel in selector_candidates:
                locator = page.locator(sel).first
                if locator.count() == 0:
                    continue
                el_type = (locator.get_attribute("type") or "").lower()
                tag = (locator.evaluate("el => el.tagName.toLowerCase()") or "").lower()
                if el_type in BANNED_TYPES or tag == "button":
                    break
                if el_type == "file":
                    skipped_paths.append(profile_path or field_id)
                    break
                try:
                    locator.fill(str(value))
                    filled_here = True
                    break
                except Exception:  # noqa: BLE001
                    continue
            if filled_here and profile_path:
                filled_paths.add(profile_path)
            elif not filled_here:
                skipped_paths.append(profile_path or field_id)

        for entry in mapping.get("skipped", []) or []:
            if isinstance(entry, dict):
                path = str(entry.get("profile_path") or entry.get("field_id") or "").strip()
                if path:
                    skipped_paths.append(path)

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
