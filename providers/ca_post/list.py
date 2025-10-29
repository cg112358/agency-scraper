# providers/ca_post/list.py
import requests
from bs4 import BeautifulSoup

class CAPostLister:
    def __init__(self, seed=""https://post.ca.gov/le-agencies""):
        self.seed = seed

    def iter_agencies(self, limit=None):
        r = requests.get(self.seed, headers={""User-Agent"": ""Mozilla/5.0""}, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, ""lxml"")
        count = 0
        for a in soup.select(""a[href]""):
            href = (a.get(""href"") or """").strip()
            name = a.get_text(strip=True)
            if href.startswith(""http"") and name:
                yield name, href
                count += 1
                if limit and count >= limit:
                    break
