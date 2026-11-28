"""Project constants and design settings.

Everything you may want to change lives here. Lines marked DECISION are
engineering choices that must be stated and justified in the report.
Units used throughout the code: L, mol, min, K, J (heat rates reported in W).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Where each dataset lives.  "real" is the bench data from the TA; "synthetic" is the
# self-test (data made from known parameters, used to prove the pipeline recovers them).
#   raw         data files exactly as returned (never edited by hand or by code)
#   experiments the run manifests: runs.csv (fitting) and validation_runs.csv
#   processed   intermediate data written by the code (fitted parameters, profiles, grids)
#   results     report-ready figures/ and tables/
_SYN = ROOT / "data" / "synthetic"
DATASETS = {
    "real": dict(raw=ROOT / "data" / "raw", experiments=ROOT / "data" / "experiments",
                 processed=ROOT / "data" / "processed", results=ROOT / "results"),
    "synthetic": dict(raw=_SYN / "raw", experiments=_SYN / "experiments",
                      processed=_SYN / "processed", results=ROOT / "results" / "synthetic_selftest"),
}

R = 8.314  # J/(mol K)

# ---------------------------------------------------------------------------
# Bench reactor (BenchtopParameters.pdf). Fixed, known.
# ---------------------------------------------------------------------------
BENCH = dict(
    V0=2.0,          # L, initial charge of A
    CA0=2.0,         # mol/L
    CBf=4.0,         # mol/L, B in the feed
    rho=0.90,        # kg/L
    cp=2000.0,       # J/(kg K)
    UA=15.0,         # W/K
    T_feed=298.15,   # K (default; can be overridden per experiment in runs.csv)
)
T_LIMIT = 373.15     # K, illustrative safety limit (boiling)

# Initial guess for the regression, and for experiment planning before any data.
# Only a starting point: the fit uses several starts around it.
PRIOR = dict(k_ref=0.05, Ea=60e3, dH=-80e3, T_ref=320.0)   # L/(mol min), J/mol, J/mol, K

# ---------------------------------------------------------------------------
# Full-scale 1000 L design basis
# ---------------------------------------------------------------------------
FULL = dict(
    V0=600.0,        # L of A charged.  DECISION: 600 L A + 300 L B = 900 L final (90 % fill)
    CA0=2.0, CBf=4.0, rho=0.90, cp=2000.0,
    T_feed=298.15,
    B_to_A=1.0,      # DECISION: total B fed / A charged (mol/mol)
)
# DECISION: jacket UA scales with wetted area ~ V^(2/3). Bench reference = 3 L
# (2 L A + 1 L B). Gives ~670 W/K at 900 L. The design step sweeps UA anyway.
UA_BENCH_REF_VOLUME = 3.0
def ua_scaled(V_final=FULL["V0"] * 1.5):
    return BENCH["UA"] * (V_final / UA_BENCH_REF_VOLUME) ** (2.0 / 3.0)

NOMINAL = dict(      # Part A nominal full-scale case.  DECISION
    T0=313.15,       # K, initial charge temperature (charge pre-heated to Tc)
    Tc=313.15,       # K, coolant temperature
    t_feed=120.0,    # min, constant-rate feed of all B
    UA_factor=1.0,   # x ua_scaled()
)
BATCH_TIME = 240.0   # min, fixed batch time for the conversion objective.  DECISION
TARGET_X = 0.92      # target conversion of A at BATCH_TIME.  DECISION D2 (28 Nov local): 92 % chosen over 95 %
                     #    for operating robustness: 9.2 K alarm-to-trip room vs 2.7 K, 0 % vs 3.5 % below target.

# ---------------------------------------------------------------------------
# Safety criterion (Part C).  DECISION - state these explicitly in the report.
# A design is "safe" if BOTH hold:
#   normal operation:  T_max  <= T_LIMIT - MARGIN_NORMAL
#   cooling failure:   MTSR_max <= T_LIMIT - MARGIN_FAILURE
# MTSR (maximum temperature of the synthesis reaction, Stoessel) = T + adiabatic
# rise of the unreacted (accumulated) limiting reactant if cooling is lost and
# the feed is stopped.
# ---------------------------------------------------------------------------
MARGIN_NORMAL = 15.0   # K
MARGIN_FAILURE = 5.0   # K
T_TRIP = 353.15        # K (80 C), high-temperature trip that cuts the B feed.  DECISION D1 (27 Nov local):
                       #    worst cooling-failure peak stays well below 95 C, clear of the 85 C region.
                       #    Action: automatic B-feed isolation, the only protection credited in the
                       #    safety calculation (operator action, cooling restoration, dump, quench: not credited).
T_ALARM = 348.15       # K (75 C), high-temperature alarm.  DECISION D1 (28 Nov local): 9.2 K above the
                       #    92 % design's normal peak (fewer nuisance alarms), 5 K below the trip
                       #    (about 12.5 min of operator time at 0.40 K/min).

# DECISION D4 (27 Nov local): design at the jacket that would be installed (ua_scaled(), 672 W/K),
# then the largest margin. "smallest" restores the earlier rule (smallest UA reaching the target).
UA_SELECTION = "installed"
UA_INSTALLED_FACTOR = 1.0

# Experimental design (Part 5).  DECISION - stated in the report.
PLAN_T_MAX = T_LIMIT - 20.0  # K, safety screen: send a run only if predicted T_max <= 80 C
                             #    (checked at the fitted Ea and both ends of its 95 % CI)
STOP_REL_CI = 5.0            # %, stop if every parameter's 95 % CI is within +/- this
STOP_MIN_GAIN = 0.10         # stop if the best candidate cuts the SE of the least certain
                             #    parameter by less than this fraction
STOP_S2_RANGE = (0.8, 1.25)
FIT_MILESTONES = [1, 3]      # number of runs at each refit, as the campaign was run: Fit 1 after Run 1,
                             #    Fit 2 after the Run 2 + 3 pair (part5_fit_history.csv)  # fit adequacy prerequisite: s^2 (weighted residual variance)

FIG_DPI = 200
