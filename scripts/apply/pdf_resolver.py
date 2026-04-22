"""Resolve resume / cover letter / combined PDFs for a job slug.

Glob-based lookup under `<applications_path>/<slug>/`:

    Christian-Martin-*-resume.pdf              -> bundle.resume
    Christian-Martin-*-cover-letter.pdf        -> bundle.cover_letter
    Christian-Martin-*-resume+coverletter.pdf  -> bundle.combined

Glob rather than slug-to-Company derivation because slug format varies
across pipeline history. Exactly 0 or 1 file per type is expected;
2+ raises PDFBundleAmbiguous so drift is loud.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from .config import get_applications_path


@dataclass
class PDFBundle:
    """Resolved PDF paths for a slug. Any field may be None."""

    slug: str
    resume: Optional[Path]
    cover_letter: Optional[Path]
    combined: Optional[Path]


class PDFBundleMissing(Exception):
    """No PDFs matched for the slug."""


class PDFBundleAmbiguous(Exception):
    """More than one PDF of the same type matched the slug folder."""


_RESUME_GLOB = "Christian-Martin-*-resume.pdf"
_COVER_GLOB = "Christian-Martin-*-cover-letter.pdf"
_COMBINED_GLOB = "Christian-Martin-*-resume+coverletter.pdf"


def _match_one(folder: Path, pattern: str, label: str) -> Optional[Path]:
    matches = sorted(folder.glob(pattern))
    if not matches:
        return None
    if len(matches) > 1:
        raise PDFBundleAmbiguous(
            f"{label} pattern {pattern!r} matched {len(matches)} files in {folder}: {matches}"
        )
    return matches[0]


def resolve_pdfs(slug: str, applications_path: Optional[Path] = None) -> PDFBundle:
    """Find resume / cover letter / combined PDFs for the given slug.

    applications_path, when provided, overrides the env/yaml/default
    precedence handled by config.get_applications_path(). Tests pass a
    tmp_path; production calls with None.
    """
    base = applications_path if applications_path is not None else get_applications_path()
    slug_dir = base / slug
    if not slug_dir.is_dir():
        raise PDFBundleMissing(
            f"no application folder for slug {slug!r}: {slug_dir}"
        )

    # PDFBundleAmbiguous is intentionally allowed to propagate. Separating
    # combined from resume matters because Christian-Martin-*-resume.pdf
    # globs do NOT match Christian-Martin-*-resume+coverletter.pdf: the
    # literal `.pdf` anchor in the pattern forbids the `+coverletter` tail.
    resume = _match_one(slug_dir, _RESUME_GLOB, "resume")
    cover_letter = _match_one(slug_dir, _COVER_GLOB, "cover_letter")
    combined = _match_one(slug_dir, _COMBINED_GLOB, "combined")

    if resume is None and cover_letter is None and combined is None:
        raise PDFBundleMissing(
            f"no PDFs matched in {slug_dir} "
            f"(looked for {_RESUME_GLOB}, {_COVER_GLOB}, {_COMBINED_GLOB})"
        )

    return PDFBundle(
        slug=slug,
        resume=resume,
        cover_letter=cover_letter,
        combined=combined,
    )
