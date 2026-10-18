"""Read filled human coder forms (one .xlsx per coder) into a long table."""

from __future__ import annotations

from pathlib import Path

import openpyxl
import pandas as pd

FORM_COLUMNS = {
    "NCO-2015 code": "nco2015",
    "Q1 Detail enough?": "q1_detail",
    "Q2 Basic digital operation": "D1",
    "Q3 Digital information processing": "D2",
    "Q4 Digital communication & collaboration": "D3",
    "Q5 Advanced / specialised digital tools": "D4",
    "Q6 Digital problem solving & content creation": "D5",
    "Q7 evidence for Q2": "D1_evidence",
    "Q7 evidence for Q3": "D2_evidence",
    "Q7 evidence for Q4": "D3_evidence",
    "Q7 evidence for Q5": "D4_evidence",
    "Q7 evidence for Q6": "D5_evidence",
    "Q8 confidence Q2": "D1_conf",
    "Q8 confidence Q3": "D2_conf",
    "Q8 confidence Q4": "D3_conf",
    "Q8 confidence Q5": "D4_conf",
    "Q8 confidence Q6": "D5_conf",
    "Q9 Overall (0–10)": "q9_overall",
    "Q10 Core / Supporting": "q10_core",
    "Q11 India today vs text": "q11_india_today",
    "Q12 Comment (optional)": "q12_comment",
}
NUMERIC = ["D1", "D2", "D3", "D4", "D5", "D1_conf", "D2_conf", "D3_conf", "D4_conf", "D5_conf", "q9_overall"]


def coder_id(path: Path) -> str:
    """Coder ID from Instructions!C6, falling back to the file name."""
    wb = openpyxl.load_workbook(path, read_only=True)
    try:
        value = wb["Instructions"]["C6"].value
    finally:
        wb.close()
    return str(value).strip() if value else path.stem


def read_coder_form(path: Path) -> pd.DataFrame:
    df = pd.read_excel(path, sheet_name="Coding", header=1, dtype=str)
    missing = set(FORM_COLUMNS) - set(df.columns)
    if missing:
        raise ValueError(f"{path.name}: missing columns {sorted(missing)}")
    df = df[list(FORM_COLUMNS)].rename(columns=FORM_COLUMNS)
    df = df[df["nco2015"].notna()]
    for col in NUMERIC:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    scored = df[["D1", "D2", "D3", "D4", "D5"]].notna().all(axis=1)
    df = df[scored].copy()
    df.insert(0, "coder_id", coder_id(path))
    return df.reset_index(drop=True)


def read_all(folder: Path) -> pd.DataFrame:
    files = sorted(p for p in folder.glob("*.xlsx") if not p.name.startswith("~$"))
    if not files:
        raise FileNotFoundError(f"no coder forms (*.xlsx) in {folder}")
    frames = [read_coder_form(p) for p in files]
    out = pd.concat(frames, ignore_index=True)
    if out.duplicated(["coder_id", "nco2015"]).any():
        raise ValueError("duplicate (coder_id, nco2015) rows: two files share a coder ID?")
    return out
