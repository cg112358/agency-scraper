from __future__ import annotations

from urllib.parse import urljoin
from collections.abc import Iterable
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import re
import time
import requests
from bs4 import BeautifulSoup
import usaddress  # in requirements.txt

# --- polite session with retries ---
_session: requests.Session | None = None
def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "agency-scraper/0.1 (+https://github.com/cg112358/agency-scraper)"
        })
        a = HTTPAdapter(
            max_retries=Retry(
                total=2,              # was 3
                backoff_factor=0.2,
                status_forcelist=[429, 500, 502, 503, 504],
                allowed_methods=["GET", "HEAD"]
            )
        )
        s.mount("http://", a)
        s.mount("https://", a)
        _session = s
    return _session

PHONE_RE = re.compile(r"""
    (?:(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4})
""", re.VERBOSE)

def normalize_phone(p: str) -> str:
    digits = re.sub(r"\D", "", p)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"
    return p.strip()

def _jsonld_addresses(soup: BeautifulSoup) -> list[dict]:
    out: list[dict] = []
    for tag in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(tag.string or "")
        except Exception:
            continue
        # handle object or array
        candidates: Iterable = data if isinstance(data, list) else [data]
        for obj in candidates:
            addr = None
            if isinstance(obj, dict) and obj.get("@type") in {"Organization","LocalBusiness","GovernmentOffice","PoliceStation"}:
                addr = obj.get("address")
            if isinstance(addr, dict) and addr.get("@type") in {"PostalAddress","Address"}:
                out.append({
                    "address_line": " ".join(filter(None, [addr.get("streetAddress","").strip()])),
                    "city": addr.get("addressLocality","").strip(),
                    "zip": addr.get("postalCode","").strip(),
                })
    return out

def _heuristic_address(text: str) -> dict[str,str] | None:
    # usaddress tries its best on free text blobs
    try:
        tagged, _ = usaddress.tag(text)
    except Exception:
        return None
    line = " ".join(filter(None, [
        tagged.get("AddressNumber"),
        tagged.get("StreetNamePreDirectional"),
        tagged.get("StreetName"),
        tagged.get("StreetNamePostType"),
        tagged.get("OccupancyType"),
        tagged.get("OccupancyIdentifier"),
    ]))
    city = tagged.get("PlaceName","")
    zipcode = tagged.get("ZipCode","")
    if line or city or zipcode:
        return {"address_line": line, "city": city, "zip": zipcode}
    return None

def _find_contact_urls(base_url: str, soup: BeautifulSoup) -> list[str]:
    hits = []
    for a in soup.select('a[href]'):
        txt = (a.get_text() or "").strip().lower()
        href = a.get("href") or ""
        if not isinstance(href, str):
            continue
        if any(k in txt for k in ("contact","about","staff","directory")):
            hits.append(urljoin(base_url, href))
    return list(dict.fromkeys(hits))  # dedupe preserve order

def extract_contacts(url: str) -> dict[str, str]:
    """Fetch a single agency site and extract contact info (phones + addresses)."""
    time.sleep(0.3)  # polite delay, reduced from 0.6

    # --- main request with shorter connect/read timeouts ---
    r = session().get(url, timeout=(5, 8))  # (connect, read)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "lxml")

    # phones on the page
    phones = {normalize_phone(m.group()) for m in PHONE_RE.finditer(soup.get_text(" ", strip=True))}
    phones.discard("")

    # addresses via JSON-LD
    addrs = _jsonld_addresses(soup)
    best_addr = next(iter(addrs), None)

    # fallback: heuristic on visible text blocks
    if not best_addr:
        chunks = [p.get_text(" ", strip=True) for p in soup.select("address, .footer, footer, .contact, p, li")]
        for blob in chunks[:40]:
            guess = _heuristic_address(blob)
            if guess and (guess["address_line"] or guess["city"] or guess["zip"]):
                best_addr = guess
                break

    data = {
        "address_line": (best_addr or {}).get("address_line", ""),
        "city":         (best_addr or {}).get("city", ""),
        "zip":          (best_addr or {}).get("zip", ""),
        "phones":       "; ".join(sorted(phones)) if phones else "",
        "source":       url,
    }

    # --- follow contact/about pages only if needed ---
    if not data["phones"] or not data["address_line"]:
        for contact_url in _find_contact_urls(url, soup)[:2]:  # reduced from 3 → 2
            try:
                # shorter timeout for contact pages too
                c = session().get(contact_url, timeout=(5, 8))
                c.raise_for_status()
                contact_soup = BeautifulSoup(c.text, "lxml")

                # extract info again from the contact page
                contact_data = extract_contacts(contact_url)
            except Exception:
                continue

            # prefer filled fields
            for k in ("address_line", "city", "zip", "phones"):
                if not data.get(k) and contact_data.get(k):
                    data[k] = contact_data[k]

            if data["phones"] and data["address_line"]:
                break

    return data

def deepen_one(row: dict[str,str]) -> dict[str,str]:
    """Given a seed row with 'website', visit and enrich with contacts."""
    try:
        enriched = extract_contacts(row["website"])
    except Exception:
        # do not fail the pipeline — return row as-is
        return row
    out = dict(row)
    out.update(enriched)
    return out
