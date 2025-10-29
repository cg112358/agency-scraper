# cli.py
import argparse
from scraper.registry import PROVIDERS
from scraper.pipeline import run_pipeline

def main():
    p = argparse.ArgumentParser()
    p.add_argument(""--provider"", required=True, help=""e.g., ca_post"")
    p.add_argument(""--limit"", type=int, default=10)
    p.add_argument(""--out"", default=""data/raw/out.csv"")
    args = p.parse_args()

    provider = PROVIDERS.get(args.provider)
    if not provider:
        raise SystemExit(f""Unknown provider: {args.provider}"")
    run_pipeline(provider, args.limit, args.out)
    print(f""Done → {args.out}"")

if __name__ == ""__main__"":
    main()
