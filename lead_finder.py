#!/usr/bin/env python3
"""
norsk-lead-finder -- Find Norwegian businesses via Bronnoysundregistrene API
No API key required. Free and open data.

Usage:
    python lead_finder.py --industry 62 --municipality OSLO
    python lead_finder.py --industry 62 --min-employees 5 --max-employees 50 --output leads.csv

Industry codes:
    62  - IT og programvare
    41  - Bygg og anlegg
    47  - Detaljhandel
    70  - Konsulentvirksomhet
    86  - Helsetjenester
    85  - Undervisning
    56  - Serveringsvirksomhet
"""

import argparse
import csv
import json
import sys
import time

try:
    import httpx
except ImportError:
    print("Error: httpx not installed. Run: pip install httpx")
    sys.exit(1)


BASE_URL = "https://data.brreg.no/enhetsregisteret/api/enheter"

INDUSTRY_NAMES = {
    "41": "Bygg og anlegg",
    "45": "Handel med motorkjoretoy",
    "47": "Detaljhandel",
    "56": "Serveringsvirksomhet",
    "62": "IT og programvare",
    "70": "Konsulentvirksomhet",
    "71": "Arkitekter og tekniske konsulenter",
    "72": "Forskning og utvikling",
    "73": "Reklame og markedsforing",
    "74": "Annen faglig virksomhet",
    "85": "Undervisning",
    "86": "Helsetjenester",
    "90": "Kunst og underholdning",
}


def fetch_companies(
    industry_code=None,
    municipality=None,
    min_employees=None,
    max_employees=None,
    limit=100,
):
    """Fetch companies from Bronnoysundregistrene API."""
    results = []
    page = 0
    page_size = min(limit, 100)
    fetched = 0

    print("Searching Bronnoysundregistrene...", file=sys.stderr)

    with httpx.Client(timeout=30.0) as client:
        while fetched < limit:
            params = {
                "page": page,
                "size": page_size,
                "sort": "navn,asc",
            }

            if industry_code:
                params["naeringskode"] = industry_code

            if municipality:
                params["kommunenavn"] = municipality.upper()

            if min_employees is not None:
                params["antallAnsatteStorre"] = min_employees - 1

            try:
                response = client.get(BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            except httpx.HTTPStatusError as e:
                print(f"HTTP error: {e.response.status_code}", file=sys.stderr)
                break
            except httpx.RequestError as e:
                print(f"Request error: {e}", file=sys.stderr)
                break
            except json.JSONDecodeError:
                print("Failed to parse API response.", file=sys.stderr)
                break

            embedded = data.get("_embedded", {})
            companies = embedded.get("enheter", [])

            if not companies:
                break

            for company in companies:
                if fetched >= limit:
                    break

                employees = company.get("antallAnsatte")

                # Filter by employee count client-side for accuracy
                if min_employees is not None and (employees is None or employees < min_employees):
                    continue
                if max_employees is not None and (employees is None or employees > max_employees):
                    continue

                nace = company.get("naeringskode1", {}) or {}
                industry_desc = nace.get("beskrivelse", "")
                industry_num = nace.get("kode", "")

                adresse = company.get("forretningsadresse", {}) or {}
                municipality_name = adresse.get("kommune", "") or ""
                postal_code = adresse.get("postnummer", "") or ""
                city = adresse.get("poststed", "") or ""
                org_form_obj = company.get("organisasjonsform", {}) or {}

                results.append({
                    "name": company.get("navn", ""),
                    "org_number": company.get("organisasjonsnummer", ""),
                    "employees": employees if employees is not None else "",
                    "industry_code": industry_num,
                    "industry": industry_desc,
                    "municipality": municipality_name,
                    "postal_code": postal_code,
                    "city": city,
                    "org_form": org_form_obj.get("beskrivelse", ""),
                    "founded": company.get("stiftelsesdato", "") or "",
                    "website": company.get("hjemmeside", "") or "",
                    "url": f"https://www.brreg.no/finn-foretak/oppslag/?orgNr={company.get('organisasjonsnummer', '')}",
                })
                fetched += 1

            page_info = data.get("page", {})
            total_pages = page_info.get("totalPages", 0)
            print(f"  Page {page + 1}/{total_pages} -- {fetched} companies collected", file=sys.stderr)

            if page >= total_pages - 1:
                break

            page += 1
            time.sleep(0.1)  # be polite to the API

    return results


def print_table(companies):
    """Print companies as a formatted table."""
    if not companies:
        print("No companies found.")
        return

    col_name = min(max((len(c["name"]) for c in companies), default=30), 45)
    col_name = max(col_name, 30)
    col_emp = 10
    col_industry = min(max((len(c["industry"]) for c in companies), default=16), 28)
    col_industry = max(col_industry, 16)
    col_muni = max((len(c["municipality"]) for c in companies), default=12)
    col_muni = max(col_muni, 12)

    header = (
        f"{'Company':<{col_name}} | {'Employees':<{col_emp}} | "
        f"{'Industry':<{col_industry}} | {'Municipality':<{col_muni}}"
    )
    separator = "-" * len(header)

    print(f"\nFound {len(companies)} companies:\n")
    print(header)
    print(separator)

    for c in companies:
        name = c["name"][:col_name - 1] if len(c["name"]) > col_name else c["name"]
        emp = str(c["employees"]) if c["employees"] != "" else "N/A"
        industry = c["industry"][:col_industry - 1] if len(c["industry"]) > col_industry else c["industry"]
        muni = c["municipality"]
        print(f"{name:<{col_name}} | {emp:<{col_emp}} | {industry:<{col_industry}} | {muni:<{col_muni}}")

    print(separator)
    print(f"Total: {len(companies)} companies")


def export_csv(companies, filepath):
    """Export companies to CSV."""
    if not companies:
        print("No companies to export.")
        return

    fieldnames = [
        "name", "org_number", "employees", "industry_code",
        "industry", "municipality", "postal_code", "city",
        "org_form", "founded", "website", "url"
    ]

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(companies)

    print(f"\nExported {len(companies)} companies to {filepath}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Find Norwegian businesses via Bronnoysundregistrene API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python lead_finder.py --industry 62 --municipality OSLO
  python lead_finder.py --industry 62 --min-employees 5 --max-employees 50
  python lead_finder.py --industry 41 --municipality BODO --output leads.csv
  python lead_finder.py --industry 70 --limit 200

Industry codes:
  62  IT og programvare          70  Konsulentvirksomhet
  41  Bygg og anlegg             71  Arkitekter/tekniske konsulenter
  47  Detaljhandel               72  Forskning og utvikling
  56  Serveringsvirksomhet       73  Reklame og markedsforing
  85  Undervisning               86  Helsetjenester
        """
    )
    parser.add_argument("--industry", "-i", type=str,
                        help="NACE industry code (e.g. 62 for IT, 41 for construction)")
    parser.add_argument("--municipality", "-m", type=str,
                        help="Municipality name (e.g. OSLO, BERGEN, BODO)")
    parser.add_argument("--min-employees", type=int, default=None,
                        help="Minimum number of employees")
    parser.add_argument("--max-employees", type=int, default=None,
                        help="Maximum number of employees")
    parser.add_argument("--limit", "-l", type=int, default=100,
                        help="Maximum number of results (default: 100)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Export results to CSV file (e.g. leads.csv)")
    parser.add_argument("--json", action="store_true",
                        help="Output raw JSON instead of table")
    return parser.parse_args()


def main():
    args = parse_args()

    if not args.industry and not args.municipality:
        print("Warning: no filters specified -- this will return a broad result set.", file=sys.stderr)
        print("Use --industry and/or --municipality to narrow results.\n", file=sys.stderr)

    companies = fetch_companies(
        industry_code=args.industry,
        municipality=args.municipality,
        min_employees=args.min_employees,
        max_employees=args.max_employees,
        limit=args.limit,
    )

    if args.json:
        print(json.dumps(companies, ensure_ascii=False, indent=2))
        return

    print_table(companies)

    if args.output:
        export_csv(companies, args.output)


if __name__ == "__main__":
    main()
