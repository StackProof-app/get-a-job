"""Entrypoint: python -m scripts.apply --id <job_id> [--dry-run]

--dry-run resolves adapter + profile but does no browser or LLM work.
Non-dry-run opens Scrapling DynamicFetcher, runs the matched adapter's
fill() inside a page_action callback, and stops before any submit button.
"""

from __future__ import annotations

import argparse
import json
import sys


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

    plan = {
        "adapter": adapter,
        "url": url,
        "job_id": job_id,
        "profile_path": profile_path,
        "profile_ok": profile_ok,
        "profile_error": profile_error,
        "cli_error": cli_error,
        "note": "fingerprint+profile resolved, full run executes in non-dry-run mode",
    }
    print(json.dumps(plan, indent=2))
    return 0


def _run(job_id: str) -> int:
    from . import cli_shim
    from .adapter import JobRef
    from .adapters.ashby import AshbyAdapter
    from .adapters.generic_llm import GenericLLMAdapter
    from .adapters.greenhouse import GreenhouseAdapter
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

    adapter_key = detect(url)
    registry = {
        "greenhouse": GreenhouseAdapter(),
        "ashby": AshbyAdapter(),
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

    captured: dict = {"result": None, "error": None}

    def page_action(page):
        try:
            captured["result"] = adapter.fill(page, profile, job_ref)
        except Exception as exc:  # noqa: BLE001
            captured["error"] = f"adapter.fill crashed: {exc}"
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

    result = captured["result"]
    if result is None:
        print("adapter returned no result", file=sys.stderr)
        return 1

    print(
        json.dumps(
            {
                "adapter": adapter_key,
                "filled_fields": result.filled_fields,
                "skipped_fields": result.skipped_fields,
                "screenshot_path": result.screenshot_path,
                "error": result.error,
            },
            indent=2,
        )
    )
    if result.error:
        try:
            cli_shim.apply_error(job_ref.id, "fill", result.error)
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
