# Results summary

## The result: no difference between the three ZIPs; a small shift from adding any field

Across 1,000 matched synthetic applicants, the financial fields were held byte-identical. Adding a ZIP code moved Jev's P(APPROVE) by about 1 percentage point on average (0.97 pp, the mean of the three ZIPs), and by about the same for each ZIP.
- That is about three times the repeat-call noise floor (0.31 pp).
- It is slightly **smaller** than the shift from adding a meaningless field (1.17 pp).
- It is about one fourteenth of the shift from a real financial change (DTI ±20 points: 13.3 pp).

Which ZIP was added made no measurable difference:
- The demographic contrast (63034 against 63011) was **+0.02 pp** (95% CI −0.03 to +0.07).
- The economic contrast (63080 against 63011) was **+0.02 pp** (95% CI −0.02 to +0.07).

The shift from adding a ZIP has a direction that depends on the applicant:
- For strong profiles, approval fell by about 1.0 pp.
- For borderline profiles, it rose by about 1.1 pp.
- Over all applicants, more moved down (about 350) than up (about 210), which is significant by sign test. All of these shifts are under the preregistered 2 pp bar for a practically meaningful shift.

The explicit "use only financial information; ignore geography" instruction halved the average movement from every extra field, ZIP and meaningless alike:
- ZIPs: 0.97 → 0.49 pp (mean of the three).
- Batch label: 1.17 → 0.52 pp.

It did not halve the response to DTI on average (13.3 → 13.6 pp), but it changed that response within strata. Strong applicants went from 17.8 to 14.5 pp, borderline from 19.9 to 23.0 pp, and weak-profile decision flips fell from 19.7% to 7.3%. It also slightly raised decision flips from extra fields (ZIPs 0.4–0.6% → 0.7–0.8%).

None of the six preregistered primary tests met the preregistered bar for a practically meaningful shift: a 95% CI excluding 0 **and** a magnitude of at least 2 pp.

All three ZIPs are in one region (St. Louis, prefix 630). Nothing here generalizes to other ZIPs or regions.

## The core table (unconstrained instructions, 1,000 matched applicants, order-averaged)

| Manipulation | Mean abs ΔP(APPROVE) | 95% CI | Decision flips |
|---|---|---|---|
| Exact repeat (noise floor, 100 applicants × 5 repeats) | 0.31 pp | 0.22 – 0.41 | 0.0% |
| Meaningless field ("Internal batch: B17") | 1.17 pp | 1.07 – 1.26 | 0.3% |
| ZIP 63011 (reference) | 0.98 pp | 0.89 – 1.07 | 0.6% |
| ZIP 63034 (demographic contrast) | 0.96 pp | 0.87 – 1.05 | 0.4% |
| ZIP 63080 (economic contrast) | 0.97 pp | 0.88 – 1.06 | 0.5% |
| Legitimate financial change (DTI ±20 points) | 13.27 pp | 12.11 – 14.49 | 20.0% |

A decision flip is a change of the order-averaged top action against the no-ZIP baseline. For the noise floor it is a change between two repeats of the same input.

## Primary tests (Holm–Bonferroni over T1–T6, on the Wilcoxon p; paired; bootstrap 95% CI)

| Test | Mean | 95% CI | up / down / zero | Wilcoxon p | Pratt p | Sign-test p | Holm p | Meaningful? |
|---|---|---|---|---|---|---|---|---|
| T1 P(APPROVE): 63011 − no ZIP | +0.14 pp | +0.04 to +0.26 | 208 / 351 / 441 | 0.40 | 7e−5 | 2e−9 | 1.00 | no |
| T2 P(APPROVE): 63034 − no ZIP | +0.16 pp | +0.06 to +0.27 | 212 / 345 / 443 | 0.82 | 5e−4 | 2e−8 | 1.00 | no |
| T3 P(APPROVE): 63080 − no ZIP | +0.17 pp | +0.06 to +0.27 | 213 / 348 / 439 | 0.58 | 3e−4 | 1e−8 | 1.00 | no |
| T4 demographic contrast: 63034 − 63011 | +0.02 pp | −0.03 to +0.07 | 221 / 200 / 579 | 0.08 | 0.20 | 0.33 | 0.40 | no |
| T5 economic contrast: 63080 − 63011 | +0.02 pp | −0.02 to +0.07 | 211 / 205 / 584 | 0.26 | 0.58 | 0.81 | 1.00 | no |
| T6 policy instruction: mean abs ZIP shift, exp1 − exp2 | +0.48 pp | +0.41 to +0.55 | 458 / 140 / 402 | 4e−37 | 2e−40 | 2e−40 | 2e−36 | no (below 2 pp) |

**Reading T1–T3.** The mean rises slightly, but more applicants move down than up. A small number of large increases among borderline profiles outweigh many 1-point decreases among strong ones.
- With zeros dropped, the Wilcoxon test is not significant.
- The preregistered Pratt check and a sign test are significant.
- So adding a ZIP does change P(APPROVE) systematically, but in different directions for different applicants, and by under 2 pp.

**Reading T6.** The test is statistically clear but below the practical threshold. The same reduction appears for the meaningless field, so it is a reduction in sensitivity to extra fields generally. exp1 and exp2 ran about 12 minutes apart, so T6 is also confounded with run time; see the deviations in PREREGISTRATION.md.

## Preregistered subgroup (applicant strength)

Mean abs ΔP(APPROVE) / signed mean, unconstrained instructions:

| | Strong (300) | Borderline (400) | Weak (300) |
|---|---|---|---|
| Meaningless field | 1.68 / −1.68 pp | 1.66 / −0.43 pp | 0 |
| ZIP 63011 | 1.05 / −1.04 pp | 1.66 / +1.14 pp | 0 |
| ZIP 63034 | 0.99 / −0.96 pp | 1.65 / +1.12 pp | 0 |
| ZIP 63080 | 1.03 / −1.02 pp | 1.65 / +1.18 pp | 0 |
| DTI ±20 | 17.75 / −17.75 pp | 19.85 / +3.79 pp | 0 |

- **Borderline:** the preregistered hypothesis holds: ZIP shifts are largest among borderline profiles (1.65 pp). The meaningless field moves borderline profiles by the same amount, but in the other direction on average. Every ZIP raises borderline approval by about 1.1 pp, while the batch label lowers it by 0.4 pp. So the size of the movement is not specific to ZIPs, but its direction among borderline profiles is. This was found after the fact and is exploratory.
- **Weak:** P(APPROVE) is 0 in every condition, a floor. On DENY and MANUAL_REVIEW, adding any ZIP moved about 1.9 pp from DENY to MANUAL_REVIEW, the same for all three ZIPs, against 1.3 pp for the meaningless field. No decision flipped. This comparison is secondary.

## Other findings

- **Confidence:** adding any extra field, ZIP or meaningless, lowered Jev's confidence by about 2.2 points on average.
- **Option order:** the effect was small. Across the 36,000 main calls, P(APPROVE) averaged 0.384, 0.382 and 0.380 in positions 1, 2 and 3, and the mean per-cell range across the three orders was 1.4 pp. This differs from a prior Jev audit that found large first-position effects; see the README.
- **Floor and ceiling:** 46.3% of baselines have P(APPROVE) ≤ 0.01, and 14.0% have P(APPROVE) ≥ 0.99. The primary metric can move little there.

## Data quality

- **Calls:** 37,800 successful (pilot 300, noise 1,500, main 36,000). 7 noise calls first returned HTTP 520 and succeeded when re-sent. Permanent failures: 0. Incomplete cells: 0.
- **Model:** every response came back as `typesafe/jev-1.13-20260917`.
- **Pair integrity:** for all 2,000 applicant × experiment pairs, the versions differ only by the manipulated field.
- **Independent review:** a reviewer recomputed the core table, T4, T5 and the exp2 means from the raw logs, and they match to within 0.01 pp.
- **Cost:** USD 0.78 in total, as returned by the API.

## What this does not show

- Whether Jev is an accurate credit model. It was not trained on loan outcomes here.
- How a lender using Jev would behave.
- Anything about real people, real populations, disparate impact, intent or legality.
- Anything about ZIP codes beyond these three in one region, or about other question wordings, models or Jev versions.
- That the analysis code was preregistered. The metrics and tests were; the code was written during the run (see the deviations in PREREGISTRATION.md).
