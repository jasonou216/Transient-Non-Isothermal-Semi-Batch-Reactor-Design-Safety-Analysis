"""Part A - Nominal 1000 L semi-batch simulation + bench-vs-plant scale-up comparison.

Outputs conversion, temperature, heat-release / removal rates and concentrations over the
batch for config.NOMINAL, and the same feed schedule (same t_feed, same B:A) run at bench
scale to show how the falling UA/V ratio changes the thermal behaviour.

    python src/full_scale.py --dataset real|synthetic
"""
import argparse

import matplotlib.pyplot as plt
import pandas as pd

import config as C
from common import bench_reactor, full_reactor, full_V_B, load_fit, mark_feed, out_dir, save_json
from model import metrics, simulate


def main(dataset):
    kin = load_fit(dataset)[0]
    folder = out_dir(dataset, "3_full_scale")
    n = C.NOMINAL
    rx = full_reactor()
    df = simulate(rx, kin, C.BATCH_TIME, n=1200)
    m = metrics(df)
    V_final = rx.V0 + full_V_B()
    bench = bench_reactor(dict(T0=n["T0"], Tc=n["Tc"], t_feed=n["t_feed"],
                               q=C.FULL["B_to_A"] * C.BENCH["CA0"] * C.BENCH["V0"] / C.BENCH["CBf"] / n["t_feed"]))
    db = simulate(bench, kin, C.BATCH_TIME, n=1200)
    mb = metrics(db)
    summary = dict(case=dict(n, UA_W_K=rx.UA, V0_L=rx.V0, V_final_L=V_final, q_Lmin=rx.feed[0][2],
                             batch_time_min=C.BATCH_TIME),
                   full_scale=m, bench_same_schedule=mb,
                   UA_per_V_bench_W_KL=bench.UA / (bench.V0 + bench.feed[0][2] * n["t_feed"]),
                   UA_per_V_full_W_KL=rx.UA / V_final,
                   XA_at_feed_stop=float(df.loc[df.t <= n["t_feed"], "XA"].iloc[-1]),
                   t_to_target_X_min=float(df.loc[df.XA >= C.TARGET_X, "t"].min()) if (df.XA >= C.TARGET_X).any() else None)
    save_json(summary, folder / "nominal_summary.json")
    df.to_csv(folder / "nominal_profiles.csv", index=False)

    fig, ax = plt.subplots(2, 2, figsize=(11, 7), sharex=True)
    ax[0, 0].plot(df.t, df.XA, label="X_A")
    ax[0, 0].axhline(C.TARGET_X, color="grey", ls="--", lw=0.8, label=f"target {C.TARGET_X}")
    ax[0, 0].set_ylabel("conversion of A (-)")
    ax[0, 1].plot(df.t, df["T"], label="T reactor")
    ax[0, 1].plot(df.t, df.MTSR, ls="--", label="MTSR (cooling-loss ceiling)")
    ax[0, 1].axhline(rx.Tc, color="C2", lw=0.8, label="T coolant")
    ax[0, 1].axhline(C.T_LIMIT, color="r", lw=1, label="T limit")
    ax[0, 1].set_ylabel("T (K)")
    ax[1, 0].plot(df.t, df.Qrxn_W / 1e3, label="heat released by reaction")
    ax[1, 0].plot(df.t, -df.Qjac_W / 1e3, label="heat removed by jacket")
    ax[1, 0].plot(df.t, -df.Qfeed_W / 1e3, label="heat absorbed by cold feed")
    ax[1, 0].set_ylabel("heat rate (kW)")
    for v in ["CA", "CB", "CC"]:
        ax[1, 1].plot(df.t, df[v], label=v)
    ax[1, 1].set_ylabel("C (mol/L)")
    for a in ax.flat:
        mark_feed(a, rx.feed)
        a.legend(fontsize=7)
    for a in ax[1]:
        a.set_xlabel("t (min)")
    fig.suptitle(f"Nominal 1000 L case: t_feed = {n['t_feed']:.0f} min, UA = {rx.UA:.0f} W/K, "
                 f"Tc = {rx.Tc:.0f} K (dotted = feed stop)")
    fig.savefig(folder / "nominal_profiles.png")
    plt.close(fig)

    fig, a = plt.subplots(figsize=(6, 4))
    a.plot(db.t, db["T"], label=f"bench 3 L (UA/V = {summary['UA_per_V_bench_W_KL']:.2f} W/K/L)")
    a.plot(df.t, df["T"], label=f"plant {V_final:.0f} L (UA/V = {summary['UA_per_V_full_W_KL']:.2f} W/K/L)")
    a.set_xlabel("t (min)")
    a.set_ylabel("T (K)")
    a.set_title("Same feed schedule, bench vs plant")
    a.legend(fontsize=8)
    fig.savefig(folder / "bench_vs_plant.png")
    plt.close(fig)
    print(pd.DataFrame({"full scale": m, "bench, same schedule": mb}).round(3).to_string())
    print(f"X_A at feed stop {summary['XA_at_feed_stop']:.3f}; time to X={C.TARGET_X}: {summary['t_to_target_X_min']}")
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
