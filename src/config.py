"""Project constants and design settings.

Everything you may want to change lives here. Lines marked DECISION are
engineering choices that must be stated and justified in the report.
Units used throughout the code: L, mol, min, K, J (heat rates reported in W).
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIRS = {"real": ROOT / "data" / "experiments", "synthetic": ROOT / "data" / "synthetic"}
VALIDATION_DIRS = {"real": ROOT / "data" / "validation", "synthetic": ROOT / "data" / "synthetic" / "validation"}
RESULTS_DIR = ROOT / "results"

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
TARGET_X = 0.95      # target conversion of A at BATCH_TIME.  DECISION

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
T_TRIP = 343.15        # K, high-temperature interlock that cuts the B feed (Part D)

FIG_DPI = 200
