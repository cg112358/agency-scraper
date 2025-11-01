# scraper/extract.py
# (Shared helpers could live here later)
# scraper/extract.py
from bs4 import BeautifulSoup

def text_blocks(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for el in soup.select("main, article, .content, .page, body"):
        yield el.get_text(" ", strip=True)
