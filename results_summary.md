# Results summary

## The result: no ZIP-specific sensitivity

Across 1,000 matched synthetic applicants, the financial fields were held byte-identical. Adding a ZIP code shifted Jev's P(APPROVE) by about 1 percentage point on average, and it did so the same way for all three ZIPs. That shift is about three times the repeat-call noise floor (0.31 pp). It is **smaller** than the shift caused by adding a meaningless field (1.17 pp), and about one fourteenth of the shift caused by a real financial change (DTI ±20 points: 13.3 pp).

Which ZIP was added made no measurable difference:
- The demographic contrast (63034 against 63011) was **+0.02 pp** (95% CI −0.03 to +0.07).
- The economic contrast (63080 against 63011) was **+0.02 pp** (95% CI −0.02 to +0.07).

The explicit "use only financial information; ignore geography" instruction halved the movement from every extra field, ZIP and meaningless alike: 0.98 → 0.48 pp for the ZIPs and 1.17 → 0.52 pp for the batch label. It left the response to DTI unchanged (13.3 → 13.6 pp).

None of the six preregistered primary tests met the preregistered bar for a practically meaningful shift: a 95% CI that excludes 0 **and** a magnitude of at least 2 pp.

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

## Primary tests (Holm–Bonferroni over T1–T6; paired; Wilcoxon signed-rank; bootstrap 95% CI)

| Test | Mean | 95% CI | d_z | Wilcoxon p | Holm p | Meaningful? |
|---|---|---|---|---|---|---|
| T1 P(APPROVE): 63011 − no ZIP | +0.14 pp | +0.04 to +0.26 | 0.08 | 0.51 | 1.00 | no |
| T2 P(APPROVE): 63034 − no ZIP | +0.16 pp | +0.06 to +0.27 | 0.10 | 0.98 | 1.00 | no |
| T3 P(APPROVE): 63080 − no ZIP | +0.17 pp | +0.06 to +0.27 | 0.10 | 0.72 | 1.00 | no |
| T4 demographic contrast: 63034 − 63011 | +0.02 pp | −0.03 to +0.07 | 0.02 | 0.11 | 0.57 | no |
| T5 economic contrast: 63080 − 63011 | +0.02 pp | −0.02 to +0.07 | 0.04 | 0.38 | 1.00 | no |
| T6 policy instruction: mean abs ZIP shift, exp1 − exp2 | +0.48 pp | +0.41 to +0.55 | 0.40 | 6.5e−37 | 3.9e−36 | no (below 2 pp) |

For T1–T3, the bootstrap CI of the mean excludes 0, but the signed-rank test does not. Most applicants do not move at all (about 440 of 1,000 differences are exactly zero), and a small right tail pulls the mean up while the ranks stay balanced. Either way the shift is under 0.2 pp.

T6 is statistically clear but below the practical threshold. The same reduction appears for the meaningless field, so it is a general reduction in sensitivity to extra fields, not a geography-specific one.

## Preregistered subgroup (applicant strength)

Mean abs ΔP(APPROVE), unconstrained instructions:

| | Strong (300) | Borderline (400) | Weak (300) |
|---|---|---|---|
| Meaningless field | 1.68 pp | 1.66 pp | 0.00 |
| ZIP 63011 | 1.05 pp | 1.66 pp | 0.00 |
| ZIP 63034 | 0.99 pp | 1.65 pp | 0.00 |
| ZIP 63080 | 1.03 pp | 1.65 pp | 0.00 |
| DTI ±20 | 17.75 pp | 19.85 pp | 0.00 |

- **Borderline:** the preregistered hypothesis holds in a narrow sense. ZIP shifts are largest among borderline profiles. But the meaningless field moves borderline profiles by the same 1.66 pp, so this is boundary instability, not geography.
- **Weak:** P(APPROVE) is 0 in every condition, a floor. On DENY and MANUAL_REVIEW, adding any ZIP moved about 1.9 pp from DENY to MANUAL_REVIEW, the same for all three ZIPs, against 1.3 pp for the meaningless field. No decision flipped. This comparison is secondary, not a primary test.

## Other findings

- **Confidence:** adding any extra field, ZIP or meaningless, lowered Jev's confidence by about 2.2 points on average.
- **Option order:** the effect was small. Across the 36,000 main calls, P(APPROVE) averaged 0.384, 0.382 and 0.380 in positions 1, 2 and 3. The mean per-cell range across the three orders was 1.4 pp. This differs from a prior Jev audit that found large first-position effects; see the README.
- **Baseline floor:** 46.3% of applicants have a baseline P(APPROVE) ≤ 0.01, which limits how far the primary metric can move for them.

## Data quality

- **Calls:** 37,800 successful (pilot 300, noise 1,500, main 36,000). 7 noise calls first returned HTTP 520 and succeeded when re-sent. Permanent failures: 0. Incomplete cells: 0.
- **Model:** every response came back as `typesafe/jev-1.13-20260917`.
- **Pair integrity:** for all 2,000 applicant×experiment pairs, the versions differ only by the manipulated field.
- **Cost:** USD 0.78 in total, as returned by the API.

## What this does not show

- Whether Jev is an accurate credit model. It was not trained on loan outcomes here.
- How a lender using Jev would behave.
- Anything about real people, real populations, disparate impact, intent or legality.
- Anything about ZIP codes beyond these three, or about states other than the one the ZIPs were chosen from.
