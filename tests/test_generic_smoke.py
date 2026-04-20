"""Generic LLM adapter smoke test against a static fixture.

Loads file://tests/fixtures/greenhouse_sample.html via Scrapling, stubs
the `claude -p` subprocess call with a canned mapping, and asserts the
adapter fills the text fields and captures a pre-submit screenshot
without clicking submit.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.apply.adapter import JobRef  # noqa: E402
from scripts.apply.adapters.generic_llm import GenericLLMAdapter  # noqa: E402
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


FIXTURE = REPO_ROOT / "tests" / "fixtures" / "greenhouse_sample.html"


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
def fake_claude(monkeypatch: pytest.MonkeyPatch):
    """Stub subprocess.run to return a canned claude -p JSON envelope."""

    mapping_payload = {
        "mappings": [
            {"field_id": "first_name", "profile_path": "identity.full_name", "value": "Test"},
            {"field_id": "last_name", "profile_path": "identity.full_name", "value": "Person"},
            {"field_id": "email", "profile_path": "identity.email", "value": "test@example.com"},
            {"field_id": "phone", "profile_path": "identity.phone", "value": "555-123-4567"},
            {"field_id": "linkedin_url", "profile_path": "identity.linkedin_url", "value": "https://linkedin.com/in/test"},
        ],
        "skipped": [
            {"field_id": "resume", "reason": "file upload"},
            {"field_id": "cover_letter", "reason": "unknown"},
        ],
    }
    claude_envelope = {"result": json.dumps(mapping_payload), "session_id": "stub"}

    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and len(cmd) > 0 and cmd[0] == "claude":
            return subprocess.CompletedProcess(
                args=list(cmd), returncode=0, stdout=json.dumps(claude_envelope), stderr=""
            )
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(
        "scripts.apply.adapters.generic_llm.subprocess.run", fake_run
    )


def test_generic_adapter_fills_fixture(tmp_path: Path, fake_claude):
    import shutil
    import uuid

    from scrapling.fetchers import DynamicFetcher

    job_id = f"smoke-test-{uuid.uuid4().hex[:8]}"
    adapter = GenericLLMAdapter()
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

    expected_paths = {"identity.full_name", "identity.email", "identity.phone"}
    assert expected_paths.issubset(set(result.filled_fields)), (
        f"missing profile paths; got {result.filled_fields}"
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
