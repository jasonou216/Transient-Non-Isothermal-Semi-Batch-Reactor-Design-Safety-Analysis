"""Part B - Choose the NEXT experiment request (sequential, model-based design).

For each candidate condition the current model (fit so far, or PRIOR before any data)
predicts:
  * T_max  -> reject candidates that come within MARGIN of the 100 C limit
  * information gain = log det(F_existing + F_candidate), where F = S^T W S is the Fisher
    information from output sensitivities S = d(CA,CB,CC,T)/d(theta) at the sampled times
    (D-optimal design). Larger = shrinks the joint confidence region of (k_ref, Ea, dH) most.
Use the ranking as evidence for your request rationale; the final choice is yours.

    python src/plan_experiments.py --dataset real [--n_points 40]
"""
import argparse
import itertools

import numpy as np
import pandas as pd

import config as C
from common import bench_reactor, kin_from_theta, load_runs, out_dir
from model import simulate

MARGIN = 20.0                                       # K below T_LIMIT for a planned run
GRID = dict(T0=[293.15, 303.15, 313.15, 323.15, 333.15],
            q=[0.02, 0.04, 0.08],
            eq_B=[1.0, 1.5],                        # mol B fed / mol A charged
            dTc=[-10.0, 0.0])                       # Tc - T0


def sensitivities(theta, cond, T_ref, t, sig, rel=1e-3):
    cols = []
    for i in range(3):
        h = rel * max(abs(theta[i]), 1.0)
        out = []
        for s in (+1, -1):
            th = theta.copy()
            th[i] += s * h
            sim = simulate(bench_reactor(cond), kin_from_theta(th, T_ref), t[-1], t_eval=t)
            out.append(np.concatenate([sim[v].to_numpy() / sig[v] for v in ["CA", "CB", "CC", "T"]]))
        cols.append((out[0] - out[1]) / (2 * h))
    return np.column_stack(cols)


def main(dataset, n_points=40):
    runs = load_runs(dataset)
    fitfile = C.RESULTS_DIR / dataset / "1_fit" / "params.json"
    if runs and fitfile.exists():
        import json
        d = json.loads(fitfile.read_text())
        theta, T_ref, sig = np.array(d["theta"]), d["T_ref"], d["noise_sigma"]
        src = f"current fit on {d['runs']}"
    else:
        p = C.PRIOR
        theta, T_ref = np.array([np.log(p["k_ref"]), p["Ea"] / 1e3, p["dH"] / 1e3]), p["T_ref"]
        sig = dict(CA=0.03, CB=0.03, CC=0.03, T=0.5)
        src = "PRIOR guess (no data yet)"
    print(f"Planning with {src}")

    F0 = 1e-6 * np.eye(3)
    for r in runs:
        S = sensitivities(theta, r["cond"], T_ref, r["data"]["t"].to_numpy(), sig)
        F0 += S.T @ S
    kin = kin_from_theta(theta, T_ref)
    rows = []
    NA0 = C.BENCH["CA0"] * C.BENCH["V0"]
    for T0, q, eq, dTc in itertools.product(*GRID.values()):
        t_feed = eq * NA0 / C.BENCH["CBf"] / q
        cond = dict(T0=T0, q=q, t_feed=t_feed, Tc=T0 + dTc, t_final=round(t_feed + 60, -1))
        t = np.linspace(0, cond["t_final"], n_points)
        sim = simulate(bench_reactor(cond), kin, cond["t_final"])
        if sim["T"].max() > C.T_LIMIT - MARGIN:
            continue
        S = sensitivities(theta, cond, T_ref, t, sig)
        gain = np.linalg.slogdet(F0 + S.T @ S)[1] - np.linalg.slogdet(F0)[1]
        se_new = np.sqrt(np.diag(np.linalg.inv(F0 + S.T @ S)))
        rows.append(dict(T0_K=T0, feed_flow_Lmin=q, feed_duration_min=round(t_feed, 1),
                         T_coolant_K=T0 + dTc, t_final_min=cond["t_final"], eq_B=eq,
                         pred_T_max_K=round(sim["T"].max(), 1), pred_X_end=round(sim["XA"].iloc[-1], 3),
                         info_gain=gain, se_Ea_after=se_new[1], se_dH_after=se_new[2]))
    table = pd.DataFrame(rows).sort_values("info_gain", ascending=False)
    folder = out_dir(dataset, "0_experiment_planning")
    table.to_csv(folder / f"candidates_after_{len(runs)}_runs.csv", index=False)
    print(table.head(10).to_string(index=False, float_format=lambda x: f"{x:.3g}"))
    return table


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    ap.add_argument("--n_points", type=int, default=40)
    a = ap.parse_args()
    main(a.dataset, a.n_points)
