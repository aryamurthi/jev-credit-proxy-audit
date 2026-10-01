"""Select the three ZIP codes (ZCTAs) for conditions B, C and D by a fixed rule over public Census data.

Source: U.S. Census Bureau, American Community Survey 2019-2023 5-year estimates, table-based summary
file (tables B01003 total population, B03002 Hispanic or Latino origin by race, B19013 median household
income), ZCTA rows only. Download URLs, sha256 and retrieval time are in data/acs/SOURCES.csv.

The rule is written down before any Jev call that contains a ZIP code, and it is run once. A ZIP code is
not a race: geography correlates with many demographic and economic characteristics at once, which is
exactly why it is studied here as a potential proxy.

Roles:
  ZIP_A  reference:            majority non-Hispanic white, low non-Hispanic Black share, upper-middle income
  ZIP_B  demographic contrast: majority non-Hispanic Black, median income close to ZIP_A's
  ZIP_C  economic contrast:    non-Hispanic white share close to ZIP_A's, median income far below ZIP_A's
All three share the same 3-digit ZIP prefix, so they are in the same postal region.
"""
import csv
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ACS = os.path.join(HERE, "..", "data", "acs")
OUT = os.path.join(HERE, "..", "data", "zip_metadata.csv")

RULE = {
    "min_population": 10000,
    "A_min_nh_white_share": 0.70,
    "A_max_nh_black_share": 0.05,
    "A_income_range": [90000, 130000],
    "B_min_nh_black_share": 0.60,
    "B_income_within_fraction_of_A": 0.15,
    "C_nh_white_share_within_pp_of_A": 0.10,
    "C_max_income_fraction_of_A": 0.50,
    "same_3_digit_prefix": True,
    "objective": "minimise |incB-incA|/incA + |whiteC-whiteA|; ties by ZCTA codes ascending",
}


def read_psv(name):
    with open(os.path.join(ACS, name), newline="") as f:
        return {r["GEO_ID"]: r for r in csv.DictReader(f, delimiter="|")}


def num(x):
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    return None if v < 0 else v  # the summary file uses negative sentinels for missing values


def load():
    pop = read_psv("acs5y2023_b01003_zcta.psv")
    race = read_psv("acs5y2023_b03002_zcta.psv")
    inc = read_psv("acs5y2023_b19013_zcta.psv")
    rows = []
    for geo, p in pop.items():
        zcta = geo[-5:]
        total = num(p.get("B01003_E001"))
        r = race.get(geo, {})
        rtot = num(r.get("B03002_E001"))
        white, black, hisp = num(r.get("B03002_E003")), num(r.get("B03002_E004")), num(r.get("B03002_E012"))
        income = num(inc.get(geo, {}).get("B19013_E001"))
        if not total or not rtot or income is None or white is None or black is None:
            continue
        rows.append({"zcta": zcta, "population": int(total), "median_household_income": int(income),
                     "nh_white_share": white / rtot, "nh_black_share": black / rtot,
                     "hispanic_share": (hisp or 0) / rtot})
    return rows


def select(rows):
    pool = [r for r in rows if r["population"] >= RULE["min_population"]]
    lo, hi = RULE["A_income_range"]
    cands_a = [r for r in pool if r["nh_white_share"] >= RULE["A_min_nh_white_share"]
               and r["nh_black_share"] <= RULE["A_max_nh_black_share"] and lo <= r["median_household_income"] <= hi]
    by_prefix = {}
    for r in pool:
        by_prefix.setdefault(r["zcta"][:3], []).append(r)
    best = None
    for a in cands_a:
        same = by_prefix[a["zcta"][:3]]
        ia, wa = a["median_household_income"], a["nh_white_share"]
        bs = [b for b in same if b["nh_black_share"] >= RULE["B_min_nh_black_share"]
              and abs(b["median_household_income"] - ia) <= RULE["B_income_within_fraction_of_A"] * ia]
        cs = [c for c in same if abs(c["nh_white_share"] - wa) <= RULE["C_nh_white_share_within_pp_of_A"]
              and c["median_household_income"] <= RULE["C_max_income_fraction_of_A"] * ia]
        for b in bs:
            for c in cs:
                score = abs(b["median_household_income"] - ia) / ia + abs(c["nh_white_share"] - wa)
                key = (round(score, 9), a["zcta"], b["zcta"], c["zcta"])
                if best is None or key < best[0]:
                    best = (key, a, b, c)
    return best, len(cands_a)


def main():
    rows = load()
    best, n_a = select(rows)
    print(json.dumps({"zcta_rows_usable": len(rows), "candidates_for_A": n_a, "found": best is not None}))
    if best is None:
        raise SystemExit("no triple satisfies the rule")
    _, a, b, c = best
    with open(OUT, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["condition", "role", "zip", "population", "median_household_income", "nh_white_share",
                    "nh_black_share", "hispanic_share", "source", "rule"])
        for cond, role, r in (("B", "ZIP_A reference", a), ("C", "ZIP_B demographic contrast", b),
                              ("D", "ZIP_C economic contrast", c)):
            w.writerow([cond, role, r["zcta"], r["population"], r["median_household_income"],
                        f"{r['nh_white_share']:.4f}", f"{r['nh_black_share']:.4f}", f"{r['hispanic_share']:.4f}",
                        "ACS 2019-2023 5-year, tables B01003 B03002 B19013 (data/acs/SOURCES.csv)",
                        json.dumps(RULE, sort_keys=True)])
    for role, r in (("A", a), ("B", b), ("C", c)):
        print(role, r)


if __name__ == "__main__":
    main()
