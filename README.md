# Agency-Scraper

### Reusable, provider-based scraper for public agency directories.
This scaffold includes a CA POST provider as an example.

**Agency-Scraper** is a modular Python program that collects and normalizes contact data from public-sector directories — starting with [CA POST](https://post.ca.gov/le-agencies).  
The system uses a provider-driven model, so each state or data source can plug in its own extraction logic while reusing a shared pipeline for parsing, cleaning, and output.

---

## 🚀 Features

- **Provider-based architecture:** easily add new data sources (`providers/ca_post`, `providers/wa_post`, etc.)
- **Deep contact scraping:** follows outbound agency links to capture address and phone details
- **Normalized CSV output:** ready for analysis, validation, or customer-specific audit pipelines
- **Extensible:** supports retry logic, rate limiting, and future SQLite or dashboard integrations

---

## 🧩 Tech Stack

- **Language:** Python 3.12  
- **Libraries:** `requests`, `beautifulsoup4`, `lxml`, `pandas`, `usaddress`  
- **CLI:** single-command runs via `cli.py`  

---

## ⚙️ Quick Start

                      

```bash
# clone repo
git clone https://github.com/cg112358/agency-scraper.git
cd agency-scraper

# set up environment
python -m venv .venv
. .venv/Scripts/activate       # Windows
pip install -r requirements.txt

# run a small sample
python cli.py --provider ca_post --limit 5 --out data/raw/sample.csv

# deep scrape with contacts
python cli.py --provider ca_post --limit 5 --deep --out data/raw/sample.csv
```

---

## 🧱 Architecture Overview

The project is structured around a **provider-based architecture** — each data source (e.g., `ca_post`) contains its own scraping logic while sharing a common pipeline for parsing, normalization, and output.

```text
agency-scraper/
├── providers/              # Source-specific scrapers (CA POST, others to come)
│   ├── ca_post/
│   │   ├── list.py         # Collects outbound agency links
│   │   ├── parse.py        # Visits agency sites, extracts contact info
│   │   └── provider.yaml
│   └── __init__.py
│
├── scraper/                # Shared pipeline utilities
│   ├── pipeline.py         # Entry point for provider execution
│   ├── normalize.py        # Cleans and formats phone/address data
│   ├── registry.py         # Manages provider registration
│   └── models.py
│
├── data/                   # Output storage
│   ├── raw/                # Unprocessed CSVs from runs
│   └── clean/              # Normalized outputs (future use)
│
├── cli.py                  # Command-line interface
├── requirements.txt
├── README.md
└── LICENSE
```
This structure makes it easy to plug in additional providers, debug in isolation, or extend the normalization pipeline without rewriting shared logic.

---

## 🧪 Testing & Debugging
### 🧭 Safe Testing

# Use small limits while testing new providers to stay polite to public servers:

```bash
python cli.py --provider ca_post --limit 5 --out data/raw/sample.csv
python cli.py --provider ca_post --limit 5 --deep --out data/raw/sample.csv
```
### These commands will:

- Fetch the first 5 agencies listed on the CA POST page
- Optionally follow each link (--deep) to collect address and phone data
- Output a normalized CSV in data/raw/

### 🧰 Debugging Tips

- If PermissionError appears, close the CSV file (Excel locks open files).
- If imports fail, clear stale bytecode:

```powershell
Get-ChildItem -Recurse -Directory -Filter __pycache__ | Remove-Item -Recurse -Force
Get-ChildItem -Recurse -Include *.pyc | Remove-Item -Force
```

- Add print statements or use VS Code breakpoints in providers/ca_post/parse.py for faster iteration.

---

## 🔄 Contributing & Future Enhancements

This project is actively evolving toward a **multi-provider scraping toolkit** for public agencies.

### Planned Enhancements
- Improve address and phone coverage via JSON-LD (`PostalAddress`) parsing  
- Add SQLite output option for relational queries  
- Integrate retry/fallback logic for broken or JS-heavy sites  
- Expand coverage beyond California (e.g., WA, TX)  
- Add CI tests to validate data completeness  

### Collaboration & Branching
- Work in a feature branch — e.g. `debug/contacts-extraction`  
- Commit incrementally with descriptive messages  
- Open a Pull Request into `main` after verifying sample output  
- Keep `main` deployable at all times  

---

## 🧭 Maintainer Notes

**Current maintainer:** Chris Galvez (`cg112358`)  
- Feel free to fork or reference this repo in portfolio materials.  
- Future versions may introduce an optional Flask dashboard for live scraping metrics.

