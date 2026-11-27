# How to run

This page takes you from a fresh download to every figure and table in the report, then explains
each step on its own: what it computes, why, and what it writes.

## 1. Prerequisites

- Python 3.10 or newer (tested on 3.13). Check with `python --version`.
- About 200 MB of disk space for the packages.
- No other software. Everything runs on a laptop in a few minutes.

## 2. Install

Run these from the repository folder (the one that holds this file).

Create a virtual environment, so the project's packages don't mix with anything else on your
computer:

```bash
python -m venv .venv
```

Activate it. On Windows (PowerShell):

```bash
.venv\Scripts\Activate.ps1
```

On macOS or Linux:

```bash
source .venv/bin/activate
```

Install the packages:

```bash
pip install -r requirements.txt
```

For the tests and the formatted tables in `results/README.md`, also install:

```bash
pip install -r requirements-dev.txt
```

## 3. Quick start: reproduce the report results

```bash
python src/run_pipeline.py
```

This takes about 2 minutes. It runs the eight steps in Section 5 in order and finishes by writing
**`results/README.md`**: an index of every figure and table, each with its caption and the report
part it belongs to. Open that file first.

Then run the two optional steps (Section 5, steps 9 and 10) if you need the design scenarios or the
Excel workbook.

To check the code is working without waiting for the full pipeline:

```bash
python -m pytest
```

Ten tests, under 5 seconds. If any fail, something in the model has been broken.

## 4. Where things go

| Folder | What is in it | Who writes it |
|---|---|---|
| `data/raw/` | Bench data files exactly as the TA returned them | you (copy the file in) |
| `data/experiments/` | `runs.csv`, `validation_runs.csv`: the conditions of each run | you (one row per run) |
| `data/processed/` | Fitted parameters, each run's data next to the model with residuals, large grids | the code |
| `results/figures/` | `fig01` ... `fig12`, numbered in report order | the code |
| `results/tables/` | `part4_...` ... `part11_...`, named by report part | the code |
| `results/README.md` | Index of the figures and tables | the code |

Rule of thumb: you only ever edit `data/raw/`, `data/experiments/` and `src/config.py`. Everything
else is regenerated, so never edit it by hand.

## 5. The steps one by one

Every command accepts `--dataset synthetic` to run on the self-test data instead (Section 8). Run
them in this order, because each step reads what the earlier ones wrote.

### Step 1: parameter estimation (Part 6)

```bash
python src/parameter_estimation.py
```

**What it does.** For a trial set of parameters θ = [ln k_ref, E_a, ΔH_rxn] it solves the reactor
balances for each bench run at that run's exact conditions and compares the predictions with the
measured C_A, C_B, C_C and T. `scipy.optimize.least_squares` adjusts θ until the weighted sum of
squared residuals is smallest. Each variable is divided by its own noise level, so a 0.5 K
temperature error and a 0.03 mol/L concentration error count equally. The fit starts from eight
different guesses, so it cannot stop in a local minimum. The parameter covariance
Cov = s²(JᵀJ)⁻¹ then gives the standard errors and 95 % confidence intervals.

**Writes.** `fig01_fit_runs.png`, `fig02_fit_residuals.png`, `part6_fitted_parameters.csv`,
`part6_parameter_correlation.csv`, `data/processed/fitted_parameters.json` (read by every later
step) and `data/processed/<run>_processed.csv` (each measurement, the model at the same time, and
the residual).

**What to look at.** s² close to 1 means the model fits to within the noise. Residuals should
scatter randomly about zero; a trend means a missing effect. A wide CI means the data so far do not
pin that parameter down.

### Step 2: model verification (Part 4)

```bash
python src/model_verification.py
```

**What it does.** It proves the solver solves the equations correctly, which is a separate question
from whether the equations describe the real reactor (that is validation, step 5). It checks, on the
bench case and the 1000 L case: atom balances (N_A + N_C stays at N_A0); the volume balance; the
adiabatic energy identity (with no cooling, every joule released must appear as temperature rise);
the isothermal analytic solution 1/C_A = 1/C_A0 + kt after the feed stops; that tightening the
solver tolerance changes nothing; and that the MTSR formula matches a simulated cooling failure.

**Writes.** `part4_verification_checks.csv` (Table 3 of the report). All 16 rows should pass.

### Step 3: verification worked examples (Appendix E)

```bash
python src/verification_examples.py
```

**Writes.** `appendixE_worked_examples.json`: the numbers used in the hand calculations, so the
appendix can be checked line by line against the code.

### Step 4: experiment planning (Part 5)

```bash
python src/experiment_planning.py --batch 2
```

**What it does.** For every candidate bench run (start temperature, feed rate, amount of B, coolant
temperature) it predicts how much that run would shrink the confidence region of the parameters.
This is the D-optimal criterion: maximise det(F), where F is the Fisher information matrix, built
from how strongly each prediction responds to each parameter. Candidates predicted to exceed 80 °C at
either end of the E_a confidence interval are removed first, for safety. `--batch 2` picks two runs
jointly, so the second complements the first instead of repeating it (the default, since runs
are requested in pairs). `--n_points` (default 150) is the number of samples per run you will ask
the TA for: more samples carry more information, so it must match the actual request. Finally it applies the
stopping rule: is the fit adequate, and is one more run still worth it?

**Writes.** `part5_candidates_after_<n>_runs.csv` (every candidate, ranked),
`part5_next_<k>_runs_after_<n>.csv` (the recommended request).

### Step 5: model validation (Part 7)

```bash
python src/model_validation.py
```

**What it does.** It predicts the held-out validation run with the fitted parameters, with no
retuning, and reports the errors. It also draws a 95 % band from the parameter uncertainty, so you
can see whether the data fall inside what the model claims to know. It is skipped until
`data/experiments/validation_runs.csv` lists a run.

**Writes.** `fig03_validation_<run>.png`, `part7_validation_errors.csv` (Table 6).

### Step 6: full-scale nominal operation (Part 8)

```bash
python src/plant_simulation.py
```

**What it does.** It runs the 1000 L reactor at the nominal conditions in `config.NOMINAL` and
compares it with the bench reactor on the same schedule. The plant runs hotter because jacket area
grows as V^(2/3) while heat released grows as V, so cooling per litre falls on scale-up.

**Writes.** `fig04_plant_nominal_profiles.png`, `fig05_bench_vs_plant.png`,
`part8_nominal_summary.json`, `data/processed/plant_nominal_profiles.csv`.

### Step 7: safety analysis (Part 9)

```bash
python src/safety_analysis.py
```

**What it does.** Three analyses:

- **Feed-rate scan.** Find the fastest feed that keeps both the peak temperature and the MTSR
  within their limits. MTSR is the temperature reached if cooling stops and all unreacted B reacts
  adiabatically.
- **Cooling-failure scan.** Fail the cooling at each time in the batch, with and without the
  high-temperature feed interlock.
- **Runaway maps.** Map safe and unsafe regions over feed rate against UA, and over feed rate
  against coolant temperature.

**Writes.** `fig06` to `fig09`, `part9_feed_rate_scan.csv`, `part9_cooling_failure_scan.csv`,
`part9_safety_summary.json`, and the map grids in `data/processed/`.

### Step 8: design recommendation and robustness (Parts 10–11)

```bash
python src/design_optimization.py
```

**What it does.** It searches feed policy (constant or staged), feed time, coolant temperature and
jacket UA. Among designs that are safe and reach the target conversion, it picks the smallest UA,
then the largest safety margin. It then tests the choice against E_a ±10 % and UA −20 %, and runs a
Monte Carlo over the fitted-parameter uncertainty. A "grid edge" warning means the optimum sits at
the boundary of the search, so the true optimum may lie outside it.

**Writes.** `fig10` to `fig12`, `part10_design_summary.json` (Table 7),
`part10_best_design_per_UA.csv`, `part10_recommended_cooling_failure.csv`,
`part11_sensitivity.csv`, and `data/processed/design_grid.csv` and `monte_carlo_samples.csv`.

### Step 9 (optional): design scenarios (Part 10 discussion)

```bash
python src/design_scenarios.py
```

About 4 minutes. It repeats the design search for other conversion targets (0.90, 0.92, 0.95) and
batch times (240, 300, 360 min), to show the trade-off between conversion and safety margin.
Writes `part10_design_scenarios.csv`.

### Step 10 (optional): results workbook (Appendix C)

```bash
python src/results_workbook.py
```

It builds `results/tables/ENCH421_Results_by_Run.xlsx`: one tab per run with the data, the mole and
conversion calculations as live formulas, the fitted model, residuals and charts. Upload it to Google
Drive to open it as a Google Sheet.

## 6. Adding a new bench run

1. Copy the file the TA returned into `data/raw/` without changing it. It can be CSV or Excel, with
   columns `time_min, CA_molL, CB_molL, CC_molL, T_K`.
2. Add one row to `data/experiments/runs.csv` with the conditions you requested. The `file` column
   is the file name in `data/raw/`. Leave `T_feed_K` blank for the default of 25 °C.
3. Refit and plan the next request:

```bash
python src/parameter_estimation.py
```

```bash
python src/experiment_planning.py --batch 2
```

4. When the fit is final, rerun everything:

```bash
python src/run_pipeline.py
```

A validation run goes in the same way, but its row goes in `data/experiments/validation_runs.csv`,
so it is never used in the fit.

## 7. Changing a design decision

Every engineering choice is in `src/config.py`, marked `DECISION`. Examples are the 1000 L fill,
batch time, target conversion, safety margins, interlock temperature and the nominal case.
`docs/design_decisions.md` explains each one and when to revisit it. After a change, rerun from
step 6 (plant simulation) onward, or simply rerun the whole pipeline.

## 8. Pipeline self-test with synthetic data

```bash
python src/synthetic_data.py
```

```bash
python src/run_pipeline.py --dataset synthetic
```

The first command invents five bench runs and one validation run from known parameters
(k_ref = 0.15 L/(mol·min) at 320 K, E_a = 65 kJ/mol, ΔH = −90 kJ/mol) plus realistic noise. The
second runs the whole analysis on them, writing to `results/synthetic_selftest/`. The check is
`part6_truth_recovery_selftest.csv`: every true value should lie inside its fitted 95 % interval.
This proves the regression and uncertainty code work. **None of these numbers belong in the report.**

## 9. Runtimes (laptop)

| Command | Time |
|---|---|
| `pytest` | under 5 s |
| `run_pipeline.py` (real, 1 run) | about 2 min |
| `run_pipeline.py --dataset synthetic` (5 runs) | about 3 min |
| `design_scenarios.py` | about 4 min |

The fit takes longer as runs are added. Most of the time is spent in the design grid search.

## 10. Troubleshooting

| Message | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'scipy'` (or pandas, ...) | The packages are not installed in the Python you are using. Activate the virtual environment, then `pip install -r requirements.txt`. |
| `ModuleNotFoundError: No module named 'config'` | Run the scripts as `python src/<script>.py` from the repository folder, or from inside `src/`. |
| `No fit for 'real' yet - run parameter_estimation.py first.` | A later step needs `data/processed/fitted_parameters.json`. Run step 1. |
| `[skip] R2: data file ... not found yet` | `runs.csv` lists a run whose file is not in `data/raw/`. Copy it in, or check the spelling in the `file` column. |
| `KeyError: 'time_min'` (or another column) | The data file's column names differ. Rename the headers to `time_min, CA_molL, CB_molL, CC_molL, T_K` (case does not matter). |
| `WARNING: recommended design sits on the edge of the search grid` | The best design is at a limit of the search. Widen that range in `design_optimization.py` and rerun step 8. |
| Tables in `results/README.md` appear as plain text | `tabulate` is not installed: `pip install -r requirements-dev.txt`. |
