# providers/ca_post/parse.py
import re, requests
from bs4 import BeautifulSoup
from scraper.models import Agency

PHONE_RE = re.compile(r""\(\d{3}\)\s*\d{3}-\d{4}"")

class CAPostParser:
    def extract_contact(self, name, website):
        try:
            r = requests.get(website, headers={""User-Agent"": ""Mozilla/5.0""}, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, ""lxml"")
            text = soup.get_text("" "", strip=True)

            phones = PHONE_RE.findall(text)
            address = """"
            m = re.search(r""\d{1,5}\s[\w\.\- ]+,\s?[A-Z][a-zA-Z\- ]+,\s?CA\s?\d{5}"", text)
            if m: address = m.group(0)

            return Agency(
                organization=name, website=website,
                address_line=address or None, city=None, state=""CA"", zip=None,
                phones=list(dict.fromkeys(phones)), source=""ca_post""
            )
        except Exception:
            return Agency(organization=name, website=website, source=""ca_post"")
