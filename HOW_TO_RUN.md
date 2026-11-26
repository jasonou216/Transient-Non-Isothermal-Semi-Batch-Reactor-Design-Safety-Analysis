# How to run

Requires Python 3.10+.

```bash
pip install -r requirements.txt
```

## Reproduce every result in the report

```bash
python src/run_all.py --dataset real
```

Runs every step in order and writes figures, tables and `results/real/SUMMARY.md`.
Takes about 3–5 minutes, mostly the design grid search.

## Steps (each can be run on its own, in this order)

| Step | Command | Output folder |
|---|---|---|
| Fit k_ref, Ea, ΔH (Part B) | `python src/fit_parameters.py --dataset real` | `results/real/1_fit/` |
| Model verification checks | `python src/verify_model.py --dataset real` | `results/real/0_verification/` |
| Rank candidate next experiments (add `--batch 2` to plan a pair) | `python src/plan_experiments.py --dataset real --batch 2` | `results/real/0_experiment_planning/` |
| Validation on held-out run | `python src/validate.py --dataset real` | `results/real/2_validation/` |
| Full-scale nominal case (Part A) | `python src/full_scale.py --dataset real` | `results/real/3_full_scale/` |
| Safety and runaway (Part C) | `python src/safety.py --dataset real` | `results/real/4_safety/` |
| Design and sensitivity (Part D) | `python src/design.py --dataset real` | `results/real/5_design/` |

## Adding experimental data

1. Put the file returned by the TA (CSV or Excel with columns `time_min, CA_molL, CB_molL, CC_molL, T_K`)
   in `data/experiments/`.
2. Add one row to `data/experiments/runs.csv` with the conditions you requested.
3. Re-run `fit_parameters.py`, then `plan_experiments.py` to choose the next request.

The validation run goes in `data/validation/`, with its own `runs.csv` in the same format.

## Settings

All design choices (full-scale volumes, batch time, target conversion, safety margins, interlock
temperature, nominal case) are in `src/config.py`.

## Pipeline self-test

```bash
python src/make_synthetic.py
python src/run_all.py --dataset synthetic
```

`make_synthetic.py` generates invented data with known parameters. Use it only to check that the
pipeline recovers them; synthetic results are not project results.
