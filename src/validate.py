"""Part B - Validation against the held-out run using the fitted parameters UNCHANGED.

Reports RMSE / bias / max error per variable, T_max and t(T_max) errors, and a 95 %
prediction band from parameter uncertainty (Monte Carlo on the fitted covariance).

    python src/validate.py --dataset real|synthetic
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from common import bench_reactor, load_fit, load_runs, mark_feed, out_dir, sample_kinetics, save_json
from model import simulate

N_MC = 200


def main(dataset):
    runs = load_runs(dataset, validation=True)
    if not runs:
        print("No validation data yet (released after parameters are submitted).")
        return None
    kin, theta, cov, _ = load_fit(dataset)
    folder = out_dir(dataset, "2_validation")
    samples = sample_kinetics(theta, cov, kin.T_ref, N_MC)
    rows = []
    for run in runs:
        d, cond = run["data"], run["cond"]
        rx = bench_reactor(cond)
        at = simulate(rx, kin, d["t"].max(), t_eval=d["t"].to_numpy())
        for v, unit in [("CA", "mol/L"), ("CB", "mol/L"), ("CC", "mol/L"), ("T", "K")]:
            e = at[v].to_numpy() - d[v].to_numpy()
            rows.append(dict(run=run["run_id"], variable=v, units=unit, RMSE=np.sqrt(np.mean(e**2)),
                             bias=e.mean(), max_abs_error=np.abs(e).max()))
        sim = simulate(rx, kin, d["t"].max())
        i_d, i_m = d["T"].idxmax(), sim["T"].idxmax()
        rows.append(dict(run=run["run_id"], variable="T_max", units="K",
                         RMSE=np.nan, bias=sim["T"][i_m] - d["T"][i_d], max_abs_error=np.nan))
        rows.append(dict(run=run["run_id"], variable="t(T_max)", units="min",
                         RMSE=np.nan, bias=sim["t"][i_m] - d["t"][i_d], max_abs_error=np.nan))

        band = np.array([simulate(rx, k, d["t"].max(), t_eval=sim["t"].to_numpy())[["CA", "CB", "CC", "T"]].to_numpy()
                         for k in samples])
        lo, hi = np.percentile(band, 2.5, axis=0), np.percentile(band, 97.5, axis=0)
        fig, (a, b) = plt.subplots(1, 2, figsize=(10, 3.8))
        for j, (v, c) in enumerate(zip(["CA", "CB", "CC"], ["C0", "C1", "C2"])):
            a.fill_between(sim["t"], lo[:, j], hi[:, j], color=c, alpha=0.2)
            a.plot(sim["t"], sim[v], color=c, label=f"{v} model")
            a.plot(d["t"], d[v], "o", ms=3, color=c, label=f"{v} data")
        b.fill_between(sim["t"], lo[:, 3], hi[:, 3], color="C3", alpha=0.2, label="95 % parameter band")
        b.plot(sim["t"], sim["T"], color="C3", label="model")
        b.plot(d["t"], d["T"], "o", ms=3, color="C3", label="data")
        for ax in (a, b):
            mark_feed(ax, rx.feed)
            ax.set_xlabel("t (min)")
        a.set_ylabel("C (mol/L)")
        b.set_ylabel("T (K)")
        a.legend(fontsize=7, ncol=2)
        b.legend(fontsize=7)
        fig.suptitle(f"Validation run {run['run_id']} - fitted parameters, no retuning")
        fig.savefig(folder / f"validation_{run['run_id']}.png")
        plt.close(fig)
    table = pd.DataFrame(rows)
    table.to_csv(folder / "validation_metrics.csv", index=False)
    print(table.to_string(index=False, float_format=lambda x: f"{x:.4g}"))
    save_json(dict(rows=table.to_dict("records")), folder / "validation_metrics.json")
    return table


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
