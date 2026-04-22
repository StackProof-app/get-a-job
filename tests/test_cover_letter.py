"""Tests for cover_letter.choose_pattern + extract_plaintext.

Covers pattern filtering by bundle shape and HTML-to-plaintext
extraction (style/script stripping, paragraph preservation, blank-run
collapsing). Uses tests/fixtures/cover-letter-sample.html as the
realistic input. Pure Python, no browser, no LLM.
"""

from __future__ import annotations

import io
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.apply.cover_letter import (  # noqa: E402
    available_patterns,
    choose_pattern,
    extract_plaintext,
)
from scripts.apply.pdf_resolver import PDFBundle  # noqa: E402


FIXTURE = REPO_ROOT / "tests" / "fixtures" / "cover-letter-sample.html"


@pytest.fixture
def guard_no_claude(monkeypatch: pytest.MonkeyPatch):
    real_run = subprocess.run

    def guarded_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "claude":
            raise AssertionError(
                f"cover_letter must not call `claude`; got cmd={list(cmd)!r}"
            )
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("subprocess.run", guarded_run)


def _bundle(*, resume=False, cover=False, combined=False, tmp_path=None) -> PDFBundle:
    return PDFBundle(
        slug="test-slug",
        resume=(tmp_path / "resume.pdf") if resume else None,
        cover_letter=(tmp_path / "cover.pdf") if cover else None,
        combined=(tmp_path / "combined.pdf") if combined else None,
    )


def test_all_three_patterns_available_when_everything_present(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=True, combined=True, tmp_path=tmp_path)
    assert available_patterns(bundle, FIXTURE) == ["separate", "combined", "text"]


def test_separate_only_when_combined_missing(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=True, combined=False, tmp_path=tmp_path)
    assert available_patterns(bundle, None) == ["separate"]


def test_combined_only_when_resume_and_cover_absent(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=False, cover=False, combined=True, tmp_path=tmp_path)
    assert available_patterns(bundle, FIXTURE) == ["combined"]


def test_text_offered_when_resume_plus_html_present(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=False, combined=False, tmp_path=tmp_path)
    assert available_patterns(bundle, FIXTURE) == ["text"]


def test_text_not_offered_when_html_missing(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=False, combined=False, tmp_path=tmp_path)
    missing = tmp_path / "nope.html"
    assert available_patterns(bundle, missing) == []


def test_choose_pattern_by_index(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=True, combined=True, tmp_path=tmp_path)
    out = io.StringIO()
    chosen = choose_pattern(bundle, FIXTURE, input_fn=lambda: "2", output=out)
    assert chosen == "combined"
    assert "Cover letter attachment patterns" in out.getvalue()


def test_choose_pattern_by_name(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=True, combined=False, tmp_path=tmp_path)
    out = io.StringIO()
    chosen = choose_pattern(bundle, None, input_fn=lambda: "separate", output=out)
    assert chosen == "separate"


def test_choose_pattern_rejects_unavailable(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=True, cover=False, combined=False, tmp_path=tmp_path)
    with pytest.raises(ValueError):
        choose_pattern(bundle, None, input_fn=lambda: "combined", output=io.StringIO())


def test_choose_pattern_raises_when_no_options(guard_no_claude, tmp_path: Path):
    bundle = _bundle(resume=False, cover=False, combined=False, tmp_path=tmp_path)
    with pytest.raises(ValueError):
        choose_pattern(bundle, None, input_fn=lambda: "text", output=io.StringIO())


def test_extract_plaintext_preserves_paragraphs(guard_no_claude):
    text = extract_plaintext(FIXTURE)
    assert "Dear Hiring Team," in text
    assert "Christian Martin" in text
    # Paragraphs separated by blank line
    assert "\n\n" in text
    # No 3+ consecutive newlines
    assert "\n\n\n" not in text


def test_extract_plaintext_strips_style_and_script(guard_no_claude):
    text = extract_plaintext(FIXTURE)
    # CSS rules must not appear.
    assert "font-family" not in text
    assert "DOMContentLoaded" not in text
    # Title is inside <head>, but BeautifulSoup's get_text walks it too;
    # the important rule is that style/script CONTENTS are gone.


def test_extract_plaintext_ends_with_single_newline(guard_no_claude):
    text = extract_plaintext(FIXTURE)
    assert text.endswith("\n")
    assert not text.endswith("\n\n")
