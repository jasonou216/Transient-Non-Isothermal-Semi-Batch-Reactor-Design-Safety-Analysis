"""Part B - Simultaneous nonlinear regression of k_ref, Ea and dH on ALL bench runs.

Method
  * theta = [ln k_ref, Ea (kJ/mol), dH (kJ/mol)]; ln k_ref keeps k > 0 and improves conditioning.
  * T_ref = mean measured temperature (rounded to 5 K) -> weakens the k_ref-Ea correlation.
  * Residuals: every measured C_A, C_B, C_C and T, each divided by that variable's noise sigma
    (weighted least squares = max. likelihood for Gaussian noise). Sigmas are re-estimated from
    the residuals and the fit repeated (two-stage), so concentrations and T are weighted fairly.
  * Several starting points -> guards against local minima.
  * Uncertainty: cov = s^2 (J^T J)^-1 (J by central differences), 95 % CI with Student t;
    the correlation matrix shows identifiability.

    python src/parameter_estimation.py --dataset real|synthetic
"""
import argparse
import itertools
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.optimize import least_squares
from scipy.stats import t as student_t

import config as C
from common import (bench_reactor, fig_path, kin_from_theta, load_runs, mark_feed, processed_path,
                    save_json, table_path)
from semi_batch_model import simulate

VARS = ["CA", "CB", "CC", "T"]


def residuals(theta, runs, T_ref, sig):
    kin = kin_from_theta(theta, T_ref)
    res = []
    for run in runs:
        d = run["data"]
        sim = simulate(bench_reactor(run["cond"]), kin, d["t"].max(), t_eval=d["t"].to_numpy())
        for v in VARS:
            e = (sim[v].to_numpy() - d[v].to_numpy()) / sig[v]
            res.append(e[np.isfinite(e)])
    return np.concatenate(res)


def jacobian(theta, runs, T_ref, sig, rel=1e-4):
    cols = []
    for i in range(len(theta)):
        h = rel * max(abs(theta[i]), 1.0)
        tp, tm = theta.copy(), theta.copy()
        tp[i] += h
        tm[i] -= h
        cols.append((residuals(tp, runs, T_ref, sig) - residuals(tm, runs, T_ref, sig)) / (2 * h))
    return np.column_stack(cols)


def per_var_sigma(theta, runs, T_ref, sig):
    kin = kin_from_theta(theta, T_ref)
    err = {v: [] for v in VARS}
    for run in runs:
        d = run["data"]
        sim = simulate(bench_reactor(run["cond"]), kin, d["t"].max(), t_eval=d["t"].to_numpy())
        for v in VARS:
            err[v].append(sim[v].to_numpy() - d[v].to_numpy())
    return {v: float(np.sqrt(np.nanmean(np.concatenate(err[v]) ** 2))) for v in VARS}


def fit(runs):
    T_ref = 5.0 * round(np.mean(np.concatenate([r["data"]["T"].to_numpy() for r in runs])) / 5.0)
    p = C.PRIOR
    k0 = p["k_ref"] * np.exp(-p["Ea"] / C.R * (1 / T_ref - 1 / p["T_ref"]))
    starts = [np.array([np.log(k0 * fk), ea, dh])
              for fk, ea, dh in itertools.product([0.3, 3.0], [40.0, 90.0], [-40.0, -150.0])]
    bounds = ([-20, 1.0, -1000.0], [10, 400.0, 200.0])
    sig = dict(CA=0.05, CB=0.05, CC=0.05, T=1.0)                    # stage-1 guess
    best = min((least_squares(residuals, x0, args=(runs, T_ref, sig), bounds=bounds,
                              diff_step=1e-5, x_scale=[1, 10, 10]) for x0 in starts),
               key=lambda s: s.cost)
    sig = per_var_sigma(best.x, runs, T_ref, sig)                    # stage 2: refit with data-based sigmas
    best = least_squares(residuals, best.x, args=(runs, T_ref, sig), bounds=bounds,
                         diff_step=1e-5, x_scale=[1, 10, 10])
    theta = best.x
    r = residuals(theta, runs, T_ref, sig)
    J = jacobian(theta, runs, T_ref, sig)
    n, npar = r.size, theta.size
    s2 = float(r @ r / (n - npar))
    cov = s2 * np.linalg.inv(J.T @ J)
    return dict(theta=theta, cov=cov, T_ref=T_ref, sig=sig, s2=s2, n=n, dof=n - npar,
                cond_number=float(np.linalg.cond(J.T @ J)), J=J)


def report(res):
    th, cov, dof = res["theta"], res["cov"], res["dof"]
    se = np.sqrt(np.diag(cov))
    tq = student_t.ppf(0.975, dof)
    k = np.exp(th[0])
    rows = [dict(parameter=f"k_ref @ {res['T_ref']:.0f} K", units="L/(mol min)", estimate=k,
                 std_error=k * se[0], ci95_low=np.exp(th[0] - tq * se[0]), ci95_high=np.exp(th[0] + tq * se[0])),
            dict(parameter="Ea", units="kJ/mol", estimate=th[1], std_error=se[1],
                 ci95_low=th[1] - tq * se[1], ci95_high=th[1] + tq * se[1]),
            dict(parameter="dH_rxn", units="kJ/mol", estimate=th[2], std_error=se[2],
                 ci95_low=th[2] - tq * se[2], ci95_high=th[2] + tq * se[2])]
    table = pd.DataFrame(rows)
    table["rel_95CI_%"] = 100 * tq * np.array([se[0], se[1] / abs(th[1]), se[2] / abs(th[2])])
    corr = cov / np.outer(se, se)
    return table, pd.DataFrame(corr, index=["lnk", "Ea", "dH"], columns=["lnk", "Ea", "dH"])


def plot_runs(runs, kin, dataset):
    n = len(runs)
    fig, axes = plt.subplots(2, n, figsize=(3.2 * n, 5.6), squeeze=False, sharex="col")
    for j, run in enumerate(runs):
        d, cond = run["data"], run["cond"]
        sim = simulate(bench_reactor(cond), kin, d["t"].max())
        a, b = axes[0, j], axes[1, j]
        for v, c in zip(["CA", "CB", "CC"], ["C0", "C1", "C2"]):
            a.plot(d["t"], d[v], "o", ms=3, color=c, label=f"{v} data")
            a.plot(sim["t"], sim[v], "-", color=c)
        b.plot(d["t"], d["T"], "o", ms=3, color="C3")
        b.plot(sim["t"], sim["T"], "-", color="C3")
        for ax in (a, b):
            mark_feed(ax, bench_reactor(cond).feed)
        a.set_title(f"{run['run_id']}: T0={cond['T0']:.0f} K, q={cond['q']} L/min,\n"
                    f"t_feed={cond['t_feed']:.0f} min, Tc={cond['Tc']:.0f} K", fontsize=8)
        b.set_xlabel("t (min)")
    axes[0, 0].set_ylabel("C (mol/L)")
    axes[1, 0].set_ylabel("T (K)")
    axes[0, 0].legend(fontsize=7)
    fig.suptitle("Fitted model (lines) vs bench data (points); dotted = feed stop")
    fig.savefig(fig_path(dataset, "fig01_fit_runs"))
    plt.close(fig)

    fig, axes = plt.subplots(1, 4, figsize=(13, 3))
    for run in runs:
        d = run["data"]
        sim = simulate(bench_reactor(run["cond"]), kin, d["t"].max(), t_eval=d["t"].to_numpy())
        for ax, v in zip(axes, VARS):
            ax.plot(d["t"], d[v] - sim[v], "o", ms=3, label=run["run_id"])
    for ax, v in zip(axes, VARS):
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"residual {v} (data - model)")
        ax.set_xlabel("t (min)")
    axes[0].legend(fontsize=7)
    fig.savefig(fig_path(dataset, "fig02_fit_residuals"))
    plt.close(fig)


def write_processed_runs(runs, kin, dataset):
    """data/processed/<run>_processed.csv: each measurement next to the fitted model at the same
    time, with the derived quantities (volume, moles, conversion) and the residuals."""
    for run in runs:
        d, rx = run["data"], bench_reactor(run["cond"])
        sim = simulate(rx, kin, d["t"].max(), t_eval=d["t"].to_numpy())
        out = pd.DataFrame({"time_min": d["t"], "V_L": sim["V"].to_numpy()})
        for v, unit in [("CA", "molL"), ("CB", "molL"), ("CC", "molL"), ("T", "K")]:
            out[f"{v}_{unit}_data"] = d[v].to_numpy()
            out[f"{v}_{unit}_model"] = sim[v].to_numpy()
            out[f"{v}_{unit}_residual"] = out[f"{v}_{unit}_data"] - out[f"{v}_{unit}_model"]
        out["XA_data"] = 1 - d["CA"].to_numpy() * out["V_L"] / (rx.CA0 * rx.V0)
        out["XA_model"] = sim["XA"].to_numpy()
        out.to_csv(processed_path(dataset, f"{run['run_id']}_processed.csv"), index=False, float_format="%.6g")


def fit_history(runs, final_res):
    """Refit at each milestone in config.FIT_MILESTONES (plus the full set) so the report can show
    how the confidence intervals shrank as runs were added. Written to part5_fit_history.csv."""
    sizes = sorted({n for n in C.FIT_MILESTONES if n < len(runs)} | {len(runs)})
    rows = []
    for i, n in enumerate(sizes, 1):
        res = final_res if n == len(runs) else fit(runs[:n])
        tab, _ = report(res)
        for _, r in tab.iterrows():
            rows.append(dict(fit=f"Fit {i}", runs=", ".join(x["run_id"] for x in runs[:n]), n_runs=n,
                             T_ref_K=res["T_ref"], s2=res["s2"], n_obs=res["n"], parameter=r["parameter"], units=r["units"],
                             estimate=r["estimate"], ci95_low=r["ci95_low"], ci95_high=r["ci95_high"],
                             rel_95CI_pct=r["rel_95CI_%"]))
    return pd.DataFrame(rows)


def main(dataset):
    runs = load_runs(dataset)
    if not runs:
        print(f"No data for '{dataset}'.")
        return None
    print(f"Fitting {len(runs)} run(s): {[r['run_id'] for r in runs]}")
    res = fit(runs)
    kin = kin_from_theta(res["theta"], res["T_ref"])
    table, corr = report(res)
    table.to_csv(table_path(dataset, "part6_fitted_parameters"), index=False)
    corr.to_csv(table_path(dataset, "part6_parameter_correlation"))
    save_json(dict(k_ref=kin.k_ref, Ea_kJmol=kin.Ea / 1e3, dH_kJmol=kin.dH / 1e3, T_ref=res["T_ref"],
                   theta=res["theta"], cov_theta=res["cov"], noise_sigma=res["sig"], s2=res["s2"],
                   n_obs=res["n"], dof=res["dof"], JtJ_condition_number=res["cond_number"],
                   runs=[r["run_id"] for r in runs]), processed_path(dataset, "fitted_parameters.json"))
    plot_runs(runs, kin, dataset)
    fit_history(runs, res).to_csv(table_path(dataset, "part5_fit_history"), index=False)
    write_processed_runs(runs, kin, dataset)
    print(table.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    print("Correlation:\n" + corr.round(3).to_string())
    print(f"Noise sigma (from residuals): {res['sig']}")

    truth = C.DATASETS[dataset]["experiments"] / "TRUE_PARAMS.json"
    if truth.exists():                     # synthetic only: did we recover the truth?
        t = json.loads(truth.read_text())
        k_true = t["k_ref"] * np.exp(-t["Ea_kJmol"] * 1e3 / C.R * (1 / res["T_ref"] - 1 / t["T_ref"]))
        true_vals = [k_true, t["Ea_kJmol"], t["dH_kJmol"]]
        chk = table[["parameter", "estimate", "ci95_low", "ci95_high"]].copy()
        chk["true"] = true_vals
        chk["true_inside_95CI"] = (chk["true"] >= chk["ci95_low"]) & (chk["true"] <= chk["ci95_high"])
        chk.to_csv(table_path(dataset, "part6_truth_recovery_selftest"), index=False)
        print("Truth recovery:\n" + chk.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
