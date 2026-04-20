"""ATS fingerprinting for the apply pipeline.

Pure function: URL primary, optional DOM HTML as secondary signal for
iframe-embedded ATS on company career pages. No I/O, no network.
"""

from __future__ import annotations

from typing import Literal
from urllib.parse import urlparse


AtsKey = Literal["greenhouse", "ashby", "lever", "generic"]


def _url_match(url: str) -> AtsKey | None:
    """Return an AtsKey if the URL host/path matches a known ATS, else None."""
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    host = (parsed.hostname or "").lower()
    path = parsed.path or ""

    if host == "boards.greenhouse.io":
        return "greenhouse"
    if host.endswith(".greenhouse.io") and "/embed/job_app" in path:
        return "greenhouse"

    if host == "jobs.ashbyhq.com":
        return "ashby"
    if host.endswith("ashbyhq.com") and "/application" in path:
        return "ashby"

    if host == "jobs.lever.co":
        return "lever"

    return None


def _dom_match(dom_html: str) -> AtsKey | None:
    """Scan embedded DOM markers when the URL host is ambiguous."""
    if not dom_html:
        return None
    haystack = dom_html.lower()

    if 'id="grnhse_iframe"' in haystack or 'id="application_form"' in haystack or 'data-source="greenhouse"' in haystack:
        return "greenhouse"
    if "data-ashby-job-posting-id" in haystack or "ashby-embed" in haystack:
        return "ashby"
    if 'data-qa="lever-application"' in haystack or "posting-page" in haystack:
        return "lever"

    return None


def detect(url: str, dom_html: str | None = None) -> AtsKey:
    """Return the ATS key for a job URL.

    Primary signal: URL host/path.
    Secondary signal: optional dom_html for iframe-embedded ATS.
    Default: "generic".
    """
    key = _url_match(url)
    if key:
        return key
    if dom_html:
        key = _dom_match(dom_html)
        if key:
            return key
    return "generic"
