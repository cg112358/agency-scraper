# scraper/browser.py
# (Optional Playwright fallback can go here later)
# scraper/browser.py
from dataclasses import dataclass
import requests

@dataclass
class FetchResult:
    url: str
    status: int
    text: str

def fetch(url: str, timeout: int = 20) -> FetchResult:
    r = requests.get(url, timeout=timeout, headers={"User-Agent":"agency-scraper/1.0"})
    return FetchResult(url=r.url, status=r.status_code, text=r.text)
