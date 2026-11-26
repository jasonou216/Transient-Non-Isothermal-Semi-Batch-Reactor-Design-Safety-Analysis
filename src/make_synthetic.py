"""Generate a SYNTHETIC data set (known 'true' parameters + measurement noise) in exactly the
format the TA returns, to verify the pipeline end to end before real data arrive.
Nothing in data/synthetic/ or results/synthetic/ may be used in the report's results.

    python src/make_synthetic.py
"""
import numpy as np
import pandas as pd

import config as C
from common import bench_reactor, save_json
from model import Kinetics, simulate

TRUE = Kinetics(k_ref=0.15, Ea=65e3, dH=-90e3, T_ref=320.0)   # invented values
NOISE = dict(CA=0.03, CB=0.03, CC=0.03, T=0.5)                  # mol/L, K (1 sigma)
N_POINTS = 40

#        run   T0      q      t_feed  Tc      t_final   purpose
RUNS = [("S1", 298.15, 0.040, 25.0, 298.15, 100.0),   # baseline, near-isothermal start
        ("S2", 313.15, 0.050, 20.0, 313.15, 90.0),    # warmer: k at a 2nd temperature
        ("S3", 328.15, 0.020, 50.0, 328.15, 100.0),   # hot, slow feed: Ea leverage
        ("S4", 298.15, 0.100, 10.0, 293.15, 90.0),    # fast feed: large exotherm -> dH
        ("S5", 308.15, 0.025, 60.0, 303.15, 120.0)]   # 1.5 eq B, long feed
VALIDATION = [("V1", 305.15, 0.030, 40.0, 305.15, 110.0)]


def write(folder, runs, rng):
    folder.mkdir(parents=True, exist_ok=True)
    rows = []
    for rid, T0, q, tf, Tc, tend in runs:
        cond = dict(T0=T0, q=q, t_feed=tf, Tc=Tc, t_final=tend)
        t = np.linspace(0.0, tend, N_POINTS)
        df = simulate(bench_reactor(cond), TRUE, tend, t_eval=t)
        out = pd.DataFrame({"time_min": t})
        for col, name in [("CA", "CA_molL"), ("CB", "CB_molL"), ("CC", "CC_molL"), ("T", "T_K")]:
            out[name] = df[col].to_numpy() + rng.normal(0.0, NOISE[col], t.size)
        out.to_csv(folder / f"{rid}.csv", index=False, float_format="%.5f")
        rows.append(dict(run_id=rid, file=f"{rid}.csv", T0_K=T0, feed_flow_Lmin=q,
                         feed_duration_min=tf, T_coolant_K=Tc, t_final_min=tend, T_feed_K="",
                         notes="synthetic"))
        print(f"  {rid}: T_max = {df['T'].max():.1f} K, X_A(end) = {df['XA'].iloc[-1]:.3f}")
    pd.DataFrame(rows).to_csv(folder / "runs.csv", index=False)


def main():
    rng = np.random.default_rng(421)
    print("Synthetic experiments:")
    write(C.DATA_DIRS["synthetic"], RUNS, rng)
    write(C.VALIDATION_DIRS["synthetic"], VALIDATION, rng)
    save_json(dict(k_ref=TRUE.k_ref, Ea_kJmol=TRUE.Ea / 1e3, dH_kJmol=TRUE.dH / 1e3,
                   T_ref=TRUE.T_ref, noise=NOISE), C.DATA_DIRS["synthetic"] / "TRUE_PARAMS.json")


if __name__ == "__main__":
    main()
