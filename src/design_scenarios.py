"""Part D decision support: how the recommended design and its robustness change with the
conversion target and the batch time.

For each (target, batch time) the design grid is searched with the same selection rule as
design_optimization.py (smallest UA reaching the target, then largest safety margin), and the chosen design
is checked against fitted-parameter uncertainty by Monte Carlo. For three of the designs it also
sweeps the high-temperature trip setting (part10_trip_sweep.csv): for each trip, does the normal
batch trip by itself (nuisance trip), and how hot does the worst cooling failure get when the
trip cuts the B feed?

    python src/design_scenarios.py --dataset real
"""
import argparse

import numpy as np
import pandas as pd

import config as C
import design_optimization as design
from common import load_fit, sample_kinetics, table_path
from semi_batch_model import metrics, simulate

SCENARIOS = [(0.95, 240.0), (0.92, 240.0), (0.90, 240.0), (0.95, 300.0), (0.95, 360.0)]
N_MC = 200
TRIP_SWEEP_CASES = [(0.95, 240.0), (0.92, 240.0), (0.95, 360.0)]
TRIPS_C = [70, 75, 80, 85, 88, 90]


def trip_sweep(kin, d, batch, n_fail=25):
    """Worst cooling failure (UA -> 0 at every failure time during the feed) for each trip setting."""
    rx = design.reactor_for(d)
    m = metrics(simulate(rx, kin, batch, n=600))
    t_feed_end = max(b for _, b, _ in rx.feed)
    rows = []
    for trip_C in TRIPS_C + [None]:            # None = no interlock: the feed continues after the failure
        trip = None if trip_C is None else trip_C + 273.15
        worst = None
        for tf in np.linspace(0.0, t_feed_end, n_fail):
            after = simulate(rx.with_(t_fail=tf, T_trip=trip), kin, tf + 600.0, n=1200)
            after = after[after.t >= tf]
            if worst is None or after["T"].max() > worst["T"].max():
                worst = after
        rows.append(dict(normal_peak_C=m["T_max"] - 273.15, MTSR_max_C=m["MTSR_max"] - 273.15,
                         trip_C="none" if trip_C is None else trip_C,
                         nuisance_trip=False if trip is None else bool(m["T_max"] >= trip), worst_failure_peak_C=worst["T"].max() - 273.15,
                         max_heating_rate_K_min=worst.dTdt.max()))
    return rows


def main(dataset):
    kin, theta, cov, _ = load_fit(dataset)
    UA0 = C.ua_scaled(C.FULL["V0"] + design.full_V_B())
    grids, rows, sweep, robust = {}, [], [], []
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
                         X_A_p05=mc.XA_end.quantile(0.05), P_below_target=(mc.XA_end < target).mean()))
        print(rows[-1])
        if (target, batch) in TRIP_SWEEP_CASES:
            for case, (k, uam) in {"base": (kin, 1.0), "Ea -10%": (kin.with_(Ea=0.9 * kin.Ea), 1.0),
                                   "Ea +10%": (kin.with_(Ea=1.1 * kin.Ea), 1.0), "plant UA -20%": (kin, 0.8)}.items():
                m = design.evaluate(k, d, uam)
                robust.append(dict(target_X=target, batch_min=batch, case=case, X_A=m["XA_end"],
                                   meets_target=bool(m["XA_end"] >= target), T_peak_C=m["T_max"] - 273.15,
                                   MTSR_max_C=m["MTSR_max"] - 273.15, margin_K=m["margin_K"], safe=bool(m["safe"])))
            for r in trip_sweep(kin, d, batch):
                sweep.append(dict(target_X=target, batch_min=batch, policy=d["policy"], t_feed_min=d["t_feed"],
                                  Tc_C=d["Tc"] - 273.15, **r))
    table = pd.DataFrame(rows)
    table.to_csv(table_path(dataset, "part10_design_scenarios"), index=False)
    print(table.round(3).to_string(index=False))
    robust = pd.DataFrame(robust)
    robust.to_csv(table_path(dataset, "part10_scenario_robustness"), index=False)
    print(robust.round(3).to_string(index=False))
    sweep = pd.DataFrame(sweep)
    sweep.to_csv(table_path(dataset, "part10_trip_sweep"), index=False)
    print(sweep.round(2).to_string(index=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
