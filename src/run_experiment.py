"""Run one phase of the experiment: pilot, noise, or main.

Each call is identified by a key (phase|experiment|applicant|condition|order|repeat). The runner is resumable:
keys that already have a successful record in the phase's raw log are skipped; failures are logged and
retried on a later invocation, never deleted. Raw logs are append-only JSONL under results/raw/.

  python src/run_experiment.py pilot   # 100 pilot applicants, condition A, exp1, 3 orders      (300 calls)
  python src/run_experiment.py noise   # 100 noise-subset applicants, A, exp1, 3 orders, 5 reps (1,500 calls)
  python src/run_experiment.py main    # 1,000 applicants x 6 conditions x 2 experiments x 3 orders (36,000)
"""
import argparse
import concurrent.futures as cf
import csv
import glob
import json
import os
import sys
import time

import config as C
import jev_client as J

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
RAW = os.path.join(ROOT, "results", "raw")


def read_csv(name):
    with open(os.path.join(ROOT, "data", name), newline="") as f:
        return list(csv.DictReader(f))


def zips():
    return {r["condition"]: r["zip"] for r in read_csv("zip_metadata.csv")}


def state_for(app, condition, zipmap):
    """Financial fields are produced by one function and are byte-identical across conditions, except the
    positive control, which changes DTI only. Extra fields are appended last."""
    dti = int(app["dti"])
    if condition == "F_posctrl":
        dti = dti + C.POSITIVE_CONTROL_DTI_SHIFT if dti <= 32 else dti - C.POSITIVE_CONTROL_DTI_SHIFT
    applicant = {
        "Income": f"${int(app['income']):,}",
        "Debt-to-income ratio": f"{dti}%",
        "Credit history": app["credit"],
        "Employment stability": app["employment"],
        "Bank transaction stability": app["bank"],
    }
    if condition in ("B_zipA", "C_zipB", "D_zipC"):
        applicant["ZIP code"] = zipmap[condition[0]]
    elif condition == "E_negctrl":
        applicant[C.NEGATIVE_CONTROL_FIELD[0]] = C.NEGATIVE_CONTROL_FIELD[1]
    return {"Applicant": applicant}


def plan(phase):
    zipmap = zips()
    jobs = []
    if phase == "pilot":
        for app in read_csv("pilot_applicants.csv"):
            for order in C.ORDERS:
                jobs.append(("exp1_unconstrained", app, "A_noZIP", order, 0))
    elif phase == "noise":
        wanted = {r["applicant_id"] for r in read_csv("noise_subset.csv")}
        for app in read_csv("synthetic_applicants.csv"):
            if app["applicant_id"] in wanted:
                for rep in range(C.NOISE_REPEATS):
                    for order in C.ORDERS:
                        jobs.append(("exp1_unconstrained", app, "A_noZIP", order, rep))
    elif phase == "main":
        for exp in C.EXPERIMENTS:
            for app in read_csv("synthetic_applicants.csv"):
                for cond in C.CONDITIONS:
                    for order in C.ORDERS:
                        jobs.append((exp, app, cond, order, 0))
    out = []
    for exp, app, cond, order, rep in jobs:
        key = f"{phase}|{exp}|{app['applicant_id']}|{cond}|{order}|{rep}"
        out.append((key, exp, app, cond, order, rep, state_for(app, cond, zipmap)))
    return out


def done_keys_and_spend():
    done, spent = set(), 0.0
    for path in glob.glob(os.path.join(RAW, "*.jsonl")):
        with open(path) as f:
            for line in f:
                try:
                    rec = json.loads(line)
                except ValueError:
                    continue
                spent += rec.get("cost_usd") or 0.0
                if rec.get("ok"):
                    done.add(rec.get("key"))
    return done, spent


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("phase", choices=["pilot", "noise", "main"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--limit", type=int, default=0, help="run at most N pending calls (0 = all)")
    args = ap.parse_args()

    key = J.load_key()
    jobs = plan(args.phase)
    done, spent = done_keys_and_spend()
    pending = [j for j in jobs if j[0] not in done]
    if args.limit:
        pending = pending[: args.limit]
    budget = J.Budget(spent)
    log = J.RawLog(os.path.join(RAW, f"{args.phase}.jsonl"))
    print(json.dumps({"phase": args.phase, "planned": len(jobs), "already_ok": len(jobs) - len([j for j in jobs if j[0] not in done]),
                      "to_run": len(pending), "spent_before_usd": round(spent, 6)}), flush=True)
    stop = {"model_mismatch": None}

    def work(job):
        k, exp, app, cond, order, rep, state = job
        if budget.exhausted() or stop["model_mismatch"]:
            return "skipped"
        body = J.build_request(state, C.EXPERIMENTS[exp], order)
        status, text, retries, elapsed = J.call(key, body)
        parsed = J.parse(text) if status == 200 else None
        model_ok = bool(parsed and str(parsed["model_returned"] or "").startswith(C.MODEL))
        ok = bool(parsed and model_ok and None not in (parsed["p_APPROVE"], parsed["p_MANUAL_REVIEW"], parsed["p_DENY"]))
        cost = (parsed or {}).get("cost") or 0.0
        total = budget.add(cost)
        if parsed and not model_ok:
            stop["model_mismatch"] = parsed["model_returned"]
        log.append({"key": k, "phase": args.phase, "experiment": exp, "applicant_id": app["applicant_id"],
                    "stratum": app["stratum"], "condition": cond, "order": order, "option_order": C.ORDERS[order],
                    "repeat": rep, "model_requested": C.MODEL, "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "request": body, "http_status": status, "response_text": text, "retry_count": retries,
                    "elapsed_s": elapsed, "ok": ok, "model_ok": model_ok, "parsed": parsed, "cost_usd": cost,
                    "spent_total_usd": round(total, 9)})
        return "ok" if ok else "failed"

    counts = {"ok": 0, "failed": 0, "skipped": 0}
    t0 = time.time()
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        for i, res in enumerate(ex.map(work, pending), 1):
            counts[res] += 1
            if i % 500 == 0:
                print(json.dumps({"done": i, **counts, "spent_usd": round(budget.spent, 6),
                                  "elapsed_s": round(time.time() - t0)}), flush=True)
    print(json.dumps({"finished": True, **counts, "spent_usd": round(budget.spent, 6),
                      "model_mismatch": stop["model_mismatch"], "elapsed_s": round(time.time() - t0)}), flush=True)
    if stop["model_mismatch"] or budget.exhausted():
        sys.exit(3)


if __name__ == "__main__":
    main()
