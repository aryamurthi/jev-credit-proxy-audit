# Independent reviews

Two reviewers checked this repository. Neither had built it, and each worked read-only on a copy.

## Round 1: changes requested
The reviewer recomputed the core table, the T4 and T5 contrasts and the exp2 means from the raw logs. They matched to within 0.01 pp. Pair integrity, the model version and the option-name mapping were also confirmed.

Eleven findings, all addressed in commit 82b2f17:
1. The analysis code was not preregistered; the record understated this.
2. A deviation entry gave the time it was written instead of the time of the fix.
3. The preregistered Pratt variant was computed but not reported. It, and a sign test, show the T1–T3 shifts are systematic in direction.
4. Floating-point residue broke ties in the Wilcoxon ranks and zero handling.
5. The 0.99 ceiling share was wrong: reported 0.0, actually 0.140.
6. The 90th-percentile example pick was wrong under the tie rule.
7. A storyboard caption overstated "largest shift".
8. "Boundary instability, not geography" overclaimed.
9. "DTI response unchanged" overclaimed; flip-rate changes under the instruction were missing.
10. The draft post implied an absence the data cannot support.
11. The run order confounds the instruction comparison.

## Round 2: changes requested
The corrections reproduced byte-for-byte. The remaining issues:
- The first rounding fix was still inexact. Rounding before subtracting changed the median example pick and some p-values. It is now fixed by rounding after subtracting, and checked against an exact integer recomputation.
- Wording: "fewer but larger" increases; "one meaningless field tested"; flip rates including the batch label; the run-time caveat on the instruction result.
- The analysis docstring and the preregistration status line.

All of these were addressed in commit e5b8b5e.
