# Norsk Lead Finder

Find Norwegian businesses by industry and size. Uses the free Bronnoysund registry API -- no API key, no rate limits.

## Install

```bash
pip install httpx
python lead_finder.py --industry 62 --min-employees 5 --max-employees 50 --municipality OSLO
```

## Usage

```bash
# Find IT companies in Oslo with 5-50 employees
python lead_finder.py --industry 62 --municipality OSLO

# Find construction companies in Bodo
python lead_finder.py --industry 41 --municipality BODO

# Export to CSV
python lead_finder.py --industry 62 --output leads.csv

# Common industry codes
# 62 -- IT og programvare
# 41 -- Bygg og anlegg
# 47 -- Detaljhandel
# 70 -- Konsulentvirksomhet
# 86 -- Helsetjenester
```

## Output

```
Company                     | Employees | Industry          | Municipality
----------------------------|-----------|-------------------|-------------
Acme Consulting AS          | 12        | IT og programvare | Oslo
Bergen Tech Solutions AS    | 28        | IT og programvare | Bergen
```

## Why

Bronnoysundregistrene has data on 1 million+ Norwegian businesses. It's free and open. Most people do not know it exists as an API.

Built by Nicholas Elvegaard.
