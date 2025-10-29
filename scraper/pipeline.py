# scraper/pipeline.py
from providers.ca_post.list import iter_agency_links
from providers.ca_post.parse import deepen_one

def run_ca_post(limit: int = 5, deep: bool = False):
    """Seed agencies from CA POST and optionally deepen on each site."""
    seed = list(iter_agency_links(limit=limit))
    if not deep:
        return seed
    return [deepen_one(row) for row in seed]

__all__ = ["run_ca_post"]
