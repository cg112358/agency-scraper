from __future__ import annotations

from collections.abc import Iterator
from bs4 import BeautifulSoup
from bs4.element import Tag, AttributeValueList
from urllib.parse import urljoin
import requests
import re
SEED_URL = "https://post.ca.gov/le-agencies"

def iter_agency_links(limit: int | None = None) -> Iterator[dict[str, str]]:
    resp = requests.get(SEED_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # narrow the type of directory so .select is known
    directory: Tag = soup.select_one("#main-content") or soup
    anchors: list[Tag] = directory.select("a[href]")

    seen: set[tuple[str, str]] = set()

    for a in anchors:
        name = a.get_text(strip=True) or ""

        raw_href: str | AttributeValueList | None = a.get("href")  # bs4 typing
        if not isinstance(raw_href, str):
            continue
        href = raw_href

        # skip internal anchors / mailto
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        
        # clean and absolutize URL
        url = clean_href(href)
        url = urljoin(SEED_URL, url)

        # skip links that just bounce around POST
        if "post.ca.gov" in url:
            continue

        key = (name.lower(), url)
        if not name or key in seen:
            continue

        seen.add(key)
        yield {"organization": name, "website": url, "source": SEED_URL}

        if limit and len(seen) >= limit:
            break

HTTP_RE = re.compile(r"(https?://\S+)", re.IGNORECASE)

def clean_href(raw: str) -> str:
    """
    Some POST rows contain strings like:
      'http://old.example/https://new.example/'
    Keep the last full http(s):// URL; otherwise fall back to raw.
    """
    if not isinstance(raw, str):
        return ""
    raw = raw.strip()
    matches = HTTP_RE.findall(raw)
    if matches:
        return matches[-1].rstrip(").,;")  # trim common trailing punctuation
    return raw