"""A2 - Numerical verification of the model (independent of the data).

 1. Mole and volume conservation:  N_A + N_C = N_A0,  N_B + N_C = moles B fed,  V = V0 + volume fed
 2. Energy-balance check: UA = 0 and T_feed = T0  =>  rho cp V (T - T0) = (-dH) N_C  exactly
 3. Isothermal post-feed analytic solution (stoichiometric feed): 1/C_A - 1/C_A(t_f) = k (t - t_f)
 4. Solver-tolerance convergence: rtol 1e-6 vs 1e-11 (max change in T and X_A)
 5. Cooling-failure check: adiabatic, feed stopped at failure => final T equals the MTSR at failure

    python src/model_verification.py --dataset real|synthetic   (uses fitted params if present, else PRIOR)
"""
import argparse

import numpy as np
import pandas as pd

import config as C
from common import bench_reactor, full_reactor, load_fit, table_path
from semi_batch_model import Kinetics, constant_feed, simulate


def main(dataset):
    try:
        kin = load_fit(dataset)[0]
        src = "fitted"
    except FileNotFoundError:
        kin, src = Kinetics(**C.PRIOR), "prior"
    rows = []

    def add(check, case, value, tol, unit):
        rows.append(dict(check=check, case=case, value=value, tolerance=tol, units=unit, passed=abs(value) <= tol))

    # Bench case = the first real experiment's conditions (so the report's Table 3 refers to Run 1);
    # falls back to a generic bench case when no data exist yet.
    from common import load_runs
    runs = load_runs(dataset)
    bench_cond = runs[0]["cond"] if runs else dict(T0=303.15, q=0.04, t_feed=25.0, Tc=298.15)
    cases = {"bench": bench_reactor(bench_cond), "full scale": full_reactor()}
    for name, rx in cases.items():
        t_end = max(b for _, b, _ in rx.feed) + 120
        df = simulate(rx, kin, t_end, n=800)
        Vfed = np.array([sum(q * max(0.0, min(t, b) - a) for a, b, q in rx.feed) for t in df["t"]])
        add("N_A + N_C = N_A0", name, (df.NA + df.NC - rx.NA0).abs().max() / rx.NA0, 1e-6, "relative")
        add("N_B + N_C = B fed", name, (df.NB + df.NC - rx.CBf * Vfed).abs().max() / rx.NA0, 1e-6, "relative")
        add("V = V0 + volume fed", name, (df.V - rx.V0 - Vfed).abs().max() / rx.V0, 1e-6, "relative")

        ad = rx.with_(UA=0.0, T_feed=rx.T0)
        da = simulate(ad, kin, t_end, n=800)
        err = (ad.rhocp * da.V * (da["T"] - ad.T0) + kin.dH * da.NC).abs().max() / (-kin.dH * rx.NA0)
        add("adiabatic energy balance", name, err, 1e-6, "relative")

        iso = rx.with_(isothermal=True)
        di = simulate(iso, kin, t_end, n=800)
        tf = max(b for _, b, _ in rx.feed)
        post = di[di.t >= tf]
        k = kin.k(rx.T0)
        CA_an = 1.0 / (1.0 / post.CA.iloc[0] + k * (post.t - post.t.iloc[0]))
        add("isothermal post-feed analytic C_A", name, (post.CA - CA_an).abs().max() / rx.CA0, 1e-5, "relative")

        lo = simulate(rx, kin, t_end, n=400, rtol=1e-6, atol=1e-6)
        hi = simulate(rx, kin, t_end, n=400, rtol=1e-11, atol=1e-11)
        add("tolerance convergence: T", name, (lo["T"] - hi["T"]).abs().max(), 0.01, "K")
        add("tolerance convergence: X_A", name, (lo.XA - hi.XA).abs().max(), 1e-4, "-")

        t_fail = 0.5 * tf
        mtsr = simulate(rx, kin, t_fail, t_eval=[0.0, t_fail])["MTSR"].iloc[-1]
        fail = rx.with_(t_fail=t_fail, feed=constant_feed(rx.feed[0][2] * t_fail, t_fail))
        Tend = simulate(fail, kin, t_fail + 3000, n=200)["T"].iloc[-1]
        add("adiabatic failure T_final = MTSR", name, Tend - mtsr, 0.05, "K")

    table = pd.DataFrame(rows)
    table.to_csv(table_path(dataset, "part4_verification_checks"), index=False)
    print(f"Model verification ({src} parameters):")
    print(table.to_string(index=False, float_format=lambda x: f"{x:.2e}"))
    print("ALL PASSED" if table.passed.all() else "SOME CHECKS FAILED")
    return table


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
