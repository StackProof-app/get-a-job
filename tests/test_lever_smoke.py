"""Lever deterministic adapter smoke test.

Loads file://tests/fixtures/lever_real.html via Scrapling and runs
LeverAdapter.fill directly. Asserts the deterministic path fills the
stable Lever identity fields, skips the file upload, leaves the custom
`cards[<uuid>][field0]` question unfilled, writes a pre-submit
screenshot, and never shells out to `claude`.

The guard_no_claude fixture fails the test if subprocess.run is ever
invoked with cmd[0] == "claude". The deterministic adapter must not
touch the LLM.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.apply.adapter import JobRef  # noqa: E402
from scripts.apply.adapters.lever import LeverAdapter  # noqa: E402
from scripts.apply.profile import (  # noqa: E402
    Address,
    EeocVoluntary,
    Employment,
    Identity,
    Profile,
    Relocation,
    Resume,
    ResumeVariant,
    WorkAuth,
)


FIXTURE = REPO_ROOT / "tests" / "fixtures" / "lever_real.html"


def _synthetic_profile() -> Profile:
    return Profile(
        identity=Identity(
            full_name="Test Person",
            preferred_name="Test",
            email="test@example.com",
            phone="555-123-4567",
            linkedin_url="https://linkedin.com/in/test",
            github_url="https://github.com/test",
            portfolio_url="https://test.dev",
        ),
        address=Address(city="Austin", state="TX", postal_code="78701", country="US"),
        work_auth=WorkAuth(status="us_citizen"),
        relocation=Relocation(current_location_preference="remote"),
        employment=Employment(current_status="employed", earliest_start_date="2026-05-01"),
        resume=Resume(variants=[ResumeVariant(key="g", label="G", path="/tmp/r.pdf", use_when="default")]),
        eeoc_voluntary=EeocVoluntary(),
    )


@pytest.fixture
def guard_no_claude(monkeypatch: pytest.MonkeyPatch):
    """Fail the test if the adapter tries to shell out to `claude`."""

    real_run = subprocess.run

    def guarded_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and len(cmd) > 0 and cmd[0] == "claude":
            raise AssertionError(
                "deterministic lever adapter must not call `claude`; "
                f"got cmd={list(cmd)!r}"
            )
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("subprocess.run", guarded_run)


def test_lever_adapter_fills_real_fixture(tmp_path: Path, guard_no_claude):
    import shutil
    import uuid

    from scrapling.fetchers import DynamicFetcher

    job_id = f"lever-smoke-{uuid.uuid4().hex[:8]}"
    adapter = LeverAdapter()
    profile = _synthetic_profile()
    job = JobRef(id=job_id, apply_url=f"file://{FIXTURE}", company="Acme", title="SWE")

    captured: dict = {"result": None, "error": None}

    def page_action(page):
        try:
            captured["result"] = adapter.fill(page, profile, job)
        except Exception as exc:  # noqa: BLE001
            captured["error"] = repr(exc)
        return page

    DynamicFetcher.fetch(
        f"file://{FIXTURE}",
        page_action=page_action,
        headless=True,
        network_idle=False,
    )

    assert captured["error"] is None, captured["error"]
    result = captured["result"]
    assert result is not None
    assert result.error is None, result.error

    assert "identity.email" in result.filled_fields, (
        f"missing email; got filled={result.filled_fields}"
    )
    name_like = {"identity.full_name", "identity.first_name"}
    assert name_like & set(result.filled_fields), (
        f"expected one of {name_like} in filled_fields; got {result.filled_fields}"
    )

    upload_skipped = any(
        "resume" in str(entry).lower() for entry in result.skipped_fields
    )
    assert upload_skipped, (
        f"expected resume entry in skipped_fields; got {result.skipped_fields}"
    )

    custom_field_name = "cards[7b840a00-bccd-4752-a3dd-2c887a15ffe2][field0]"
    assert custom_field_name not in result.filled_fields, (
        f"custom cards[] field must fall through; got filled={result.filled_fields}"
    )

    assert result.screenshot_path is not None
    screenshot = Path(result.screenshot_path)
    try:
        assert screenshot.exists(), f"screenshot not created at {screenshot}"
        assert screenshot.stat().st_size > 0
    finally:
        job_dir = Path.home() / "gaj" / "applications" / job_id
        if job_dir.exists():
            shutil.rmtree(job_dir, ignore_errors=True)
