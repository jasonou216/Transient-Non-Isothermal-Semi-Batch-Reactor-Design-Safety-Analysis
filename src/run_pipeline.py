"""Run the whole analysis in order and write an index of every figure and table.

    python src/run_pipeline.py                      # real bench data  -> results/
    python src/run_pipeline.py --dataset synthetic  # self-test        -> results/synthetic_selftest/

Order of the steps (each one reads what the step before it wrote):
    1  parameter_estimation   fit k_ref, Ea, dH to the bench runs              (Part 6)
    2  model_verification     prove the solver solves the equations correctly  (Part 4)
    3  verification_examples  hand-calculation numbers for Appendix E          (Part 4)
    4  experiment_planning    rank candidate next runs, apply stopping rule    (Part 5)
    5  model_validation       predict held-out runs with no retuning           (Part 7)
    6  plant_simulation       1000 L nominal case                              (Part 8)
    7  safety_analysis        feed-rate scan, cooling failure, runaway maps    (Part 9)
    8  design_optimization    pick the design, sensitivity, Monte Carlo        (Parts 10-11)

Steps whose input does not exist yet (for example validation data) are skipped with a message.
design_scenarios.py and results_workbook.py are run separately (see HOW_TO_RUN.md).
"""
import argparse
import json
import time

import pandas as pd

import config as C
import design_optimization
import experiment_planning
import model_validation
import model_verification
import parameter_estimation
import plant_simulation
import safety_analysis
import verification_examples

STEPS = [("1 Parameter estimation (Part 6)", parameter_estimation.main),
         ("2 Model verification (Part 4)", model_verification.main),
         ("3 Verification worked examples (Appendix E)", verification_examples.main),
         ("4 Experiment planning (Part 5)", experiment_planning.main),
         ("5 Model validation (Part 7)", model_validation.main),
         ("6 Full-scale nominal operation (Part 8)", plant_simulation.main),
         ("7 Safety analysis (Part 9)", safety_analysis.main),
         ("8 Design recommendation and robustness (Parts 10-11)", design_optimization.main)]

# What each figure shows, in report order. Used for the captions in results/README.md.
FIGURES = {
    "fig01_fit_runs": ("Part 6", "Fitted model (lines) against the bench measurements (points) for every "
                       "fitting run. Top: concentrations; bottom: temperature; dotted line: feed stops."),
    "fig02_fit_residuals": ("Part 6", "Residuals (data minus model) against time. Random scatter about zero "
                            "means the model explains the data to within the measurement noise."),
    "fig03_validation_": ("Part 7", "Validation run predicted with the fitted parameters and no retuning. "
                          "Shaded band: 95 % range from the parameter uncertainty."),
    "fig04_plant_nominal_profiles": ("Part 8", "1000 L reactor, nominal case, against time: conversion of A, "
                                     "reactor temperature with the MTSR (cooling-loss ceiling), the three heat "
                                     "flows (reaction, jacket, cold feed) and the concentrations."),
    "fig05_bench_vs_plant": ("Part 8", "Same recipe at bench and plant scale. The plant runs hotter because "
                             "jacket area grows as V^(2/3) while heat release grows as V."),
    "fig06_feed_rate_scan": ("Part 9", "Left: peak temperature (normal operation) and MTSR (cooling loss) "
                             "against feed rate, with both safety limits; this sets the maximum safe feed "
                             "rate. Right: Morbidelli-Varma sensitivity s = d ln T_max / d ln q; a sharp "
                             "peak marks the runaway boundary."),
    "fig07_cooling_failure": ("Part 9", "Total cooling loss during the nominal batch. Left: peak temperature "
                              "reached against the time of failure, with and without the feed interlock, and "
                              "the MTSR at that time. Right: temperature profiles for the worst failure time."),
    "fig08_runaway_map_q_vs_UA": ("Part 9", "Runaway map over feed rate and jacket UA. Green: safe; red: "
                                  "unsafe. Blue line: peak-temperature limit; orange dashed: MTSR limit; "
                                  "black: peak-temperature contours."),
    "fig09_runaway_map_q_vs_Tc": ("Part 9", "Runaway map over feed rate and coolant temperature, same "
                                  "colour code as fig08."),
    "fig10_conversion_vs_UA": ("Part 10", "Best safe conversion reachable at each jacket UA; the "
                               "recommended design is the smallest UA that meets the target."),
    "fig11_recommended_design": ("Part 10", "Recommended design: feed-rate schedule, temperature, MTSR and "
                                 "conversion in normal operation, and the worst-case cooling failure with "
                                 "and without the interlock."),
    "fig12_monte_carlo": ("Part 11", "Monte Carlo over the fitted-parameter uncertainty: spread of "
                          "conversion and MTSR for the recommended design."),
}

# What each table holds, by report part.
TABLES = {
    "part4_verification_checks": ("Part 4", "Table 3: verification checks (conservation, analytic limits, "
                                  "tolerance convergence, MTSR consistency)."),
    "appendixE_worked_examples": ("Appendix E", "Numbers used in the hand calculations."),
    "part5_candidates_after_": ("Part 5", "Every candidate next run, ranked by information gain, after "
                                "the safety screen."),
    "part5_next_": ("Part 5", "Recommended batch of next runs, chosen jointly (greedy D-optimal)."),
    "part6_fitted_parameters": ("Part 6", "Table 5: fitted parameters with standard errors and 95 % CIs."),
    "part6_parameter_correlation": ("Part 6", "Correlation between the fitted parameters."),
    "part6_truth_recovery_selftest": ("Part 6", "Self-test only: true parameters against the fitted 95 % CIs."),
    "part7_validation_errors": ("Part 7", "Table 6: validation errors (RMSE, bias, peak error)."),
    "part8_nominal_summary": ("Part 8", "Nominal full-scale case: conditions and key results."),
    "part9_feed_rate_scan": ("Part 9", "Peak temperature, MTSR and conversion for each feed time."),
    "part9_cooling_failure_scan": ("Part 9", "Outcome of cooling loss at each failure time."),
    "part9_safety_summary": ("Part 9", "Safety criterion, maximum safe feed rate, criticality class."),
    "part10_best_design_per_UA": ("Part 10", "Best design found at each jacket UA."),
    "part10_recommended_cooling_failure": ("Part 10", "Cooling-failure scan for the recommended design."),
    "part10_design_summary": ("Part 10", "Table 7: the recommended design."),
    "part10_design_scenarios": ("Part 10", "Recommended design for other conversion targets and batch times."),
    "part11_sensitivity": ("Part 11", "Effect of Ea +/- 10 % and UA - 20 % on the recommended design."),
    "ENCH421_Results_by_Run": ("Appendix C", "Workbook: every run with its calculations and charts."),
}


def md_table(df):
    try:
        return df.to_markdown(index=False, floatfmt=".4g")
    except ImportError:                       # 'tabulate' not installed
        return "```\n" + df.to_string(index=False) + "\n```"


def describe(name, catalogue):
    for key, val in catalogue.items():
        if name == key or (key.endswith("_") and name.startswith(key)):
            return val
    return ("", "")


def write_index(dataset):
    """results/README.md: every figure (embedded, with caption) and every table, by report part."""
    res = C.DATASETS[dataset]["results"]
    figs = sorted((res / "figures").glob("*.png"))
    tabs = sorted(p for p in (res / "tables").glob("*") if p.suffix in (".csv", ".json", ".xlsx"))
    L = [f"# Results index ({'bench data' if dataset == 'real' else 'synthetic self-test'})", "",
         "Generated by `python src/run_pipeline.py"
         + (" --dataset synthetic" if dataset != "real" else "") + "`. Do not edit by hand.", ""]
    if dataset != "real":
        L += ["> SYNTHETIC DATA. This folder only proves the code recovers known parameters. "
              "None of these numbers go in the report.", ""]
    fitfile = C.DATASETS[dataset]["processed"] / "fitted_parameters.json"
    if fitfile.exists():
        fit = json.loads(fitfile.read_text())
        L += [f"Runs used in the fit: {', '.join(fit['runs'])}. "
              f"Weighted residual variance s^2 = {fit['s2']:.3f} (close to 1 means the model fits to within "
              "the noise).", ""]
        L += ["## Key numbers", "", md_table(pd.read_csv(res / "tables" / "part6_fitted_parameters.csv")), ""]
    ds = res / "tables" / "part10_design_summary.json"
    if ds.exists():
        d = json.loads(ds.read_text())
        rec, met = d.get("recommended", {}), d.get("recommended_metrics", {})
        if rec:
            rows = [("Feed policy", rec["policy"], ""), ("Feed time", f"{rec['t_feed']:.0f}", "min"),
                    ("Coolant temperature", f"{rec['Tc'] - 273.15:.0f}", "C"),
                    ("Jacket UA", f"{rec['UA_W_K']:.0f}", "W/K"),
                    ("Conversion at end of batch", f"{met.get('XA_end', float('nan')):.3f}", "-"),
                    ("Peak temperature", f"{met.get('T_max', float('nan')) - 273.15:.1f}", "C"),
                    ("Highest MTSR", f"{met.get('MTSR_max', float('nan')) - 273.15:.1f}", "C"),
                    ("Margin to the failure limit", f"{met.get('margin_K', float('nan')):.1f}", "K")]
            L += [f"Recommended design (target X_A = {C.TARGET_X} in {C.BATCH_TIME:.0f} min):", "",
                  md_table(pd.DataFrame(rows, columns=["quantity", "value", "units"])), ""]

    L += ["## Figures", "", "| File | Report | What it shows |", "|---|---|---|"]
    for f in figs:
        part, cap = describe(f.stem, FIGURES)
        L.append(f"| [{f.name}](figures/{f.name}) | {part} | {cap} |")
    L.append("")
    for f in figs:
        part, cap = describe(f.stem, FIGURES)
        L += [f"### {f.stem} ({part})", "", f"![{f.stem}](figures/{f.name})", "", cap, ""]

    L += ["## Tables", "", "| File | Report | What it holds |", "|---|---|---|"]
    for f in tabs:
        part, cap = describe(f.stem, TABLES)
        L.append(f"| [{f.name}](tables/{f.name}) | {part} | {cap} |")
    L.append("")
    for name in ["part4_verification_checks", "part7_validation_errors", "part11_sensitivity",
                 "part10_design_scenarios", "part6_truth_recovery_selftest"]:
        p = res / "tables" / f"{name}.csv"
        if p.exists():
            L += [f"### {name}", "", md_table(pd.read_csv(p)), ""]
    (res / "README.md").write_text("\n".join(L))
    return res / "README.md"


def main(dataset):
    t0 = time.time()
    for name, fn in STEPS:
        print(f"\n=== {name} ===")
        out = fn(dataset)
        if out is None and name.startswith("1 "):
            print("No fitting data yet - running experiment planning on the prior guess only.")
            experiment_planning.main(dataset)
            break
    index = write_index(dataset)
    print(f"\nDone in {time.time() - t0:.0f} s. Index of every figure and table: {index}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
