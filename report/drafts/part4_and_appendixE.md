**Part 4: Numerical Implementation and Verification**

The model passes all seven verification checks for both the bench and the 1000 L case. The smallest margin is the independent spreadsheet comparison, whose largest temperature difference is 23 times below the measurement noise (Table 3).

**Implementation.** The five balances of Part 3 are solved as one system with state vector $\mathbf{y}$:

$$\frac{d\mathbf{y}}{dt}=\mathbf{f}(t,\mathbf{y}),\qquad \mathbf{y}=\left[V,\ N_A,\ N_B,\ N_C,\ T\right]^{T}$$

The system is integrated with scipy.integrate.solve_ivp (LSODA, rtol = atol = 10⁻⁹), which adapts its step so that the estimated local error stays below atol + rtol·|yᵢ|. Because q(t) drops to zero when the feed stops, the integration is stopped exactly at t_feed and restarted, so the solver never steps across the discontinuity. Each run is reported at 800 equally spaced times, and each check reports the worst error over those times.

**Approach.** Verification tests whether the code solves the equations of Part 3; whether those equations describe the real reactor is the separate question of validation (Part 7). Each check therefore compares the code with a result known exactly. The pass limit for the exact identities is 10⁻⁶: far above round-off (about 10⁻¹⁶) and solver error (about 10⁻⁹), and far below the errors of order 10⁻² to 1 that a coding mistake produces. A pass therefore indicates no coding error, and a failure could not be caused by numerical noise alone.

All checks use the Run 1 fit (k_ref = 0.006546 L/(mol·min) at T_ref = 300 K, E_a = 47.15 kJ/mol, ΔH_rxn = −84.14 kJ/mol). The bench case uses the Run 1 conditions (T₀ = T_c = T_f = 298.15 K, q = 0.05 L/min for 20 min), and the 1000 L case is the nominal plant case. Derivations and sample calculations are given in Appendix E.

**Check 1: conservation of A, B and volume.** Stoichiometry alone fixes these sums, whatever the rate or temperature:

$$N_A+N_C=N_{A0},\qquad N_B+N_C=C_{B,f}\,q\,\min(t,\,t_{feed}),\qquad V=V_0+q\,\min(t,\,t_{feed})$$

This check detects a wrong stoichiometric coefficient or sign, the feed entering the wrong balance, or the feed failing to switch off. Because the solver preserves these linear sums exactly, it confirms the structure of the equations rather than numerical accuracy; Checks 3 and 4 test accuracy.

**Check 2: adiabatic energy identity.** With UA = 0 and T_f = T₀, the temperature rise must equal the heat released by the moles reacted:

$$\rho c_p\,V(t)\left[T(t)-T_0\right]=\left(-\Delta H_{rxn}\right)N_C(t)$$

This detects a wrong sign on the reaction or feed term, a missing factor of 60 (W to J/min), V₀ used in place of V(t), or a wrong ρc_p.

**Check 3: isothermal solution after the feed.** With T held at T₀ and a stoichiometric feed, C_A = C_B after the feed and the second-order solution is exact:

$$\frac{1}{C_A(t)}-\frac{1}{C_A(t_{feed})}=k\left(t-t_{feed}\right)$$

This detects a wrong rate law, a wrong Arrhenius evaluation and integration inaccuracy. It is the first check whose exact answer depends on how accurately the solver integrates a nonlinear equation.

**Check 4: tolerance convergence.** The same case is solved at rtol = atol = 10⁻⁶ and at 10⁻¹¹; the production setting (10⁻⁹) lies between them.

$$\Delta T=\max_t\left|T_{10^{-6}}-T_{10^{-11}}\right|,\qquad \Delta X_A=\max_t\left|X_{A,10^{-6}}-X_{A,10^{-11}}\right|$$

This detects a tolerance too loose for the problem, or stiffness the solver is mishandling.

**Check 5: a cooling failure ends at the MTSR.** If cooling and feed stop at t_fail, the simulation must end exactly at the MTSR predicted at that moment:

$$T(t\to\infty)=\mathrm{MTSR}(t_{fail})=T(t_{fail})+\frac{\left(-\Delta H_{rxn}\right)\min\left[N_A(t_{fail}),\ N_B(t_{fail})\right]}{\rho c_p\,V(t_{fail})}$$

This detects errors in the failure logic (UA or feed not switching off) and in the MTSR formula used throughout Part 9.

**Check 6: independent spreadsheet implementation.** Checks 1 to 5 share one code base, so the model was rebuilt separately in a spreadsheet using explicit Euler steps. The two implementations agree to within 0.013 K in T and 0.001 mol/L in C_A at all Run 1 sample times. The difference decreases in proportion to the Euler step size, as first-order theory predicts, so it is Euler's truncation error rather than a disagreement in the equations. This check detects an error shared by the model and its own checks.

**Check 7: heat balance at the temperature peak.** At the peak dT/dt = 0, so the three heat terms must cancel (t = 28.8 min):

$$\dot{Q}_{rxn}+\dot{Q}_{jacket}+\dot{Q}_{feed}=36.95\ \mathrm{W}-36.95\ \mathrm{W}+0=0$$

This confirms the Arrhenius term, the rate law, the unit conversion and the sign of every heat term together.

**Table 3:** Verification results (Run 1 fit; bench = Run 1 conditions; 1000 L = nominal plant case).

| Check | Quantity | Bench | 1000 L | Pass limit | Pass |
|:---:|:------------------------------|:---:|:---:|:---:|:---:|
| 1 | $\varepsilon_A$, conservation of A | 9 × 10⁻¹⁶ | 8 × 10⁻¹⁶ | 10⁻⁶ | Yes |
| 1 | $\varepsilon_B$, conservation of B | 2 × 10⁻¹⁵ | 9 × 10⁻¹⁶ | 10⁻⁶ | Yes |
| 1 | $\varepsilon_V$, volume | 1 × 10⁻¹⁵ | 2 × 10⁻¹⁵ | 10⁻⁶ | Yes |
| 2 | $\varepsilon_E$, adiabatic energy identity | 5 × 10⁻¹⁰ | 1 × 10⁻¹⁰ | 10⁻⁶ | Yes |
| 3 | Isothermal $C_A$, relative error | 4 × 10⁻¹⁰ | 7 × 10⁻¹⁰ | 10⁻⁵ | Yes |
| 4 | $\Delta T$ (K) | 2 × 10⁻⁴ | 1 × 10⁻⁴ | 0.01 | Yes |
| 4 | $\Delta X_A$ | 2 × 10⁻⁶ | 1 × 10⁻⁶ | 10⁻⁴ | Yes |
| 5 | $\lvert T(\infty)-\mathrm{MTSR}\rvert$ (K) | 3 × 10⁻⁹ | 7 × 10⁻⁸ | 0.05 | Yes |
| 6 | Spreadsheet vs solver, max $\lvert\Delta T\rvert$ (K) | 0.013 | n/a | 0.3 (noise) | Yes |

*Source: results/tables/part4_verification_checks.csv, generated by src/model_verification.py.*

```{=openxml}
<w:p><w:r><w:br w:type="page"/></w:r></w:p>
```

**Appendix E: Verification Derivations and Sample Calculations**

Values come from src/model_verification.py and src/verification_examples.py (results/tables/part4_verification_checks.csv and appendixE_worked_examples.json), using the Run 1 fit and Run 1 bench conditions. Constants: ρc_p = 0.90 kg/L × 2000 J/(kg·K) = 1800 J/(L·K) and N_A0 = 2.0 L × 2.0 mol/L = 4.0 mol.

**E.1 Conservation of A, B and volume**

Adding the A and C balances of Part 3 eliminates the reaction term:

$$\frac{dN_A}{dt}+\frac{dN_C}{dt}=-rV+rV=0\quad\Rightarrow\quad N_A(t)+N_C(t)=N_{A0}+N_{C0}=N_{A0}$$

Adding the B and C balances leaves only the feed, which is constant during feeding and zero afterwards (N_B0 = N_C0 = 0). The volume balance dV/dt = q integrates in the same way:

$$\frac{dN_B}{dt}+\frac{dN_C}{dt}=q\,C_{B,f}\quad\Rightarrow\quad N_B(t)+N_C(t)=C_{B,f}\int_0^t q\,dt'=C_{B,f}\,q\,\min(t,\,t_{feed})$$

$$V(t)=V_0+q\,\min(t,\,t_{feed})$$

The error measures are the largest dimensionless mismatch over the output times:

$$\varepsilon_A=\max_t\frac{\left|N_A+N_C-N_{A0}\right|}{N_{A0}},\qquad \varepsilon_B=\max_t\frac{\left|N_B+N_C-C_{B,f}\,q\,\min(t,t_{feed})\right|}{N_{A0}},\qquad \varepsilon_V=\max_t\frac{\left|V-V_0-q\,\min(t,t_{feed})\right|}{V_0}$$

**Sample calculation.**

| t (min) | $N_A$ (mol) | $N_B$ (mol) | $N_C$ (mol) | $N_A+N_C$ (mol) | $N_B+N_C$ (mol) | B fed (mol) | V (L) |
|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---:|
| 9.99 (feeding) | 3.9011 | 1.8986 | 0.0989 | 4.0000 | 1.9975 | 4.0 × 0.05 × 9.99 = 1.9975 | 2.4994 |
| 100.05 (after feed) | 2.2371 | 2.2371 | 1.7629 | 4.0000 | 4.0000 | 4.0 × 0.05 × 20 = 4.0000 | 3.0000 |

**Result.** ε_A = 9 × 10⁻¹⁶, ε_B = 2 × 10⁻¹⁵ and ε_V = 1 × 10⁻¹⁵, which is round-off level. The solver advances every state with the same weighted combination of right-hand-side evaluations, and rV is subtracted from N_A and added to N_C exactly, so any fixed linear combination of the states is preserved at every step, whatever the step size. This check therefore proves that the equations have the correct structure but does not test numerical accuracy.

**E.2 Adiabatic energy identity**

Starting from the Part 3 energy balance:

$$\rho c_p V\frac{dT}{dt}=q\,\rho c_p\left(T_f-T\right)+\left(-\Delta H_{rxn}\right)rV+UA\left(T_c-T\right)$$

Set UA = 0 and T_f = T₀, and define θ = T − T₀, so that T_f − T = −θ:

$$\rho c_p\left(V\frac{d\theta}{dt}+q\,\theta\right)=\left(-\Delta H_{rxn}\right)rV$$

With dV/dt = q, the product rule gives d(Vθ)/dt = V dθ/dt + qθ, which is the bracket on the left. From the C balance, rV = dN_C/dt. Integrating from t = 0, where θ and N_C are both zero:

$$\rho c_p\frac{d(V\theta)}{dt}=\left(-\Delta H_{rxn}\right)\frac{dN_C}{dt}\quad\Rightarrow\quad \rho c_p\,V(t)\left[T(t)-T_0\right]=\left(-\Delta H_{rxn}\right)N_C(t)$$

The condition T_f = T₀ is required, because a colder feed would add qρc_p(T_f − T₀) to the right-hand side. The error measure is scaled by the total heat the charge can release:

$$\varepsilon_E=\max_t\frac{\left|\rho c_p V\left(T-T_0\right)-\left(-\Delta H_{rxn}\right)N_C\right|}{\left(-\Delta H_{rxn}\right)N_{A0}}$$

**Sample calculation.** Run 1 conditions with UA = 0, at t = 100.05 min: V = 3.0 L, T = 350.08 K, N_C = 3.3328 mol.

$$\rho c_p V\left(T-T_0\right)=1800\times3.0\times(350.08-298.15)=280\,421\ \mathrm{J},\qquad \left(-\Delta H_{rxn}\right)N_C=84\,139\times3.3328=280\,421\ \mathrm{J}$$

Without its jacket, the bench reactor would be 52 K above its starting temperature after 100 min.

**Result.** ε_E = 5 × 10⁻¹⁰ (bench) and 1 × 10⁻¹⁰ (1000 L), at the solver-tolerance level because T is now integrated with real numerical error.

**E.3 Isothermal analytical solution after the feed**

Hold T = T₀ so that k is constant. Subtracting the B balance from the A balance removes the reaction term:

$$\frac{d(N_A-N_B)}{dt}=-rV-\left(q\,C_{B,f}-rV\right)=-q\,C_{B,f}\quad\Rightarrow\quad N_A-N_B=N_{A0}-C_{B,f}\,q\,t_{feed}$$

With a stoichiometric feed, C_B,f q t_feed = N_A0, so N_A = N_B and C_A = C_B after the feed. With q = 0 and V = V_f constant, the A balance becomes second order and separates:

$$\frac{dC_A}{dt}=-k\,C_A^{2}\quad\Rightarrow\quad -\int_{C_A(t_{feed})}^{C_A(t)}\frac{dC_A}{C_A^{2}}=\int_{t_{feed}}^{t}k\,dt'\quad\Rightarrow\quad \frac{1}{C_A(t)}-\frac{1}{C_A(t_{feed})}=k\left(t-t_{feed}\right)$$

**Sample calculation.** At T = 298.15 K:

$$k=0.006546\exp\left[-\frac{47\,147}{8.314}\left(\frac{1}{298.15}-\frac{1}{300}\right)\right]=0.006546\times0.88933=0.0058218\ \mathrm{L/(mol\,min)}$$

The first output time after the feed is t = 20.15 min, where C_A = C_B = 1.22574 mol/L. At t = 120.20 min:

$$C_A^{analytic}=\left[\frac{1}{1.22574}+0.0058218\times(120.20-20.15)\right]^{-1}=\left(0.81583+0.58247\right)^{-1}=0.715153\ \mathrm{mol/L}$$

The solver gives C_A = 0.715153 mol/L.

**Result.** The largest post-feed difference divided by C_A0 is 4 × 10⁻¹⁰ (bench) and 7 × 10⁻¹⁰ (1000 L).

**E.4 Solver tolerance convergence**

The same case is solved at rtol = atol = 10⁻⁶ and at 10⁻¹¹, both on 400 output times, with the tight solution as reference. The production setting (10⁻⁹) lies between them, so it is at least as accurate as the loose run.

**Sample calculation.** The largest temperature difference occurs at t = 9.12 min, during the feed, when T changes fastest: both runs give T = 299.050 K, differing by 0.00016 K.

**Result.** ΔT = 1.6 × 10⁻⁴ K (bench) and 1.5 × 10⁻⁴ K (1000 L), against a limit of 0.01 K, which is itself 30 times below the 0.3 K measurement noise. ΔX_A = 2 × 10⁻⁶, against a limit of 10⁻⁴.

**E.5 Cooling failure ends at the MTSR**

After a failure at t_fail with the feed also stopped, UA = 0, q = 0 and V is constant, so the energy balance reduces to

$$\rho c_p V\frac{dT}{dt}=\left(-\Delta H_{rxn}\right)rV=\left(-\Delta H_{rxn}\right)\frac{dN_C}{dt}$$

Integrating from t_fail until the limiting reactant is used up, the additional C formed is min(N_A, N_B) at t_fail:

$$T(t\to\infty)=T(t_{fail})+\frac{\left(-\Delta H_{rxn}\right)\min\left[N_A(t_{fail}),\ N_B(t_{fail})\right]}{\rho c_p\,V(t_{fail})}=\mathrm{MTSR}(t_{fail})$$

**Sample calculation.** Failure at t_fail = 10 min, halfway through the Run 1 feed: T = 299.158 K, N_A = 3.9009 mol, N_B = 1.9009 mol (B is limiting because only half of it has been fed), V = 2.5 L.

$$\mathrm{MTSR}=299.158+\frac{84\,139\times1.9009}{1800\times2.5}=299.158+35.54=334.699\ \mathrm{K}$$

The simulation, continued for 3000 min after the failure, ends at 334.699 K.

**Result.** The difference is 3 × 10⁻⁹ K (bench) and 7 × 10⁻⁸ K (1000 L), against a limit of 0.05 K.

**E.6 Independent spreadsheet implementation (explicit Euler)**

A Taylor expansion about t_n gives

$$\mathbf{y}(t_n+\Delta t)=\mathbf{y}(t_n)+\Delta t\,\mathbf{f}(t_n,\mathbf{y}_n)+\frac{\Delta t^{2}}{2}\,\mathbf{y}''(\xi)$$

Explicit Euler keeps the first two terms:

$$\mathbf{y}_{n+1}=\mathbf{y}_n+\Delta t\,\mathbf{f}(t_n,\mathbf{y}_n)$$

Each step makes an error of order Δt², and reaching time t takes t/Δt steps, so the global error is of order Δt² × t/Δt, that is, O(Δt). Halving Δt should halve the error, and observing this confirms that the spreadsheet formulas implement the method correctly.

**Sample calculation: two steps by hand** (Δt = 0.25 min; Model check tab, rows 25 to 27). At t = 0: V = 2 L, N_A = 4 mol, N_B = 0 and T = 298.15 K. Since N_B = 0, rV = 0, and with T = T_c = T_f every heat term is zero:

$$V_1=2+0.05\times0.25=2.0125\ \mathrm{L},\qquad N_{B,1}=0+0.05\times4.0\times0.25=0.05\ \mathrm{mol},\qquad N_{A,1}=4\ \mathrm{mol},\qquad T_1=298.15\ \mathrm{K}$$

At t = 0.25 min the reaction has started:

$$rV=k\,\frac{N_A N_B}{V}=0.0058218\times\frac{4\times0.05}{2.0125}=5.786\times10^{-4}\ \mathrm{mol/min}$$

$$\dot{Q}_{rxn}=\frac{84\,139\times5.786\times10^{-4}}{60}=0.811\ \mathrm{W},\qquad \frac{dT}{dt}=\frac{0.811\times60}{1800\times2.0125}=0.01344\ \mathrm{K/min}$$

$$T_2=298.15+0.01344\times0.25=298.1534\ \mathrm{K},\qquad N_{A,2}=4-5.786\times10^{-4}\times0.25=3.99986\ \mathrm{mol}$$

$$N_{B,2}=0.05+\left(0.05\times4.0-5.786\times10^{-4}\right)\times0.25=0.09986\ \mathrm{mol}$$

These values match rows 26 and 27 of the Model check tab.

**Result.** At all 150 Run 1 sample times, the spreadsheet and solve_ivp differ by at most 0.013 K in T and 0.001 mol/L in C_A. The difference decreases in proportion to Δt, as first-order theory predicts, so it is Euler's truncation error rather than a disagreement in the equations.

| Δt (min) | 0.5 | 0.25 | 0.1 |
|:------------------------------|:---:|:---:|:---:|
| Max $\lvert T_{Euler}-T_{solver}\rvert$ (K) | 0.0267 | 0.0132 | 0.0052 |
| Ratio to previous step size | | 2.0 | 2.5 |

**E.7 Heat balance at the temperature peak**

At the peak dT/dt = 0, so the three heat terms must sum to zero. At t = 28.8 min: T = 300.61 K, C_A = C_B = 1.136 mol/L, V = 3.0 L, feed off.

$$k=0.006804\ \mathrm{L/(mol\,min)},\qquad rV=k\,C_A C_B\,V=0.02635\ \mathrm{mol/min}$$

$$\dot{Q}_{rxn}=\frac{84\,139\times0.02635}{60}=+36.95\ \mathrm{W},\qquad \dot{Q}_{jacket}=15\times(298.15-300.61)=-36.95\ \mathrm{W},\qquad \dot{Q}_{feed}=0$$

The terms sum to zero, confirming the Arrhenius term, the rate law, the unit conversion and the sign of each heat term together.
