
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
          preset: Optional[str] = typer.Option(None, "--preset", help="Preset name (without .yaml)")):
    """Stub scoring command: loads config, reads input, assigns dummy scores for now."""
    cfg = _load_cfg(config, preset)
    rows = []
    with open(input, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # For now: very simple placeholder scoring using min_headcount only.
            # We'll replace with real scoring once enrichment is implemented.
            employees = 50  # placeholder
            base = 40 if employees >= cfg.min_headcount else 5
            composite = base + int(10 * cfg.scoring.weights.fit) + int(10 * cfg.scoring.weights.dq)
            row_out = {
                "company_name": row.get("company_name", ""),
                "postcode": row.get("postcode", ""),
                "composite_score": composite,
                "exclusion_reason": "" if employees >= cfg.min_headcount else "below_min_headcount",
            }
            rows.append(row_out)
    rows = sorted(rows, key=lambda r: r["composite_score"], reverse=True)[:top]
    os.makedirs(os.path.dirname(output), exist_ok=True)
    with open(output, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    rprint(f"[green]Wrote shortlist:[/green] {output} (top {len(rows)})")

@app.callback()
def main():
    pass

if __name__ == "__main__":
    app()
