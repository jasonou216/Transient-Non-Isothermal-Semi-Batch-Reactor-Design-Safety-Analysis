# Semi-Batch Reactor Scale-Up and Thermal Safety Analysis

**ENCH 421 Chemical Reaction Engineering, design project. Group G33: Jason Ou, Bella Kim.**
Due Fri Dec 4, 2026, 12:00 noon.

This project takes the exothermic liquid-phase reaction **A + B → C** (rate r = k(T) C_A C_B) from
a 2 L bench reactor to a **1000 L jacketed semi-batch reactor**, where A is charged first and B is fed
in. The work answers four questions:

1. **Model (Parts 3–4).** What do the transient mole, volume and energy balances predict, and can
   we show the numerical solution is correct?
2. **Kinetics (Parts 5–7).** Which bench experiments give the most information about the rate
   constant k_ref, the activation energy E_a and the heat of reaction ΔH_rxn? How precisely do
   five runs pin them down, and does the fitted model predict a held-out run?
3. **Safety (Parts 8–9).** How fast can B be fed before the reactor runs away, and what happens
   if cooling fails part-way through the batch?
4. **Design (Parts 10–12).** Which feed policy, coolant temperature and jacket UA reach the target
   conversion safely, and how robust is that choice to uncertain parameters?

## Status (Nov 28)

| Stage | State |
|---|---|
| Model, solver and verification | Done. All 16 verification checks pass (`results/tables/part4_verification_checks.csv`). |
| Pipeline self-test on synthetic data | Done. True parameters recovered inside the 95 % confidence intervals. |
| Bench experiments | **Runs 1–3 received.** The stopping rule now says stop; the group decides whether to use Runs 4–5. |
| Parameter fit | Fit 2 (Runs 1–3). |
| Validation run | Not yet released. |
| Plant, safety and design results | Computed with Fit 2. The target conversion, batch time and trip setting are still being decided. |
| Report | In progress. |

### Current results (Fit 2, Runs 1–3)

| Quantity | Value | Source |
|---|---|---|
| k_ref at 315 K | 0.01964 L/(mol·min), ±0.6 % | `results/tables/part6_fitted_parameters.csv` |
| E_a | 57.7 kJ/mol, ±0.5 % (Fit 1 was 47 ± 22 kJ/mol) | same |
| ΔH_rxn | −83.6 kJ/mol, ±0.8 % | same |
| Fit quality | s² = 1.002, no residual trend in any run | `data/processed/fitted_parameters.json` |
| Max safe feed rate (MTSR criterion) | 12.5 L/min | `results/tables/part9_safety_summary.json` |
| Design for X_A ≥ 0.95 in 240 min | staged feed over 125 min, coolant 40 °C; peak 71.2 °C, MTSR 80.3 °C | `results/tables/part10_design_summary.json` |
| Other targets and batch times | see the scenario table and the trip-setting sweep | `part10_design_scenarios.csv`, `part10_trip_sweep.csv` |

Every figure and table, with a caption and the report section it belongs to, is listed in
**[results/README.md](results/README.md)**.

## Repository structure

```
.
├── README.md                   this file
├── HOW_TO_RUN.md               install, run, add new data, troubleshoot
├── requirements.txt            Python packages (tested versions)
├── requirements-dev.txt        extra packages for the tests
│
├── src/                        the analysis code (one module per step, run in this order)
│   ├── config.py               every constant and engineering DECISION in one place
│   ├── semi_batch_model.py     balances, ODE solver, derived safety quantities
│   ├── parameter_estimation.py weighted nonlinear least squares for k_ref, Ea, dH
│   ├── model_verification.py   checks that the solver solves the equations correctly
│   ├── verification_examples.py  numbers for the hand calculations (Appendix E)
│   ├── experiment_planning.py  D-optimal choice of the next bench runs, stopping rule
│   ├── model_validation.py     predicts held-out runs without retuning
│   ├── plant_simulation.py     1000 L nominal case, bench vs plant
│   ├── safety_analysis.py      max safe feed rate, cooling failure, runaway maps
│   ├── design_optimization.py  design search, sensitivity, Monte Carlo
│   ├── design_scenarios.py     how the design changes with target and batch time
│   ├── results_workbook.py     Excel workbook of every run with live formulas
│   ├── results_pack.py         one document with every figure and table (Word / Google Doc)
│   ├── synthetic_data.py       invented data with known parameters (self-test)
│   ├── run_pipeline.py         runs every step and writes results/README.md
│   └── common.py               data loading, reactor builders, file paths
│
├── data/
│   ├── raw/                    bench data exactly as returned by the TA (never edited)
│   ├── experiments/            runs.csv and validation_runs.csv: conditions of each run
│   ├── processed/              written by the code: fitted parameters, per-run residuals, grids
│   └── synthetic/              self-test data set (raw / experiments / processed)
│
├── results/
│   ├── README.md               index: every figure and table with caption and report part
│   ├── figures/                fig01 ... fig12, numbered in report order
│   ├── tables/                 part4_ ... part11_ CSV/JSON tables, named by report part
│   └── synthetic_selftest/     the same outputs for the synthetic data (not for the report)
│
├── tests/                      pytest checks (conservation, analytic limits, data layout)
│
├── report/
│   ├── ENCH421_Final_Report.pdf  final submission (added at the end)
│   └── drafts/                 report skeleton and section drafts
│
└── docs/
    ├── design_decisions.md     every decision, its value, the reason, and when to revisit
    ├── project_plan.md         schedule and pipeline diagram
    ├── project_brief/          assignment statement, bench parameters, rubric
    └── references/             course tutorial and computational lab handouts
```

## How the pieces fit together

```
data/raw/ + data/experiments/runs.csv
        │
        ▼
 parameter_estimation ──► data/processed/fitted_parameters.json ──┐
        │                                                         │
        ├─► experiment_planning: which run next? stop yet?        │  every later step
        ├─► model_verification: is the solver right?              │  reads the fitted
        ├─► model_validation: does it predict a new run?          │  parameters
        ▼                                                         │
 plant_simulation ─► safety_analysis ─► design_optimization ◄─────┘
        │
        ▼
 results/figures + results/tables  ─►  results/README.md  ─►  report
```

The same code runs on two data sets. `real` is the bench data. `synthetic` is invented data made
from known parameters: if the fit recovers those parameters, the regression and uncertainty code
work, so it is tested before the real data are trusted to it.

## Quick start

```bash
pip install -r requirements.txt
```

```bash
python src/run_pipeline.py
```

That takes about 2 minutes and rewrites `results/`. See **[HOW_TO_RUN.md](HOW_TO_RUN.md)** for each
step on its own, adding a new run, and troubleshooting.

## Report map

| Report part | Code | Outputs |
|---|---|---|
| 3 Model development | `semi_batch_model.py`, `config.py` | |
| 4 Numerical implementation and verification | `model_verification.py`, `verification_examples.py` | `part4_verification_checks.csv`, `appendixE_worked_examples.json` |
| 5 Experimental design | `experiment_planning.py` | `part5_candidates_*`, `part5_next_*` |
| 6 Parameter estimation | `parameter_estimation.py` | fig01, fig02, `part6_fitted_parameters.csv`, `part6_parameter_correlation.csv` |
| 7 Validation | `model_validation.py` | fig03, `part7_validation_errors.csv` |
| 8 Full-scale nominal operation | `plant_simulation.py` | fig04, fig05, `part8_nominal_summary.json` |
| 9 Runaway and cooling failure | `safety_analysis.py` | fig06–fig09, `part9_*` |
| 10 Design recommendation | `design_optimization.py`, `design_scenarios.py` | fig10, fig11, `part10_*` |
| 11 Sensitivity and robustness | `design_optimization.py` | fig12, `part11_sensitivity.csv` |
| Appendix A Code and how to run | this repository | `HOW_TO_RUN.md` |
| Appendix C Experimental requests and raw data | `results_workbook.py` | `data/raw/`, `data/experiments/` |

## Use of AI tools

The course allows AI tools to help with code and with checking reasoning. The analysis,
interpretation and engineering decisions are the group's own. AI use is logged and the log is
included as Appendix B of the report.
