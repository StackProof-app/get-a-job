"""Offline tests for config.get_applications_path + pdf_resolver.resolve_pdfs.

Covers env/yaml/default precedence and all PDFBundle shapes. Uses
tmp_path as the applications folder; no real disk or network work.

guard_no_claude fixture attached to every test so a regression that
accidentally shells out to the LLM is caught here too, matching the
Phase 11-13 deterministic adapter tests.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.apply import config as config_mod  # noqa: E402
from scripts.apply.config import ConfigError, get_applications_path  # noqa: E402
from scripts.apply.pdf_resolver import (  # noqa: E402
    PDFBundleAmbiguous,
    PDFBundleMissing,
    resolve_pdfs,
)


@pytest.fixture
def guard_no_claude(monkeypatch: pytest.MonkeyPatch):
    real_run = subprocess.run

    def guarded_run(cmd, *args, **kwargs):
        if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "claude":
            raise AssertionError(
                f"pdf_resolver must not call `claude`; got cmd={list(cmd)!r}"
            )
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr("subprocess.run", guarded_run)


@pytest.fixture
def isolated_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    """Ensure no ambient GAJ_APPLICATIONS_PATH leaks and ~/gaj/config.yaml is ignored."""
    monkeypatch.delenv("GAJ_APPLICATIONS_PATH", raising=False)
    # Point CONFIG_PATH at a non-existent file so ambient ~/gaj/config.yaml is ignored.
    fake_config = tmp_path / "nonexistent-config.yaml"
    monkeypatch.setattr(config_mod, "CONFIG_PATH", fake_config)
    return tmp_path


def _mk_slug_dir(base: Path, slug: str) -> Path:
    d = base / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def _touch(path: Path) -> Path:
    path.write_bytes(b"%PDF-1.4 stub\n")
    return path


def test_env_precedence_wins(guard_no_claude, isolated_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    env_dir = tmp_path / "env-apps"
    env_dir.mkdir()
    # yaml would point at a different path if it were read, but CONFIG_PATH is fake.
    monkeypatch.setenv("GAJ_APPLICATIONS_PATH", str(env_dir))
    assert get_applications_path() == env_dir


def test_yaml_fallback_when_env_unset(
    guard_no_claude, isolated_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    yaml_dir = tmp_path / "yaml-apps"
    yaml_dir.mkdir()
    config_file = tmp_path / "config.yaml"
    config_file.write_text(f"applications_path: {yaml_dir}\n", encoding="utf-8")
    monkeypatch.setattr(config_mod, "CONFIG_PATH", config_file)
    assert get_applications_path() == yaml_dir


def test_default_fallback_when_env_and_yaml_unset(
    guard_no_claude, isolated_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    default_dir = tmp_path / "default-apps"
    default_dir.mkdir()
    monkeypatch.setattr(config_mod, "DEFAULT_APPLICATIONS_PATH", default_dir)
    assert get_applications_path() == default_dir


def test_default_path_constant_matches_spec():
    """The literal default path must match the plan's documented folder."""
    assert str(config_mod.DEFAULT_APPLICATIONS_PATH) == (
        "/Users/christianmartin/ANTIGRAVITY PROJECTS/OPERATION GETAJOB 2026/resume/applications"
    )


def test_config_error_when_resolved_path_missing(
    guard_no_claude, isolated_env: Path, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    monkeypatch.setenv("GAJ_APPLICATIONS_PATH", str(tmp_path / "does-not-exist"))
    with pytest.raises(ConfigError):
        get_applications_path()


def test_resume_only_bundle(guard_no_claude, tmp_path: Path):
    slug = "zillow--ml-engineer-agentic-ai"
    folder = _mk_slug_dir(tmp_path, slug)
    resume = _touch(folder / "Christian-Martin-Zillow-resume.pdf")

    bundle = resolve_pdfs(slug, applications_path=tmp_path)
    assert bundle.slug == slug
    assert bundle.resume == resume
    assert bundle.cover_letter is None
    assert bundle.combined is None


def test_cover_letter_only_bundle(guard_no_claude, tmp_path: Path):
    slug = "acme--backend-engineer"
    folder = _mk_slug_dir(tmp_path, slug)
    cover = _touch(folder / "Christian-Martin-Acme-cover-letter.pdf")

    bundle = resolve_pdfs(slug, applications_path=tmp_path)
    assert bundle.resume is None
    assert bundle.cover_letter == cover
    assert bundle.combined is None


def test_combined_only_bundle(guard_no_claude, tmp_path: Path):
    slug = "stripe--platform-eng"
    folder = _mk_slug_dir(tmp_path, slug)
    combined = _touch(folder / "Christian-Martin-Stripe-resume+coverletter.pdf")

    bundle = resolve_pdfs(slug, applications_path=tmp_path)
    assert bundle.resume is None
    assert bundle.cover_letter is None
    assert bundle.combined == combined


def test_all_three_bundle(guard_no_claude, tmp_path: Path):
    slug = "anthropic--ae"
    folder = _mk_slug_dir(tmp_path, slug)
    resume = _touch(folder / "Christian-Martin-Anthropic-resume.pdf")
    cover = _touch(folder / "Christian-Martin-Anthropic-cover-letter.pdf")
    combined = _touch(folder / "Christian-Martin-Anthropic-resume+coverletter.pdf")

    bundle = resolve_pdfs(slug, applications_path=tmp_path)
    assert bundle.resume == resume
    assert bundle.cover_letter == cover
    assert bundle.combined == combined


def test_combined_glob_does_not_match_resume_filename(guard_no_claude, tmp_path: Path):
    """Regression guard: resume glob must not swallow the combined file."""
    slug = "foo--role"
    folder = _mk_slug_dir(tmp_path, slug)
    resume = _touch(folder / "Christian-Martin-Foo-resume.pdf")
    combined = _touch(folder / "Christian-Martin-Foo-resume+coverletter.pdf")

    bundle = resolve_pdfs(slug, applications_path=tmp_path)
    assert bundle.resume == resume
    assert bundle.combined == combined


def test_missing_bundle_raises(guard_no_claude, tmp_path: Path):
    slug = "empty--role"
    _mk_slug_dir(tmp_path, slug)
    with pytest.raises(PDFBundleMissing):
        resolve_pdfs(slug, applications_path=tmp_path)


def test_missing_folder_raises(guard_no_claude, tmp_path: Path):
    with pytest.raises(PDFBundleMissing):
        resolve_pdfs("does-not-exist", applications_path=tmp_path)


def test_ambiguous_resume_raises(guard_no_claude, tmp_path: Path):
    slug = "dup--role"
    folder = _mk_slug_dir(tmp_path, slug)
    _touch(folder / "Christian-Martin-FooCo-resume.pdf")
    _touch(folder / "Christian-Martin-FooCorp-resume.pdf")
    with pytest.raises(PDFBundleAmbiguous):
        resolve_pdfs(slug, applications_path=tmp_path)
