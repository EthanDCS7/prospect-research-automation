# prospect_automation/scoring.py
from __future__ import annotations
from typing import Dict, Optional, Tuple


def _parse_int(val: str | int | float | None) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, (int, float)):
        return int(val)
    s = str(val).strip().replace(",", "")
    if not s:
        return None
    try:
        return int(float(s))
    except Exception:
        return None


def _band_score(value: Optional[int], bands: Dict[str, int]) -> int:
    if value is None:
        return 0
    # bands like {"0-19": 0, "20-49": 25, ...}
    for rng, pts in bands.items():
        lo_s, hi_s = rng.split("-")
        lo, hi = int(lo_s), int(hi_s)
        if lo <= value <= hi:
            return int(pts)
    return 0


def compute_score(
    *,
    row: Dict[str, str],
    cfg,
    fallback_employees: Optional[int] = None,
    industry_group: Optional[str] = None,
    region: Optional[str] = None,
    dq_score: int = 10,
) -> Tuple[int, Dict[str, int], Optional[str]]:
    """
    Returns (composite_score, contributions, exclusion_reason)
    """
    # employees from common columns; fall back if absent
    emp_val = None
    for k in ("employees", "employees_accounts", "headcount", "staff"):
        if k in row:
            emp_val = _parse_int(row.get(k))
            if emp_val is not None:
                break
    if emp_val is None:
        emp_val = fallback_employees

    exclusion_reason = None
    if emp_val is not None and emp_val < cfg.min_headcount:
        exclusion_reason = "below_min_headcount"

    size_points = _band_score(emp_val, cfg.scoring.bands.employees)

    industry_points = 0
    if industry_group and industry_group in cfg.scoring.boosts.industry:
        industry_points = int(cfg.scoring.boosts.industry[industry_group])

    region_points = 0
    if region and region in cfg.scoring.boosts.region:
        region_points = int(cfg.scoring.boosts.region[region])

    dq_points = max(0, min(10, int(dq_score)))

    base_components = {
        "size": size_points,
        "fit": industry_points + region_points,
        "dq": dq_points,
    }

    weighted = (
        base_components["size"] * cfg.scoring.weights.size
        + base_components["fit"] * cfg.scoring.weights.fit
        + base_components["dq"] * cfg.scoring.weights.dq
    )
    composite = int(round(weighted))

    contributions = {
        "size_contrib": int(round(base_components["size"] * cfg.scoring.weights.size)),
        "fit_contrib": int(round(base_components["fit"] * cfg.scoring.weights.fit)),
        "dq_contrib": int(round(base_components["dq"] * cfg.scoring.weights.dq)),
        "industry_boost": industry_points,
        "region_boost": region_points,
    }
    return composite, contributions, exclusion_reason
