# providers/ca_post/list.py
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import requests

SEED_URL = "https://post.ca.gov/le-agencies"

def iter_agency_links(limit=None):
    resp = requests.get(SEED_URL, timeout=20)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "lxml")

    # This targets the main directory list (adjust if POST tweaks markup)
    # Try the most specific stable wrapper first; fall back to all anchors under the directory section.
    directory = soup.select_one("#main-content") or soup  # fallback
    anchors = directory.select("a[href]")

    seen = set()
    for a in anchors:
        name = (a.get_text(strip=True) or "")
        href = a.get("href", "")
        if not name or not href:
            continue
        # Only keep external agency links (skip internal POST anchors, mailto, etc.)
        if href.startswith("#") or href.startswith("mailto:"):
            continue
        url = urljoin(SEED_URL, href)
        # Heuristic: skip links that resolve to post.ca.gov
        if "post.ca.gov" in url:
            continue
        key = (name.lower(), url)
        if key in seen:
            continue
        seen.add(key)
        yield {"organization": name, "website": url, "source": SEED_URL}
        if limit and len(seen) >= limit:
            break
