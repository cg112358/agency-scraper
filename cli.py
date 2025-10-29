# cli.py
import argparse
import csv
from scraper.pipeline import run_ca_post

COLS = [
    "organization", "website",
    "address_line", "city", "state", "zip",
    "phones", "source"
]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=["ca_post"])
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--deep", action="store_true",
                    help="visit each agency site to extract contacts")
    ap.add_argument("--out", default="data/raw/sample.csv")
    args = ap.parse_args()

    if args.provider == "ca_post":
        rows = run_ca_post(limit=args.limit, deep=args.deep)

    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})

    print(f"Done → {args.out}")

if __name__ == "__main__":
    main()
