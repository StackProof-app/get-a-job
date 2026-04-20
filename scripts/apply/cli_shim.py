"""Subprocess shim around `npx tsx scripts/pipeline-cli.ts`.

TypeScript owns every DB write. Python calls into the TS CLI rather than
touching better-sqlite3 or opening a sqlite3 connection. Any import of
sqlite3 from this package is a bug.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
PIPELINE_CLI = REPO_ROOT / "scripts" / "pipeline-cli.ts"


class CliShimError(RuntimeError):
    """Raised when the TS CLI exits non-zero or returns unparseable output."""


def _run(verb: str, *args: str) -> str:
    cmd = ["npx", "tsx", str(PIPELINE_CLI), verb, *args]
    try:
        result = subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            check=True,
            text=True,
            capture_output=True,
        )
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()
        raise CliShimError(f"pipeline-cli {verb} failed: {stderr}") from exc
    return result.stdout


def _parse_json(stdout: str, verb: str) -> Any:
    try:
        return json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise CliShimError(f"pipeline-cli {verb} returned invalid JSON: {exc}") from exc


def apply_queue() -> list[dict]:
    """Return the list of jobs in cover-letter-ready status, oldest first."""
    payload = _parse_json(_run("apply-queue"), "apply-queue")
    if not isinstance(payload, dict):
        raise CliShimError("apply-queue: expected object payload")
    jobs = payload.get("jobs", [])
    return [j for j in jobs if isinstance(j, dict)]


def apply_next() -> dict | None:
    """Return the oldest cover-letter-ready job or None."""
    payload = _parse_json(_run("apply-next"), "apply-next")
    if not isinstance(payload, dict):
        raise CliShimError("apply-next: expected object payload")
    job = payload.get("job")
    return job if isinstance(job, dict) else None


def apply_finalize(job_id: str, submission_screenshot_path: str) -> None:
    """Flip a job to applied after a human-confirmed submit."""
    data = json.dumps({"id": job_id, "submission_screenshot_path": submission_screenshot_path})
    _run("apply-finalize", data)


def apply_error(job_id: str, error_step: str, error_message: str) -> None:
    """Record an autofill error without changing status."""
    data = json.dumps({"id": job_id, "error_step": error_step, "error_message": error_message})
    _run("apply-error", data)
