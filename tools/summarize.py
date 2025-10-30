"""Summarize a scraper run:
- computes success/failure rates (%)
- reports phone/address coverage
- accepts input CSV path and prints a one-line summary
"""

# tools/summarize.py
import sys, csv, re
from pathlib import Path

csv_path = Path(sys.argv[1])
rows = list(csv.DictReader(open(csv_path, encoding="utf-8")))
total = len(rows)
phones = sum(1 for r in rows if r.get("phones"))
addr   = sum(1 for r in rows if r.get("address_line"))
print(f"CSV: rows={total}, phones={phones/total:.0%}, addresses={addr/total:.0%}")

log = Path("data/scraper.log")
if log.exists():
    text = log.read_text(encoding="utf-8")
    blocked = len(re.findall(r"^\[BLOCKED\]", text, re.M))
    print(f"Log: BLOCKED={blocked}")


# Bash: run: python tools/summarize.py data/raw/ca_post_50.csv 
