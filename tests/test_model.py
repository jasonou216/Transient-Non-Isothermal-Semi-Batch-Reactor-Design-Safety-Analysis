"""Fast automated checks (about 10 s):  pytest

These repeat the core Part 4 verification checks on a bench case and a 1000 L case, using the
PRIOR kinetics so they do not depend on any fit, and check the data files are where the code
expects them. If any of these fail after a code change, the change broke the model.
"""
import numpy as np
import pandas as pd
import pytest

import config as C
from common import bench_reactor, full_reactor, load_runs
from semi_batch_model import Kinetics, constant_feed, simulate

KIN = Kinetics(**C.PRIOR)
CASES = {"bench": bench_reactor(dict(T0=303.15, q=0.04, t_feed=25.0, Tc=298.15)),
         "full scale": full_reactor()}


def fed_volume(rx, t):
    return np.array([sum(q * max(0.0, min(ti, b) - a) for a, b, q in rx.feed) for ti in t])


def t_end(rx):
    return max(b for _, b, _ in rx.feed) + 120


@pytest.mark.parametrize("name", CASES)
def test_mole_and_volume_balances_close(name):
    """A is only consumed by making C, B only enters by the feed, volume only grows by the feed."""
    rx = CASES[name]
    df = simulate(rx, KIN, t_end(rx), n=400)
    Vfed = fed_volume(rx, df["t"])
    assert (df.NA + df.NC - rx.NA0).abs().max() / rx.NA0 < 1e-6
    assert (df.NB + df.NC - rx.CBf * Vfed).abs().max() / rx.NA0 < 1e-6
    assert (df.V - rx.V0 - Vfed).abs().max() / rx.V0 < 1e-6


@pytest.mark.parametrize("name", CASES)
def test_adiabatic_energy_identity(name):
    """No jacket and feed at T0: all reaction heat must show up as sensible heat."""
    rx = CASES[name].with_(UA=0.0, T_feed=CASES[name].T0)
    df = simulate(rx, KIN, t_end(rx), n=400)
    err = (rx.rhocp * df.V * (df["T"] - rx.T0) + KIN.dH * df.NC).abs().max() / (-KIN.dH * rx.NA0)
    assert err < 1e-6


@pytest.mark.parametrize("name", CASES)
def test_isothermal_matches_analytic_second_order(name):
    """After the feed stops at constant T and V with C_A = C_B, 1/C_A rises linearly with slope k."""
    rx = CASES[name].with_(isothermal=True)
    df = simulate(rx, KIN, t_end(rx), n=400)
    post = df[df.t >= max(b for _, b, _ in rx.feed)]
    CA_an = 1.0 / (1.0 / post.CA.iloc[0] + KIN.k(rx.T0) * (post.t - post.t.iloc[0]))
    assert (post.CA - CA_an).abs().max() / rx.CA0 < 1e-5


def test_cooling_failure_ends_at_mtsr():
    """Lose cooling and stop the feed: the adiabatic end temperature must equal the MTSR."""
    rx = CASES["full scale"]
    t_fail = 0.5 * max(b for _, b, _ in rx.feed)
    mtsr = simulate(rx, KIN, t_fail, t_eval=[0.0, t_fail])["MTSR"].iloc[-1]
    fail = rx.with_(t_fail=t_fail, feed=constant_feed(rx.feed[0][2] * t_fail, t_fail))
    assert abs(simulate(fail, KIN, t_fail + 3000, n=200)["T"].iloc[-1] - mtsr) < 0.05


@pytest.mark.parametrize("validation", [False, True])
def test_every_manifest_row_has_its_raw_file(validation):
    """Each run listed in data/experiments/ must have its data file in data/raw/."""
    d = C.DATASETS["real"]
    manifest = d["experiments"] / ("validation_runs.csv" if validation else "runs.csv")
    rows = pd.read_csv(manifest, comment="#")
    missing = [f for f in rows["file"] if not (d["raw"] / f).exists()]
    assert not missing, f"listed in {manifest.name} but not in data/raw/: {missing}"


def test_real_runs_load_with_expected_columns():
    runs = load_runs("real")
    assert runs, "no fitting runs found in data/experiments/runs.csv"
    for r in runs:
        assert list(r["data"].columns) == ["t", "CA", "CB", "CC", "T"]
        assert r["data"]["t"].is_monotonic_increasing
