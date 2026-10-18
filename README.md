# dti-india

Code for *Measuring the Digital Task Intensity of Indian Occupations Using Large Language
Models: Evidence on Wage Premiums and Labour Market Inequality from PLFS*
(Nair, Anand & Shome, Nirma University).

An LLM scores every NCO-2015 occupation description on five digital dimensions with a
fixed rubric. The scores are checked for stability, against human coders and against
O\*NET, combined into a Digital Task Intensity (DTI) index, and merged onto PLFS workers
by occupation code for the wage analysis.

## Status

| Stage | What | Status |
|---|---|---|
| 1 | NCO-2015 corpus (3,450 occupations) + NCO-2004 link | done: `dti corpus` |
| 2 | Rubric (5 dimensions, 0–4 anchors) shared by LLM and human coders | done: `configs/rubric.yaml` |
| 3 | LLM scoring on GPU via vLLM, repeated runs, evidence check | done: `dti score` — needs GPU run |
| 4 | Consensus, DTI, aggregation to NCO-2015 4/3-digit and NCO-2004 3-digit | done: `dti aggregate` |
| 5 | Reliability: run stability, cross-model, human vs LLM | done: `dti reliability` — needs data |
| 6 | Keyword baseline on NCO text | done: `dti baseline` |
| 7 | O\*NET: same-prompt LLM scoring of O\*NET text, conventional measures, ISCO-08 crosswalk, India–US gap (RQ2) | done: `dti onet-download`, `onet-build`, `score --corpus onet`, `gap` — needs GPU + 2 BLS files |
| 8 | PLFS harmonisation, all rounds (NCO-2004 and NCO-2015), wages, weights, DTI merge | done: `dti plfs-build` — needs microdata + column mapping |
| 9 | Wage models (RQ3–RQ4): FE ladder, Oster, robustness, wild bootstrap, Heckman, RIF/quantile, Oaxaca, interactions, DoubleML BLP/GATE, grf export | done: `dti analysis` — tested on synthetic data |

**Running it:** step-by-step runbook in [docs/HANDOFF.md](docs/HANDOFF.md).
Decisions taken and open questions: [docs/decisions.md](docs/decisions.md).

## Setup

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -e ".[dev]"          # laptop: everything except the GPU server
pip install -e ".[dev,gpu]"      # GPU server: adds vLLM
pytest
```

## Run

```bash
dti corpus                        # forms/DTI_Coder_Form_NCO2015.xlsx -> data/interim/
dti pilot --n 50                  # stratified prompt-development sample
dti prompt --codes 2512.0100      # print the exact messages sent for one occupation

# pipeline check without a GPU (keyword mock; not research data)
dti score --model mock --sample data/interim/pilot_50_seed0.csv --runs 3

dti aggregate                     # -> data/processed/
dti baseline
dti reliability                   # -> reports/  (reads data/human/*.xlsx if present)

# O*NET benchmark (RQ2)
dti onet-download && dti onet-build
dti score --model <m> --corpus onet && dti aggregate --corpus onet
dti gap --model <m>               # -> reports/gap/

# PLFS + wage models (RQ3-RQ4); dry run on synthetic data first
dti synth-plfs --model <m>
dti plfs-build --config data/synthetic/plfs_synthetic.yaml --model <m> --out data/synthetic/plfs_harmonised.parquet
dti analysis --input data/synthetic/plfs_harmonised.parquet --out reports/econ_synthetic
dti plfs-build --model <m> && dti analysis    # real data, after filling configs/plfs.yaml
```

### On the Nirma GPU server

```bash
# pilot first: 50 occupations x 5 runs
bash scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 1 --sample data/interim/pilot_50_seed0.csv
# full corpus once the prompt is frozen
bash scripts/run_scoring.sh qwen32b Qwen/Qwen2.5-32B-Instruct 8000 1
# or under SLURM (edit partition/env in the file first)
sbatch scripts/score.sbatch qwen32b Qwen/Qwen2.5-32B-Instruct
```

`run_scoring.sh` starts a vLLM OpenAI-compatible server, waits for it, runs `dti score`,
and stops the server. Models are configured in `configs/models.yaml`; any
OpenAI-compatible endpoint (including hosted APIs) works by changing `base_url`.
Gated models (Llama) need `huggingface-cli login` first.

Scoring is **resumable**: rerunning a command scores only missing or failed
(occupation, run) pairs.

## How the measurement is controlled

- **One rubric, two instruments.** The prompt is generated from `configs/rubric.yaml`,
  the same text the human coders get, with the same worked example (Accounts Clerk).
- **Prompt versioning.** Each output line records a hash of the prompt, example and
  schema. Outputs land in `data/llm/<model>/<prompt-hash>/`, so results from different
  prompt versions are never mixed. Freeze the prompt after the pilot.
- **Structured output.** The model must return JSON matching `src/dti/schema.py`
  (scores 0–4, confidence 1–3, Q1–Q12). Invalid output is retried, then logged as failed.
- **Evidence check.** Every quote the model gives as evidence is checked against the
  description. `D*_ungrounded` reports the share of runs citing words not in the text.
- **Stability runs.** Each occupation is scored `runs` times (default 5, seeds 0–4,
  temperature 0.7). Consensus = median per dimension; run SD flags occupations for
  manual review (`reports/unstable_occupations.csv`).

## Outputs

| File | Level | Use |
|---|---|---|
| `data/interim/nco2015_corpus.csv` | 8-digit occupation | scoring input |
| `data/interim/nco2015_to_nco2004.csv` | 8-digit occupation | NCO-2004 link with link type |
| `data/processed/dti_occupation_nco2015.csv` | 8-digit occupation | consensus scores + DTI |
| `data/processed/dti_family4_nco2015.csv` | NCO-2015 family | — |
| `data/processed/dti_group3_nco2015.csv` | NCO-2015 3-digit | merge onto PLFS from July 2021 |
| `data/processed/dti_group3_nco2004.csv` | NCO-2004 3-digit | merge onto PLFS before July 2021 |
| `reports/stability_runs.csv` | model x dimension | ICC, alpha across runs |
| `reports/human_vs_llm.csv` | pair x dimension | kappa, alpha, Spearman: human-human vs human-LLM |

**Read occupation codes as text** (`pd.read_csv(..., dtype=str)`): `1111.0100` read as a
number becomes `1111.01`.

## Data not in git

- `data/human/`: filled coder forms (coders' personal data) — share privately, drop the
  `.xlsx` files here to run `dti reliability`.
- `data/raw/`: O\*NET and BLS downloads, PLFS microdata (MoSPI terms do not allow redistribution).
- `data/llm/`, `data/processed/`, `data/synthetic/`, `reports/`: generated; reproducible from code + inputs.

Reference papers are cited in the plan document and are not stored here.

## Attribution

`data/interim/onet_corpus.csv` and the O\*NET measures are built from the O\*NET 31.0 Database by the U.S. Department of Labor, Employment and Training Administration (USDOL/ETA), used under the CC BY 4.0 license. USDOL/ETA has not approved, endorsed, or tested these modifications.
