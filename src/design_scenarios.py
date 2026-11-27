"""Part D decision support: how the recommended design and its robustness change with the
conversion target and the batch time.

For each (target, batch time) the design grid is searched with the same selection rule as
design.py (smallest UA reaching the target, then largest safety margin), and the chosen design
is checked against fitted-parameter uncertainty by Monte Carlo.

    python src/design_scenarios.py --dataset real
"""
import argparse

import pandas as pd

import config as C
import design
from common import load_fit, out_dir, sample_kinetics

SCENARIOS = [(0.95, 240.0), (0.92, 240.0), (0.90, 240.0), (0.95, 300.0), (0.95, 360.0)]
N_MC = 200


def main(dataset):
    kin, theta, cov, _ = load_fit(dataset)
    UA0 = C.ua_scaled(C.FULL["V0"] + design.full_V_B())
    grids, rows = {}, []
    samples = sample_kinetics(theta, cov, kin.T_ref, N_MC, seed=1)
    for target, batch in SCENARIOS:
        C.TARGET_X, C.BATCH_TIME = target, batch
        if batch not in grids:
            print(f"grid search, batch time {batch:.0f} min ...")
            grids[batch] = design.optimise(kin, design.UA_FACTORS)
        rec, met = design.pick(grids[batch])
        d = {k: (rec[k] if k == "policy" else float(rec[k]))
             for k in ["policy", "t_feed", "frac", "ratio", "Tc", "UA_factor"]}
        mc = pd.DataFrame([design.evaluate(k, d) for k in samples])
        rows.append(dict(target_X=target, batch_min=batch, meets_target=met, policy=d["policy"],
                         t_feed_min=d["t_feed"], Tc_C=d["Tc"] - 273.15, UA_W_K=d["UA_factor"] * UA0,
                         X_A=rec["XA_end"], T_peak_C=rec["T_max"] - 273.15,
                         MTSR_max_C=rec["MTSR_max"] - 273.15, margin_K=rec["margin_K"],
                         P_unsafe=1 - mc.safe.mean(), MTSR_p95_C=mc.MTSR_max.quantile(0.95) - 273.15,
                         X_A_p05=mc.XA_end.quantile(0.05)))
        print(rows[-1])
    table = pd.DataFrame(rows)
    table.to_csv(out_dir(dataset, "5_design") / "scenarios.csv", index=False)
    print(table.round(3).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
