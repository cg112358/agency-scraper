# scraper/pipeline.py
import csv
from scraper.normalize import normalize_phone

def run_pipeline(provider, limit, out_path):
    lister = provider[""lister""]()
    parser = provider[""parser""]()

    rows = []
    for org, url in lister.iter_agencies(limit=limit):
        record = parser.extract_contact(org, url)
        phones = [normalize_phone(p) for p in (record.phones or []) if p]
        rows.append({
            ""organization"": record.organization,
            ""website"": record.website,
            ""address_line"": record.address_line or """",
            ""city"": record.city or """",
            ""state"": record.state or """",
            ""zip"": record.zip or """",
            ""phones"": "" ; "".join(phones),
            ""source"": record.source or """",
        })

    if not rows:
        rows = [{k: "" for k in (""organization"", ""website"", ""address_line"", ""city"", ""state"", ""zip"", ""phones"", ""source"")}]

    with open(out_path, ""w"", newline="""", encoding=""utf-8"") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
