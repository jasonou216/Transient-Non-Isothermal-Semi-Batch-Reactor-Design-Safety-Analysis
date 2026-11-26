# Pipeline summary - dataset: `synthetic`

> SYNTHETIC DATA - pipeline self-test only. Do not use these numbers in the report.

## Fitted parameters
```
    parameter       units   estimate  std_error   ci95_low  ci95_high  rel_95CI_%
k_ref @ 310 K L/(mol min)   0.067888   0.000546   0.066824   0.068969    1.579568
           Ea      kJ/mol  64.408320   0.500765  63.425346  65.391295    1.526161
       dH_rxn      kJ/mol -90.198533   0.707788 -91.587883 -88.809184    1.540324
```

### Truth recovery (synthetic)
```
    parameter   estimate   ci95_low  ci95_high       true  true_inside_95CI
k_ref @ 310 K   0.067888   0.066824   0.068969   0.068205              True
           Ea  64.408320  63.425346  65.391295  65.000000              True
       dH_rxn -90.198533 -91.587883 -88.809184 -90.000000              True
```

## Model verification
```
                            check       case         value  tolerance    units  passed
                 N_A + N_C = N_A0      bench  8.881784e-16   0.000001 relative    True
                N_B + N_C = B fed      bench  1.332268e-15   0.000001 relative    True
              V = V0 + volume fed      bench  2.886580e-15   0.000001 relative    True
         adiabatic energy balance      bench  8.743339e-10   0.000001 relative    True
isothermal post-feed analytic C_A      bench  9.256637e-10   0.000010 relative    True
         tolerance convergence: T      bench  3.679874e-04   0.010000        K    True
       tolerance convergence: X_A      bench  5.834238e-06   0.000100        -    True
 adiabatic failure T_final = MTSR      bench -1.170974e-10   0.050000        K    True
                 N_A + N_C = N_A0 full scale  1.326346e-15   0.000001 relative    True
                N_B + N_C = B fed full scale  1.705303e-15   0.000001 relative    True
              V = V0 + volume fed full scale  1.329307e-15   0.000001 relative    True
         adiabatic energy balance full scale  3.804387e-11   0.000001 relative    True
isothermal post-feed analytic C_A full scale  3.083362e-10   0.000010 relative    True
         tolerance convergence: T full scale  4.904042e-05   0.010000        K    True
       tolerance convergence: X_A full scale  2.388116e-07   0.000100        -    True
 adiabatic failure T_final = MTSR full scale -8.253664e-11   0.050000        K    True
```

## Validation
```
run variable units     RMSE      bias  max_abs_error
 V1       CA mol/L 0.029245  0.007558       0.066099
 V1       CB mol/L 0.031842 -0.005960       0.101635
 V1       CC mol/L 0.029234  0.005143       0.077227
 V1        T     K 0.523966 -0.026740       1.141277
 V1    T_max     K      NaN -1.025560            NaN
 V1 t(T_max)   min      NaN  2.520939            NaN
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
  "T_max": 329.7298707606481,
  "t_Tmax": 80.26688907422853,
  "dTdt_max": 0.5531249220585033,
  "S_max": 1.6413953158671082,
  "MTSR_max": 335.5420667887753,
  "acc_max": 0.11789901869625977,
  "XA_end": 0.968973556108416,
  "Qrxn_max_W": 16315.045001456187
 },
 "bench_same_schedule": {
  "T_max": 315.9710351043469,
  "t_Tmax": 28.023352793994995,
  "dTdt_max": 0.2388098708491743,
  "S_max": 0.2411405882293251,
  "MTSR_max": 327.81382952587876,
  "acc_max": 0.19174824050477146,
  "XA_end": 0.9495258754564955,
  "Qrxn_max_W": 47.35992059662449
 },
 "UA_per_V_bench_W_KL": 5.0,
 "UA_per_V_full_W_KL": 0.7469007910928607,
 "XA_at_feed_stop": 0.8812669529467757,
 "t_to_target_X_min": 161.9349457881568
}
```

## Safety
```
{
 "max_safe_feed_rate_Lmin": {
  "(a) T_max criterion": 15.945674391740875,
  "(b) MTSR criterion": 20.36335919066617,
  "(c) Morbidelli-Varma peak": 5.3053434689829535,
  "design: (a) AND (b)": 15.945674391740875
 },
 "max_safe_feed_min_time_min": {
  "(a) T_max criterion": 18.813879716206056,
  "(b) MTSR criterion": 14.732343381612067,
  "(c) Morbidelli-Varma peak": 56.54676304256521,
  "design: (a) AND (b)": 18.813879716206056
 },
 "cooling_failure_nominal": {
  "no interlock": {
   "case": "no interlock",
   "t_fail": 0.0,
   "T_at_fail": 313.15,
   "MTSR_at_fail": 313.15,
   "T_max": 374.9435739947508,
   "dT_rise": 61.79357399475083,
   "TMR_min": 17.211474316210808,
   "dTdt_max": 0.7976657156817281,
   "t_to_limit_min": 120.88058705803869
  },
  "high-T interlock": {
   "case": "high-T interlock",
   "t_fail": 87.93103448275862,
   "T_at_fail": 329.7440053600617,
   "MTSR_at_fail": 333.5276174266569,
   "T_max": 348.06305184499166,
   "dT_rise": 18.31904648492997,
   "TMR_min": 7.525706793034431,
   "dTdt_max": 0.471488897414282,
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
  "t_feed": 200.0,
  "frac": 0.3,
  "ratio": 3.0,
  "Tc": 303.15,
  "UA_factor": 0.25,
  "UA_W_K": 168.05267799589365
 },
 "recommended_meets_target": true,
 "recommended_metrics": {
  "XA_end": 0.9675538056241177,
  "T_max": 333.0969666570735,
  "MTSR_max": 336.7728648194453,
  "margin_K": 25.053033342926483,
  "S_max": 9.876270689779643,
  "acc_max": 0.09547550145683402
 },
 "worst_cooling_failure": {
  "no interlock": {
   "case": "no interlock",
   "t_fail": 0.0,
   "T_at_fail": 303.15,
   "MTSR_at_fail": 303.15,
   "T_max": 368.2622067898385,
   "dT_rise": 65.11220678983852,
   "TMR_min": 25.216811207471647,
   "dTdt_max": 1.3724904951956263,
   "t_to_limit_min": NaN
  },
  "high-T interlock": {
   "case": "high-T interlock",
   "t_fail": 142.75862068965517,
   "T_at_fail": 333.06456387313943,
   "MTSR_at_fail": 334.9673331525827,
   "T_max": 346.10674856848266,
   "dT_rise": 13.042184695343224,
   "TMR_min": 7.874214993903962,
   "dTdt_max": 0.22334396496482958,
   "t_to_limit_min": NaN
  }
 },
 "monte_carlo": {
  "P_unsafe": 0.0,
  "T_max_p95": 333.5190005406353,
  "MTSR_max_p95": 337.21609399561464,
  "XA_p05": 0.9668469317621083
 }
}
```
### Sensitivity
```
         case  fixed_XA  fixed_Tmax  fixed_MTSR  fixed_margin_K  fixed_safe reopt_policy  reopt_t_feed  reopt_Tc  reopt_UA_W_K  reopt_XA  reopt_meets_target
         base  0.967554  333.096967  336.772865       25.053033        True       staged         200.0    303.15    168.052678  0.967554                True
      Ea -10%  0.963049  332.883198  336.977558       25.266802        True       staged         200.0    303.15    168.052678  0.963049                True
      Ea +10%  0.971585  333.292680  336.590827       24.857320        True       staged         200.0    303.15    168.052678  0.971585                True
plant UA -20%  0.974784  337.172391  340.677691       20.977609        True       staged         200.0    303.15    134.442142  0.974784                True
```
