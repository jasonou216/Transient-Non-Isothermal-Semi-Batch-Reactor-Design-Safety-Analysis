# Part 5: experimental strategy and stopping rule (as in the report)

Settings used by the code: `src/config.py` (PLAN_T_MAX, STOP_REL_CI, STOP_MIN_GAIN, STOP_S2_RANGE).
The planner prints whether the stopping rule is met: `python src/plan_experiments.py --dataset real --batch 2 --n_points 150`.

**Experimental strategy**

1. **Identifiability:** can the data pin down each parameter?
   - k_ref: how fast C_A and C_B fall at a known temperature.
   - E_a: the slope of ln k against 1/T, so runs are needed at temperatures far apart. With the Run 1 estimate (E_a = 47 kJ/mol), k changes 1.8 times over 10 K (300 to 310 K) but 7.4 times between Run 1 (298 K) and Run 2 (333 K).
   - ΔH: the size of the temperature bump, which a faster feed makes larger.
   - Why a known UA matters: the jacket's heat removal can be calculated exactly, so the remaining heat gives ΔH. If UA were unknown, a larger ΔH with a larger UA could fit the same temperature curve.
2. **Safety screen:** each run is simulated with the current fit before it is sent, at the fitted E_a and at both ends of its 95% confidence interval, and is only sent if the predicted T_max ≤ 80 °C. The 20 K margin below the 100 °C limit covers the uncertainty in early fits.
3. **Batched sequential design:** runs are sent in pairs (TA-approved, one-day turnaround), the model is refitted after each pair, and the next pair targets what is still uncertain. Candidate pairs are scored by det(F), F = Σ JᵀWJ, the Fisher information of the runs already done plus the candidates (J: sensitivities of the predicted data to each parameter; W = 1/σ²). A larger det(F) means a smaller joint confidence region; scoring the pair together prevents near-duplicate runs. The top pair placed both runs at 333 K; Run 3 was moved to 315 K at a small cost (predicted E_a standard error 0.13 instead of 0.11 kJ/mol) so that three temperatures test the Arrhenius form.

**Stopping rule**

The fit must first be adequate: every run fitted to within measurement noise (s² close to 1) with no trend in the residuals. Experimentation then stops as soon as either:
- every parameter's 95% confidence interval is within ±5% of its value (for E_a = 47 kJ/mol, about ±2.4 kJ/mol), or
- the best remaining candidate would reduce the standard error of the least certain parameter by less than 10%.

Otherwise, runs continue until the 5-run budget is used.

After Run 1: adequacy met (s² = 1.004); precision not met (E_a ±47%); the best pair cuts the E_a standard error by 99% → continue.
