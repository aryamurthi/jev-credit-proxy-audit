"""Charts from results/processed/cells.csv and analysis/statistics.json. Run after analyze.py."""
import json
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
FIG = os.path.join(ROOT, "figures")
ZIPS = {"B_zipA": "ZIP 63011 (reference)", "C_zipB": "ZIP 63034 (demographic contrast)",
        "D_zipC": "ZIP 63080 (economic contrast)"}
CTRL = {"E_negctrl": "Meaningless field (negative control)", "F_posctrl": "DTI ±20 pts (positive control)"}
COL = {"B_zipA": "#4C72B0", "C_zipB": "#DD8452", "D_zipC": "#55A868", "E_negctrl": "#8C8C8C",
       "F_posctrl": "#C44E52", "noise": "#B0B0B0"}
plt.rcParams.update({"figure.dpi": 150, "font.size": 10, "axes.spines.top": False, "axes.spines.right": False})


def load():
    cells = pd.read_csv(os.path.join(ROOT, "results", "processed", "cells.csv"))
    stat = json.load(open(os.path.join(ROOT, "analysis", "statistics.json")))
    summ = pd.read_csv(os.path.join(ROOT, "analysis", "summary.csv"))
    return cells, stat, summ


def wide(cells, exp, value="p_APPROVE"):
    m = cells[(cells.phase == "main") & (cells.experiment == exp)]
    return m.pivot_table(index=["applicant_id", "stratum"], columns="condition", values=value)


def ci(row):
    lo, hi = [float(x) for x in str(row).strip("[]").split(",")]
    return lo, hi


def fig1(cells):
    w = wide(cells, "exp1_unconstrained")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    bins = np.arange(-0.065, 0.135, 0.01)
    for c, label in ZIPS.items():
        d = (w[c] - w["A_noZIP"]).dropna() * 100
        ax.hist(d, bins=bins * 100, histtype="step", linewidth=1.6, color=COL[c], label=f"{label}  (n={len(d)})")
    ax.set_yscale("log")
    ax.set_xlabel("Change in P(APPROVE) vs no ZIP, percentage points (order-averaged)")
    ax.set_ylabel("Applicants (log scale)")
    ax.set_title("Distribution of ΔP(APPROVE) for each ZIP, unconstrained instructions")
    ax.axvline(0, color="black", linewidth=0.6)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "probability_shift_distribution.png"))


def examples(cells):
    """Preregistered selection: C_zipB vs A, exp1, median / 90th percentile / largest |ΔP(APPROVE)|, ties by id."""
    w = wide(cells, "exp1_unconstrained")
    d = (w["C_zipB"] - w["A_noZIP"]).abs().dropna().reset_index()
    d.columns = ["applicant_id", "stratum", "absd"]
    d["absd"] = d.absd.round(9)  # equal values must compare equal for the lowest-id tie rule
    d = d.sort_values(["absd", "applicant_id"]).reset_index(drop=True)
    picks = {}
    for label, q in (("median", 0.5), ("90th percentile", 0.9)):
        target = d.absd.quantile(q, interpolation="lower")
        picks[label] = d[d.absd == target].sort_values("applicant_id").iloc[0].applicant_id
    top = d.absd.max()
    picks["largest"] = d[d.absd == top].sort_values("applicant_id").iloc[0].applicant_id
    return picks


def fig2(cells):
    picks = examples(cells)
    m = cells[(cells.phase == "main") & (cells.experiment == "exp1_unconstrained")]
    conds = ["A_noZIP", "B_zipA", "C_zipB", "D_zipC", "E_negctrl"]
    names = ["No ZIP", "63011", "63034", "63080", "Batch B17"]
    fig, axes = plt.subplots(1, 3, figsize=(11, 3.8), sharey=True)
    for ax, (label, aid) in zip(axes, picks.items()):
        g = m[m.applicant_id == aid].set_index("condition")
        bottom = np.zeros(len(conds))
        for k, color in (("p_APPROVE", "#55A868"), ("p_MANUAL_REVIEW", "#E1B53C"), ("p_DENY", "#C44E52")):
            vals = np.array([g.loc[c, k] for c in conds])
            ax.bar(names, vals, bottom=bottom, color=color, label=k[2:])
            bottom += vals
        ax.set_title(f"{label} |ΔP(APPROVE)| (63034 vs no ZIP)\n{aid}, {g.stratum.iloc[0]}", fontsize=9)
        ax.tick_params(axis="x", rotation=30, labelsize=8)
    axes[0].set_ylabel("Order-averaged probability")
    axes[0].legend(frameon=False, fontsize=8, loc="lower left")
    fig.suptitle("Same applicant, financial fields identical; only the extra field changes (preregistered picks)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "paired_zip_effects.png"))
    return picks


def fig3(summ, stat):
    s = summ[(summ.experiment == "exp1_unconstrained") & (summ.stratum == "all") & (summ.outcome == "APPROVE")]
    rows = [("Repeat-call noise\n(same input)", stat["noise_floor_order_averaged"]["abs_dP_APPROVE_mean"],
             stat["noise_floor_order_averaged"]["abs_dP_APPROVE_ci95"], COL["noise"])]
    for c, label in {**{"E_negctrl": "Meaningless field"}, **{k: v.split(" (")[0] for k, v in ZIPS.items()},
                     "F_posctrl": "DTI ±20 pts"}.items():
        r = s[s.comparison == f"{c} vs A_noZIP"].iloc[0]
        rows.append((label, r.abs_mean, ci(r.abs_ci95), COL[c]))
    fig, ax = plt.subplots(figsize=(8, 4.2))
    x = np.arange(len(rows))
    means = np.array([r[1] for r in rows]) * 100
    err = np.array([[r[1] - r[2][0], r[2][1] - r[1]] for r in rows]).T * 100
    ax.bar(x, means, color=[r[3] for r in rows], yerr=err, capsize=4)
    for i, v in enumerate(means):
        ax.text(i, v + max(means) * 0.02, f"{v:.2f}", ha="center", fontsize=8)
    ax.set_xticks(x, [r[0] for r in rows], fontsize=8)
    ax.set_ylabel("Mean |ΔP(APPROVE)|, percentage points")
    ax.set_title("How much P(APPROVE) moves: noise vs meaningless field vs ZIP vs real financial change\n"
                 "(unconstrained instructions, 1,000 matched applicants, 95% bootstrap CIs)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "controls_comparison.png"))


def fig4(summ):
    s = summ[(summ.experiment == "exp1_unconstrained") & (summ.outcome == "APPROVE")]
    strata = ["strong", "borderline", "weak"]
    conds = ["E_negctrl", "B_zipA", "C_zipB", "D_zipC"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.2
    for j, c in enumerate(conds):
        vals, errs = [], []
        for st in strata:
            r = s[(s.comparison == f"{c} vs A_noZIP") & (s.stratum == st)].iloc[0]
            lo, hi = ci(r.abs_ci95)
            vals.append(r.abs_mean * 100)
            errs.append([(r.abs_mean - lo) * 100, (hi - r.abs_mean) * 100])
        ax.bar(np.arange(3) + (j - 1.5) * width, vals, width, yerr=np.array(errs).T, capsize=3, color=COL[c],
               label={**ZIPS, "E_negctrl": "Meaningless field"}[c])
    ax.set_xticks(np.arange(3), ["Strong (300)", "Borderline (400)", "Weak (300)"])
    ax.text(2, 0.05, "P(APPROVE) = 0 in every\ncondition (floor): no shift\nmeasurable on this outcome", ha="center",
            va="bottom", fontsize=8, color="#555555")
    ax.set_ylabel("Mean |ΔP(APPROVE)|, percentage points")
    ax.set_title("Shift by applicant strength (unconstrained instructions, 95% CIs)", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "effect_by_credit_strength.png"))


def fig5(summ):
    s = summ[(summ.stratum == "all") & (summ.outcome == "APPROVE")]
    conds = ["E_negctrl", "B_zipA", "C_zipB", "D_zipC", "F_posctrl"]
    labels = ["Meaningless\nfield", "63011", "63034", "63080", "DTI ±20"]
    fig, ax = plt.subplots(figsize=(8, 4.2))
    width = 0.38
    for j, (exp, name, color) in enumerate((("exp1_unconstrained", "Unconstrained", "#4C72B0"),
                                            ("exp2_policy", "“Ignore geography” instruction", "#DD8452"))):
        vals, errs = [], []
        for c in conds:
            r = s[(s.experiment == exp) & (s.comparison == f"{c} vs A_noZIP")].iloc[0]
            lo, hi = ci(r.abs_ci95)
            vals.append(r.abs_mean * 100)
            errs.append([(r.abs_mean - lo) * 100, (hi - r.abs_mean) * 100])
        xs = np.arange(len(conds)) + (j - 0.5) * width
        ax.bar(xs, vals, width, yerr=np.array(errs).T, capsize=3, color=color, label=name)
        for xx, v in zip(xs, vals):
            ax.text(xx, v + 0.25, f"{v:.2f}", ha="center", fontsize=7)
    ax.set_xticks(np.arange(len(conds)), labels)
    ax.set_ylabel("Mean |ΔP(APPROVE)| vs no extra field, pp")
    ax.set_title("Unconstrained vs explicit policy instruction (1,000 matched applicants, 95% CIs)", fontsize=10)
    ax.legend(frameon=False, fontsize=8)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "policy_instruction_comparison.png"))


def fig6(cells):
    w = wide(cells, "exp1_unconstrained", "confidence")
    fig, ax = plt.subplots(figsize=(8, 4.2))
    data, labels = [], []
    for c, label in {**ZIPS, **CTRL}.items():
        data.append(((w[c] - w["A_noZIP"]).dropna() * 100).to_numpy())
        labels.append(label.replace(" (", "\n("))
    ax.boxplot(data, showfliers=True, flierprops={"markersize": 2})
    ax.set_xticks(range(1, len(labels) + 1), labels, fontsize=7)
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_ylabel("Change in confidence vs no extra field, pp")
    ax.set_title("Confidence changes (unconstrained instructions)", fontsize=10)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "confidence_changes.png"))


def main():
    os.makedirs(FIG, exist_ok=True)
    cells, stat, summ = load()
    fig1(cells)
    picks = fig2(cells)
    fig3(summ, stat)
    fig4(summ)
    fig5(summ)
    fig6(cells)
    with open(os.path.join(ROOT, "analysis", "example_picks.json"), "w") as f:
        json.dump(picks, f, indent=2)
    print(json.dumps(picks))


if __name__ == "__main__":
    main()
