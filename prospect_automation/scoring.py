from __future__ import annotations
from typing import Dict, Tuple, Optional

def _band_score(value: Optional[int], bands: Dict[str, int]) -> int:
    if value is None:
        return 0
    for rng, pts in bands.items():
        lo, hi = rng.split("-")
        lo, hi = int(lo), int(hi)
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
    - row: dict from CSV (may include 'employees' as int-like)
    - cfg: AppConfig
    """
    exclusion_reason = None

    # employees
    emp_val = None
    for k in ("employees", "employees_accounts", "headcount", "staff"):
        if k in row and str(row[k]).strip():
            try:
                emp_val = int(float(str(row[k]).replace(",", "")))
                break
            except Exception:
                pass
    if emp_val is None:
        emp_val = fallback_employees

    # min headcount exclusion
    if emp_val is not None and emp_val < cfg.min_headcount:
        exclusion_reason = "below_min_headcount"

    # size band
    size_points = _band_score(emp_val, cfg.scoring.bands.employees)

    # boosts
    industry_points = 0
    if industry_group and industry_group in cfg.scoring.boosts.industry:
        industry_points = int(cfg.scoring.boosts.industry[industry_group])

    region_points = 0
    if region and region in cfg.scoring.boosts.region:
        region_points = int(cfg.scoring.boosts.region[region])

    # DQ points (max 10 scaled by weight; we treat dq_score as 0-10 input)
    dq_points = max(0, min(10, dq_score))

    # phase 1: raw components before weights
    components = {
        "size": size_points,
        "fit": industry_points + region_points,
        "dq": dq_points,
    }

    # apply weights (weights sum not required to be 1)
    weighted = (
        components["size"] * cfg.scoring.weights.size
        + components["fit"] * cfg.scoring.weights.fit
        + components["dq"] * cfg.scoring.weights.dq
    )

    composite = int(round(weighted))

    contributions = {
        "size_contrib": int(round(components["size"] * cfg.scoring.weights.size)),
        "fit_contrib": int(round(components["fit"] * cfg.scoring.weights.fit)),
        "dq_contrib": int(round(components["dq"] * cfg.scoring.weights.dq)),
        "industry_boost": industry_points,
        "region_boost": region_points,
    }
    return composite, contributions, exclusion_reason
