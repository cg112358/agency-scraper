# providers/ca_post/parse.py
import re, time
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup
import usaddress

PHONE_RE = re.compile(r"""
(?:\+?1[\s\-.]?)?
(?:\(?\d{3}\)?[\s\-.]?)\d{3}[\s\-.]?\d{4}
""", re.VERBOSE)

CONTACT_HINTS = [
    "contact", "about", "directory", "staff", "police", "department", "city hall",
    "administration", "headquarters"
]

def fetch(url):
    r = requests.get(url, timeout=25, headers={"User-Agent":"Mozilla/5.0"})
    r.raise_for_status()
    return r

def find_candidate_links(soup, base):
    links = []
    for a in soup.select("a[href]"):
        text = (a.get_text(" ", strip=True) or "").lower()
        href = urljoin(base, a["href"])
        if any(k in text for k in CONTACT_HINTS):
            links.append(href)
    # Dedup while preserving order
    seen = set(); out = []
    for u in links:
        if u not in seen:
            seen.add(u); out.append(u)
    return out[:6]  # keep it small

def extract_contact_fields(soup):
    # phone
    phones = set()
    for text in soup.stripped_strings:
        for m in PHONE_RE.findall(text):
            phones.add(m)
    phones_norm = sorted({normalize_phone(p) for p in phones if p})

    # address (rough heuristic: look for postal cues)
    addr_block = None
    for cand in soup.select("address, footer, .contact, .footer, .vcard, [itemtype*='PostalAddress']"):
        txt = " ".join(cand.stripped_strings)
        if has_postal_cues(txt):
            addr_block = txt
            break
    address_line = city = state = zipc = ""
    if addr_block:
        try:
            tagged = usaddress.parse(addr_block)
            parts = group_usaddress(tagged)
            address_line = parts.get("AddressLine","")
            city        = parts.get("PlaceName","")
            state       = parts.get("StateName","")
            zipc        = parts.get("ZipCode","")
        except Exception:
            pass

    return {
        "phones": "; ".join(phones_norm) if phones_norm else "",
        "address_line": address_line,
        "city": city,
        "state": state,
        "zip": zipc
    }

def has_postal_cues(s):
    s = s.lower()
    return any(k in s for k in [" ca ", " california", " ave", " st ", " blvd", " rd ", " drive", " zip"])

def normalize_phone(p):
    digits = re.sub(r"\D","", p)
    if len(digits) == 10:
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    if len(digits) == 11 and digits[0] == "1":
        return f"({digits[1:4]}) {digits[4:7]}-{digits[7:11]}"
    return p  # fallback

def group_usaddress(tagged):
    # tagged: list of (token, label)
    d = {}
    addr = []
    for token, label in tagged:
        if label.endswith("AddressNumber") or "Street" in label or "USPSBox" in label or "Occupancy" in label or "Building" in label:
            addr.append(token)
        else:
            d[label] = (d.get(label,"") + " " + token).strip()
    if addr:
        d["AddressLine"] = " ".join(addr)
    return d

def deepen_one(agency):
    # agency: {"organization","website","source"}
    try:
        r = fetch(agency["website"])
        soup = BeautifulSoup(r.text, "lxml")
        # Try homepage first
        fields = extract_contact_fields(soup)
        source = agency["website"]

        # If weak, walk a few likely links
        if not fields["phones"] and not fields["address_line"]:
            for u in find_candidate_links(soup, agency["website"]):
                try:
                    r2 = fetch(u)
                    soup2 = BeautifulSoup(r2.text, "lxml")
                    f2 = extract_contact_fields(soup2)
                    if any(f2.values()):
                        fields = f2
                        source = u
                        break
                except Exception:
                    continue
                finally:
                    time.sleep(0.8)  # politeness

        return {
            "organization": agency["organization"],
            "website": canonical_domain(agency["website"]),
            **fields,
            "source": source
        }
    except Exception:
        return {
            "organization": agency["organization"],
            "website": canonical_domain(agency.get("website","")),
            "address_line": "", "city":"", "state":"", "zip":"", "phones":"", "source": agency.get("website","")
        }

def canonical_domain(url):
    try:
        netloc = urlparse(url).netloc
        scheme = urlparse(url).scheme or "https"
        return f"{scheme}://{netloc}"
    except Exception:
        return url
