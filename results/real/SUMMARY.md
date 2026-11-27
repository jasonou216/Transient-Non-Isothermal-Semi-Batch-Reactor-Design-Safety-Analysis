# Pipeline summary - dataset: `real`

## Fitted parameters
```
    parameter       units   estimate  std_error   ci95_low  ci95_high  rel_95CI_%
k_ref @ 300 K L/(mol min)   0.006546   0.000030   0.006487   0.006606    0.912448
           Ea      kJ/mol  47.146709  11.334870  24.885641  69.407776   47.216589
       dH_rxn      kJ/mol -84.138861   1.453204 -86.992875 -81.284847    3.392028
```

## Model verification
```
                            check       case         value  tolerance    units  passed
                 N_A + N_C = N_A0      bench  8.881784e-16   0.000001 relative    True
                N_B + N_C = B fed      bench  1.554312e-15   0.000001 relative    True
              V = V0 + volume fed      bench  1.054712e-15   0.000001 relative    True
         adiabatic energy balance      bench  5.217117e-10   0.000001 relative    True
isothermal post-feed analytic C_A      bench  3.624645e-10   0.000010 relative    True
         tolerance convergence: T      bench  1.572523e-04   0.010000        K    True
       tolerance convergence: X_A      bench  1.559382e-06   0.000100        -    True
 adiabatic failure T_final = MTSR      bench -2.867012e-09   0.050000        K    True
                 N_A + N_C = N_A0 full scale  7.579123e-16   0.000001 relative    True
                N_B + N_C = B fed full scale  9.473903e-16   0.000001 relative    True
              V = V0 + volume fed full scale  2.084259e-15   0.000001 relative    True
         adiabatic energy balance full scale  1.117455e-10   0.000001 relative    True
isothermal post-feed analytic C_A full scale  6.920450e-10   0.000010 relative    True
         tolerance convergence: T full scale  1.494971e-04   0.010000        K    True
       tolerance convergence: X_A full scale  1.477966e-06   0.000100        -    True
 adiabatic failure T_final = MTSR full scale -7.105865e-08   0.050000        K    True
```

## Full scale nominal
```
{
 "case": {
  "T0": 313.15,
  "Tc": 313.15,
  "t_feed": 120.0,
  "UA_factor": 1.0,
  "UA_W_K": 672.2107119835746,
  "V0_L": 600.0,
  "V_final_L": 900.0,
  "q_Lmin": 2.5,
  "batch_time_min": 240.0
 },
 "full_scale": {
  "T_max": 325.06879075304875,
  "t_Tmax": 96.28023352793996,
  "dTdt_max": 0.212826842693926,
  "S_max": 0.8333037696008717,
  "MTSR_max": 347.3353985574816,
  "acc_max": 0.3673655379426046,
  "XA_end": 0.8389461923541901,
  "Qrxn_max_W": 11464.465735143325
 },
 "bench_same_schedule": {
  "T_max": 314.8697881778116,
  "t_Tmax": 70.65888240200167,
  "dTdt_max": 0.05888140113487637,
  "S_max": 0.11270751627080347,
  "MTSR_max": 343.6681040899773,
  "acc_max": 0.46577064684265485,
  "XA_end": 0.7814429179748117,
  "Qrxn_max_W": 30.048907382858342
 },
 "UA_per_V_bench_W_KL": 5.0,
 "UA_per_V_full_W_KL": 0.7469007910928607,
 "XA_at_feed_stop": 0.6318004337004318,
 "t_to_target_X_min": null
}
```

## Safety
```
{
 "max_safe_feed_rate_Lmin": {
  "(a) T_max criterion": 300.0,
  "(b) MTSR criterion": 9.777545173032587,
  "(c) Morbidelli-Varma peak": 3.676238763360168,
  "design: (a) AND (b)": 9.777545173032587
 },
 "max_safe_feed_min_time_min": {
  "(a) T_max criterion": 1.0,
  "(b) MTSR criterion": 30.682548092687817,
  "(c) Morbidelli-Varma peak": 81.60514572393905,
  "design: (a) AND (b)": 30.682548092687817
 },
 "cooling_failure_nominal": {
  "no interlock": {
   "case": "no interlock",
   "t_fail": 5.172413793103448,
   "T_at_fail": 313.124177485459,
   "MTSR_at_fail": 316.84163171376593,
   "T_max": 370.06951653442434,
   "dT_rise": 56.945339048965366,
   "TMR_min": 59.01865611557132,
   "dTdt_max": 0.5725910856040244,
   "t_to_limit_min": NaN
  },
  "high-T interlock": {
   "case": "high-T interlock",
   "t_fail": 72.41379310344828,
   "T_at_fail": 324.2124537881107,
   "MTSR_at_fail": 342.38411582530017,
   "T_max": 360.20493181885865,
   "dT_rise": 35.992478030747975,
   "TMR_min": 45.56140875526211,
   "dTdt_max": 0.4747974213959494,
   "t_to_limit_min": NaN
  }
 }
}
```

## Design
```
{
 "UA_scaled_W_K": 672.2107119835746,
 "recommended": {
  "policy": "staged",
  "t_feed": 98.67985940279371,
  "frac": 0.5,
  "ratio": 3.0,
  "Tc": 323.15,
  "UA_factor": 0.25,
  "UA_W_K": 168.05267799589365
 },
 "recommended_meets_target": true,
 "recommended_metrics": {
  "XA_end": 0.9563260121299524,
  "T_max": 354.34492918089666,
  "MTSR_max": 364.2273178956206,
  "margin_K": 3.805070819103321,
  "S_max": 5.889462037031289,
  "acc_max": 0.2828455022176385
 },
 "worst_cooling_failure": {
  "no interlock": {
   "case": "no interlock",
   "t_fail": 4.437236531130818,
   "T_at_fail": 322.93354265474545,
   "MTSR_at_fail": 330.731542033377,
   "T_max": 376.85295605770136,
   "dT_rise": 53.91941340295591,
   "TMR_min": 20.562835960483664,
   "dTdt_max": 1.11174786309798,
   "t_to_limit_min": 116.93408314590077
  },
  "high-T interlock": {
   "case": "high-T interlock",
   "t_fail": 4.437236531130818,
   "T_at_fail": 322.93354265474545,
   "MTSR_at_fail": 330.731542033377,
   "T_max": 358.3766571726328,
   "dT_rise": 35.44311451788735,
   "TMR_min": 20.562835960483664,
   "dTdt_max": 1.11174786309798,
   "t_to_limit_min": NaN
  }
 },
 "monte_carlo": {
  "P_unsafe": 0.10666666666666669,
  "T_max_p95": 356.62968618718435,
  "MTSR_max_p95": 369.3413672803719,
  "XA_p05": 0.8785616855354463
 }
}
```
### Sensitivity
```
         case  fixed_XA  fixed_Tmax  fixed_MTSR  fixed_margin_K  fixed_safe reopt_policy  reopt_t_feed  reopt_Tc  reopt_UA_W_K  reopt_XA  reopt_meets_target
         base  0.956326  354.344929  364.227318        3.805071        True       staged     98.679859    323.15    168.052678  0.956326                True
      Ea -10%  0.944179  353.344724  365.340486        2.809514        True       staged     77.976074    333.15    336.105356  0.947082               False
      Ea +10%  0.965675  355.253968  363.268321        2.896032        True       staged     98.679859    313.15    168.052678  0.950345                True
plant UA -20%  0.961899  356.964948  366.294276        1.185052        True       staged     77.976074    313.15    134.442142  0.951195                True
```
