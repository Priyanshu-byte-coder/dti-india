# Runbook: from code to results

For whoever runs the pipeline on the Nirma GPU and with the PLFS microdata. Every step
is one command. Steps 1–4 need a GPU, step 5 needs a browser download, steps 6–8 need
PLFS. Steps already done in the repo are marked.

Open decisions that change configs are in [decisions.md](decisions.md); check them first.
PLFS data notes (rounds, quirks, weights): [PLFS_DATA_NOTES.md](PLFS_DATA_NOTES.md).

## 0. Setup

```bash
git clone https://github.com/Priyanshu-byte-coder/dti-india.git && cd dti-india
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,gpu]"          # GPU server; drop ",gpu" on a laptop
pytest                               # 32 tests, ~10 s
huggingface-cli login                # only for gated models (Llama)
```

## 1. Choose models (needs GPU spec)

Edit `configs/models.yaml`. Rough bf16 memory: 7–9B ≈ 18 GB, 27–32B ≈ 65 GB, 70B ≈ 140 GB.
Use two model families (cross-model agreement is part of RQ1). Keep `runs: 5`.

## 2. Pilot: 50 occupations, then freeze the prompt

```bash
# data/interim/pilot_50_seed0.csv is already in the repo
bash scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 1 --sample data/interim/pilot_50_seed0.csv
dti aggregate && dti reliability
```

Check:
- `reports/stability_runs.csv`: ICC across runs (target ≥ 0.9)
- `data/processed/dti_occupation_nco2015.csv`: `D*_ungrounded` should be near 0 (quotes not in the text)
- failed lines in `data/llm/<model>/<hash>/nco.jsonl` (`"ok": false`, see `errors`)
- read 10–15 rationales by hand

If the rubric or prompt changes, the prompt hash changes and outputs go to a new folder,
so pilot and final runs never mix. Once satisfied, **do not change `configs/rubric.yaml`**.

Decision pending (decisions.md, open item 1): strict text-only scoring may leave most
occupations at 0. Show the pilot's score distribution to the professors.

## 3. Full NCO corpus (3,450 occupations × 5 runs × each model)

```bash
bash scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 2      # tp = number of GPUs
bash scripts/run_scoring.sh llama8b meta-llama/Llama-3.1-8B-Instruct 8001 1
# or: sbatch scripts/score.sbatch qwen32b Qwen/Qwen2.5-32B-Instruct
dti aggregate                        # -> data/processed/dti_*  (NCO-2015 family/group + NCO-2004 group)
dti baseline
dti reliability                      # -> reports/
```

Interrupted? Run the same command again; only missing (occupation, run) pairs are scored.

## 4. O*NET corpus with the same prompt (RQ2)

```bash
dti onet-download                    # O*NET 31.0 + taxonomy crosswalk (also prints step 5)
dti onet-build                       # -> data/interim/onet_corpus.csv (923 occupations)
bash scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 2 --corpus onet
dti aggregate --corpus onet
```

## 5. BLS files (browser download — bls.gov blocks scripts)

Save as:
- `data/raw/bls/ISCO_SOC_Crosswalk.xls` from https://www.bls.gov/soc/ISCO_SOC_Crosswalk.xls
- `data/raw/bls/oews_national.xlsx`: the "National" XLSX from https://www.bls.gov/oes/tables.htm
  (latest May release; the file inside the zip named `national_M20xx_dl.xlsx`)

```bash
dti onet-build                       # now also writes ISCO-08 aggregates, weighted by US employment
dti aggregate --corpus onet
dti gap --model qwen32b              # -> reports/gap/
```

Check `reports/gap/unmatched_codes.json`: NCO-2015 families with no ISCO-08 match.

## 6. Human coders (RQ1)

Put each coder's filled `DTI_Coder_Form_NCO2015.xlsx` in `data/human/` (any file name;
the coder ID is read from the Instructions sheet), then `dti reliability` again →
`reports/human_vs_llm.csv`, `reports/alpha_multi_rater.csv`.

## 7. PLFS (all rounds)

1. From https://microdata.gov.in (PLFS collection) download the **seven annual July–June
   rounds**: 2017-18, 2018-19, 2019-20, 2020-21, 2021-22, 2022-23, 2023-24. Skip the
   calendar-year files (they repeat the same interviews) and the 2025 redesign files.
   Per round take the first-visit person file, first-visit household file, data layout
   and instruction manual. Put them under `data/raw/plfs/<round>/`.
2. In `configs/plfs.yaml`, for each round fill `files`, `format` and `columns` (raw column
   name for each standard name; see the comment at the top of the file). Religion and
   social group come from the household file: fill the round's `household:` block. For fixed-width
   files, make a layout CSV (`name,start,width`) from the round's data layout sheet.
3. Check every code list under `codes:` against that round's instruction manual
   (status, education, contract, social security).
4. Optional: `data/raw/cpi.csv` with columns `state, sector (rural/urban), year, cpi`.

Dry run first on synthetic data (fake rounds with a known premium built in):

```bash
dti synth-plfs --model qwen32b
dti plfs-build --config data/synthetic/plfs_synthetic.yaml --model qwen32b --out data/synthetic/plfs_harmonised.parquet
dti analysis --input data/synthetic/plfs_harmonised.parquet --out reports/econ_synthetic
```

Then the real data:

```bash
dti plfs-build --model qwen32b       # -> data/processed/plfs_harmonised.parquet + DTI coverage per round
dti analysis                         # -> reports/econ/
```

`plfs_harmonised_dti_coverage.csv` must show close to 100% of employed workers matched in
every round; unmatched occupation codes are listed there.

## 8. What `dti analysis` produces (reports/econ/)

| File | Content |
|---|---|
| `sample_summary.csv` | sample by round |
| `baseline.csv` | M1–M5 ladder; M4 = preferred (division FE) |
| `oster.csv` | Oster (2019) δ and β at δ = 1 |
| `robustness.csv` | unweighted, wild cluster bootstrap p, monthly earnings, regular/casual only, NCO-2015 vs NCO-2004 rounds, direct NCO-2004 links only, DTI quintiles, self-employed |
| `heckman.csv` | selection-corrected M4, all / men / women |
| `rif.csv`, `cqr.csv` | unconditional (RIF) and conditional quantile effects |
| `oaxaca.csv` | gender gap: explained (DTI's share) vs unexplained |
| `interactions.csv` | DTI × gender/rural/education/age/employment type; also with full occupation FE |
| `subgroups.csv` | M4 by subgroup |
| `dml_ate.csv`, `dml_blp.csv`, `dml_gate.csv` | DoubleML average effect, best linear projection, group effects |
| `grf_input.csv` | input for `Rscript scripts/grf_causal_forest.R` (causal forest; R not tested here) |

Skip slow steps with `--skip dml cqr`. Specification choices (sample, outcome, FE,
clustering, weights, heterogeneity list) are in `configs/analysis.yaml`, each marked
OPEN where the professors have not confirmed.
