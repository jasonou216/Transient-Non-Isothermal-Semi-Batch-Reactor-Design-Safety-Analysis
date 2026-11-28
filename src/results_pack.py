"""Build results/ENCH421_Results_Pack.docx: every report figure with its finding caption and the
key tables, in the report's format (Times New Roman, black, bold labels). Upload it to Drive to
open it as a Google Doc. Numbers are read from results/ and data/processed/, never typed in.

    python src/results_pack.py
"""
import json

import numpy as np
import pandas as pd
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Inches, Pt

import config as C
from run_pipeline import FIGURES, describe, findings

K = 273.15
D = C.DATASETS["real"]
TAB, FIG = D["results"] / "tables", D["results"] / "figures"


def style(doc):
    st = doc.styles["Normal"]
    st.font.name, st.font.size = "Times New Roman", Pt(10)
    st.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")


def para(doc, text, bold=False, size=10, italic=False, align=None):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic, r.font.size = bold, italic, Pt(size)
    if align:
        p.alignment = align
    return p


def table(doc, df, caption, source, fmt="{:.4g}"):
    para(doc, caption, bold=True)
    t = doc.add_table(rows=1, cols=len(df.columns))
    t.style = "Table Grid"
    for c, name in zip(t.rows[0].cells, df.columns):
        c.text = ""
        c.paragraphs[0].add_run(str(name)).bold = True
    for _, row in df.iterrows():
        cells = t.add_row().cells
        for c, v in zip(cells, row):
            c.text = fmt.format(v) if isinstance(v, (float, np.floating)) else str(v)
    for row in t.rows:
        for c in row.cells:
            for p in c.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(8.5)
    para(doc, f"Source: {source}", italic=True, size=8)


def figure(doc, n, stem, found):
    path = FIG / f"{stem}.png"
    if not path.exists():
        return n
    doc.add_picture(str(path), width=Inches(6.5))
    doc.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
    part, what = describe(stem, FIGURES)
    p = doc.add_paragraph()
    p.add_run(f"Figure {n} ({part}). ").bold = True
    p.add_run(what + (" " + found[stem] if stem in found else ""))
    para(doc, f"Source: results/figures/{stem}.png", italic=True, size=8)
    return n + 1


def main():
    fit = json.loads((D["processed"] / "fitted_parameters.json").read_text())
    found = findings("real")
    doc = Document()
    style(doc)
    para(doc, "ENCH 421 Design Project, Group G33: Results Pack", bold=True, size=14)
    para(doc, "Jason Ou (30260612), Bella Kim (30246960)")
    para(doc, f"Parameters: fit to runs {', '.join(fit['runs'])}. Design settings at the time of generation: "
              f"target X_A = {C.TARGET_X} in {C.BATCH_TIME:.0f} min, feed trip {C.T_TRIP - K:.0f} C, "
              f"design at the installed jacket. The conversion target is still under group decision (D2).")
    para(doc, "Every number below is read from the repository's results files by src/results_pack.py. "
              "The interpretation and discussion are in the report.", italic=True)

    n = 1
    para(doc, "1. Parameter estimation (Parts 5 and 6)", bold=True, size=12)
    h = pd.read_csv(TAB / "part5_fit_history.csv")
    h = h.assign(estimate=h.estimate.map("{:.4g}".format),
                 ci=[f"{a:.4g} to {b:.4g}" for a, b in zip(h.ci95_low, h.ci95_high)],
                 rel=h.rel_95CI_pct.map("{:.2f}".format))
    table(doc, h[["fit", "runs", "parameter", "units", "estimate", "ci", "rel", "s2"]]
          .rename(columns={"ci": "95 % CI", "rel": "95 % CI (+/- %)", "s2": "s^2"}),
          "Table A. Parameter estimates after each refit.", "results/tables/part5_fit_history.csv")
    corr = pd.read_csv(TAB / "part6_parameter_correlation.csv").rename(columns={"Unnamed: 0": ""})
    table(doc, corr, "Table B. Correlation between the fitted parameters (Fit 2).",
          "results/tables/part6_parameter_correlation.csv", fmt="{:.3f}")
    for s in ["fig01_fit_runs", "fig02_fit_residuals"]:
        n = figure(doc, n, s, found)

    para(doc, "2. Verification (Part 4)", bold=True, size=12)
    v = pd.read_csv(TAB / "part4_verification_checks.csv")
    v = v.assign(value=v.value.map("{:.1e}".format), tolerance=v.tolerance.map("{:.0e}".format),
                 passed=v.passed.map({True: "pass", False: "FAIL"}))
    table(doc, v, "Table C. Verification checks (Fit 2 parameters).", "results/tables/part4_verification_checks.csv")

    para(doc, "3. Full-scale nominal operation (Part 8)", bold=True, size=12)
    s8 = json.loads((TAB / "part8_nominal_summary.json").read_text())
    rows = [("X_A at end of batch", s8["full_scale"]["XA_end"], s8["bench_same_schedule"]["XA_end"], "-"),
            ("Peak temperature", s8["full_scale"]["T_max"] - K, s8["bench_same_schedule"]["T_max"] - K, "C"),
            ("Highest MTSR", s8["full_scale"]["MTSR_max"] - K, s8["bench_same_schedule"]["MTSR_max"] - K, "C"),
            ("Peak heat release", s8["full_scale"]["Qrxn_max_W"], s8["bench_same_schedule"]["Qrxn_max_W"], "W"),
            ("UA per litre", s8["UA_per_V_full_W_KL"], s8["UA_per_V_bench_W_KL"], "W/(K L)")]
    table(doc, pd.DataFrame(rows, columns=["quantity", "1000 L plant", "bench, same schedule", "units"]),
          "Table D. Nominal case: plant against bench.", "results/tables/part8_nominal_summary.json")
    for s in ["fig04_plant_nominal_profiles", "fig05_bench_vs_plant"]:
        n = figure(doc, n, s, found)

    para(doc, "4. Runaway and cooling failure (Part 9)", bold=True, size=12)
    s9 = json.loads((TAB / "part9_safety_summary.json").read_text())
    q = s9["max_safe_feed_rate_Lmin"]
    rows = [(k, v, s9["max_safe_feed_min_time_min"][k]) for k, v in q.items()]
    table(doc, pd.DataFrame(rows, columns=["criterion", "max feed rate (L/min)", "min feed time (min)"]),
          "Table E. Maximum safe feed rate by criterion (nominal case).", "results/tables/part9_safety_summary.json")
    rows = [(c, v["t_fail"], v["T_at_fail"] - K, v["MTSR_at_fail"] - K, v["T_max"] - K, v["TMR_min"])
            for c, v in s9["cooling_failure_nominal"].items()]
    table(doc, pd.DataFrame(rows, columns=["case", "worst failure time (min)", "T at failure (C)",
                                           "MTSR at failure (C)", "peak after failure (C)", "time to peak rate (min)"]),
          "Table F. Worst cooling failure, nominal case.", "results/tables/part9_safety_summary.json")
    for s in ["fig06_feed_rate_scan", "fig07_cooling_failure", "fig08_runaway_map_q_vs_UA", "fig09_runaway_map_q_vs_Tc"]:
        n = figure(doc, n, s, found)

    para(doc, "5. Design recommendation (Parts 10 and 12)", bold=True, size=12)
    sc = pd.read_csv(TAB / "part10_design_scenarios.csv")
    sc = sc[["target_X", "batch_min", "policy", "t_feed_min", "Tc_C", "UA_W_K", "X_A", "T_peak_C", "MTSR_max_C",
             "margin_K", "P_unsafe", "X_A_p05"]]
    table(doc, sc.rename(columns={"margin_K": "margin (K)", "P_unsafe": "P(unsafe)", "X_A_p05": "X_A 5th pct"}),
          "Table G. Best design for each conversion target and batch time (installed jacket).",
          "results/tables/part10_design_scenarios.csv")
    tr = pd.read_csv(TAB / "part10_trip_sweep.csv")
    tr = tr[["target_X", "batch_min", "normal_peak_C", "trip_C", "nuisance_trip", "worst_failure_peak_C",
             "max_heating_rate_K_min"]]
    table(doc, tr, "Table H. Feed-trip setting against nuisance trips and the worst cooling-failure peak.",
          "results/tables/part10_trip_sweep.csv")
    for s in ["fig10_conversion_vs_UA", "fig11_recommended_design"]:
        n = figure(doc, n, s, found)

    para(doc, "6. Sensitivity and robustness (Part 11)", bold=True, size=12)
    se = pd.read_csv(TAB / "part11_sensitivity.csv")
    se = se.assign(fixed_Tmax=se.fixed_Tmax - K, fixed_MTSR=se.fixed_MTSR - K)
    table(doc, se[["case", "fixed_XA", "fixed_Tmax", "fixed_MTSR", "fixed_margin_K", "fixed_safe", "reopt_meets_target"]]
          .rename(columns={"fixed_XA": "X_A", "fixed_Tmax": "peak (C)", "fixed_MTSR": "MTSR (C)",
                           "fixed_margin_K": "margin (K)", "fixed_safe": "safe", "reopt_meets_target": "re-optimised meets target"}),
          "Table I. Recommended design under perturbed parameters (design held fixed).",
          "results/tables/part11_sensitivity.csv")
    n = figure(doc, n, "fig12_monte_carlo", found)

    out = D["results"] / "ENCH421_Results_Pack.docx"
    doc.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
