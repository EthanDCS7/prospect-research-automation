
from __future__ import annotations
import typer, os, csv
from rich import print as rprint
from rich.table import Table
from typing import Optional
from .config import load_config, AppConfig

app = typer.Typer(add_completion=False, help="Prospect Research Automation 2.1")

def _load_cfg(config: Optional[str], preset: Optional[str]) -> AppConfig:
    if preset:
        # look under configs/presets/{preset}.yaml
        cfg_path = os.path.join("configs", "presets", f"{preset}.yaml")
    else:
        cfg_path = config or os.path.join("configs", "defaults.yaml")
    cfg = load_config(cfg_path)
    return cfg

@app.command("presets")
def presets_list():
    """List available presets."""
    presets_dir = os.path.join("configs", "presets")
    if not os.path.isdir(presets_dir):
        rprint("[yellow]No presets directory found.[/yellow]")
        raise typer.Exit(0)
    table = Table(title="Presets")
    table.add_column("Name")
    table.add_column("File")
    for f in sorted(os.listdir(presets_dir)):
        if f.endswith(".yaml") or f.endswith(".yml"):
            name = os.path.splitext(f)[0]
            table.add_row(name, os.path.join(presets_dir, f))
    rprint(table)

@app.command()
def validate(config: Optional[str] = typer.Option(None, "--config", help="Path to config YAML"),
             preset: Optional[str] = typer.Option(None, "--preset", help="Preset name (without .yaml)")):
    """Validate a config or preset file."""
    cfg = _load_cfg(config, preset)
    rprint(f"[green]OK[/green] Loaded config: [bold]{cfg.name}[/bold] (min_headcount={cfg.min_headcount})")

@app.command()
def score(input: str = typer.Option(..., "--input", help="Input targets CSV"),
          output: str = typer.Option("data/outputs/shortlist.csv", "--output", help="Output CSV path"),
          top: int = typer.Option(100, "--top", help="Top N to export"),
          config: Optional[str] = typer.Option(None, "--config", help="Path to config YAML"),
          preset: Optional[str] = typer.Option(None, "--preset", help="Preset name (without .yaml)"),
          fallback_employees: Optional[int] = typer.Option(None, "--fallback-employees", help="If CSV lacks employees, use this number for preliminary scoring"),
          industry_col: str = typer.Option("industry_group", help="Column name for industry group if present"),
          region_col: str = typer.Option("region", help="Column name for region if present")):
    """
    Config-driven scoring. Reads bands/weights/boosts from YAML.
    Outputs contributions and an exclusion reason (if any).
    """
    from .scoring import compute_score

    cfg = _load_cfg(config, preset)

    # read records
    import csv, os
    rows_in = []
    with open(input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_in.append(row)

    rows_out = []
    for row in rows_in:
        industry_val = row.get(industry_col) or None
        region_val = row.get(region_col) or None
        composite, contribs, excl = compute_score(
            row=row,
            cfg=cfg,
            fallback_employees=fallback_employees,
            industry_group=industry_val,
            region=region_val,
            dq_score=10,  # placeholder until DQ module is wired
        )
        out = {
            "company_name": row.get("company_name", row.get("company_name_clean", "")),
            "postcode": row.get("postcode", ""),
            "industry_group": industry_val or "",
            "region": region_val or "",
            "composite_score": composite,
            "exclusion_reason": excl or "",
            **contribs,
        }
        rows_out.append(out)

    rows_out.sort(key=lambda r: (r["exclusion_reason"] != "", -r["composite_score"]))
    rows_out = rows_out[:top]

    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8") as f:
        fieldnames = list(rows_out[0].keys()) if rows_out else [
            "company_name","postcode","industry_group","region","composite_score","exclusion_reason",
            "size_contrib","fit_contrib","dq_contrib","industry_boost","region_boost"
        ]
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows_out)

    rprint(f"[green]Wrote shortlist:[/green] {output} (top {len(rows_out)})")

@app.callback()
def main():
    pass

if __name__ == "__main__":
    app()
