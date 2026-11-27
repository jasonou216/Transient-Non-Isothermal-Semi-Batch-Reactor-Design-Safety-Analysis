# Project plan

Due **Fri Dec 4, 2026, 12:00 noon**. Late penalty: −25 % within 72 h, −75 % after.

## Pipeline

```
TA data ─► data/raw/ + data/experiments/runs.csv
             │
             ▼
   1 parameter_estimation ──► k_ref, Ea, ΔH ± 95 % CI           (Part 6)
             │            └─► experiment_planning: next request  (Part 5)
             ▼
   2 model_verification: conservation / energy / analytic checks (Part 4)
   5 model_validation: held-out run, no retuning                 (Part 7)
   6 plant_simulation: 1000 L nominal + bench vs plant           (Part 8)
   7 safety_analysis: max safe feed, cooling failure, maps       (Part 9)
   8 design_optimization: policy, UA, sensitivity, MC            (Parts 10-11)
             │
             ▼
   results/README.md ─► report
```

## Schedule

Assumes each experiment takes 1 business day to come back.

| Day | Action |
|---|---|
| Fri Nov 27 | Run 1 back → fit → plan → request Runs 2 + 3 together |
| Mon Nov 30 | Runs 2–3 back → refit → plan → request Runs 4 + 5 |
| Tue Dec 1 | Final fit → submit parameters → request validation data |
| Wed Dec 2 | Validation back → `run_pipeline.py` → all figures and tables |
| Thu Dec 3 | Write discussion sections; AI log into the appendix |
| Fri Dec 4 | Final check, submit before noon |

Five runs sent one at a time cannot finish in time. Batch two runs per request if the TA allows it.

## Your decisions

All of these live in `src/config.py`; reasons and status are in `docs/design_decisions.md`.

| Decision | Current placeholder | Revisit when |
|---|---|---|
| Full-scale fill: 600 L A + 300 L B | 90 % of 1000 L | now |
| B : A feed ratio | 1.0 | after fit |
| Batch time / target conversion | 240 min / 0.95 | after fit |
| Safety margins: normal / cooling failure | 15 K / 5 K | §9.1 of the report |
| High-T interlock trip | 70 °C | after the safety results |
| Nominal Part A case | T0 = Tc = 40 °C, 120 min feed | after fit |
| UA scaling | ∝ V^(2/3), about 670 W/K | fixed (the design step sweeps UA) |
| Safety screen for requests | predicted T_max ≤ 80 °C at the fitted Ea and both ends of its 95 % CI | set (Part 5) |
| Stopping rule | adequate fit (s² 0.8–1.25), then all 95 % CIs ≤ ±5 % or best batch cuts the worst SE by < 10 % | set (Part 5) |

## Status

- [x] Pipeline built and checked on synthetic data: true parameters recovered inside the 95 % CI, all verification checks pass
- [x] Report skeleton (`report/drafts/ENCH421_Report_Skeleton.docx`)
- [x] Run 1 data → `data/raw/`, fitted; Runs 2–3 requested
- [ ] Runs 2–5, validation, report
