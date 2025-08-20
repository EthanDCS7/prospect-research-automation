
# Prospect Research Automation 2.1

EB-focused, free-first enrichment + scoring with editable YAML presets.

## Quickstart

```bash
# 1) Create venv
python -m venv .venv && source .venv/bin/activate  # (Windows: .venv\Scripts\activate)

# 2) Install
pip install -e ".[dev]"

# 3) Run help
prospect --help

# 4) Try scoring with a preset (stubs for now)
prospect presets list
prospect score --preset pro_services_london --top 50 --input inputs/sample_targets.csv --output data/outputs/shortlist.csv
```

## Structure
- `prospect_automation/` – package and CLI
- `configs/` – defaults + presets (editable)
- `data/reference/` – SIC maps, exclusions
- `inputs/` – your target lists
- `data/outputs/` – exports/reports (git-ignored)

> This scaffold includes working config/preset loading & validation, 
> a deep-merge `extends` feature, and stub CLI commands for presets and scoring.
> Enrichment (Companies House, financials, web meta) will be added next.
