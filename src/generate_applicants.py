"""Generate the synthetic applicants deterministically from config.py. No LLM is used.

Writes data/synthetic_applicants.csv (1,000 main applicants), data/pilot_applicants.csv (100, separate seed,
never used in the hypothesis tests) and data/noise_subset.csv (the preregistered 100-case noise-floor subset).
"""
import csv
import os
import random

import config as C

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, "..", "data")
FIELDS = ["applicant_id", "stratum", "income", "dti", "credit_idx", "employment_idx", "bank_idx",
          "credit", "employment", "bank"]


def weighted(rng, weights):
    keys = sorted(weights)
    return rng.choices(keys, weights=[weights[k] for k in keys], k=1)[0]


def make(seed, size_key, prefix):
    rng = random.Random(seed)
    rows = []
    for stratum in ("strong", "borderline", "weak"):
        s = C.STRATA[stratum]
        for _ in range(s[size_key]):
            income = int(round(rng.uniform(*s["income"]) / 1000.0)) * 1000
            dti = rng.randint(*s["dti"])
            ci, ei, bi = weighted(rng, s["credit"]), weighted(rng, s["employment"]), weighted(rng, s["bank"])
            rows.append({"stratum": stratum, "income": income, "dti": dti, "credit_idx": ci, "employment_idx": ei,
                         "bank_idx": bi, "credit": C.CREDIT[ci], "employment": C.EMPLOYMENT[ei], "bank": C.BANK[bi]})
    for i, r in enumerate(rows, 1):
        r["applicant_id"] = f"{prefix}{i:04d}"
    return rows


def write(rows, name):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)


def noise_subset(main):
    rng = random.Random(C.SEED_NOISE_SUBSET)
    picked = []
    for stratum, n in (("strong", 30), ("borderline", 40), ("weak", 30)):
        ids = [r["applicant_id"] for r in main if r["stratum"] == stratum]
        picked += sorted(rng.sample(ids, n))
    return picked


def main():
    os.makedirs(DATA, exist_ok=True)
    main_rows = make(C.SEED_MAIN, "n_main", "M")
    pilot_rows = make(C.SEED_PILOT, "n_pilot", "P")
    write(main_rows, "synthetic_applicants.csv")
    write(pilot_rows, "pilot_applicants.csv")
    with open(os.path.join(DATA, "noise_subset.csv"), "w") as f:
        f.write("applicant_id\n" + "\n".join(noise_subset(main_rows)) + "\n")
    print(len(main_rows), "main,", len(pilot_rows), "pilot")


if __name__ == "__main__":
    main()
