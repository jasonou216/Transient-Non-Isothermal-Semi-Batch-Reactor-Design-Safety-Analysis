# Design decisions

Every engineering choice in this project, in one list. All engineering decisions were made by the group. AI tools were used to generate supporting calculations and to challenge the reasoning; outputs used in the report were reviewed before adoption. Each entry gives the value, where it is set
in the code, why it was chosen, and its status. Settled decisions are justified in the report
section listed. Open decisions wait on more data.

All values live in `src/config.py` unless stated otherwise. To change one, edit it there and rerun
`python src/run_pipeline.py`.

## 1. Full-scale design basis (report Part 2, Table 2)

| # | Decision | Value | Set in | Reason | Status |
|---|---|---|---|---|---|
| D1 | Charge of A | 600 L at 2.0 mol/L | `FULL["V0"]` | With 300 L of B the final volume is 900 L, a 90 % fill of the 1000 L vessel. Typical working fills are 70–85 %, so this is at the high end; revisit if more headspace is needed. | Settled |
| D2 | B fed per A charged | 1.0 mol/mol | `FULL["B_to_A"]` | Stoichiometric. Excess B would speed the end of the batch but adds unreacted B that can react if cooling fails (higher MTSR). | TBD: decide at the end with all runs |
| D3 | Jacket UA scaling | UA ∝ V^(2/3) from 15 W/K at 3 L, about 670 W/K at 900 L | `ua_scaled()` | Heat transfer area of geometrically similar vessels scales with V^(2/3). The design step sweeps UA from 0.25 to 2 times this value, so the result does not hinge on the estimate. | Settled |
| D4 | Feed temperature | 25 °C | `FULL["T_feed"]` | B stored at ambient. The cold feed absorbs some reaction heat. | Settled |

## 2. Model assumptions (report Part 3)

| # | Decision | Reason | Status |
|---|---|---|---|
| M1 | Perfect mixing; constant density (0.90 kg/L) and heat capacity (2000 J/(kg·K)) | Given bench properties; dilute liquid phase | Settled |
| M2 | Elementary rate law r = k(T) C_A C_B with Arrhenius k about T_ref | Given form; checked by the residuals and the validation run | Settled; checked in Part 7 |
| M3 | Volume adds linearly (V = V0 + volume fed) | No volume change on mixing at constant density | Settled |
| M4 | Arrhenius reference temperature T_ref = mean measured temperature | Centring reduces the correlation between k_ref and E_a, so both are estimated more precisely | Settled |

## 3. Numerical method (report Part 4)

| # | Decision | Value | Set in | Reason | Status |
|---|---|---|---|---|---|
| N1 | ODE solver | LSODA, rtol = atol = 1e-9 | `semi_batch_model.py` | Switches automatically between stiff and non-stiff methods. The tolerance check in Table 3 shows the results do not depend on it. | Settled |
| N2 | Integration split at every feed switch | | `simulate()` | The feed rate jumps; integrating across a jump would force tiny steps and lose accuracy. | Settled |
| N3 | Interlock modelled as a terminal event | trip at `T_TRIP` | `simulate()` | The feed is cut exactly when T crosses the trip, not at the next output time. | Settled |

## 4. Experimental design (report Part 5)

| # | Decision | Value | Set in | Reason | Status |
|---|---|---|---|---|---|
| E1 | Planning criterion | D-optimal: maximise det(F) | `experiment_planning.py` | Shrinks the joint confidence region of (k_ref, E_a, ΔH) the most per run. | Settled |
| E2 | Safety screen for requested runs | predicted T_max ≤ 80 °C at the fitted E_a and both ends of its 95 % CI | `PLAN_T_MAX` | 20 K below the 100 °C limit, robust to the large E_a uncertainty of early fits. | Settled |
| E3 | Runs requested in pairs, 150 samples, 150 min | | planner defaults | TA approved pairs with one-day turnaround. Five single runs could not finish before the deadline. | Settled |
| E4 | Run 3 moved from 333 K to 315 K | | request email | Planner's top pair had both runs at 333 K. A third temperature tests the Arrhenius form, at a small cost in predicted E_a precision (SE 0.13 instead of 0.11 kJ/mol). | Settled (deliberate override) |
| E5 | Stopping rule | Fit adequate (s² 0.8–1.25, no residual trend), then stop when every 95 % CI is within ±5 % or the best next run cuts the worst SE by < 10 %; otherwise use the 5-run budget | `STOP_*` | Stops when more data would not change the design. | Settled |
| E6 | Runs 4 and 5 | stop at 3 runs | | Stopping rule after Fit 2 met: s² = 1.002, all 95 % CIs within ±1 %; more runs would not change a design number. | Settled 27 Nov (local) |

## 5. Safety criterion (report Part 9)

| # | Decision | Value | Set in | Reason | Status |
|---|---|---|---|---|---|
| S1 | Temperature limit | 100 °C | `T_LIMIT` | Illustrative boiling limit of the solvent. | Settled |
| S2 | Normal-operation margin | T_max ≤ 85 °C (15 K) | `MARGIN_NORMAL` | Room for disturbances and control overshoot. | Settled |
| S3 | Cooling-failure margin | MTSR ≤ 95 °C (5 K) | `MARGIN_FAILURE` | MTSR is already a worst case (all unreacted B reacts adiabatically), so a smaller margin is used. | Settled |
| S4 | Criticality assessment | Stoessel classes from MTSR, MTT and TD24 | report | Industry-standard thermal risk classification. | Settled |
| S5 | High-temperature alarm and trip | alarm 75 °C, trip 80 °C; trip action: automatic B-feed isolation | `T_ALARM`, `T_TRIP` | Alarm 9.2 K above the 92 % design's normal peak (65.8 °C) to avoid nuisance alarms, 5 K below the trip (about 12.5 min at 0.40 K/min). Trip keeps the worst cooling-failure peak at 88.5 °C, 6.5 K below 95 °C (`part10_trip_sweep.csv`). Only the feed isolation is credited. | Settled 28 Nov (local) |

## 5a. Margin definitions (ledger decision D3, settled 28 Nov local)

| Name | Definition | 92 % / 240 min design |
|---|---|---|
| Normal margin | 85 °C − normal peak temperature | 85 − 65.8 = 19.2 K |
| Failure margin (primary safety metric) | 95 °C − MTSR | 95 − 74.7 = 20.3 K |
| Protection-system margin | 95 °C − worst simulated cooling-failure peak with the 80 °C feed trip | 95 − 88.5 = 6.5 K |
| 100 °C margin | 100 °C − normal peak | 34.2 K |

## 6. Design objective and selection rule (report Part 10)

| # | Decision | Value | Set in | Reason | Status |
|---|---|---|---|---|---|
| P1 | Batch time | 240 min | `BATCH_TIME` | 360 min rejected: about a third less throughput for margins similar to 92 % / 240 min. | Settled 27 Nov (local) |
| P2 | Target conversion of A | 0.92 | `TARGET_X` | Operating robustness at the installed jacket: 9.2 K alarm-to-trip room vs 2.7 K at 95 %, 0 % vs 3.5 % probability below target, conversion spare 0.008 vs 0.0003; cost 2.4 % less product per batch, same throughput (`part10_design_scenarios.csv`, `part10_trip_sweep.csv`, `part10_scenario_robustness.csv`). | Settled 28 Nov (local) |
| P3 | Selection rule | installed jacket (672 W/K), then the largest safety margin | `config.UA_SELECTION`, `design_optimization.pick()` | Designing at the jacket that would exist avoids a design that only works with deliberately restricted cooling. | Settled 27 Nov (local), replaces "smallest UA" |
| P4 | Feed policies searched | constant rate; two-stage (fast then slow) | `design_optimization.py` | A staged feed lets B react early while the reactor is cool, limiting accumulation. | Settled |
| P5 | Robustness tests | E_a ±10 %, UA −20 %, Monte Carlo over the parameter covariance | `design_optimization.py` | Required by the brief; the Monte Carlo uses the actual fitted uncertainty. | Settled |

## Key insight behind P1–P2

MTSR assumes cooling has already failed, so jacket size cannot lower it. Only less unreacted B in
the reactor lowers it, which means a slower feed. Under a fixed batch time, a slower feed leaves less
time to finish the reaction. So the **conversion target and the batch time**, not UA, set the safety
margin, and those are the decisions to settle once the final parameters are known.
