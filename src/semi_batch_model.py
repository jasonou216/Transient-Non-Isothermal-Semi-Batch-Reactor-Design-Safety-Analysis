"""Transient, non-isothermal semi-batch reactor model (same equations for bench and 1000 L).

Reaction A + B -> C, r = k(T) C_A C_B,  k(T) = k_ref exp[-Ea/R (1/T - 1/T_ref)].
States y = [V (L), N_A, N_B, N_C (mol), T (K)], time in min. Mole-based states are
used because V changes with time (Lab 2).

  dV/dt   = q(t)                                  (constant density, additive volumes)
  dN_A/dt = -r V
  dN_B/dt = q(t) C_Bf - r V
  dN_C/dt = +r V
  rho cp V dT/dt = q rho cp (T_f - T) + (-dH) r V + UA (T_c - T)        [J/min]

The energy balance comes from d(rho cp V T)/dt = q rho cp T_f + (-dH) r V + UA (T_c - T)
minus T times the volume balance (constant rho, cp, no shaft work, negligible mixing heat).
"""
from dataclasses import dataclass, replace

import numpy as np
import pandas as pd
from scipy.integrate import solve_ivp

from config import R


@dataclass(frozen=True)
class Kinetics:
    k_ref: float  # L/(mol min) at T_ref
    Ea: float     # J/mol
    dH: float     # J/mol (negative = exothermic)
    T_ref: float  # K

    def k(self, T):
        return self.k_ref * np.exp(-self.Ea / R * (1.0 / T - 1.0 / self.T_ref))

    def with_(self, **kw):
        return replace(self, **kw)


@dataclass(frozen=True)
class Reactor:
    V0: float
    CA0: float
    CBf: float
    rho: float
    cp: float
    UA: float                 # W/K
    T0: float
    Tc: float
    T_feed: float
    feed: tuple               # ((t_start, t_end, q [L/min]), ...)
    t_fail: float = None      # cooling failure: UA -> 0 for t >= t_fail
    T_trip: float = None      # high-T interlock: B feed cut permanently once T >= T_trip
    isothermal: bool = False  # verification only

    @property
    def NA0(self):
        return self.CA0 * self.V0

    @property
    def rhocp(self):          # J/(L K)
        return self.rho * self.cp

    def with_(self, **kw):
        return replace(self, **kw)


# ----------------------------------------------------------------------------- feed policies
def constant_feed(V_B, t_feed, t_start=0.0):
    """Feed a total volume V_B (L) at constant rate over t_feed (min)."""
    return ((t_start, t_start + t_feed, V_B / t_feed),)


def staged_feed(V_B, t_total, frac_first, rate_ratio):
    """Two constant-rate stages: stage 1 delivers frac_first of V_B at q1, stage 2 the rest
    at q2 = q1 / rate_ratio, total duration t_total."""
    v1, v2 = frac_first * V_B, (1 - frac_first) * V_B
    t1 = t_total * v1 / (v1 + rate_ratio * v2)
    return ((0.0, t1, v1 / t1), (t1, t_total, v2 / (t_total - t1)))


def feed_rate(feed, t, cut=None):
    """Vectorised q(t) for a piecewise-constant feed; zero after a feed cut."""
    t = np.asarray(t, float)
    q = np.zeros_like(t)
    for a, b, qq in feed:
        q = np.where((t >= a) & (t < b), qq, q)
    if cut is not None:
        q = np.where(t >= cut, 0.0, q)
    return q


# ----------------------------------------------------------------------------- ODEs
def _rhs(t, y, rx, kin, cut):
    V, NA, NB, NC, T = y
    q = float(feed_rate(rx.feed, t, cut))
    UA = 0.0 if (rx.t_fail is not None and t >= rx.t_fail) else rx.UA
    rV = kin.k(T) * max(NA, 0.0) * max(NB, 0.0) / V            # mol/min
    if rx.isothermal:
        dT = 0.0
    else:
        dT = (q * rx.rhocp * (rx.T_feed - T) - kin.dH * rV + UA * 60.0 * (rx.Tc - T)) / (rx.rhocp * V)
    return [q, -rV, q * rx.CBf - rV, rV, dT]


def simulate(rx, kin, t_end, t_eval=None, n=500, rtol=1e-9, atol=1e-9):
    """Integrate piecewise between feed changes / failure / interlock trip (no
    discontinuities inside a solver step). Returns a DataFrame with states and
    derived quantities; df.attrs['t_cut'] = time the feed was cut by the interlock."""
    t_eval = np.linspace(0.0, t_end, n) if t_eval is None else np.asarray(t_eval, float)
    fixed = {0.0, t_end, *(x for a, b, _ in rx.feed for x in (a, b))}
    if rx.t_fail is not None:
        fixed.add(rx.t_fail)
    fixed = sorted(x for x in fixed if 0.0 <= x <= t_end)

    t, y, cut = 0.0, np.array([rx.V0, rx.NA0, 0.0, 0.0, rx.T0]), None
    if rx.T_trip is not None and rx.T0 >= rx.T_trip:
        cut = 0.0
    ts, ys = [], []
    while t < t_end - 1e-12:
        t1 = min(x for x in fixed if x > t + 1e-12)
        events = None
        if rx.T_trip is not None and cut is None:
            def trip(tt, yy, *_):
                return yy[4] - rx.T_trip
            trip.terminal, trip.direction = True, 1
            events = trip
        sol = solve_ivp(_rhs, (t, t1), y, method="LSODA", args=(rx, kin, cut), rtol=rtol,
                        atol=atol, dense_output=True, events=events)
        if not sol.success:
            raise RuntimeError(sol.message)
        t_stop = sol.t[-1]
        last = t_stop >= t_end - 1e-12
        m = (t_eval >= t) & ((t_eval <= t_stop) if last else (t_eval < t_stop))
        if m.any():
            ts.append(t_eval[m])
            ys.append(sol.sol(t_eval[m]))
        if sol.status == 1:                       # interlock tripped
            cut = t_stop
        t, y = t_stop, sol.y[:, -1]
    t_out = np.concatenate(ts)
    Y = np.concatenate(ys, axis=1)
    df = derived(rx, kin, t_out, Y, cut)
    df.attrs["t_cut"] = cut
    return df


def derived(rx, kin, t, Y, cut=None):
    V, NA, NB, NC, T = Y
    q = feed_rate(rx.feed, t, cut)
    failed = (t >= rx.t_fail) if rx.t_fail is not None else np.zeros_like(t, bool)
    UA = np.where(failed, 0.0, rx.UA)
    rV = kin.k(T) * np.clip(NA, 0, None) * np.clip(NB, 0, None) / V
    Qrxn = -kin.dH * rV / 60.0                                  # W, heat released
    Qjac = UA * (rx.Tc - T)                                     # W, into reactor (<0 = removal)
    Qfeed = q * rx.rhocp * (rx.T_feed - T) / 60.0               # W, sensible heat of feed
    dTdt = 0.0 * T if rx.isothermal else (Qrxn + Qjac + Qfeed) * 60.0 / (rx.rhocp * V)
    # Semenov-type ratio: d(heat generation)/dT over d(heat removal)/dT. >1 = locally unstable.
    S = (Qrxn * kin.Ea / (R * T**2)) / np.maximum(UA + q * rx.rhocp / 60.0, 1e-12)
    # MTSR: temperature reached if cooling and feed stop now and all accumulated
    # limiting reactant reacts adiabatically.
    MTSR = T - kin.dH * np.minimum(np.clip(NA, 0, None), np.clip(NB, 0, None)) / (rx.rhocp * V)
    return pd.DataFrame(dict(
        t=t, V=V, NA=NA, NB=NB, NC=NC, T=T, CA=NA / V, CB=NB / V, CC=NC / V, q=q,
        r=rV / V, XA=1.0 - NA / rx.NA0, Qrxn_W=Qrxn, Qjac_W=Qjac, Qfeed_W=Qfeed,
        dTdt=dTdt, S=S, MTSR=MTSR, acc=np.minimum(NA, NB) / rx.NA0))


def metrics(df):
    i = int(df["T"].idxmax())
    return dict(T_max=df["T"].max(), t_Tmax=df["t"][i], dTdt_max=df["dTdt"].max(),
                S_max=df["S"].max(), MTSR_max=df["MTSR"].max(), acc_max=df["acc"].max(),
                XA_end=df["XA"].iloc[-1], Qrxn_max_W=df["Qrxn_W"].max())
