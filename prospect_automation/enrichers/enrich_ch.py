# prospect_automation/enrichers/enrich_ch.py
from __future__ import annotations
import csv
from typing import Dict, List, Optional
from ..api_clients.companies_house import CHClient
from ..api_clients import postcodes as pc_api


def load_sic_map(path: str) -> dict[str, str]:
    out = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out[row["sic_code"].strip()] = row["industry_group"].strip()
    return out

def map_sic_to_industry(sic_codes: list[str], sic_map: dict[str, str]) -> str | None:
    """
    Supports exact codes (e.g., 62020) and wildcard prefixes like '62*' or '30*'.
    Chooses the longest matching key (most specific).
    """
    best = None
    best_len = -1
    for code in sic_codes or []:
        code = (code or "").strip()
        # exact
        if code in sic_map and len(code) > best_len:
            best, best_len = sic_map[code], len(code)
        # wildcard prefixes
        for key, grp in sic_map.items():
            if key.endswith("*"):
                pref = key[:-1]
                if code.startswith(pref) and len(pref) > best_len:
                    best, best_len = grp, len(pref)
    return best

def enrich_row(row: Dict[str, str], ch: CHClient, sic_map: Dict[str, str]) -> Dict[str, str]:
    company_number = (row.get("company_number") or "").strip()
    company_name = row.get("company_name") or row.get("company_name_clean") or ""
    postcode = (row.get("postcode") or "").strip()

    # If no company number, search and pick best
    if not company_number and company_name:
        results = ch.search_companies(company_name, items_per_page=10)
        from .match import best_match
        match = best_match(results, company_name, postcode)
        if match:
            company_number = match.get("company_number") or company_number

    out = dict(row)
    out["company_number"] = company_number

    if not company_number:
        # nothing else to enrich
        out.update({
            "status": "",
            "company_type": "",
            "incorporation_date": "",
            "sic_codes": "",
            "industry_group": out.get("industry_group", "") or "",
            "registered_address": "",
            "region": out.get("region", "") or "",
        })
        return out

    profile = ch.get_company_profile(company_number)
    status = profile.get("company_status") or ""
    ctype = profile.get("type") or ""
    inc = profile.get("date_of_creation") or ""

    # Registered address + postcode
    addr = profile.get("registered_office_address") or {}
    reg_pc = " ".join([p for p in (addr.get("postal_code") or "").split()]).strip()
    out_pc = reg_pc or postcode

    # Region via postcodes.io (only if we have a postcode and no region yet)
    region = (out.get("region") or "").strip()
    if out_pc and not region:
        p = pc_api.lookup(out_pc)
        if p:
            region = p.get("region") or ""

    # SIC & industry
    sic_codes = profile.get("sic_codes") or []
    industry_group = (out.get("industry_group") or "").strip() or map_sic_to_industry(sic_codes, sic_map) or ""

    out.update({
        "status": status,
        "company_type": ctype,
        "incorporation_date": inc,
        "registered_address": " ".join([str(v) for v in addr.values() if v]).strip(),
        "postcode": out_pc or postcode,
        "region": region,
        "sic_codes": ",".join(sic_codes),
        "industry_group": industry_group,
    })
    return out


def enrich_file(input_csv: str, output_csv: str, sic_map_path: str, api_key: Optional[str] = None) -> int:
    # ✅ Pass the key through to the client
    ch = CHClient(api_key=api_key)
    sic_map = load_sic_map(sic_map_path)

    rows: List[Dict[str, str]] = []
    with open(input_csv, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    enriched: List[Dict[str, str]] = []
    for r in rows:
        enriched.append(enrich_row(r, ch, sic_map))

    if not enriched:
        return 0

    cols = [
        "company_name","company_number","status","company_type","incorporation_date",
        "sic_codes","industry_group","registered_address","postcode","region","domain"
    ]
    for k in rows[0].keys():
        if k not in cols:
            cols.append(k)

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(enriched)
    return len(enriched)
