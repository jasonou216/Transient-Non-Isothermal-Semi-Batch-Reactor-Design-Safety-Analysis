"""Shared helpers: data loading, reactor builders, fitted-parameter I/O, plotting style."""
import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import config as C
from model import Kinetics, Reactor, constant_feed

plt.rcParams.update({"figure.dpi": 100, "savefig.dpi": C.FIG_DPI, "font.size": 10,
                     "axes.grid": True, "grid.alpha": 0.3, "savefig.bbox": "tight"})

DATA_COLS = {"time_min": "t", "ca_moll": "CA", "cb_moll": "CB", "cc_moll": "CC", "t_k": "T"}


# ----------------------------------------------------------------------------- data
def load_runs(dataset, validation=False):
    """Read runs.csv (one row per experiment, the conditions you requested) and each
    returned data file. Columns expected in the data: time_min, CA_molL, CB_molL, CC_molL, T_K."""
    folder = (C.VALIDATION_DIRS if validation else C.DATA_DIRS)[dataset]
    manifest = folder / "runs.csv"
    if not manifest.exists():
        return []
    runs = []
    for _, row in pd.read_csv(manifest, comment="#").iterrows():
        path = folder / str(row["file"]).strip()
        if not path.exists():
            print(f"  [skip] {row['run_id']}: data file {path.name} not found yet")
            continue
        raw = pd.read_excel(path) if path.suffix in (".xlsx", ".xls") else pd.read_csv(path)
        raw.columns = [c.strip().lower() for c in raw.columns]
        df = raw.rename(columns=DATA_COLS)[list(DATA_COLS.values())].astype(float)
        T_feed = row.get("T_feed_K")
        cond = dict(T0=float(row["T0_K"]), q=float(row["feed_flow_Lmin"]),
                    t_feed=float(row["feed_duration_min"]), Tc=float(row["T_coolant_K"]),
                    t_final=float(row["t_final_min"]),
                    T_feed=float(T_feed) if pd.notna(T_feed) else C.BENCH["T_feed"])
        runs.append(dict(run_id=str(row["run_id"]), cond=cond, data=df))
    return runs


def bench_reactor(cond, **kw):
    b = C.BENCH
    return Reactor(V0=b["V0"], CA0=b["CA0"], CBf=b["CBf"], rho=b["rho"], cp=b["cp"],
                   UA=kw.pop("UA", b["UA"]), T0=cond["T0"], Tc=cond["Tc"],
                   T_feed=cond.get("T_feed", b["T_feed"]),
                   feed=((0.0, cond["t_feed"], cond["q"]),), **kw)


def full_V_B():
    f = C.FULL
    return f["B_to_A"] * f["CA0"] * f["V0"] / f["CBf"]          # L of B solution


def full_reactor(feed=None, UA_factor=None, T0=None, Tc=None, **kw):
    f, n = C.FULL, C.NOMINAL
    feed = feed or constant_feed(full_V_B(), n["t_feed"])
    UA = (n["UA_factor"] if UA_factor is None else UA_factor) * C.ua_scaled(f["V0"] + full_V_B())
    return Reactor(V0=f["V0"], CA0=f["CA0"], CBf=f["CBf"], rho=f["rho"], cp=f["cp"], UA=UA,
                   T0=n["T0"] if T0 is None else T0, Tc=n["Tc"] if Tc is None else Tc,
                   T_feed=f["T_feed"], feed=feed, **kw)


# ----------------------------------------------------------------------------- results
def out_dir(dataset, step):
    d = C.RESULTS_DIR / dataset / step
    d.mkdir(parents=True, exist_ok=True)
    return d


def save_json(obj, path):
    def conv(o):
        if isinstance(o, (np.floating, np.integer)):
            return o.item()
        if isinstance(o, np.ndarray):
            return o.tolist()
        raise TypeError(type(o))
    path.write_text(json.dumps(obj, indent=2, default=conv))


def load_fit(dataset):
    """Fitted Kinetics + covariance of theta = [ln k_ref, Ea (kJ/mol), dH (kJ/mol)]."""
    p = C.RESULTS_DIR / dataset / "1_fit" / "params.json"
    if not p.exists():
        raise FileNotFoundError(f"No fit for '{dataset}' yet - run fit_parameters.py first.")
    d = json.loads(p.read_text())
    kin = Kinetics(k_ref=d["k_ref"], Ea=d["Ea_kJmol"] * 1e3, dH=d["dH_kJmol"] * 1e3, T_ref=d["T_ref"])
    return kin, np.array(d["theta"]), np.array(d["cov_theta"]), d


def kin_from_theta(theta, T_ref):
    return Kinetics(k_ref=float(np.exp(theta[0])), Ea=theta[1] * 1e3, dH=theta[2] * 1e3, T_ref=T_ref)


def sample_kinetics(theta, cov, T_ref, n, seed=0):
    rng = np.random.default_rng(seed)
    return [kin_from_theta(th, T_ref) for th in rng.multivariate_normal(theta, cov, n)]


def mark_feed(ax, feed, cut=None):
    end = max(b for _, b, _ in feed)
    if cut is not None:
        end = min(end, cut)
    ax.axvline(end, color="grey", ls=":", lw=1)
