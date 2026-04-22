"""Cover letter pattern chooser + HTML-to-plaintext extractor.

Three cover-letter attachment patterns:

  separate  - resume PDF + cover letter PDF upload into two file inputs
  combined  - resume+coverletter PDF upload into one file input
  text      - resume PDF upload; cover letter pasted as plaintext

The human picks per-ATS at the pre-upload gate. No LLM in any path;
extract_plaintext is a pure BeautifulSoup call.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Literal, Optional

from bs4 import BeautifulSoup

from .pdf_resolver import PDFBundle


Pattern = Literal["separate", "combined", "text"]
PATTERNS: tuple[Pattern, ...] = ("separate", "combined", "text")


def available_patterns(bundle: PDFBundle, cover_html_path: Optional[Path]) -> list[Pattern]:
    """Return only the patterns the bundle + assets actually support.

    separate requires both resume and cover_letter PDFs.
    combined requires the combined PDF.
    text requires a resume PDF and the source HTML for paste-back.
    """
    out: list[Pattern] = []
    if bundle.resume is not None and bundle.cover_letter is not None:
        out.append("separate")
    if bundle.combined is not None:
        out.append("combined")
    if bundle.resume is not None and cover_html_path is not None and cover_html_path.is_file():
        out.append("text")
    return out


def choose_pattern(
    bundle: PDFBundle,
    cover_html_path: Optional[Path] = None,
    *,
    input_fn=input,
    output=sys.stdout,
) -> Pattern:
    """Prompt the human to pick an attachment pattern.

    input_fn / output are injected for testing. Production calls use
    built-in input() and sys.stdout.
    """
    options = available_patterns(bundle, cover_html_path)
    if not options:
        raise ValueError(
            "no attachment patterns available for this bundle; "
            "need resume+cover-letter PDFs, a combined PDF, or a resume PDF + cover HTML"
        )

    print("Cover letter attachment patterns:", file=output)
    for idx, name in enumerate(options, start=1):
        print(f"  [{idx}] {name}", file=output)
    print(f"Select (1-{len(options)} or name): ", file=output, end="", flush=True)
    raw = input_fn().strip().lower()

    if raw.isdigit():
        i = int(raw)
        if 1 <= i <= len(options):
            return options[i - 1]
        raise ValueError(f"invalid index {i}; expected 1-{len(options)}")

    for name in options:
        if raw == name:
            return name
    raise ValueError(
        f"invalid pattern {raw!r}; expected one of: {', '.join(options)}"
    )


_BLANK_RUN = re.compile(r"\n{3,}")


def extract_plaintext(html_path: Path) -> str:
    """Strip the HTML to plaintext for paste-back.

    Drops <style>/<script>, preserves paragraph breaks via get_text(sep='\\n\\n'),
    and collapses 3+ consecutive newlines to 2 so the paste is clean.
    """
    raw = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(raw, "html.parser")
    for tag in soup(["style", "script"]):
        tag.decompose()
    text = soup.get_text(separator="\n\n")
    text = _BLANK_RUN.sub("\n\n", text)
    return text.strip() + "\n"
