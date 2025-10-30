# cli.py
import argparse
import csv
from scraper.pipeline import run_ca_post

print(">>> cli.py loaded:", __file__, flush=True)

# keep just these
COLS = [
    "organization",
    "website",
    "address_line",
    "city",
    "phones",]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--provider", required=True, choices=["ca_post"])
    ap.add_argument("--limit", type=int, default=5)
    ap.add_argument("--deep", action="store_true",
                help="visit each agency site to extract contacts")
    ap.add_argument("--backoff", type=float, default=0.0,
                help="sleep seconds between agency requests")
    ap.add_argument("--out", default="data/raw/sample.csv")
    args = ap.parse_args()

    if args.provider == "ca_post":
        rows = run_ca_post(limit=args.limit, deep=args.deep, backoff=args.backoff)

    
    with open(args.out, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in COLS})

    # quick summary
    total = len(rows)
    if total:
        have_phone = sum(1 for r in rows if r.get("phones"))
        have_addr  = sum(1 for r in rows if r.get("address_line"))
        print(f"Summary → rows={total}, phones={have_phone/total:.0%}, addresses={have_addr/total:.0%}")
    else:
        print("Summary → rows=0, phones=0%, addresses=0%")

        print(f"Done → {args.out}")

if __name__ == "__main__":
    main()


