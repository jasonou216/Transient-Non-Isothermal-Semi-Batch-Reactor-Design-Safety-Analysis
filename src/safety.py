"""Part C - Runaway / safety analysis at full scale.

 1. Feed-rate scan -> maximum safe feed rate under each candidate criterion:
      (a) T_max <= T_LIMIT - MARGIN_NORMAL                       (normal operation)
      (b) MTSR_max <= T_LIMIT - MARGIN_FAILURE                   (cooling-failure ceiling, Stoessel)
      (c) Morbidelli-Varma: runaway boundary = feed rate where the normalised sensitivity
          s = (q / T_max) dT_max/dq peaks (onset of parametric sensitivity)
    The design criterion used in maps/design is (a) AND (b) - see config.py.
 2. Cooling failure (UA -> 0) at every point in the batch, with and without the high-T
    interlock that cuts the feed: temperature rise, T_max, time-to-maximum-rate (TMR).
 3. Runaway / no-runaway maps: feed time vs UA, and feed time vs coolant temperature.

    python src/safety.py --dataset real|synthetic
"""
import argparse

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C
from common import full_reactor, full_V_B, load_fit, out_dir, save_json
from model import constant_feed, metrics, simulate

T_SAFE_NORMAL = C.T_LIMIT - C.MARGIN_NORMAL
T_SAFE_FAIL = C.T_LIMIT - C.MARGIN_FAILURE


def is_safe(m):
    return (m["T_max"] <= T_SAFE_NORMAL) and (m["MTSR_max"] <= T_SAFE_FAIL)


def run(kin, t_feed, t_end=None, **kw):
    rx = full_reactor(feed=constant_feed(full_V_B(), t_feed), **kw)
    return metrics(simulate(rx, kin, t_end or max(C.BATCH_TIME, t_feed + 120), n=500))


def cooling_failure_scan(rx, kin, t_end, n=30):
    """UA -> 0 at t_fail; case 'no interlock' keeps feeding, case 'interlock' cuts the feed at T_TRIP."""
    t_feed_end = max(b for _, b, _ in rx.feed)
    rows, worst = [], {}
    for t_fail in np.linspace(0.0, min(t_feed_end + 30.0, t_end), n):
        for case, trip in [("no interlock", None), ("high-T interlock", C.T_TRIP)]:
            df = simulate(rx.with_(t_fail=t_fail, T_trip=trip), kin, t_fail + 600.0, n=1500)
            after = df[df.t >= t_fail]
            T_fail = after["T"].iloc[0]
            i = after.dTdt.idxmax()
            hit = after.loc[after["T"] >= C.T_LIMIT, "t"]
            row = dict(case=case, t_fail=t_fail, T_at_fail=T_fail, MTSR_at_fail=after.MTSR.iloc[0],
                       T_max=after["T"].max(), dT_rise=after["T"].max() - T_fail,
                       TMR_min=after.t[i] - t_fail, dTdt_max=after.dTdt[i],
                       t_to_limit_min=(hit.iloc[0] - t_fail) if len(hit) else np.nan)
            rows.append(row)
            if case not in worst or row["T_max"] > worst[case][0]["T_max"]:
                worst[case] = (row, df)
    return pd.DataFrame(rows), worst


def main(dataset):
    kin = load_fit(dataset)[0]
    folder = out_dir(dataset, "4_safety")
    summary = {}

    # 1. feed-rate scan (constant feed of all B, nominal UA and Tc)
    t_feeds = np.geomspace(1, 400, 50)
    scan = pd.DataFrame([dict(t_feed=tf, q=full_V_B() / tf, **run(kin, tf)) for tf in t_feeds])
    q = scan.q.to_numpy()
    scan["MV_sensitivity"] = np.gradient(scan.T_max.to_numpy(), np.log(q)) / scan.T_max
    scan.to_csv(folder / "feed_rate_scan.csv", index=False)
    lim = {}
    ok_a = scan.T_max <= T_SAFE_NORMAL
    ok_b = scan.MTSR_max <= T_SAFE_FAIL
    lim["(a) T_max criterion"] = scan.loc[ok_a, "q"].max() if ok_a.any() else np.nan
    lim["(b) MTSR criterion"] = scan.loc[ok_b, "q"].max() if ok_b.any() else np.nan
    i_mv = int(scan.MV_sensitivity.idxmax())
    # a peak at the edge of the scanned range is not a sensitivity peak -> no MV runaway found
    lim["(c) Morbidelli-Varma peak"] = scan.q[i_mv] if 0 < i_mv < len(scan) - 1 else np.nan
    lim["design: (a) AND (b)"] = scan.loc[ok_a & ok_b, "q"].max() if (ok_a & ok_b).any() else np.nan
    summary["max_safe_feed_rate_Lmin"] = lim
    summary["max_safe_feed_min_time_min"] = {k: full_V_B() / v for k, v in lim.items()}

    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    ax[0].semilogx(q, scan.T_max, "o-", ms=3, label="T_max (normal operation)")
    ax[0].semilogx(q, scan.MTSR_max, "s-", ms=3, label="MTSR_max (cooling loss)")
    ax[0].axhline(T_SAFE_NORMAL, color="C0", ls="--", lw=0.8, label="T_LIMIT - margin (normal)")
    ax[0].axhline(T_SAFE_FAIL, color="C1", ls="--", lw=0.8, label="T_LIMIT - margin (failure)")
    ax[0].axhline(C.T_LIMIT, color="r", lw=1, label="T limit")
    ax[0].set_xlabel("B feed rate q (L/min)")
    ax[0].set_ylabel("T (K)")
    ax[0].legend(fontsize=7)
    ax[1].semilogx(q, scan.MV_sensitivity, "o-", ms=3)
    if np.isfinite(lim["(c) Morbidelli-Varma peak"]):
        ax[1].axvline(lim["(c) Morbidelli-Varma peak"], color="r", ls=":")
    ax[1].set_xlabel("B feed rate q (L/min)")
    ax[1].set_ylabel("s = d ln T_max / d ln q")
    ax[1].set_title("Morbidelli-Varma parametric sensitivity")
    fig.savefig(folder / "feed_rate_scan.png")
    plt.close(fig)

    # 2. cooling failure on the nominal design
    rx = full_reactor()
    cf, worst = cooling_failure_scan(rx, kin, C.BATCH_TIME)
    cf.to_csv(folder / "cooling_failure_scan.csv", index=False)
    summary["cooling_failure_nominal"] = {c: worst[c][0] for c in worst}
    fig, ax = plt.subplots(1, 2, figsize=(11, 4))
    for c, g in cf.groupby("case"):
        ax[0].plot(g.t_fail, g.T_max, "o-", ms=3, label=f"T_max after failure ({c})")
    g = cf[cf.case == "no interlock"]
    ax[0].plot(g.t_fail, g.MTSR_at_fail, "k--", lw=1, label="MTSR at failure time")
    ax[0].axhline(C.T_LIMIT, color="r", lw=1, label="T limit")
    ax[0].set_xlabel("time of cooling failure (min)")
    ax[0].set_ylabel("T (K)")
    ax[0].legend(fontsize=7)
    for c, (row, df) in worst.items():
        ax[1].plot(df.t, df["T"], label=f"worst case, {c} (fail at {row['t_fail']:.0f} min)")
    ax[1].axhline(C.T_LIMIT, color="r", lw=1)
    ax[1].axhline(C.T_TRIP, color="grey", ls=":", lw=1, label="interlock trip")
    ax[1].set_xlabel("t (min)")
    ax[1].set_ylabel("T (K)")
    ax[1].legend(fontsize=7)
    fig.suptitle("Cooling failure (UA -> 0) during the nominal batch")
    fig.savefig(folder / "cooling_failure.png")
    plt.close(fig)

    # 3. runaway maps
    tf_grid = np.geomspace(10, 400, 22)
    for name, values, kw, label in [("UA", np.linspace(0.25, 3.0, 16), "UA_factor", "UA / UA_scaled"),
                                    ("Tc", np.linspace(283.15, 333.15, 16), "Tc", "coolant T (K)")]:
        Tm = np.zeros((values.size, tf_grid.size))
        Ms = np.zeros_like(Tm)
        for i, v in enumerate(values):
            for j, tf in enumerate(tf_grid):
                m = run(kin, tf, **{kw: v})
                Tm[i, j], Ms[i, j] = m["T_max"], m["MTSR_max"]
        safe = (Tm <= T_SAFE_NORMAL) & (Ms <= T_SAFE_FAIL)
        qg = full_V_B() / tf_grid
        fig, a = plt.subplots(figsize=(6.5, 4.8))
        a.contourf(qg, values, safe.astype(float), levels=[-0.5, 0.5, 1.5], colors=["#f4b6b6", "#bfe3c0"])
        cs = a.contour(qg, values, Tm, levels=np.arange(300, 480, 10), colors="k", linewidths=0.5)
        a.clabel(cs, fontsize=6, fmt="%.0f K")
        a.contour(qg, values, Tm, levels=[T_SAFE_NORMAL], colors="C0", linewidths=2)
        a.contour(qg, values, Ms, levels=[T_SAFE_FAIL], colors="C1", linewidths=2, linestyles="--")
        a.set_xscale("log")
        a.set_xlabel("B feed rate q (L/min)")
        a.set_ylabel(label)
        a.set_title("Safe (green) / unsafe (red).  Blue: T_max limit;  orange dashed: MTSR limit;\n"
                    "black: T_max contours", fontsize=8)
        fig.savefig(folder / f"runaway_map_q_vs_{name}.png")
        plt.close(fig)
        pd.DataFrame(Tm, index=values, columns=qg).to_csv(folder / f"map_Tmax_q_vs_{name}.csv")
        pd.DataFrame(Ms, index=values, columns=qg).to_csv(folder / f"map_MTSR_q_vs_{name}.csv")

    save_json(summary, folder / "safety_summary.json")
    print(pd.Series(lim, name="max safe q (L/min)").to_string())
    print(pd.DataFrame(summary["cooling_failure_nominal"]).T.round(2).to_string())
    return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
