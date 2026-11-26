"""Run the whole pipeline and write results/<dataset>/SUMMARY.md (numbers for the report).

    python src/run_all.py --dataset real         # your experiments
    python src/run_all.py --dataset synthetic    # pipeline self-test with invented data

Steps that need data that do not exist yet are skipped with a message.
"""
import argparse
import json
import time

import pandas as pd

import config as C
import design
import fit_parameters
import full_scale
import plan_experiments
import safety
import validate
import verify_model


def table(df):
    try:
        return df.to_markdown(index=False, floatfmt=".4g")
    except ImportError:                       # 'tabulate' not installed
        return "```\n" + df.to_string(index=False) + "\n```"


def main(dataset):
    t0 = time.time()
    res = C.RESULTS_DIR / dataset
    steps = [("Parameter fit (Part B)", fit_parameters.main), ("Model verification (A2)", verify_model.main),
             ("Next-experiment planning (Part B)", plan_experiments.main),
             ("Validation (Part B)", validate.main), ("Full scale nominal (Part A)", full_scale.main),
             ("Safety (Part C)", safety.main), ("Design (Part D)", design.main)]
    for name, fn in steps:
        print(f"\n=== {name} ===")
        out = fn(dataset)
        if out is None and name.startswith("Parameter fit"):
            print("No data yet - stopping after experiment planning.")
            plan_experiments.main(dataset)
            return

    lines = [f"# Pipeline summary - dataset: `{dataset}`", ""]
    if dataset == "synthetic":
        lines += ["> SYNTHETIC DATA - pipeline self-test only. Do not use these numbers in the report.", ""]
    lines += ["## Fitted parameters", table(pd.read_csv(res / "1_fit" / "params_table.csv")), ""]
    if (res / "1_fit" / "truth_recovery.csv").exists():
        lines += ["### Truth recovery (synthetic)", table(pd.read_csv(res / "1_fit" / "truth_recovery.csv")), ""]
    lines += ["## Model verification", table(pd.read_csv(res / "0_verification" / "verification.csv")), ""]
    if (res / "2_validation" / "validation_metrics.csv").exists():
        lines += ["## Validation", table(pd.read_csv(res / "2_validation" / "validation_metrics.csv")), ""]
    fs = json.loads((res / "3_full_scale" / "nominal_summary.json").read_text())
    lines += ["## Full scale nominal", "```", json.dumps(fs, indent=1), "```", ""]
    sf = json.loads((res / "4_safety" / "safety_summary.json").read_text())
    lines += ["## Safety", "```", json.dumps(sf, indent=1), "```", ""]
    ds = json.loads((res / "5_design" / "design_summary.json").read_text())
    lines += ["## Design", "```", json.dumps({k: v for k, v in ds.items() if k != "sensitivity"}, indent=1), "```",
              "### Sensitivity", table(pd.read_csv(res / "5_design" / "sensitivity.csv")), ""]
    (res / "SUMMARY.md").write_text("\n".join(lines))
    print(f"\nDone in {time.time() - t0:.0f} s -> {res / 'SUMMARY.md'}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
