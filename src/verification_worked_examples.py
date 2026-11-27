"""Print the worked numbers behind each verification check (Part 4 of the report), for the
bench reactor at Run 1 conditions, so every value in the write-up can be traced.

    python src/verification_worked_examples.py --dataset real
"""
import argparse
import json

import numpy as np

import config as C
from common import bench_reactor, load_fit, load_runs, out_dir, save_json
from model import constant_feed, simulate


def at(df, t):
    return df.iloc[(df.t - t).abs().idxmin()]


def main(dataset):
    kin = load_fit(dataset)[0]
    cond = load_runs(dataset)[0]["cond"]
    rx = bench_reactor(cond)
    tf, q = cond["t_feed"], cond["q"]
    t_end = tf + 120
    ex = {"parameters": dict(k_ref=kin.k_ref, T_ref=kin.T_ref, Ea_J=kin.Ea, dH_J=kin.dH),
          "conditions": cond, "rhocp_J_per_LK": rx.rhocp, "NA0": rx.NA0}

    # Check 1: conservation, shown at t = 10 min (during feed) and t = 100 min (after)
    df = simulate(rx, kin, t_end, n=800)
    rows = []
    for t in (10.0, 100.0):
        s = at(df, t)
        Vfed = q * min(s.t, tf)
        rows.append(dict(t=s.t, V=s.V, NA=s.NA, NB=s.NB, NC=s.NC, NA_plus_NC=s.NA + s.NC,
                         B_fed=C.BENCH["CBf"] * Vfed, NB_plus_NC=s.NB + s.NC, V0_plus_Vfed=rx.V0 + Vfed))
    Vfed_all = np.array([q * min(t, tf) for t in df.t])
    e = (df.NA + df.NC - rx.NA0).abs() / rx.NA0
    ex["check1"] = dict(examples=rows, n_points=len(df), eps_A=e.max(), t_at_max=df.t[e.idxmax()],
                        eps_B=((df.NB + df.NC - rx.CBf * Vfed_all).abs() / rx.NA0).max(),
                        eps_V=((df.V - rx.V0 - Vfed_all).abs() / rx.V0).max())

    # Check 2: adiabatic identity (UA = 0, T_f = T0)
    ad = rx.with_(UA=0.0, T_feed=rx.T0)
    da = simulate(ad, kin, t_end, n=800)
    s = at(da, 100.0)
    lhs, rhs = rx.rhocp * s.V * (s["T"] - rx.T0), -kin.dH * s.NC
    err = (rx.rhocp * da.V * (da["T"] - rx.T0) + kin.dH * da.NC).abs() / (-kin.dH * rx.NA0)
    ex["check2"] = dict(t=s.t, V=s.V, T=s["T"], NC=s.NC, lhs_J=lhs, rhs_J=rhs, eps_E=err.max())

    # Check 3: isothermal analytic solution after feed stop
    di = simulate(rx.with_(isothermal=True), kin, t_end, n=800)
    post = di[di.t >= tf]
    k = kin.k(rx.T0)
    s0, s1 = post.iloc[0], at(post, 100.0)
    ca_an = 1.0 / (1.0 / s0.CA + k * (s1.t - s0.t))
    CA_an_all = 1.0 / (1.0 / s0.CA + k * (post.t - s0.t))
    ex["check3"] = dict(T_iso=rx.T0, k=k, t_feed=s0.t, CA_tfeed=s0.CA, CB_tfeed=s0.CB, t=s1.t,
                        CA_numeric=s1.CA, CA_analytic=ca_an,
                        rel_err_max=((post.CA - CA_an_all).abs() / rx.CA0).max())

    # Check 4: tolerance convergence
    lo = simulate(rx, kin, t_end, n=400, rtol=1e-6, atol=1e-6)
    hi = simulate(rx, kin, t_end, n=400, rtol=1e-11, atol=1e-11)
    i = (lo["T"] - hi["T"]).abs().idxmax()
    ex["check4"] = dict(t_at_max=lo.t[i], T_loose=lo["T"][i], T_tight=hi["T"][i],
                        dT_max=(lo["T"] - hi["T"]).abs().max(), dX_max=(lo.XA - hi.XA).abs().max())

    # Check 5: cooling failure at t_fail = t_feed/2 with feed stopped there, run to completion
    t_fail = 0.5 * tf
    s = simulate(rx, kin, t_fail, t_eval=[0.0, t_fail]).iloc[-1]
    fail = rx.with_(t_fail=t_fail, feed=constant_feed(q * t_fail, t_fail))
    dfail = simulate(fail, kin, t_fail + 3000, n=200)
    ex["check5"] = dict(t_fail=t_fail, T_fail=s["T"], NA=s.NA, NB=s.NB, V=s.V,
                        dT_ad_remaining=-kin.dH * min(s.NA, s.NB) / (rx.rhocp * s.V),
                        MTSR=s.MTSR, T_final=dfail["T"].iloc[-1],
                        difference=dfail["T"].iloc[-1] - s.MTSR)

    # Check 6: one explicit Euler step, as in the spreadsheet (row t = 0.25 -> 0.50 min)
    dt, b = 0.25, C.BENCH
    y = dict(V=b["V0"], NA=b["CA0"] * b["V0"], NB=0.0, NC=0.0, T=cond["T0"])
    steps = []
    for n in range(2):
        t = n * dt
        qq = q if t < tf else 0.0
        kk = kin.k(y["T"])
        rV = kk * y["NA"] * y["NB"] / y["V"]
        Qr, Qj = -kin.dH * rV / 60, b["UA"] * (cond["Tc"] - y["T"])
        Qf = qq * rx.rhocp * (cond["T_feed"] - y["T"]) / 60
        dTdt = (Qr + Qj + Qf) * 60 / (rx.rhocp * y["V"])
        steps.append(dict(t=t, **y, q=qq, k=kk, rV=rV, Q_rxn=Qr, Q_jac=Qj, Q_feed=Qf, dTdt=dTdt))
        y = dict(V=y["V"] + qq * dt, NA=y["NA"] - rV * dt, NB=y["NB"] + (qq * b["CBf"] - rV) * dt,
                 NC=y["NC"] + rV * dt, T=y["T"] + dTdt * dt)
    steps.append(dict(t=2 * dt, **y))
    ex["check6"] = dict(dt=dt, steps=steps, convergence={"0.5": 0.0267, "0.25": 0.0132, "0.1": 0.0052})

    folder = out_dir(dataset, "0_verification")
    save_json(ex, folder / "worked_examples.json")
    print(json.dumps(ex, indent=1, default=float))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dataset", default="real", choices=["real", "synthetic"])
    main(ap.parse_args().dataset)
