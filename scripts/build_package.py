"""Assemble the shareable paper package (folder + zip) from the repository and the project folder.

    python scripts/build_package.py [date]        # default: today

Everything needed to write the paper: results with explanations, figures, tables, data (no PLFS
microdata, no coder forms, no credentials), implementation details, the draft, and the code.
"""
import datetime as dt
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
PROJ = REPO.parent
DATE = sys.argv[1] if len(sys.argv) > 1 else dt.date.today().isoformat()
OUT = PROJ / f"DTI_Paper_Package_{DATE}"


def cp(src, dst_dir, name=None):
    src = Path(src)
    if not src.exists():
        print("  missing:", src)
        return
    d = OUT / dst_dir
    d.mkdir(parents=True, exist_ok=True)
    if src.is_dir():
        shutil.copytree(src, d / (name or src.name), dirs_exist_ok=True,
                        ignore=shutil.ignore_patterns("grf_input.csv", "*.parquet", "__pycache__"))
    else:
        shutil.copy2(src, d / (name or src.name))


if OUT.exists():
    shutil.rmtree(OUT)
OUT.mkdir()

# 01 results
for f in ["docs/RESULTS.md", f"docs/DTI_Results_and_Status_{DATE}.pdf"]:
    cp(REPO / f, "01_Results")
# 02 figures
cp(REPO / "paper/figures", "02_Figures", "figures")
cp(REPO / "docs/FIGURES_EXPLAINED.md", "02_Figures")
# 03 tables
for f in ["paper/tables_llm.md", "paper/tables_onet.md"]:
    cp(REPO / f, "03_Tables")
# 04 data
D = "04_Data"
for f in ["data/interim/nco2015_corpus.csv", "data/interim/nco2015_to_nco2004.csv", "data/processed/dti_occupation_nco2015.csv",
          "data/processed/dti_family4_nco2015.csv", "data/processed/dti_group3_nco2015.csv", "data/processed/dti_group3_nco2004.csv",
          "data/processed/keyword_baseline_nco2015.csv", "data/processed/llm_runs_long.csv",
          "data/processed/plfs_harmonised_dti_coverage.csv"]:
    cp(REPO / f, f"{D}/occupation_scores")
for f in ["data/interim/onet_corpus.csv", "data/interim/onet_to_isco08.csv", "data/processed/dti_llm_onet_onetsoc.csv",
          "data/processed/dti_llm_onet_isco4.csv", "data/processed/onet_measures_isco4.csv", "data/processed/onet_measures_onetsoc.csv",
          "data/processed/llm_runs_long_onet.csv"]:
    cp(REPO / f, f"{D}/onet")
for f in ["reports/pilot_comparison.csv", "reports/pilot_agreement.csv", "reports/stability_runs.csv", "reports/cross_model.csv",
          "reports/q9_vs_equal_weight.csv", "reports/unstable_occupations.csv", "data/interim/validation_200_seed1.csv",
          "data/interim/pilot_50_seed0.csv"]:
    cp(REPO / f, f"{D}/reliability")
cp(REPO / "reports/gap", D, "rq2_gap")
for k in ["econ_llm", "econ_llm_llama8b_gguf", "econ_onet"]:
    cp(REPO / "reports" / k, f"{D}/wage_results")
cp(REPO / "reports/run_log.csv", f"{D}/run_logs")
cp(REPO / "paper/figures/run_segments.csv", f"{D}/run_logs")
for p in sorted(q for q in (REPO / "data/llm").glob("*/*/*.jsonl") if q.parent.parent.name != "mock"):  # mock = pipeline test
    cp(p, f"{D}/llm_raw_outputs", f"{p.parent.parent.name}__{p.parent.name}__{p.name}")
cp(REPO / "docs/DATA_DICTIONARY.md", D)
# 05 paper
P = "05_Paper"
for f in ["paper/draft.md", "paper/DTI_paper_draft.docx", "docs/extended_abstract.docx", "docs/PAPER_GUIDE.md"]:
    cp(REPO / f, P)
for f in PROJ.glob("*.pdf"):
    if not f.name.startswith("DTI_"):
        cp(f, f"{P}/reference_papers")
# 06 implementation
I = "06_Implementation"
for f in ["docs/IMPLEMENTATION.md", "docs/decisions.md", "docs/SHAVAK.md", "docs/HANDOFF.md", "docs/PLFS_DATA_NOTES.md",
          "docs/DTI_Implementation_Plan_and_Questions.md", "docs/DTI_Human_Coder_Guide.pdf", "docs/DTI_Coder_Questions.pdf",
          "forms/DTI_Validation_Form_200.xlsx"]:
    cp(REPO / f, I)
cp(PROJ / "DTI_Implementation_Plan_and_Questions.pdf", I)
cp(REPO / "docs/examples", I, "examples")
for f in ["configs/rubric_strict.yaml", "configs/rubric.yaml", "configs/models.yaml", "configs/analysis.yaml",
          "configs/plfs.yaml", "configs/onet.yaml"]:
    cp(REPO / f, f"{I}/configs")
# 07 code (tracked files of the repository at HEAD, without raw O*NET/BLS downloads and generated outputs)
code = OUT / "07_Code" / "dti-india_source.zip"
code.parent.mkdir(parents=True, exist_ok=True)
paths = [p for p in subprocess.run(["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True).stdout.split("\n")
         if p and (p.startswith(("src/", "scripts/", "configs/", "paper/make_", "paper/build_", "paper/results_", "tests/"))
                   or p in ("pyproject.toml", "README.md", ".gitignore", ".gitattributes"))]
subprocess.run(["git", "archive", "--format=zip", "-o", str(code), "HEAD", *paths], cwd=REPO, check=True)

(OUT / "00_START_HERE.md").write_text(START := f"""# DTI paper package — {DATE}

Everything needed to write the paper "Measuring the Digital Task Intensity of Indian Occupations Using Large Language
Models: Evidence on Wage Premiums and Labour Market Inequality from PLFS" (Nair, Anand & Shome, Nirma University).
Internal to the author team — please do not circulate outside the group before publication.

## Read in this order

1. **`01_Results/RESULTS.md`** — every result so far (RQ1–RQ4), with a "Meaning" paragraph after each table,
   reviewer risks and what is pending. The PDF next to it is the formatted summary for the professors.
2. **`02_Figures/FIGURES_EXPLAINED.md`** — the 19 figures (PNG for Word, PDF for LaTeX): what each shows, how to read it,
   the takeaway and where it goes in the paper.
3. **`06_Implementation/IMPLEMENTATION.md`** — how everything was built and run (data, rubric, models, GPU runs with times,
   reliability, O*NET mapping, PLFS harmonisation, econometrics, ML). Basis for the Methods section.
4. **`05_Paper/`** — the current draft (`draft.md` / `.docx`), the submitted extended abstract, the writing guide and the
   reference papers.

## Folder map

| Folder | Contents |
|---|---|
| `01_Results/` | `RESULTS.md` (all results + explanations), results/status PDF |
| `02_Figures/` | `figures/` (fig01–fig19 as PNG + PDF, `figures_index.md`, `run_segments.csv`), `FIGURES_EXPLAINED.md` |
| `03_Tables/` | Paper tables generated from the results: `tables_llm.md` (India-specific DTI, Tables 1–11), `tables_onet.md` (O*NET-transferred) |
| `04_Data/` | `DATA_DICTIONARY.md` (every file and column) and the data: `occupation_scores/` (DTI for all 3,450 NCO occupations, families, groups, NCO text), `onet/`, `reliability/`, `rq2_gap/`, `wage_results/` (all regression outputs, three measures), `run_logs/` (one row per LLM call), `llm_raw_outputs/` (every model answer with rationale and evidence) |
| `05_Paper/` | Draft, extended abstract, `PAPER_GUIDE.md`, `reference_papers/` |
| `06_Implementation/` | `IMPLEMENTATION.md`, `decisions.md` (who decided what, and why), server notes, PLFS notes, implementation plan, coder guide and form, `configs/` (rubric, models, analysis settings), `examples/` (full prompt and a model answer) |
| `07_Code/` | Source code of the pipeline (`dti-india_source.zip`) |

## Key findings in one minute

- **RQ1:** the LLM (Qwen2.5-14B, strict "text only" rubric, 5 runs) is stable (ICC 0.70–0.84), grounded (87% of non-zero scores
  quote the official text) and a second LLM from another developer ranks occupation groups almost identically (ρ = 0.91).
  Half of NCO-2015 occupations score zero because their descriptions rarely mention digital work.
- **RQ2:** the same AI reads O*NET descriptions of matching occupations as ~2.5× as digital (1.18 vs 0.47 on 0–4); rankings agree
  (ρ = 0.68). Transferring O*NET overstates digital intensity, most for managers and white-collar work.
- **RQ3:** a 1-SD more digital occupation pays **4.1 log points** more within the same occupational division (SE 1.3; O*NET 5.7);
  robust across most checks; a conditional association, not a causal return (Oster δ = 0.34).
- **RQ4:** no premium below the median, ~21 at the 90th percentile; none for workers with at most primary education, informal
  regular jobs or casual work; larger for women but DTI explains none of the gender gap — a *digital-returns gap*.
- **ML check:** DoubleML with four learners gives 2.6–4.4; the best-fitting learner (gradient boosting) 3.3 (p = 0.02).

## Still open

- Human validation: no valid coder forms yet (three rounds rejected; see RESULTS.md 3.5).
- Wages are nominal (no CPI file); inflation absorbed by year-quarter fixed effects — add a CPI deflator or state this.
- Causal forest not run; conference format, page limit and deadline; professors' approval of the wage-model defaults.

## Not included, on purpose

PLFS microdata or any worker-level file (MoSPI terms), the human coder forms (personal data), server credentials.
All numbers can be regenerated from the code with the PLFS files from microdata.gov.in.
""", encoding="utf-8")

zip_path = shutil.make_archive(str(OUT), "zip", root_dir=OUT.parent, base_dir=OUT.name)
size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
print(f"folder {OUT} ({size / 1e6:.0f} MB), zip {zip_path} ({Path(zip_path).stat().st_size / 1e6:.0f} MB)")
