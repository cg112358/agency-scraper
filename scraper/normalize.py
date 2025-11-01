# scraper/normalize.py
import re

LABEL_NOISE = re.compile(r'^(about|contact|hours?|city(?:\s+news)?|community|election|press\s+room|pay)\b', re.I)
PHONE_RE = re.compile(r'\+?1?[\s().-]*\d{3}[\s().-]*\d{3}[\s().-]*\d{4}\b')
CA_ZIP_RE = re.compile(r'\b9\d{4}(?:-\d{4})?\b')
STREET_RE = re.compile(r'\b\d{1,6}\s+[\w .-]+(?:st|ave|av|blvd|rd|dr|ln|ct|pl|pkwy|hwy|way|terr|trl|cir)\b', re.I)

def norm(s: str) -> str:
    if s is None: return ""
    return " ".join(str(s).replace("\xa0"," ").replace("<br>"," ").replace("<br/>"," ").split()).strip()

def normalize_website(url: str) -> str:
    u = norm(url)
    if u.startswith("https://errors.edgesuite.net/"):
        return ""
    return u

def normalize_city(city: str, fallback_from_org: str = "") -> str:
    c = norm(city)
    if LABEL_NOISE.match(c): c = ""
    if not c and fallback_from_org:
        # "Auburn Police Department" -> "Auburn"
        m = re.match(r'^(.*?)\s+(Police Department|Sheriff\'s Office|County|City)\b', fallback_from_org, re.I)
        if m: c = m.group(1)
    return c

def looks_like_address(s: str) -> bool:
    s = norm(s)
    if not s: return False
    if s.lower().startswith(("http://","https://","www.")): return False
    if LABEL_NOISE.match(s): return False
    return bool(STREET_RE.search(s) or CA_ZIP_RE.search(s))

def normalize_address(addr: str) -> tuple[str, str, bool]:
    """
    Normalize and validate an address string.

    Returns:
        tuple[str, str, bool]:
            (normalized_address, zipcode, is_confident)
    """
    a = norm(addr)
    if not a:
        return "", "", False

    score = 0

    # weight signals that look like valid streets or zip codes
    if STREET_RE.search(a):
        score += 60
    m_zip = CA_ZIP_RE.search(a)
    if m_zip:
        score += 40

    accept = score >= 60
    zipcode = m_zip.group(0) if m_zip else ""

    # strip stray commas/spaces from the normalized address
    return a.strip(" ,"), zipcode, accept


def normalize_phones(phones: str) -> str:
    p = norm(phones)
    found = PHONE_RE.findall(p)
    return ", ".join(dict.fromkeys(found))  # dedupe preserving order

def clean_row(row: dict) -> dict:
    # basic fields
    org     = norm(row.get("organization", "")) or norm(row.get("name", ""))
    website = normalize_website(row.get("website", ""))
    city    = normalize_city(row.get("city", ""), fallback_from_org=org)

    # address
    addr_raw = row.get("address_line", "") or ""
    addr_norm, zipc, ok = normalize_address(addr_raw)
    street_block = addr_norm if ok else ""
    needs: list[str] = []
    if not ok:
        needs.append("address_low_conf")

    # if the scraper stuffed a URL into address_line, move it to website
    if addr_raw and addr_raw.strip().lower().startswith(("http://", "https://", "www.")) and not website:
        website = addr_raw

    # phones
    phones = normalize_phones(row.get("phones", ""))

    # final normalized row
    out = {
        "organization":  org,
        "website":       website,
        "address_line":  street_block,  # normalized street goes here
        "street_block":  street_block,  # keep for downstream logic
        "city":          city,
        "state":         "CA",
        "zip":           zipc,
        "country":       "US",
        "phones":        phones,
    }

    # optional review flags
    if needs:
        out["needs_review"] = ";".join(needs)
    if zipc and not str(zipc).startswith("9"):
        out["needs_review"] = (out.get("needs_review", "") + ";zip_not_CA_like").strip(";")

    return out


