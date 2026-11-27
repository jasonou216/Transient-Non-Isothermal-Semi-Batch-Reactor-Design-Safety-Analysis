"""Part B - Choose the NEXT experiment request (sequential, model-based design).

For each candidate condition the current model (fit so far, or PRIOR before any data)
predicts:
  * T_max  -> reject candidates that come within MARGIN of the 100 C limit, checked at the
              fitted Ea AND at its 95 % upper and lower bounds (robust to Ea uncertainty)
  * information gain = log det(F_existing + F_candidate), where F = S^T W S is the Fisher
    information from output sensitivities S = d(CA,CB,CC,T)/d(theta) at the sampled times
    (D-optimal design). Larger = shrinks the joint confidence region of (k_ref, Ea, dH) most.
Use the ranking as evidence for your request rationale; the final choice is yours.

--batch 2 plans two runs to request TOGETHER: greedy D-optimal selection (pick the best run,
add its information, pick the run that best complements it). The pair is chosen jointly, so
the second run is not a near-duplicate of the first.

    python src/plan_experiments.py --dataset real [--batch 2] [--n_points 40]
"""
import argparse
import itertools

import numpy as np
import pandas as pd

import config as C
from common import bench_reactor, kin_from_theta, load_runs, out_dir
from model import simulate

MARGIN = C.T_LIMIT - C.PLAN_T_MAX                   # K below T_LIMIT for a planned run (config)
T_FINAL_MIN = 150.0                                 # min run length (TA: no limit on t_final / n_points)
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


def main(dataset, n_points=40, batch=1):
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
    se_Ea = np.sqrt(np.linalg.inv(F0)[1, 1]) if runs else 0.3 * theta[1]
    kin_band = [kin_from_theta(theta + np.array([0, s * 1.96 * se_Ea, 0]), T_ref) for s in (-1, 1)]
    rows, infos = [], []
    NA0 = C.BENCH["CA0"] * C.BENCH["V0"]
    for T0, q, eq, dTc in itertools.product(*GRID.values()):
        t_feed = eq * NA0 / C.BENCH["CBf"] / q
        cond = dict(T0=T0, q=q, t_feed=t_feed, Tc=T0 + dTc, t_final=max(T_FINAL_MIN, round(t_feed + 60, -1)))
        t = np.linspace(0, cond["t_final"], n_points)
        sim = simulate(bench_reactor(cond), kin, cond["t_final"])
        T_worst = max(simulate(bench_reactor(cond), k, cond["t_final"])["T"].max() for k in kin_band)
        if T_worst > C.T_LIMIT - MARGIN:
            continue
        S = sensitivities(theta, cond, T_ref, t, sig)
        infos.append(S.T @ S)
        gain = np.linalg.slogdet(F0 + S.T @ S)[1] - np.linalg.slogdet(F0)[1]
        se_new = np.sqrt(np.diag(np.linalg.inv(F0 + S.T @ S)))
        rows.append(dict(T0_K=T0, feed_flow_Lmin=q, feed_duration_min=round(t_feed, 1),
                         T_coolant_K=T0 + dTc, t_final_min=cond["t_final"], eq_B=eq,
                         pred_T_max_K=round(sim["T"].max(), 1), T_max_worst_Ea_K=round(T_worst, 1),
                         pred_X_end=round(sim["XA"].iloc[-1], 3),
                         info_gain=gain, se_Ea_after=se_new[1], se_dH_after=se_new[2]))
    table = pd.DataFrame(rows)
    folder = out_dir(dataset, "0_experiment_planning")
    table.sort_values("info_gain", ascending=False).to_csv(
        folder / f"candidates_after_{len(runs)}_runs.csv", index=False)
    print(table.sort_values("info_gain", ascending=False).head(10)
          .to_string(index=False, float_format=lambda x: f"{x:.3g}"))

    if batch > 1:                                  # greedy joint selection
        F, chosen = F0.copy(), []
        for _ in range(batch):
            gains = [np.linalg.slogdet(F + I)[1] if i not in chosen else -np.inf for i, I in enumerate(infos)]
            i = int(np.argmax(gains))
            chosen.append(i)
            F = F + infos[i]
        se0, se1 = np.sqrt(np.diag(np.linalg.inv(F0))), np.sqrt(np.diag(np.linalg.inv(F)))
        pick = table.iloc[chosen].copy()
        pick.insert(0, "request", [f"next #{k + 1}" for k in range(batch)])
        pick.to_csv(folder / f"batch_of_{batch}_after_{len(runs)}_runs.csv", index=False)
        print(f"\nRecommended batch of {batch} (chosen jointly):")
        print(pick.drop(columns=["info_gain", "se_Ea_after", "se_dH_after"]).to_string(index=False))
        print("Predicted std. error  [ln k_ref, Ea kJ/mol, dH kJ/mol]: "
              f"now {np.round(se0, 3)} -> after batch {np.round(se1, 3)}")
        if runs and fitfile.exists():
            stopping_rule(dataset, se0, se1)
    return table


def stopping_rule(dataset, se_now, se_after):
    """Part 5 stopping rule: adequacy first, then precision OR diminishing returns."""
    import json
    d = json.loads((C.RESULTS_DIR / dataset / "1_fit" / "params.json").read_text())
    tab = pd.read_csv(C.RESULTS_DIR / dataset / "1_fit" / "params_table.csv")
    rel = tab["rel_95CI_%"].to_numpy()                   # order: k_ref, Ea, dH (= theta order)
    worst = int(np.argmax(rel))
    gain = (se_now[worst] - se_after[worst]) / se_now[worst]
    lo, hi = C.STOP_S2_RANGE
    adequate = lo <= d["s2"] <= hi
    precise = bool((rel <= C.STOP_REL_CI).all())
    small_gain = gain < C.STOP_MIN_GAIN
    print("\nStopping rule (Part 5):")
    print(f"  adequacy  s^2 = {d['s2']:.3f} within {C.STOP_S2_RANGE}: {adequate}  (also inspect residual plots)")
    print(f"  precision every 95% CI within +/-{C.STOP_REL_CI}%: {precise}  "
          f"(k_ref {rel[0]:.1f}%, Ea {rel[1]:.1f}%, dH {rel[2]:.1f}%)")
    print(f"  diminishing returns: best batch cuts SE of {tab.parameter[worst]} by {100 * gain:.0f}% "
          f"(stop if < {100 * C.STOP_MIN_GAIN:.0f}%): {small_gain}")
    verdict = adequate and (precise or small_gain)
    print("  -> STOP experimenting" if verdict else "  -> CONTINUE: request the recommended batch")
    return verdict


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    ap.add_argument("--n_points", type=int, default=40)
    ap.add_argument("--batch", type=int, default=1)
    a = ap.parse_args()
    main(a.dataset, a.n_points, a.batch)
