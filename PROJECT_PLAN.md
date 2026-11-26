# Project plan

Due **Fri Dec 4, 2026, 12:00 noon**. Late penalty: −25 % within 72 h, −75 % after.

## Pipeline

```
TA data ─► data/experiments/ + runs.csv
             │
             ▼
   1 fit_parameters ──► k_ref, Ea, ΔH ± 95 % CI       (Part B, rubric A3/B2)
             │      └─► plan_experiments: rank next request (B1)
             ▼
   0 verify_model: conservation / energy / analytic checks  (A2)
   2 validate: held-out run, no retuning                     (A4/B2)
   3 full_scale: 1000 L nominal + bench vs plant             (Part A, B3)
   4 safety: max safe feed, cooling failure, runaway maps    (Part C, B4)
   5 design: feed policy, required UA, sensitivity, MC       (Part D, B5/B6)
             │
             ▼
   results/real/SUMMARY.md ─► report/ENCH421_Report_Skeleton.docx
```

## Schedule

Assumes each experiment takes 1 business day to come back.

| Day | Action |
|---|---|
| Fri Nov 27 | Run 1 back → fit → plan → request Runs 2 + 3 together |
| Mon Nov 30 | Runs 2–3 back → refit → plan → request Runs 4 + 5 |
| Tue Dec 1 | Final fit → submit parameters → request validation data |
| Wed Dec 2 | Validation back → `run_all.py` → all figures and tables |
| Thu Dec 3 | Write discussion sections; AI log into the appendix |
| Fri Dec 4 | Final check, submit before noon |

Five runs sent one at a time cannot finish in time. Batch two runs per request if the TA allows it.

## Your decisions

All of these live in `src/config.py`.

| Decision | Current placeholder | Revisit when |
|---|---|---|
| Full-scale fill: 600 L A + 300 L B | 90 % of 1000 L | now |
| B : A feed ratio | 1.0 | after fit |
| Batch time / target conversion | 240 min / 0.95 | after fit |
| Safety margins: normal / cooling failure | 15 K / 5 K | §9.1 of the report |
| High-T interlock trip | 70 °C | after the safety results |
| Nominal Part A case | T0 = Tc = 40 °C, 120 min feed | after fit |
| UA scaling | ∝ V^(2/3), about 670 W/K | fixed (the design step sweeps UA) |

## Status

- [x] Pipeline built and checked on synthetic data: true parameters recovered inside the 95 % CI, all verification checks pass
- [x] Report skeleton (`report/ENCH421_Report_Skeleton.docx`)
- [ ] Run 1 data → `data/experiments/`
- [ ] Runs 2–5, validation, report
