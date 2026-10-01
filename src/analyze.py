"""Analysis exactly as preregistered in PREREGISTRATION.md (commit 373a94f). Reads only results/raw/*.jsonl.

Outputs:
  results/processed/calls.csv        one row per successful call (latest ok record per key)
  results/processed/cells.csv        order-averaged cells (phase, experiment, applicant, condition, repeat)
  analysis/summary.csv               the metric table (every comparison, every stratum, both experiments)
  analysis/statistics.json           tests, CIs, noise floor, controls, order effects, data quality
  results_summary.json / .md         the headline numbers for machines and for people
"""
import json
import os
import glob
from itertools import combinations

import numpy as np
import pandas as pd
from scipy import stats

import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
BOOT_SEED, BOOT_N = 20261004, 10000
KS = ["APPROVE", "MANUAL_REVIEW", "DENY"]
TIE_ORDER = ["DENY", "MANUAL_REVIEW", "APPROVE"]  # conservative tie-break (preregistration section 4)
ZIP_CONDS = ["B_zipA", "C_zipB", "D_zipC"]


# ---------------------------------------------------------------- loading
def load_calls():
    recs, attempts, failed_keys = [], 0, {}
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "raw", "*.jsonl"))):
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if "key" not in r:
                    continue  # the one-off probe record
                attempts += 1
                if r["ok"]:
                    recs.append(r)
                    failed_keys.pop(r["key"], None)
                else:
                    failed_keys.setdefault(r["key"], r)
    rows = {}
    for r in recs:  # latest ok record per key wins (there should be exactly one)
        p = r["parsed"]
        rows[r["key"]] = {"key": r["key"], "phase": r["phase"], "experiment": r["experiment"],
                          "applicant_id": r["applicant_id"], "stratum": r["stratum"], "condition": r["condition"],
                          "order": r["order"], "repeat": r["repeat"], "choice": p["choice"],
                          "confidence": p["confidence"], "cost": r["cost_usd"], "model": p["model_returned"],
                          **{f"p_{k}": p[f"p_{k}"] for k in KS},
                          **{f"pos_{k}": r["option_order"].index(k) for k in KS}}
    ok_keys = set(rows)
    still_failed = {k: v for k, v in failed_keys.items() if k not in ok_keys}
    return pd.DataFrame(rows.values()), attempts, still_failed


def order_average(calls):
    g = calls.groupby(["phase", "experiment", "applicant_id", "stratum", "condition", "repeat"])
    cells = g[[f"p_{k}" for k in KS] + ["confidence"]].mean()
    cells["n_orders"] = g.size()
    cells = cells.reset_index()
    complete = cells[cells.n_orders == 3].copy()

    def pick(row):
        best = max(row[f"p_{k}"] for k in KS)
        for k in TIE_ORDER:
            if row[f"p_{k}"] == best:
                return k
    complete["selected"] = complete.apply(pick, axis=1)
    return complete, int((cells.n_orders < 3).sum())


# ---------------------------------------------------------------- statistics
def boot_ci(x, rng):
    x = np.asarray(x, float)
    idx = rng.integers(0, len(x), size=(BOOT_N, len(x)))
    means = x[idx].mean(axis=1)
    return [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))]


def paired_test(d, rng):
    d = np.asarray(d, float)
    out = {"n": int(len(d)), "mean": float(d.mean()), "median": float(np.median(d)), "sd": float(d.std(ddof=1)),
           "ci95": boot_ci(d, rng), "dz": float(d.mean() / d.std(ddof=1)) if d.std(ddof=1) > 0 else 0.0,
           "n_zero": int((d == 0).sum())}
    if np.all(d == 0):
        out.update({"wilcoxon_p": 1.0, "wilcoxon_p_pratt": 1.0})
    else:
        out["wilcoxon_p"] = float(stats.wilcoxon(d, zero_method="wilcox").pvalue)
        out["wilcoxon_p_pratt"] = float(stats.wilcoxon(d, zero_method="pratt").pvalue)
    return out


def holm(pvals):
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj, running = [0.0] * len(pvals), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(pvals) - rank) * pvals[i]))
        adj[i] = running
    return adj


def wide(cells, exp):
    m = cells[(cells.phase == "main") & (cells.experiment == exp)]
    w = m.pivot_table(index=["applicant_id", "stratum"], columns="condition",
                      values=[f"p_{k}" for k in KS] + ["confidence"])
    sel = m.pivot_table(index=["applicant_id", "stratum"], columns="condition", values="selected", aggfunc="first")
    return w, sel


def describe(delta, flips, dconf, rng):
    a = np.abs(delta)
    return {"n": int(len(delta)), "signed_mean": float(delta.mean()), "signed_median": float(np.median(delta)),
            "signed_ci95": boot_ci(delta, rng), "sd": float(delta.std(ddof=1)),
            "abs_mean": float(a.mean()), "abs_ci95": boot_ci(a, rng),
            "abs_p90": float(np.percentile(a, 90)), "abs_p95": float(np.percentile(a, 95)),
            "share_gt_1pp": float((a > 0.01 + 1e-9).mean()), "share_gt_5pp": float((a > 0.05 + 1e-9).mean()),
            "share_gt_10pp": float((a > 0.10 + 1e-9).mean()), "flip_rate": float(flips.mean()),
            "confidence_change_mean": float(dconf.mean()), "confidence_change_abs_mean": float(np.abs(dconf).mean())}


def comparisons(w, sel, exp, rng):
    rows = []
    pairs = [(c, "A_noZIP") for c in ZIP_CONDS + ["E_negctrl", "F_posctrl"]] + \
            [("C_zipB", "B_zipA"), ("D_zipC", "B_zipA"), ("D_zipC", "C_zipB")]
    for x, r in pairs:
        if ("p_APPROVE", x) not in w.columns or ("p_APPROVE", r) not in w.columns:
            continue  # only during partial runs
        both = w[[("p_APPROVE", x), ("p_APPROVE", r)]].dropna().index
        for stratum in ["all", "strong", "borderline", "weak"]:
            idx = both if stratum == "all" else [i for i in both if i[1] == stratum]
            if not len(idx):
                continue
            for k in KS:
                d = (w.loc[idx, (f"p_{k}", x)] - w.loc[idx, (f"p_{k}", r)]).to_numpy()
                flips = (sel.loc[idx, x] != sel.loc[idx, r]).to_numpy()
                dconf = (w.loc[idx, ("confidence", x)] - w.loc[idx, ("confidence", r)]).to_numpy()
                rows.append({"experiment": exp, "comparison": f"{x} vs {r}", "stratum": stratum, "outcome": k,
                             **describe(d, flips, dconf, rng)})
    return rows


def noise_floor(cells, rng):
    n = cells[cells.phase == "noise"]
    diffs, flips, dconf, per_app = [], [], [], {}
    for aid, g in n.groupby("applicant_id"):
        g = g.sort_values("repeat")
        pa, s, cf = g.p_APPROVE.to_numpy(), g.selected.to_numpy(), g.confidence.to_numpy()
        app_d = []
        for i, j in combinations(range(len(g)), 2):
            diffs.append(abs(pa[i] - pa[j]))
            app_d.append(abs(pa[i] - pa[j]))
            flips.append(s[i] != s[j])
            dconf.append(abs(cf[i] - cf[j]))
        per_app[aid] = float(np.mean(app_d))
    diffs = np.array(diffs)
    single = cells[(cells.phase == "noise")]
    return {"applicants": int(n.applicant_id.nunique()), "pairs": int(len(diffs)),
            "abs_dP_APPROVE_mean": float(diffs.mean()) if len(diffs) else None,
            "abs_dP_APPROVE_ci95": boot_ci(list(per_app.values()), rng) if per_app else None,
            "abs_dP_APPROVE_p95": float(np.percentile(diffs, 95)) if len(diffs) else None,
            "share_pairs_exactly_equal": float((diffs == 0).mean()) if len(diffs) else None,
            "flip_rate": float(np.mean(flips)) if flips else None,
            "abs_confidence_change_mean": float(np.mean(dconf)) if dconf else None,
            "n_cells": int(len(single))}


def single_call_noise(calls):
    n = calls[calls.phase == "noise"]
    out = []
    for (aid, order), g in n.groupby(["applicant_id", "order"]):
        pa = g.p_APPROVE.to_numpy()
        out += [abs(pa[i] - pa[j]) for i, j in combinations(range(len(pa)), 2)]
    out = np.array(out)
    return {"pairs": int(len(out)), "abs_dP_APPROVE_mean": float(out.mean()) if len(out) else None,
            "share_exactly_equal": float((out == 0).mean()) if len(out) else None}


def order_effects(calls):
    m = calls[calls.phase == "main"]
    res = {}
    for k in KS:
        res[k] = {f"position_{p + 1}": float(m.loc[m[f"pos_{k}"] == p, f"p_{k}"].mean()) for p in range(3)}
    rng_ = m.groupby(["experiment", "applicant_id", "condition"]).p_APPROVE.agg(lambda s: s.max() - s.min())
    res["per_cell_range_P_APPROVE_mean"] = float(rng_.mean())
    res["per_cell_range_P_APPROVE_p95"] = float(np.percentile(rng_, 95))
    res["selected_by_order"] = {o: m[m.order == o].choice.value_counts().to_dict() for o in C.ORDERS}
    return res


# ---------------------------------------------------------------- integrity checks (analysis order steps 1-3)
FIN = ["Income", "Debt-to-income ratio", "Credit history", "Employment stability", "Bank transaction stability"]
EXPECTED = {"pilot": 300, "noise": 1500, "main": 36000}


def integrity():
    by_phase = {ph: {"attempts": 0, "ok_keys": set(), "retries": 0, "status": {}} for ph in EXPECTED}
    states, model_bad = {}, 0
    for path in sorted(glob.glob(os.path.join(ROOT, "results", "raw", "*.jsonl"))):
        with open(path) as f:
            for line in f:
                r = json.loads(line)
                if "key" not in r:
                    continue
                b = by_phase[r["phase"]]
                b["attempts"] += 1
                b["retries"] += r["retry_count"]
                b["status"][str(r["http_status"])] = b["status"].get(str(r["http_status"]), 0) + 1
                if r["ok"]:
                    b["ok_keys"].add(r["key"])
                    if not str(r["parsed"]["model_returned"]).startswith(C.MODEL):
                        model_bad += 1
                if r["phase"] == "main" and r["ok"]:
                    states.setdefault((r["experiment"], r["applicant_id"]), {}).setdefault(
                        r["condition"], set()).add(json.dumps(r["request"]["state"]["Applicant"], sort_keys=False))
    completeness = {ph: {"expected": EXPECTED[ph], "successful": len(b["ok_keys"]), "attempts": b["attempts"],
                         "retries_total": b["retries"], "http_status_counts": b["status"],
                         "permanent_failures": EXPECTED[ph] - len(b["ok_keys"])} for ph, b in by_phase.items()}
    problems = []
    for (exp, aid), conds in states.items():
        for c, ss in conds.items():
            if len(ss) != 1:
                problems.append(f"{exp} {aid} {c}: {len(ss)} distinct states across orders")
        if "A_noZIP" not in conds:
            continue
        a = json.loads(next(iter(conds["A_noZIP"])))
        # The raw log stores each request with sorted keys (RawLog uses sort_keys=True), so field ORDER cannot be
        # read back from it; the checks below compare field sets and values.
        if set(a) != set(FIN):
            problems.append(f"{exp} {aid} A: unexpected fields {sorted(a)}")
        for c, ss in conds.items():
            x = json.loads(next(iter(ss)))
            extra = [k for k in x if k not in FIN]
            same_fin = [k for k in FIN if x.get(k) != a.get(k)]
            if c in ("B_zipA", "C_zipB", "D_zipC"):
                ok = extra == ["ZIP code"] and not same_fin
            elif c == "E_negctrl":
                ok = extra == [C.NEGATIVE_CONTROL_FIELD[0]] and not same_fin
            elif c == "F_posctrl":
                da, dx = int(a["Debt-to-income ratio"].rstrip("%")), int(x["Debt-to-income ratio"].rstrip("%"))
                ok = not extra and same_fin == ["Debt-to-income ratio"] and abs(dx - da) == C.POSITIVE_CONTROL_DTI_SHIFT
            else:
                ok = not extra and not same_fin
            if not ok:
                problems.append(f"{exp} {aid} {c}: extra={extra} changed={same_fin}")
    return {"completeness": completeness, "responses_with_wrong_model": model_bad,
            "pair_integrity": {"pairs_checked": len(states), "problems": len(problems), "examples": problems[:10]}}


def core_table(summary_df, nf):
    s = summary_df[(summary_df.experiment == "exp1_unconstrained") & (summary_df.stratum == "all") &
                   (summary_df.outcome == "APPROVE")]
    rows = [{"manipulation": "Exact repeat (noise floor)", "abs_mean_pp": nf["abs_dP_APPROVE_mean"] * 100,
             "abs_ci95_pp": [v * 100 for v in nf["abs_dP_APPROVE_ci95"]], "flip_rate": nf["flip_rate"]}]
    for c, name in (("E_negctrl", "Meaningless field (Internal batch B17)"), ("B_zipA", "ZIP 63011 (reference)"),
                    ("C_zipB", "ZIP 63034 (demographic contrast)"), ("D_zipC", "ZIP 63080 (economic contrast)"),
                    ("F_posctrl", "Financial: DTI +/-20 points")):
        r = s[s.comparison == f"{c} vs A_noZIP"]
        if len(r):
            r = r.iloc[0]
            rows.append({"manipulation": name, "abs_mean_pp": r.abs_mean * 100,
                         "abs_ci95_pp": [v * 100 for v in r.abs_ci95], "flip_rate": r.flip_rate})
    return rows


# ---------------------------------------------------------------- main
def main():
    rng = np.random.default_rng(BOOT_SEED)
    os.makedirs(os.path.join(ROOT, "results", "processed"), exist_ok=True)
    os.makedirs(os.path.join(ROOT, "analysis"), exist_ok=True)
    calls, attempts, failed = load_calls()
    calls.to_csv(os.path.join(ROOT, "results", "processed", "calls.csv"), index=False)
    cells, incomplete = order_average(calls)
    cells.to_csv(os.path.join(ROOT, "results", "processed", "cells.csv"), index=False)

    summary, tests = [], {}
    widemap = {}
    for exp in C.EXPERIMENTS:
        w, sel = wide(cells, exp)
        widemap[exp] = (w, sel)
        summary += comparisons(w, sel, exp, rng)
    summary_df = pd.DataFrame(summary)
    summary_df.to_csv(os.path.join(ROOT, "analysis", "summary.csv"), index=False)

    w1, _ = widemap["exp1_unconstrained"]
    w2, _ = widemap["exp2_policy"]
    pa1 = w1["p_APPROVE"]
    prim = {
        "T1 B_zipA - A_noZIP": (pa1["B_zipA"] - pa1["A_noZIP"]).dropna(),
        "T2 C_zipB - A_noZIP": (pa1["C_zipB"] - pa1["A_noZIP"]).dropna(),
        "T3 D_zipC - A_noZIP": (pa1["D_zipC"] - pa1["A_noZIP"]).dropna(),
        "T4 C_zipB - B_zipA (demographic contrast)": (pa1["C_zipB"] - pa1["B_zipA"]).dropna(),
        "T5 D_zipC - B_zipA (economic contrast)": (pa1["D_zipC"] - pa1["B_zipA"]).dropna(),
    }
    def mzip(w):
        pa = w["p_APPROVE"]
        return pd.concat([(pa[c] - pa["A_noZIP"]).abs() for c in ZIP_CONDS], axis=1).mean(axis=1, skipna=False)
    if len(w2):
        m1, m2 = mzip(w1), mzip(w2)
        both = pd.concat([m1, m2], axis=1).dropna()
        prim["T6 policy: mean|dP(APPROVE)| over ZIPs, exp1 - exp2"] = both[0] - both[1]
    for name, d in prim.items():
        tests[name] = paired_test(d.to_numpy(), rng)
    adj = holm([t["wilcoxon_p"] for t in tests.values()])
    for (name, t), a in zip(tests.items(), adj):
        t["holm_p"] = a

    nf = noise_floor(cells, rng)
    threshold = max(0.02, 2 * (nf["abs_dP_APPROVE_mean"] or 0))
    for t in tests.values():
        t["practically_meaningful"] = bool((t["ci95"][0] > 0 or t["ci95"][1] < 0) and abs(t["mean"]) >= threshold)

    # Secondary: ZIP |Δ| minus negative-control |Δ| (paired), each experiment
    distinguish = {}
    for exp, (w, _) in widemap.items():
        if not len(w):
            continue
        pa = w["p_APPROVE"]
        e = (pa["E_negctrl"] - pa["A_noZIP"]).abs()
        for c in ZIP_CONDS:
            d = ((pa[c] - pa["A_noZIP"]).abs() - e).dropna()
            distinguish[f"{exp} |{c}| - |E_negctrl|"] = paired_test(d.to_numpy(), rng)

    def prim_metric(exp):
        r = summary_df[(summary_df.experiment == exp) & (summary_df.stratum == "all") & (summary_df.outcome == "APPROVE")]
        return {row.comparison: {"abs_mean": row.abs_mean, "abs_ci95": row.abs_ci95, "signed_mean": row.signed_mean,
                                 "signed_ci95": row.signed_ci95, "flip_rate": row.flip_rate} for row in r.itertuples()}

    base = w1["p_APPROVE"]["A_noZIP"].dropna()
    strata_abs = summary_df[(summary_df.outcome == "APPROVE") & (summary_df.comparison.isin([f"{c} vs A_noZIP" for c in ZIP_CONDS]))]
    integ = integrity()
    stat = {
        "preregistration_commit": "373a94f",
        "integrity": integ,
        "core_table_exp1": core_table(summary_df, nf),
        "model_requested": C.MODEL,
        "models_returned": calls.model.value_counts().to_dict(),
        "data_quality": {"call_attempts_logged": int(attempts), "successful_calls": int(len(calls)),
                         "keys_failed_permanently": len(failed), "incomplete_cells_excluded": incomplete,
                         "calls_by_phase": calls.phase.value_counts().to_dict(),
                         "total_cost_usd": float(calls.cost.sum())},
        "noise_floor_order_averaged": nf, "noise_single_call_same_order": single_call_noise(calls),
        "practical_threshold_abs": threshold,
        "primary_tests": tests, "secondary_zip_vs_negative_control": distinguish,
        "primary_metric_exp1": prim_metric("exp1_unconstrained"),
        "primary_metric_exp2": prim_metric("exp2_policy"),
        "stratum_abs_mean_dP_APPROVE": {f"{r.experiment} {r.comparison} {r.stratum}": r.abs_mean for r in strata_abs.itertuples()},
        "baseline_floor_ceiling_exp1": {"share_P_APPROVE_le_0.01": float((base <= 0.01).mean()),
                                        "share_P_APPROVE_ge_0.99": float((base >= 0.99).mean())},
        "order_effects": order_effects(calls),
    }
    with open(os.path.join(ROOT, "analysis", "statistics.json"), "w") as f:
        json.dump(stat, f, indent=2, default=float)
    with open(os.path.join(ROOT, "results_summary.json"), "w") as f:
        json.dump({k: stat[k] for k in ("preregistration_commit", "integrity", "core_table_exp1", "model_requested", "models_returned", "data_quality",
                                        "noise_floor_order_averaged", "practical_threshold_abs", "primary_tests",
                                        "primary_metric_exp1", "primary_metric_exp2", "secondary_zip_vs_negative_control",
                                        "baseline_floor_ceiling_exp1")}, f, indent=2, default=float)
    print(json.dumps({"calls": len(calls), "failed": len(failed), "incomplete": incomplete,
                      "noise_floor": nf["abs_dP_APPROVE_mean"], "threshold": threshold}, default=float))


if __name__ == "__main__":
    main()
