# scraper/pipeline.py
from providers.ca_post.list import iter_agency_links
from providers.ca_post.parse import deepen_one

def run_ca_post(limit: int = 5, deep: bool = False, backoff: float = 0.0):
    seed = list(iter_agency_links(limit=limit))
    
    if not deep:
        return seed

    out = []
    total = len(seed)
    for i, row in enumerate(seed, 1):
        org = row.get("organization", "?")
        url = row.get("website", "?")
        print(f"[{i}/{total}] {org} → {url}")
        try:
            out.append(deepen_one(row, backoff=backoff))
        except Exception as e:
            print(f"   ! deep error: {e}")
            out.append(row)
    return out

