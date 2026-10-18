"""Paths and YAML config loading."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
CONFIGS = ROOT / "configs"
DATA = ROOT / "data"
INTERIM = DATA / "interim"
LLM_OUT = DATA / "llm"
HUMAN = DATA / "human"
PROCESSED = DATA / "processed"
REPORTS = ROOT / "reports"
FORM_XLSX = ROOT / "forms" / "DTI_Coder_Form_NCO2015.xlsx"
CORPUS_CSV = INTERIM / "nco2015_corpus.csv"

DIMENSIONS = ("D1", "D2", "D3", "D4", "D5")


def load_yaml(path: Path) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_rubric(path: Path | None = None) -> dict[str, Any]:
    rubric = load_yaml(path or CONFIGS / "rubric.yaml")
    ids = tuple(d["id"] for d in rubric["dimensions"])
    if ids != DIMENSIONS:
        raise ValueError(f"rubric dimensions must be {DIMENSIONS}, got {ids}")
    return rubric


def load_models(path: Path | None = None) -> dict[str, Any]:
    return load_yaml(path or CONFIGS / "models.yaml")


def model_settings(name: str, path: Path | None = None) -> dict[str, Any]:
    """Model entry merged over the defaults block."""
    cfg = load_models(path)
    if name not in cfg["models"]:
        raise KeyError(f"model '{name}' not in models.yaml; choose from {sorted(cfg['models'])}")
    return {"name": name, **cfg.get("defaults", {}), **cfg["models"][name]}
