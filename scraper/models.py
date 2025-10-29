# scraper/models.py
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class Agency:
    organization: str
    website: str
    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    phones: List[str] = field(default_factory=list)
    source: Optional[str] = None
