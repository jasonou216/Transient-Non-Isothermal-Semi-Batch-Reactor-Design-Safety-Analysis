"""Part D - Feed policy, required jacket UA, sensitivity and uncertainty.

 1. Grid search: maximise X_A at BATCH_TIME subject to the safety criterion (config.py),
    over feed policy (constant vs two-stage), coolant/charge temperature and UA.
 2. Selection (config.UA_SELECTION). "installed": among the safe designs that reach TARGET_X with
    the installed jacket (UA_INSTALLED_FACTOR x ua_scaled()), pick the LARGEST safety margin (min of
    the two criterion margins). "smallest": the smallest UA whose best safe design reaches TARGET_X,
    then the largest margin at that UA. The grid over UA is still searched and reported
    (part10_best_design_per_UA.csv) to show how the design depends on jacket size.
 3. Recommended design checked against cooling failure (with / without high-T interlock).
 4. Sensitivity: Ea +/-10 % (k_ref at T_ref held fixed) and plant UA 20 % below assumed:
    (i) recommended design as-is, (ii) re-optimised design.
 5. Monte Carlo over the fitted parameter covariance -> probability the design is unsafe.

    python src/design_optimization.py --dataset real|synthetic
"""
import argparse
import itertools

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C
from common import (fig_path, full_reactor, full_V_B, load_fit, mark_feed, processed_path, sample_kinetics,
                    save_json, table_path)
from semi_batch_model import constant_feed, metrics, simulate, staged_feed
from safety_analysis import T_SAFE_FAIL, T_SAFE_NORMAL, cooling_failure_scan, is_safe

UA_FACTORS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0]
TC_GRID = [303.15, 313.15, 323.15, 333.15, 343.15]
T_FEED_GRID = np.geomspace(15, 200, 12)
STAGED = dict(frac=[0.3, 0.5, 0.7], ratio=[1 / 3, 3.0])          # ratio = q1/q2
N_MC = 300


def policies():
    for tf in T_FEED_GRID:
        yield dict(policy="constant", t_feed=tf, frac=np.nan, ratio=np.nan)
    for tf, f, r in itertools.product(T_FEED_GRID, STAGED["frac"], STAGED["ratio"]):
        yield dict(policy="staged", t_feed=tf, frac=f, ratio=r)


def to_feed(p):
    if p["policy"] == "constant":
        return constant_feed(full_V_B(), p["t_feed"])
    return staged_feed(full_V_B(), p["t_feed"], p["frac"], p["ratio"])


def reactor_for(d, UA_mult=1.0, **kw):
    return full_reactor(feed=to_feed(d), UA_factor=d["UA_factor"] * UA_mult, T0=d["Tc"], Tc=d["Tc"], **kw)


def evaluate(kin, d, UA_mult=1.0):
    m = metrics(simulate(reactor_for(d, UA_mult), kin, C.BATCH_TIME, n=300))
    margin = min(T_SAFE_NORMAL - m["T_max"], T_SAFE_FAIL - m["MTSR_max"])
    return dict(m, safe=is_safe(m), margin_K=margin)


def optimise(kin, UA_factors, UA_mult=1.0):
    rows = []
    for ua, tc, p in itertools.product(UA_factors, TC_GRID, policies()):
        d = dict(p, Tc=tc, UA_factor=ua)
        rows.append(dict(d, **evaluate(kin, d, UA_mult)))
    return pd.DataFrame(rows)


def best_per_ua(grid):
    s = grid[grid.safe]
    return s.loc[s.groupby(["UA_factor", "policy"]).XA_end.idxmax()].sort_values(["UA_factor", "policy"])


def pick(grid):
    """Target-meeting safe design with the largest margin, at the installed UA or the smallest UA."""
    s = grid[grid.safe]
    if s.empty:
        return grid.loc[grid.margin_K.idxmax()], False
    ok = s[s.XA_end >= C.TARGET_X]
    if ok.empty:
        return s.loc[s.XA_end.idxmax()], False
    if C.UA_SELECTION == "installed":
        ok = ok[np.isclose(ok.UA_factor, C.UA_INSTALLED_FACTOR)]
        if ok.empty:
            at = s[np.isclose(s.UA_factor, C.UA_INSTALLED_FACTOR)]
            return (at.loc[at.XA_end.idxmax()] if len(at) else s.loc[s.XA_end.idxmax()]), False
    else:
        ok = ok[ok.UA_factor == ok.UA_factor.min()]
    return ok.sort_values("margin_K", ascending=False).iloc[0], True


def main(dataset):
    kin, theta, cov, _ = load_fit(dataset)
    UA0 = C.ua_scaled(C.FULL["V0"] + full_V_B())
    print(f"Grid search ({len(UA_FACTORS) * len(TC_GRID) * len(list(policies()))} designs)...")
    grid = optimise(kin, UA_FACTORS)
    grid.to_csv(processed_path(dataset, "design_grid.csv"), index=False)
    best = best_per_ua(grid)
    best.to_csv(table_path(dataset, "part10_best_design_per_UA"), index=False)
    rec, met = pick(grid)
    rec_d = {k: (rec[k] if k == "policy" else float(rec[k])) for k in ["policy", "t_feed", "frac", "ratio", "Tc", "UA_factor"]}
    edges = [n for n, v, g in [("UA", rec_d["UA_factor"], UA_FACTORS), ("Tc", rec_d["Tc"], TC_GRID),
                               ("t_feed", rec_d["t_feed"], T_FEED_GRID)] if v in (min(g), max(g))]
    if edges:
        print(f"WARNING: recommended design sits on the edge of the search grid for {edges} - "
              "widen that grid in design_optimization.py before trusting the optimum.")

    fig, a = plt.subplots(figsize=(6, 4))
    for pol, g in best.groupby("policy"):
        a.plot(g.UA_factor * UA0, g.XA_end, "o-", label=f"best safe {pol} feed")
    a.axhline(C.TARGET_X, color="grey", ls="--", label=f"target X = {C.TARGET_X}")
    a.set_xlabel("jacket UA (W/K)")
    a.set_ylabel(f"X_A at {C.BATCH_TIME:.0f} min")
    a.set_title("Best safe conversion vs installed cooling capacity")
    a.legend(fontsize=8)
    fig.savefig(fig_path(dataset, "fig10_conversion_vs_UA"))
    plt.close(fig)

    # recommended design: profiles + cooling failure
    rx = reactor_for(rec_d)
    df = simulate(rx, kin, C.BATCH_TIME, n=1200)
    cf, worst = cooling_failure_scan(rx, kin, C.BATCH_TIME)
    cf.to_csv(table_path(dataset, "part10_recommended_cooling_failure"), index=False)
    fig, ax = plt.subplots(1, 3, figsize=(14, 3.8))
    ax[0].plot(df.t, df.q, label="q (L/min)")
    ax[0].set_ylabel("B feed rate (L/min)")
    ax[1].plot(df.t, df["T"], label="T")
    ax[1].plot(df.t, df.MTSR, "--", label="MTSR")
    ax[1].axhline(C.T_LIMIT, color="r", lw=1, label="T limit")
    ax[1].set_ylabel("T (K)")
    ax2 = ax[1].twinx()
    ax2.plot(df.t, df.XA, color="C2", label="X_A")
    ax2.set_ylabel("X_A", color="C2")
    ax2.grid(False)
    for c, (row, d) in worst.items():
        ax[2].plot(d.t, d["T"], label=f"{c}, fail at {row['t_fail']:.0f} min")
    ax[2].axhline(C.T_LIMIT, color="r", lw=1)
    ax[2].axhline(C.T_TRIP, color="grey", ls=":", lw=1, label="interlock trip")
    ax[2].set_title("worst-case cooling failure")
    for a in ax:
        a.set_xlabel("t (min)")
        a.legend(fontsize=7, loc="lower right")
    mark_feed(ax[0], rx.feed)
    fig.suptitle(f"Recommended: {rec_d['policy']} feed over {rec_d['t_feed']:.0f} min, Tc = {rec_d['Tc']:.0f} K, "
                 f"UA = {rec_d['UA_factor'] * UA0:.0f} W/K")
    fig.savefig(fig_path(dataset, "fig11_recommended_design"))
    plt.close(fig)

    # sensitivity
    cases = {"base": (kin, 1.0), "Ea -10%": (kin.with_(Ea=0.9 * kin.Ea), 1.0),
             "Ea +10%": (kin.with_(Ea=1.1 * kin.Ea), 1.0), "plant UA -20%": (kin, 0.8)}
    sens = []
    for name, (k, uam) in cases.items():
        fixed = evaluate(k, rec_d, uam)
        g = optimise(k, UA_FACTORS, uam)
        r, ok = pick(g)
        sens.append(dict(case=name, fixed_XA=fixed["XA_end"], fixed_Tmax=fixed["T_max"],
                         fixed_MTSR=fixed["MTSR_max"], fixed_margin_K=fixed["margin_K"], fixed_safe=fixed["safe"],
                         reopt_policy=r["policy"], reopt_t_feed=r["t_feed"], reopt_Tc=r["Tc"],
                         reopt_UA_W_K=r["UA_factor"] * UA0 * uam, reopt_XA=r["XA_end"], reopt_meets_target=ok))
    sens = pd.DataFrame(sens)
    sens.to_csv(table_path(dataset, "part11_sensitivity"), index=False)

    # parameter-uncertainty Monte Carlo on the recommended design
    mc = pd.DataFrame([evaluate(k, rec_d) for k in sample_kinetics(theta, cov, kin.T_ref, N_MC, seed=1)])
    mc.to_csv(processed_path(dataset, "monte_carlo_samples.csv"), index=False)
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.5))
    ax[0].hist(mc.T_max, 30)
    ax[0].axvline(T_SAFE_NORMAL, color="r", ls="--")
    ax[0].set_xlabel("T_max (K)")
    ax[1].hist(mc.MTSR_max, 30, color="C1")
    ax[1].axvline(T_SAFE_FAIL, color="r", ls="--")
    ax[1].set_xlabel("MTSR_max (K)")
    fig.suptitle(f"Recommended design under fitted-parameter uncertainty ({N_MC} samples)")
    fig.savefig(fig_path(dataset, "fig12_monte_carlo"))
    plt.close(fig)

    summary = dict(UA_scaled_W_K=UA0, recommended=dict(rec_d, UA_W_K=rec_d["UA_factor"] * UA0),
                   recommended_meets_target=met,
                   recommended_metrics={k: rec[k] for k in ["XA_end", "T_max", "MTSR_max", "margin_K", "S_max", "acc_max"]},
                   worst_cooling_failure={c: worst[c][0] for c in worst},
                   monte_carlo=dict(P_unsafe=float(1 - mc.safe.mean()),
                                    T_max_p95=float(mc.T_max.quantile(0.95)),
                                    MTSR_max_p95=float(mc.MTSR_max.quantile(0.95)),
                                    XA_p05=float(mc.XA_end.quantile(0.05))),
                   sensitivity=sens.to_dict("records"))
    save_json(summary, table_path(dataset, "part10_design_summary", "json"))
    print(best[["UA_factor", "policy", "t_feed", "frac", "ratio", "Tc", "XA_end", "T_max", "MTSR_max", "margin_K"]]
          .round(3).to_string(index=False))
    print("Recommended:", {k: (round(v, 3) if isinstance(v, float) else v) for k, v in summary["recommended"].items()})
    print(sens.round(3).to_string(index=False))
    print("Monte Carlo:", summary["monte_carlo"])
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
