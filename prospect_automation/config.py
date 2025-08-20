
from __future__ import annotations
from pydantic import BaseModel, field_validator
from typing import Dict, List, Optional, Any
import yaml, os
from .utils.merge import deep_merge

class DQPenalties(BaseModel):
    postcode_invalid: int = 10
    sic_missing: int = 10
    duplicate: int = 15
    financials_outdated: int = 8

class DQConfig(BaseModel):
    fail_threshold: int = 60
    penalties: DQPenalties = DQPenalties()

class ScoringBands(BaseModel):
    employees: Dict[str, int]

class ScoringWeights(BaseModel):
    size: float = 0.6
    fit: float = 0.3
    dq: float = 0.1

class ScoringBoosts(BaseModel):
    industry: Dict[str, int] = {}
    region: Dict[str, int] = {}

class ScoringRecency(BaseModel):
    accounts_months_12: int = 5
    accounts_months_24: int = 2

class ScoringConfig(BaseModel):
    bands: ScoringBands
    weights: ScoringWeights = ScoringWeights()
    boosts: ScoringBoosts = ScoringBoosts()
    recency: ScoringRecency = ScoringRecency()

class ExclusionsConfig(BaseModel):
    statuses: List[str] = ["dissolved", "converted/closed"]
    company_types_blocklist: List[str] = []
    sic_blocklist_prefixes: List[int] = []

class ExportsConfig(BaseModel):
    business_view_columns: List[str] = []

class AppConfig(BaseModel):
    version: int = 1
    name: str = "defaults"
    extends: Optional[str] = None
    exclusions: ExclusionsConfig = ExclusionsConfig()
    min_headcount: int = 20
    scoring: ScoringConfig
    dq: DQConfig = DQConfig()
    exports: ExportsConfig = ExportsConfig()

    @field_validator('version')
    @classmethod
    def check_version(cls, v):
        if v != 1:
            raise ValueError("Only config version 1 is supported")
        return v

def _load_yaml(path: str) -> dict:
    with open(path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}

def resolve_path(base_path: str, rel: str) -> str:
    if os.path.isabs(rel):
        return rel
    return os.path.normpath(os.path.join(os.path.dirname(base_path), rel))

def load_config(path: str) -> AppConfig:
    raw = _load_yaml(path)
    if 'extends' in raw and raw['extends']:
        parent_path = resolve_path(path, raw['extends'])
        parent = _load_yaml(parent_path)
        merged = deep_merge(parent, raw)
    else:
        merged = raw
    return AppConfig.model_validate(merged)
