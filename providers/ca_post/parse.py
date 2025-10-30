from __future__ import annotations

# stdlib
import json
import re
import time
from collections.abc import Iterable
from pathlib import Path
from urllib.parse import urljoin, urlparse, urlunparse

# third-party
import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import usaddress  # in requirements.txt

DATA_DIR = Path("data")
LOG_PATH = DATA_DIR / "scraper.log"
DATA_DIR.mkdir(parents=True, exist_ok=True)   # one-time ensure

BLOCKED_HOSTS = ("edgesuite.net", "akamai", "captcha")

def _log(line: str) -> None:
    with open(LOG_PATH, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")

# --- polite session with retries ---

def variants(u: str) -> list[str]:
    """Yield a couple of harmless URL variants to dodge simple 403 blocks."""
    try:
        p = urlparse(u)
    except Exception:
        return [u]

    outs = [u]

    # flip scheme http<->https
    if p.scheme in {"http", "https"}:
        flipped = p._replace(scheme=("https" if p.scheme == "http" else "http"))
        outs.append(urlunparse(flipped))

    # toggle www.
    host = p.netloc
    if host.startswith("www."):
        outs.append(urlunparse(p._replace(netloc=host[4:])))
    else:
        outs.append(urlunparse(p._replace(netloc="www." + host)))

    # de-dup while preserving order
    seen, uniq = set(), []
    for x in outs:
        if x not in seen:
            uniq.append(x); seen.add(x)
    return uniq

_session: requests.Session | None = None
def session() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        s.headers.update({
            "User-Agent": "agency-scraper/0.1 (+https://github.com/cg112358/agency-scraper)",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://post.ca.gov/le-agencies",
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

def extract_contacts(url: str, backoff: float = 0.0) -> dict[str, str]:
    """Fetch a single agency site and extract contact info (phones + addresses)."""
    start = time.time()
    print(f"   ↳ visiting {url}")
    time.sleep(0.3)
    resp = None
    # Ensure "data" directory exists once before any logging
    Path("data").mkdir(parents=True, exist_ok=True)

    resp = None
    for cand in variants(url)[:3]:
        try:
            if backoff:
                time.sleep(backoff)               # grace pause
            resp = session().get(cand, timeout=(5, 8))
            resp.raise_for_status()

            # blocked-hosts guard
            if any(h in resp.url for h in BLOCKED_HOSTS):
                elapsed = round(time.time() - start, 2)
                log_line = f"[BLOCKED] {url} ({elapsed}s) -> {resp.url}"
                print(f"   🧱 blocked by host ({resp.url}), skipping")
                _log(log_line)
                return {"source": url, "phones": ""}

            url = cand  # lock onto the working canonical URL
            break          

        except requests.exceptions.RequestException as e:
            print(f"   ⚠️ request failed for variant {cand}: {e}")
            continue

    if resp is None:
        print(f"   ⚠️ request failed for all variants")
        return {"source": url}

    soup = BeautifulSoup(resp.text, "lxml")

    # phones on the page
    phones = {normalize_phone(m.group()) for m in PHONE_RE.finditer(soup.get_text(" ", strip=True))}
    phones.discard("")

    # addresses via JSON-LD
    addrs = _jsonld_addresses(soup)
    best_addr = next(iter(addrs), None)

    # If no address on the landing page, follow one likely contact/about page
    if not best_addr:
        hits = _find_contact_urls(url, soup)
        for hit in hits[:1]:  # only one follow to stay polite
            try:
                if backoff:
                    time.sleep(backoff)
                resp2 = session().get(hit, timeout=(5, 8))
                resp2.raise_for_status()
                soup2 = BeautifulSoup(resp2.text, "lxml")

                # try JSON-LD on the contact page
                addrs2 = _jsonld_addresses(soup2)
                best_addr = next(iter(addrs2), None)

                # fallback: heuristic on the contact page
                if not best_addr:
                    chunks2 = [p.get_text(" ", strip=True)
                            for p in soup2.select("address, .footer, footer, .contact, p, li")]
                    for blob in chunks2[:40]:
                        guess2 = _heuristic_address(blob)
                        if guess2 and (guess2["address_line"] or guess2["city"] or guess2["zip"]):
                            best_addr = guess2
                            break

                if best_addr:
                    break  # we found something; stop following
            except requests.exceptions.RequestException:
                continue

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

    elapsed = round(time.time() - start, 2)
    print(f"   ✅ done in {elapsed}s\n")

    return data

def deepen_one(row: dict[str,str], backoff: float = 0.0) -> dict[str,str]:
    """Given a seed row with 'website', visit and enrich with contacts."""
    try:
        enriched = extract_contacts(row["website"])
    except Exception:
        # do not fail the pipeline — return row as-is
        return row
    out = dict(row)
    out.update(enriched)
    return out
