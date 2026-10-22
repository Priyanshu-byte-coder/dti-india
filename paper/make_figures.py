"""Figures for the paper and for describing the runs. Every figure is drawn from result files.

    python paper/make_figures.py [out_dir]          # default paper/figures

Writes each figure as PNG (300 dpi) and PDF (vector), plus figures_index.md with captions.
Colours: one fixed slot per measure everywhere — NCO-LLM / Qwen = blue, O*NET = orange,
second LLM (Llama) = aqua (validated palette; aqua is always paired with a legend/marker).
"""
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
R, P = ROOT / "reports", ROOT / "data" / "processed"
OUT = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "paper" / "figures"
OUT.mkdir(parents=True, exist_ok=True)

BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#ffffff"
C = {"qwen14b": BLUE, "llama8b_gguf": AQUA, "onet": ORANGE}
LAB = {"qwen14b": "Qwen2.5-14B (main)", "llama8b_gguf": "Llama-3.1-8B (second model)", "onet": "O*NET-transferred"}
D = ["D1", "D2", "D3", "D4", "D5"]
DIM = {"D1": "Basic digital operation", "D2": "Digital information processing", "D3": "Digital communication",
       "D4": "Specialised digital tools", "D5": "Digital problem solving / content"}
DIV = {"1": "Managers", "2": "Professionals", "3": "Technicians & assoc. prof.", "4": "Clerical support",
       "5": "Service & sales", "6": "Skilled agriculture", "7": "Craft & related trades",
       "8": "Plant & machine operators", "9": "Elementary occupations"}
IST = "Asia/Kolkata"

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10.5, "axes.titleweight": "bold",
    "axes.titlelocation": "left", "axes.labelsize": 9, "axes.labelcolor": INK2, "axes.edgecolor": GRID,
    "axes.linewidth": 0.8, "xtick.color": INK2, "ytick.color": INK2, "xtick.labelsize": 8, "ytick.labelsize": 8,
    "axes.grid": True, "grid.color": GRID, "grid.linewidth": 0.6, "axes.axisbelow": True,
    "axes.spines.top": False, "axes.spines.right": False, "legend.frameon": False, "legend.fontsize": 8,
    "figure.facecolor": SURF, "axes.facecolor": SURF, "text.color": INK, "savefig.bbox": "tight",
})
index = []


def legend_below(ax, ncol=3, y=-0.2):
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, y), ncol=ncol, frameon=False)


def save(fig, name, caption, source):
    for ext in ("png", "pdf"):
        fig.savefig(OUT / f"{name}.{ext}", dpi=300)
    plt.close(fig)
    index.append((name, caption, source))
    print("wrote", name)


def rd(*p):
    return pd.read_csv(R.joinpath(*p))


def coef(df, model, term="dti_std"):
    r = df[(df["model"] == model) & (df["term"] == term)]
    return None if r.empty else r.iloc[0]


# =================================================================== run figures
log = pd.read_csv(R / "run_log.csv", parse_dates=["timestamp_utc"])
log["t"] = log["timestamp_utc"].dt.tz_convert(IST)
log = log.sort_values("t")
RUBRIC = {"46a323537a": "strict", "8153504f69": "described-task"}


def segments(gap_min=20):
    """Contiguous scoring jobs: split each model × rubric × corpus stream at gaps > gap_min."""
    out = []
    for (m, pv, cp), g in log.groupby(["model_name", "prompt_version", "corpus"]):
        g = g.sort_values("t")
        cut = (g["t"].diff() > pd.Timedelta(minutes=gap_min)).cumsum()
        for _, s in g.groupby(cut):
            out.append({"model": m, "rubric": RUBRIC.get(pv, pv), "corpus": cp, "start": s["t"].min(), "end": s["t"].max(),
                        "calls": len(s), "ok": int(s["ok"].sum()), "tokens_in": int(s["prompt_tokens"].sum()),
                        "tokens_out": int(s["completion_tokens"].sum())})
    seg = pd.DataFrame(out).sort_values("start").reset_index(drop=True)
    seg["phase"] = np.where(seg["calls"] <= 250, "pilot", "full run")
    seg["hours"] = (seg["end"] - seg["start"]).dt.total_seconds() / 3600
    return seg


seg = segments()
seg.to_csv(OUT / "run_segments.csv", index=False)

# F1 timeline (Gantt)
fig, ax = plt.subplots(figsize=(8.6, 3.4))
rows = []
for r in seg.itertuples():
    corpus = "O*NET occupations" if r.corpus == "onet" else "NCO occupations"
    rows.append((f"{LAB[r.model].split(' (')[0]} · {corpus} · {r.rubric}" + (" (pilot)" if r.phase == "pilot" else ""), r))
for i, (lab, r) in enumerate(rows[::-1]):
    col = C[r.model] if r.corpus == "nco" else ORANGE
    ax.barh(i, (r.end - r.start).total_seconds() / 86400, left=mdates.date2num(r.start), height=0.55, color=col,
            alpha=0.55 if r.phase == "pilot" else 1.0, edgecolor=SURF, linewidth=1.5)
    extra = " (+250 from pilot)" if (r.phase == "full run" and r.corpus == "nco") else ""
    ax.text(mdates.date2num(r.end) + 0.01, i, f"{r.calls:,} calls{extra} · {r.hours:.1f} h", va="center", fontsize=7.5, color=INK2)
ax.set_yticks(range(len(rows)))
ax.set_yticklabels([lab for lab, _ in rows[::-1]], fontsize=7.5)
ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 6, 12, 18], tz=log["t"].dt.tz))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d Oct\n%H:%M", tz=log["t"].dt.tz))
ax.set_xlim(mdates.date2num(seg["start"].min()) - 0.05, mdates.date2num(seg["end"].max()) + 0.45)
ax.grid(axis="y", visible=False)
ax.set_title("LLM scoring runs on PARAM Shavak (Quadro GP100), 20–22 Oct 2026, IST")
save(fig, "fig01_run_timeline",
     "Timeline of every LLM scoring job (pilot runs lighter). Each bar runs from the first to the last completed call; label = calls and wall-clock hours.",
     "reports/run_log.csv")

# F2 cumulative progress of the three full runs
fig, ax = plt.subplots(figsize=(7.2, 3.4))
full = seg[seg["phase"] == "full run"]
for r in full.itertuples():
    g = log[(log["model_name"] == r.model) & (log["corpus"] == r.corpus) & (log["prompt_version"] == "46a323537a")
            & (log["t"] >= r.start) & (log["t"] <= r.end)]
    h = (g["t"] - r.start).dt.total_seconds() / 3600
    col = ORANGE if r.corpus == "onet" else C[r.model]
    tot = r.calls + (250 if r.corpus == "nco" else 0)
    name = f"{LAB[r.model].split(' (')[0]}, {'O*NET' if r.corpus == 'onet' else 'NCO'} ({tot:,} calls" + (", 250 from pilot)" if r.corpus == "nco" else ")")
    ax.plot(h, np.arange(1, len(g) + 1), color=col, lw=2, label=name)
    ax.annotate(f"{r.hours:.1f} h", (h.iloc[-1], len(g)), xytext=(4, 0), textcoords="offset points", fontsize=7.5, color=INK2, va="center")
ax.set_xlabel("Hours since the job started")
ax.set_ylabel("Completed LLM calls")
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:,.0f}"))
legend_below(ax, ncol=1, y=-0.18)
ax.set_title("Progress of the full scoring runs (0 failed calls)")
save(fig, "fig02_run_progress",
     "Cumulative completed calls for the three full runs; 3,450 NCO occupations × 5 runs per model and 923 O*NET occupations × 5 runs.",
     "reports/run_log.csv")

# F3 throughput (calls per hour, 30-min bins)
fig, ax = plt.subplots(figsize=(7.2, 3.2))
for r in full.itertuples():
    g = log[(log["model_name"] == r.model) & (log["corpus"] == r.corpus) & (log["prompt_version"] == "46a323537a")
            & (log["t"] >= r.start) & (log["t"] <= r.end)].set_index("t")
    rate = g["ok"].resample("30min").sum() * 2
    rate = rate.iloc[1:-1] if len(rate) > 2 else rate  # drop partial first/last bins
    col = ORANGE if r.corpus == "onet" else C[r.model]
    ax.plot(rate.index, rate.values, color=col, lw=2, marker="o", ms=3,
            label=f"{LAB[r.model].split(' (')[0]}, {'O*NET' if r.corpus == 'onet' else 'NCO'}: median {np.median(rate):.0f}/h")
ax.xaxis.set_major_locator(mdates.HourLocator(byhour=[0, 12], tz=log["t"].dt.tz))
ax.xaxis.set_major_formatter(mdates.DateFormatter("%d Oct\n%H:%M", tz=log["t"].dt.tz))
ax.set_ylabel("Completed calls per hour")
ax.set_ylim(bottom=0)
legend_below(ax, ncol=1, y=-0.22)
ax.set_title("Scoring throughput over time (30-minute bins)")
save(fig, "fig03_run_throughput",
     "Calls completed per hour. The 8B model is about 2.5× faster than the 14B model; O*NET prompts are longer (core tasks), so slower.",
     "reports/run_log.csv")

# F4 tokens processed
tok = seg[seg["phase"] == "full run"].copy()
fig, ax = plt.subplots(figsize=(6.4, 2.6))
labels = [f"{LAB[r.model].split(' (')[0]}, {'O*NET' if r.corpus == 'onet' else 'NCO'}" for r in tok.itertuples()]
y = np.arange(len(tok))
ax.barh(y + 0.18, tok["tokens_in"] / 1e6, height=0.34, color=BLUE, label="Prompt tokens (input)")
ax.barh(y - 0.18, tok["tokens_out"] / 1e6, height=0.34, color=ORANGE, label="Generated tokens (output)")
for yi, a, b in zip(y, tok["tokens_in"], tok["tokens_out"]):
    ax.text(a / 1e6 + 0.3, yi + 0.18, f"{a / 1e6:.1f} M", va="center", fontsize=7.5, color=INK2)
    ax.text(b / 1e6 + 0.3, yi - 0.18, f"{b / 1e6:.1f} M", va="center", fontsize=7.5, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels(labels)
ax.set_xlabel("Million tokens")
ax.grid(axis="y", visible=False)
ax.set_xlim(0, 35)
legend_below(ax, ncol=2)
ax.set_title("Tokens processed in the full runs")
save(fig, "fig04_run_tokens", "Input and output tokens per full run (llama.cpp usage counts).", "reports/run_log.csv")

# =================================================================== RQ1
pilot = rd("pilot_comparison.csv")
fig, axes = plt.subplots(1, 3, figsize=(8.6, 2.6), sharey=True)
order = [("qwen14b", "strict (v1.0)"), ("qwen14b", "described-task (v1.1)"), ("llama8b_gguf", "strict (v1.0)"),
         ("llama8b_gguf", "described-task (v1.1)")]
ylab = [f"{'Qwen' if m == 'qwen14b' else 'Llama'}, {rb.split(' (')[0]}" for m, rb in order]
for ax, (col, title, fmt) in zip(axes, [("share_all_zero", "Occupations all-zero", "{:.0%}"),
                                         ("icc_runs_median", "Run stability (median ICC)", "{:.2f}"),
                                         ("grounded_share", "Non-zero scores grounded", "{:.0%}")]):
    vals = [float(pilot[(pilot.model == m) & (pilot.rubric == rb)][col].iloc[0]) for m, rb in order]
    cols = [C[m] for m, _ in order]
    hatch = ["", "///", "", "///"]
    for i, (v, c, h) in enumerate(zip(vals, cols, hatch)):
        ax.barh(i, v, color=c, hatch=h, edgecolor=SURF, height=0.6)
        ax.text(v + 0.02, i, fmt.format(v), va="center", fontsize=7.5, color=INK2)
    ax.set_xlim(0, 1.15)
    ax.set_title(title, fontsize=9)
    ax.grid(axis="y", visible=False)
axes[0].set_yticks(range(4))
axes[0].set_yticklabels(ylab)
axes[0].invert_yaxis()
fig.suptitle("Pilot: 50 occupations × 5 runs, two models × two rubric readings (hatched = described-task)", x=0.01, ha="left",
             fontsize=10.5, fontweight="bold")
fig.tight_layout()
save(fig, "fig05_pilot", "Pilot comparison used to choose the strict rubric and Qwen as the main instrument.", "reports/pilot_comparison.csv")

stab = rd("stability_runs.csv")
fig, ax = plt.subplots(figsize=(6.6, 3.0))
y = np.arange(5)
for k, (m, off) in enumerate([("qwen14b", 0.19), ("llama8b_gguf", -0.19)]):
    s = stab[stab.model_name == m].set_index("dimension").loc[D]
    ax.barh(y + off, s["icc_2_1"], height=0.36, color=C[m], label=LAB[m], edgecolor=SURF)
    for yi, v in zip(y, s["icc_2_1"]):
        ax.text(v + 0.01, yi + off, f"{v:.2f}", va="center", fontsize=7.5, color=INK2)
ax.axvline(0.75, color=INK2, lw=0.8, ls="--")
ax.text(0.755, -0.75, "0.75 = 'good'", fontsize=7, color=INK2)
ax.set_yticks(y)
ax.set_yticklabels([DIM[d] for d in D])
ax.invert_yaxis()
ax.set_xlim(0, 1)
ax.set_xlabel("ICC(2,1) across five repeated runs (3,450 occupations)")
ax.grid(axis="y", visible=False)
legend_below(ax, ncol=2)
ax.set_title("RQ1 · Run-to-run stability by dimension", pad=14)
save(fig, "fig06_stability", "Intra-model stability: ICC(2,1) across the five runs at temperature 0.7, per dimension and model.",
     "reports/stability_runs.csv")

occ = pd.read_csv(P / "dti_occupation_nco2015.csv", dtype={"nco2015": str, "division": str})
occ["m"] = occ[D].mean(axis=1)
q = occ[occ.model_name == "qwen14b"]
dv = q.groupby("division").agg(mean=("m", "mean"), zero=("m", lambda s: (s == 0).mean()), n=("m", "size"))
dv = dv.sort_values("mean")
fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), sharey=True, gridspec_kw={"width_ratios": [1.3, 1]})
yy = np.arange(len(dv))
axes[0].barh(yy, dv["mean"], color=BLUE, height=0.62)
for yi, v in zip(yy, dv["mean"]):
    axes[0].text(v + 0.02, yi, f"{v:.2f}", va="center", fontsize=7.5, color=INK2)
axes[0].set_xlabel("Mean dimension score (0–4)")
axes[0].set_title("Mean NCO-LLM score", fontsize=9)
axes[1].barh(yy, dv["zero"], color="#86b6ef", height=0.62)
for yi, v in zip(yy, dv["zero"]):
    axes[1].text(v + 0.02, yi, f"{v:.0%}", va="center", fontsize=7.5, color=INK2)
axes[1].set_xlim(0, 1.12)
axes[1].set_xlabel("Share scoring 0 on every dimension")
axes[1].set_title("All-zero occupations", fontsize=9)
axes[0].set_yticks(yy)
axes[0].set_yticklabels([f"{d}. {DIV[d]} ({n})" for d, n in zip(dv.index, dv["n"])])
for a in axes:
    a.grid(axis="y", visible=False)
fig.suptitle("RQ1 · Digital task intensity of NCO-2015 occupations by division (Qwen2.5-14B, strict rubric)", x=0.01, ha="left",
             fontsize=10.5, fontweight="bold")
fig.tight_layout()
save(fig, "fig07_dti_by_division", "Mean score and all-zero share by NCO division (number of 8-digit occupations in brackets).",
     "data/processed/dti_occupation_nco2015.csv")

g3 = pd.read_csv(P / "dti_group3_nco2015.csv", dtype={"group3": str})
w = g3.pivot(index="group3", columns="model_name", values="dti_z").dropna()
rho = w.corr(method="spearman").iloc[0, 1]
fig, ax = plt.subplots(figsize=(4.4, 4.2))
ax.scatter(w["qwen14b"], w["llama8b_gguf"], s=26, color=BLUE, edgecolor=SURF, linewidth=1, zorder=3)
lim = [min(w.min()) - 0.3, max(w.max()) + 0.3]
ax.plot(lim, lim, color=INK2, lw=0.8, ls="--")
ax.set_xlim(lim)
ax.set_ylim(lim)
ax.set_xlabel("DTI (z), Qwen2.5-14B")
ax.set_ylabel("DTI (z), Llama-3.1-8B")
ax.text(0.03, 0.95, f"{len(w)} NCO-2015 3-digit groups\nSpearman ρ = {rho:.2f}", transform=ax.transAxes, va="top", fontsize=8.5)
ax.set_title("RQ1 · Two LLM families, same occupations")
save(fig, "fig08_cross_model", "Cross-model agreement at the 3-digit group level used in the PLFS wage models; dashed = equality.",
     "data/processed/dti_group3_nco2015.csv")

cm = rd("cross_model.csv")
fig, ax = plt.subplots(figsize=(6.4, 2.8))
items = D + ["q9_overall"]
cmi = cm.set_index("item").loc[items]
ax.barh(np.arange(6), cmi["kappa_quadratic"], color=BLUE, height=0.6)
for yi, v, e in zip(range(6), cmi["kappa_quadratic"], cmi["exact_agree"]):
    ax.text(v + 0.01, yi, f"κ {v:.2f} · exact {e:.0%}", va="center", fontsize=7.5, color=INK2)
ax.set_yticks(range(6))
ax.set_yticklabels([DIM.get(i, "Holistic score (Q9, 0–10)") for i in items])
ax.invert_yaxis()
ax.set_xlim(0, 1.15)
ax.set_xlabel("Quadratic-weighted κ, Qwen vs Llama (3,450 occupations)")
ax.grid(axis="y", visible=False)
ax.set_title("RQ1 · Agreement between the two LLMs per dimension")
save(fig, "fig09_cross_model_dims", "Occupation-level agreement between the two LLMs per dimension.", "reports/cross_model.csv")

# =================================================================== RQ2
gap = pd.read_csv(R / "gap" / "gap_dti_mean_score_llm.csv", dtype={"division": str})
corr = pd.read_csv(R / "gap" / "correlations.csv")
same = corr[corr.onet_measure == "dti_mean_score_onet"].iloc[0]
fig, ax = plt.subplots(figsize=(4.6, 4.3))
ax.scatter(gap["nco"], gap["onet"], s=18, color=ORANGE, edgecolor=SURF, linewidth=0.8, zorder=3, alpha=0.9)
ax.plot([0, 3.5], [0, 3.5], color=INK2, lw=0.8, ls="--")
ax.text(2.35, 2.1, "equal", fontsize=7.5, color=INK2, rotation=45)
ax.set_xlim(-0.1, 3.5)
ax.set_ylim(-0.1, 3.5)
ax.set_xlabel("Mean score from NCO-2015 text (0–4)")
ax.set_ylabel("Mean score from O*NET text (0–4)")
ax.text(0.97, 0.03, f"{int(same['n'])} NCO families · same LLM and rubric\nSpearman ρ = {same['spearman']:.2f}\n"
        f"mean: NCO {gap['nco'].mean():.2f} vs O*NET {gap['onet'].mean():.2f}", transform=ax.transAxes,
        va="bottom", ha="right", fontsize=8)
ax.set_title("RQ2 · Same instrument, Indian vs US descriptions")
save(fig, "fig10_rq2_scatter", "Each dot is an NCO-2015 family; points above the dashed line are read as more digital in O*NET than in NCO.",
     "reports/gap/gap_dti_mean_score_llm.csv")

gd = pd.read_csv(R / "gap" / "gap_dti_mean_score_llm_by_division.csv", dtype={"division": str}).sort_values("gap_raw_mean")
fig, ax = plt.subplots(figsize=(6.4, 3.0))
yy = np.arange(len(gd))
ax.barh(yy, gd["gap_raw_mean"], color=ORANGE, height=0.62)
for yi, v, n in zip(yy, gd["gap_raw_mean"], gd["gap_raw_count"]):
    ax.text(v + 0.02, yi, f"+{v:.2f}  ({n} families)", va="center", fontsize=7.5, color=INK2)
ax.set_yticks(yy)
ax.set_yticklabels([f"{d}. {DIV[d]}" for d in gd["division"]])
ax.set_xlim(0, 1.8)
ax.set_xlabel("DigitalGap = O*NET-text score − NCO-text score (0–4 scale)")
ax.grid(axis="y", visible=False)
ax.set_title("RQ2 · Where transferring O*NET overstates digital intensity")
save(fig, "fig11_rq2_gap_division", "Mean family-level DigitalGap by NCO division (same LLM and rubric on both texts).",
     "reports/gap/gap_dti_mean_score_llm_by_division.csv")

# =================================================================== RQ3
E = {"qwen14b": "econ_llm", "llama8b_gguf": "econ_llm_llama8b_gguf", "onet": "econ_onet"}
base = {k: rd(v, "baseline.csv") for k, v in E.items()}
fig, ax = plt.subplots(figsize=(7.0, 3.2))
ladder = ["M1", "M2", "M3", "M4"]
names = ["M1 no controls", "M2 + individual", "M3 + state, industry,\nyear-quarter FE", "M4 + division FE\n(preferred)"]
for k, off, mk in [("qwen14b", -0.2, "o"), ("llama8b_gguf", 0.0, "s"), ("onet", 0.2, "D")]:
    for i, m in enumerate(ladder):
        r = coef(base[k], m)
        ax.errorbar(i + off, 100 * r["coef"], yerr=196 * r["se"], fmt=mk, color=C[k], ms=6, capsize=0, lw=1.6,
                    label=LAB[k] if i == 0 else None)
    r4 = coef(base[k], "M4")
    ax.text(3 + off + 0.04, 100 * r4["coef"] + 2.5, f"{100 * r4['coef']:.1f}", fontsize=7.5, color=INK2, ha="center")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks(range(4))
ax.set_xticklabels(names, fontsize=7.8)
ax.set_ylabel("Log points per 1 SD of DTI (95% CI)")
ax.grid(axis="x", visible=False)
ax.legend(loc="upper right")
ax.set_title("RQ3 · Conditional digital occupational wage premium (PLFS 2017-18 to 2023-24)")
save(fig, "fig12_premium_ladder",
     "Coefficient on standardised DTI in ln real hourly wage, regular and casual workers 15–64, PLFS weights, SEs clustered by occupation.",
     "reports/econ_llm*/baseline.csv, reports/econ_onet/baseline.csv")

rob = {k: rd(v, "robustness.csv") for k, v in E.items()}
specs = [("M4 unweighted", "Unweighted"), ("M4 monthly earnings", "Monthly earnings"),
         ("M4 regular wage workers only", "Regular workers only"), ("M4 casual workers only", "Casual workers only"),
         ("M4 NCO-2015 rounds (Jul 2021+)", "NCO-2015 rounds (2021-24)"), ("M4 NCO-2004 rounds (pre Jul 2021)", "NCO-2004 rounds (2017-21)"),
         ("M4 NCO-2004 groups with >=75% direct links", "Direct NCO-2004 links only"),
         ("M4 self-employed (earnings incl. capital returns)", "Self-employed")]
fig, ax = plt.subplots(figsize=(6.8, 4.0))
yy = np.arange(len(specs) + 1)
for k, off, mk in [("qwen14b", -0.2, "o"), ("llama8b_gguf", 0.0, "s"), ("onet", 0.2, "D")]:
    vals = [coef(base[k], "M4")] + [coef(rob[k], s) for s, _ in specs]
    for yi, r in zip(yy, vals):
        if r is not None:
            ax.errorbar(100 * r["coef"], yi + off, xerr=196 * r["se"], fmt=mk, color=C[k], ms=5, lw=1.4,
                        label=LAB[k] if yi == 0 else None)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy)
ax.set_yticklabels(["Preferred M4"] + [lab for _, lab in specs])
ax.invert_yaxis()
ax.set_xlabel("Log points per 1 SD of DTI (95% CI)")
ax.grid(axis="y", visible=False)
legend_below(ax, ncol=3, y=-0.14)
ax.set_title("RQ3 · Robustness of the premium")
save(fig, "fig13_robustness", "Preferred specification and robustness checks for the three DTI measures.", "reports/econ_*/robustness.csv")

# =================================================================== RQ4
rif = {k: rd(E[k], "rif.csv") for k in ("qwen14b", "onet")}
fig, ax = plt.subplots(figsize=(6.4, 3.2))
for k, mk in [("qwen14b", "o"), ("onet", "D")]:
    d = rif[k].sort_values("quantile")
    x = 100 * d["quantile"]
    ax.fill_between(x, 100 * d["ci_low"], 100 * d["ci_high"], color=C[k], alpha=0.14, lw=0)
    ax.plot(x, 100 * d["coef"], color=C[k], lw=2, marker=mk, ms=6, label=LAB[k])
    ax.annotate(f"{100 * d['coef'].iloc[-1]:.1f}", (x.iloc[-1], 100 * d["coef"].iloc[-1]), xytext=(6, 0),
                textcoords="offset points", fontsize=7.5, color=INK2, va="center")
ax.axhline(0, color=INK2, lw=0.8)
ax.set_xticks([10, 25, 50, 75, 90])
ax.set_xlabel("Percentile of the hourly wage distribution")
ax.set_ylabel("Log points per 1 SD of DTI")
ax.legend(loc="upper left")
ax.set_title("RQ4 · Premium across the wage distribution (unconditional quantile, RIF)")
save(fig, "fig14_rif_quantiles", "RIF (unconditional quantile) regressions with 95% CI bands.", "reports/econ_llm/rif.csv, reports/econ_onet/rif.csv")

sg = {k: rd(v, "subgroups.csv") for k, v in E.items()}
groups = [("edu_band=up_to_primary", "Education: up to primary"), ("edu_band=middle_secondary", "Education: middle/secondary"),
          ("edu_band=tertiary", "Education: tertiary"), ("formal_ss=0.0", "Regular, no social security"),
          ("formal_ss=1.0", "Regular, with social security"), ("emp_type=casual", "Casual workers"),
          ("female=0", "Men"), ("female=1", "Women"), ("rural=0", "Urban"), ("rural=1", "Rural"),
          ("age_band=15-24", "Age 15–24"), ("age_band=45-54", "Age 45–54")]
fig, ax = plt.subplots(figsize=(6.8, 4.8))
yy = np.arange(len(groups))
for k, off, mk in [("qwen14b", -0.2, "o"), ("llama8b_gguf", 0.0, "s"), ("onet", 0.2, "D")]:
    for yi, (g, _) in zip(yy, groups):
        r = coef(sg[k], f"M4 | {g}")
        if r is not None:
            ax.errorbar(100 * r["coef"], yi + off, xerr=196 * r["se"], fmt=mk, color=C[k], ms=5, lw=1.4,
                        label=LAB[k] if yi == 0 else None)
for yb in [2.5, 5.5, 7.5, 9.5]:
    ax.axhline(yb, color=GRID, lw=0.8)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy)
ax.set_yticklabels([lab for _, lab in groups])
ax.invert_yaxis()
ax.set_xlabel("Log points per 1 SD of DTI (95% CI), M4 estimated within each group")
ax.grid(axis="y", visible=False)
legend_below(ax, ncol=3, y=-0.11)
ax.set_title("RQ4 · Who gains? Premium by group")
save(fig, "fig15_subgroups", "Preferred specification estimated separately for each group.", "reports/econ_*/subgroups.csv")

it = {k: rd(E[k], "interactions.csv") for k in ("qwen14b", "onet")}
terms = [("occupation FE + interactions", "dti_x_female", "Women vs men"), ("occupation FE + interactions", "dti_x_rural", "Rural vs urban"),
         ("occupation FE + interactions", "dti_x_edu_band_middle_secondary", "Middle/secondary vs ≤ primary"),
         ("occupation FE + interactions", "dti_x_edu_band_tertiary", "Tertiary vs ≤ primary"),
         ("occupation FE + interactions", "dti_x_emp_type_casual", "Casual vs regular"),
         ("occupation FE + formality interaction (regular)", "dti_x_formal_ss", "Formal vs informal (regular)")]
fig, ax = plt.subplots(figsize=(6.6, 3.1))
yy = np.arange(len(terms))
for k, off, mk in [("qwen14b", -0.15, "o"), ("onet", 0.15, "D")]:
    for yi, (m, t, _) in zip(yy, terms):
        r = coef(it[k], m, t)
        ax.errorbar(100 * r["coef"], yi + off, xerr=196 * r["se"], fmt=mk, color=C[k], ms=5, lw=1.4,
                    label=LAB[k] if yi == 0 else None)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy)
ax.set_yticklabels([lab for _, _, lab in terms])
ax.invert_yaxis()
ax.set_xlabel("Difference in the premium, log points (95% CI), within the same 3-digit occupation")
ax.grid(axis="y", visible=False)
legend_below(ax, ncol=2)
ax.set_title("RQ4 · Differences within occupations (DTI × group, occupation FE)")
save(fig, "fig16_interactions", "Interaction terms from models with full 3-digit occupation fixed effects.", "reports/econ_llm/interactions.csv")

ox = {k: rd(E[k], "oaxaca.csv").set_index("component")["value"] for k in ("qwen14b", "onet")}
comp = ["explained: dti", "explained: education", "explained: industry", "explained: age", "explained: state",
        "explained: occupation division", "unexplained"]
fig, ax = plt.subplots(figsize=(6.4, 3.0))
yy = np.arange(len(comp))
for k, off in [("qwen14b", -0.18), ("onet", 0.18)]:
    v = [100 * ox[k][c] for c in comp]
    ax.barh(yy + off, v, height=0.34, color=C[k], label=LAB[k], edgecolor=SURF)
for yi, c in zip(yy, comp):
    ax.text(max(100 * ox["qwen14b"][c], 100 * ox["onet"][c], 0) + 0.6, yi, f"{100 * ox['qwen14b'][c]:.1f}", va="center", fontsize=7.5, color=INK2)
ax.axvline(0, color=INK2, lw=0.8)
ax.set_yticks(yy)
ax.set_yticklabels([c.replace("explained: ", "Explained by ").replace("dti", "DTI").replace("unexplained", "Unexplained") for c in comp])
ax.invert_yaxis()
ax.set_xlabel(f"Log points of the {100 * ox['qwen14b']['total gap']:.1f}-point male–female wage gap")
ax.grid(axis="y", visible=False)
legend_below(ax, ncol=2)
ax.set_title("RQ4 · Oaxaca–Blinder: DTI explains almost none of the gender gap")
save(fig, "fig17_oaxaca", "Pooled Oaxaca–Blinder decomposition of the gender gap in ln hourly wages (selected components).",
     "reports/econ_llm/oaxaca.csv")

lr = {k: rd(E[k], "dml_learners.csv") for k in ("qwen14b", "onet")}
LN = {"linear": "Linear regression", "lasso": "Lasso (CV)", "random_forest": "Random forest", "gradient_boosting": "Gradient boosting"}
fig, axes = plt.subplots(1, 2, figsize=(8.4, 2.9), gridspec_kw={"width_ratios": [1.6, 1]}, sharey=True)
yy = np.arange(4)
for k, off, mk in [("qwen14b", -0.15, "o"), ("onet", 0.15, "D")]:
    d = lr[k].set_index("learner").loc[list(LN)]
    axes[0].errorbar(100 * d["coef"], yy + off, xerr=[100 * (d["coef"] - d["ci_low"]), 100 * (d["ci_high"] - d["coef"])],
                     fmt=mk, color=C[k], ms=5, lw=1.4, label=LAB[k])
    axes[1].barh(yy + off, d["r2_wage"], height=0.3, color=C[k], edgecolor=SURF)
    for yi, v in zip(yy, d["r2_wage"]):
        axes[1].text(v + 0.005, yi + off, f"{v:.3f}", va="center", fontsize=7, color=INK2)
axes[0].axvline(0, color=INK2, lw=0.8)
axes[0].set_yticks(yy)
axes[0].set_yticklabels(list(LN.values()))
axes[0].invert_yaxis()
axes[0].set_xlabel("Average effect, log points (95% CI, clustered by occupation)")
legend_below(axes[0], ncol=2, y=-0.24)
axes[1].set_xlim(0.45, 0.63)
axes[1].set_xlabel("Out-of-sample R², wage model")
for a in axes:
    a.grid(axis="y", visible=False)
fig.suptitle("ML check · Double/debiased ML with four learners", x=0.01, ha="left", fontsize=10.5, fontweight="bold")
fig.tight_layout()
save(fig, "fig18_dml_learners", "DoubleML partially linear model, 200,000-worker subsample, cluster-based cross-fitting; higher R² = better learner.",
     "reports/econ_*/dml_learners.csv")

ss = rd("econ_llm", "sample_summary.csv")
fig, ax = plt.subplots(figsize=(6.4, 2.8))
cols = [BLUE if s == "nco2015" else "#86b6ef" for s in ss["occ_system"]]
ax.bar(ss["round"], ss["n"] / 1000, color=cols, width=0.65)
for i, (n, wn) in enumerate(zip(ss["n"], ss["weighted_n_millions"])):
    ax.text(i, n / 1000 + 1, f"{n / 1000:.1f}k\n({wn:.0f} m)", ha="center", fontsize=7, color=INK2)
ax.set_ylabel("Wage earners in sample (thousands)")
ax.set_ylim(0, 100)
ax.grid(axis="x", visible=False)
ax.legend(handles=[plt.Rectangle((0, 0), 1, 1, color="#86b6ef"), plt.Rectangle((0, 0), 1, 1, color=BLUE)],
          labels=["NCO-2004 rounds (linked)", "NCO-2015 rounds"], loc="upper center", ncol=2)
ax.set_title("PLFS analysis sample by round (weighted population in millions)")
save(fig, "fig19_plfs_sample", "Regular and casual wage earners aged 15–64 per PLFS round.", "reports/econ_llm/sample_summary.csv")

# index
lines = ["# Figures", "", "PNG (300 dpi) for Word/slides, PDF (vector) for LaTeX. Regenerate: `python paper/make_figures.py`.",
         "Colours are fixed by measure: blue = NCO-LLM (Qwen, main), aqua = second LLM (Llama), orange = O*NET.", "",
         "| File | What it shows | Data |", "|---|---|---|"]
lines += [f"| `{n}` | {c} | `{s}` |" for n, c, s in index]
lines += ["", "`run_segments.csv`: start, end, duration, calls and tokens of every scoring job (from `reports/run_log.csv`)."]
(OUT / "figures_index.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
print(f"{len(index)} figures -> {OUT}")
