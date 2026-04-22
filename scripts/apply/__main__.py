"""Entrypoint: python -m scripts.apply --id <job_id> [--dry-run]

--dry-run resolves adapter + profile but does no browser or LLM work.
Non-dry-run opens Scrapling DynamicFetcher, runs the matched adapter's
fill() inside a page_action callback, and stops before any submit button.

Phase 14: pre-upload gate runs after the job record and PDF bundle are
resolved but before any file input is touched. The human picks the
attachment pattern (separate / combined / text) or aborts.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m scripts.apply",
        description="GAJ ATS autofill: fingerprint ATS, load profile, fill form, stop before submit.",
    )
    parser.add_argument("--id", type=str, help="Job id from the GAJ pipeline.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Resolve adapter and profile but do not open a browser or call the LLM.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Queue mode: drain every cover-letter-ready job. Not yet implemented.",
    )
    parser.add_argument(
        "--preview-url",
        type=str,
        default=None,
        help="Optional URL to preview field extraction against (dry-run only).",
    )
    return parser


def _get_slug(job: dict | None) -> Optional[str]:
    """Pull slug from a cli_shim job record; None if unset or record missing."""
    if not job:
        return None
    raw = job.get("slug")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return None


def _pre_upload_gate(
    slug: str,
    *,
    input_fn=input,
    output=sys.stdout,
) -> tuple[Optional[str], Optional[object]]:
    """Resolve PDFs for slug, display the gate, return (pattern, bundle).

    Returns (None, None) when the human aborts or when no PDFs exist.
    Any error is printed to output; the caller treats that as abort.
    """
    from .cover_letter import available_patterns, choose_pattern
    from .pdf_resolver import PDFBundle, PDFBundleAmbiguous, PDFBundleMissing, resolve_pdfs

    try:
        bundle: PDFBundle = resolve_pdfs(slug)
    except (PDFBundleMissing, PDFBundleAmbiguous) as exc:
        print(f"Pre-upload gate: PDF resolution failed: {exc}", file=output)
        return None, None

    cover_html: Optional[Path] = None
    candidate = Path(
        "/Users/christianmartin/ANTIGRAVITY PROJECTS/OPERATION GETAJOB 2026/resume/cover-letters"
    ) / f"{slug}.html"
    if candidate.is_file():
        cover_html = candidate

    options = available_patterns(bundle, cover_html)
    if not options:
        print(
            "Pre-upload gate: no attachment patterns available for this bundle. "
            "Need resume+cover-letter PDFs, a combined PDF, or a resume PDF + cover HTML.",
            file=output,
        )
        return None, None

    print("", file=output)
    print("=== Pre-upload gate ===", file=output)
    print(f"Slug: {slug}", file=output)
    print("Resolved PDFs:", file=output)
    print(f"  resume:       {bundle.resume}", file=output)
    print(f"  cover_letter: {bundle.cover_letter}", file=output)
    print(f"  combined:     {bundle.combined}", file=output)
    if cover_html is not None:
        print(f"  cover_html:   {cover_html}", file=output)
    print(f"Available patterns: {', '.join(options)}", file=output)
    print("Type a pattern name, its number, or 'abort':", file=output, flush=True)

    raw = input_fn().strip().lower()
    if raw == "abort" or raw == "":
        print("Pre-upload gate: aborted by user.", file=output)
        return None, None

    try:
        pattern = choose_pattern(
            bundle,
            cover_html,
            input_fn=lambda: raw,
            output=output,
        )
    except ValueError as exc:
        print(f"Pre-upload gate: invalid selection: {exc}", file=output)
        return None, None

    return pattern, bundle


def _dry_run(job_id: str, preview_url: str | None) -> int:
    from . import cli_shim
    from .fingerprint import detect
    from .profile import load_profile, resolve_profile_path

    job: dict | None = None
    cli_error: str | None = None
    try:
        queue = cli_shim.apply_queue()
        for candidate in queue:
            if str(candidate.get("id")) == job_id:
                job = candidate
                break
    except cli_shim.CliShimError as exc:
        cli_error = str(exc)

    url = preview_url or (job.get("apply_url") if job else None) or ""
    adapter = detect(url) if url else "generic"

    profile_path = resolve_profile_path()
    profile_ok = True
    profile_error: str | None = None
    try:
        load_profile(profile_path)
    except FileNotFoundError:
        profile_ok = False
        profile_error = f"profile not found at {profile_path}"
    except Exception as exc:  # noqa: BLE001
        profile_ok = False
        profile_error = str(exc)

    slug = _get_slug(job)
    plan = {
        "adapter": adapter,
        "url": url,
        "job_id": job_id,
        "profile_path": profile_path,
        "profile_ok": profile_ok,
        "profile_error": profile_error,
        "cli_error": cli_error,
        "slug": slug,
        "note": "fingerprint+profile resolved, full run executes in non-dry-run mode",
    }
    print(json.dumps(plan, indent=2))

    if slug:
        pattern, bundle = _pre_upload_gate(slug)
        if pattern is None:
            return 0
        print(
            json.dumps(
                {
                    "would_upload": {
                        "pattern": pattern,
                        "resume": str(bundle.resume) if bundle.resume else None,
                        "cover_letter": str(bundle.cover_letter) if bundle.cover_letter else None,
                        "combined": str(bundle.combined) if bundle.combined else None,
                    }
                },
                indent=2,
            )
        )
    else:
        print("(dry-run: slug unset on job record; pre-upload gate skipped)")
    return 0


def _run(job_id: str) -> int:
    from . import cli_shim
    from .adapter import JobRef
    from .adapters.ashby import AshbyAdapter
    from .adapters.generic_llm import GenericLLMAdapter
    from .adapters.greenhouse import GreenhouseAdapter
    from .adapters.lever import LeverAdapter
    from .fingerprint import detect
    from .profile import load_profile, resolve_profile_path

    try:
        queue = cli_shim.apply_queue()
    except cli_shim.CliShimError as exc:
        print(f"cli_shim failure: {exc}", file=sys.stderr)
        return 1

    job_record: dict | None = None
    for candidate in queue:
        if str(candidate.get("id")) == job_id:
            job_record = candidate
            break

    if not job_record:
        print(f"job {job_id} not in cover-letter-ready queue", file=sys.stderr)
        return 1

    url = str(job_record.get("apply_url") or "")
    if not url:
        print(f"job {job_id} has no apply_url", file=sys.stderr)
        return 1

    slug = _get_slug(job_record)
    if not slug:
        print(
            f"job {job_id} has no slug; set it via "
            f"`npx tsx scripts/pipeline-cli.ts update {job_id} slug <slug>` first.",
            file=sys.stderr,
        )
        return 1

    pattern, bundle = _pre_upload_gate(slug)
    if pattern is None:
        return 0

    adapter_key = detect(url)
    registry = {
        "greenhouse": GreenhouseAdapter(),
        "ashby": AshbyAdapter(),
        "lever": LeverAdapter(),
        "generic": GenericLLMAdapter(),
    }
    adapter = registry.get(adapter_key, registry["generic"])

    profile = load_profile(resolve_profile_path())
    job_ref = JobRef(
        id=str(job_record.get("id")),
        apply_url=url,
        company=str(job_record.get("company") or job_record.get("company_name") or ""),
        title=str(job_record.get("role") or job_record.get("job_title") or ""),
    )

    try:
        from scrapling.fetchers import DynamicFetcher
    except ImportError as exc:
        print(f"scrapling import failed: {exc}", file=sys.stderr)
        return 1

    captured: dict = {
        "fill_result": None,
        "upload_result": None,
        "error": None,
    }

    def page_action(page):
        try:
            captured["fill_result"] = adapter.fill(page, profile, job_ref)
        except Exception as exc:  # noqa: BLE001
            captured["error"] = f"adapter.fill crashed: {exc}"
            return page
        try:
            if hasattr(adapter, "upload_pdfs"):
                captured["upload_result"] = adapter.upload_pdfs(page, bundle, pattern)
        except Exception as exc:  # noqa: BLE001
            captured["error"] = f"adapter.upload_pdfs crashed: {exc}"
        return page

    try:
        DynamicFetcher.fetch(url, page_action=page_action, headless=True, network_idle=True)
    except Exception as exc:  # noqa: BLE001
        print(f"scrapling fetch failed: {exc}", file=sys.stderr)
        return 1

    if captured["error"]:
        print(captured["error"], file=sys.stderr)
        try:
            cli_shim.apply_error(job_ref.id, "fill", captured["error"])
        except cli_shim.CliShimError as exc:
            print(f"failed to log apply-error: {exc}", file=sys.stderr)
        return 1

    fill_result = captured["fill_result"]
    upload_result = captured["upload_result"]
    if fill_result is None:
        print("adapter returned no fill result", file=sys.stderr)
        return 1

    payload: dict = {
        "adapter": adapter_key,
        "pattern": pattern,
        "filled_fields": fill_result.filled_fields,
        "skipped_fields": fill_result.skipped_fields,
        "screenshot_path": fill_result.screenshot_path,
        "error": fill_result.error,
    }
    if upload_result is not None:
        payload["uploaded_fields"] = upload_result.uploaded_fields
        payload["skipped_uploads"] = upload_result.skipped_uploads
        payload["upload_error"] = upload_result.error

    print(json.dumps(payload, indent=2))
    if fill_result.error or (upload_result and upload_result.error):
        step = "fill" if fill_result.error else "upload"
        msg = fill_result.error or (upload_result.error if upload_result else "")
        try:
            cli_shim.apply_error(job_ref.id, step, msg)
        except cli_shim.CliShimError as exc:
            print(f"failed to log apply-error: {exc}", file=sys.stderr)
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.all:
        print("--all not yet implemented, see Phase 15", file=sys.stderr)
        return 2

    if not args.id:
        parser.print_help()
        return 1

    if args.dry_run:
        return _dry_run(args.id, args.preview_url)
    return _run(args.id)


if __name__ == "__main__":
    sys.exit(main())
