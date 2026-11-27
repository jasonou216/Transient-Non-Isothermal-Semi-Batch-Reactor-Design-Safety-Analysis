"""Build results/tables/ENCH421_Results_by_Run.xlsx: one tab per run (data, mole and conversion
calculations as live formulas, fitted model, residuals, charts), plus Inputs, Fit history and
Method tabs. Upload to Drive to convert it to a Google Sheet.

    python src/results_workbook.py
"""
import json

import numpy as np
from openpyxl import Workbook
from openpyxl.chart import Reference, ScatterChart, Series
from openpyxl.comments import Comment
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

import config as C
from common import bench_reactor, kin_from_theta, load_runs, processed_path, table_path
from semi_batch_model import simulate

FONT = "Arial"
HEAD = PatternFill("solid", fgColor="D9E2F0")
INPUT_FONT = Font(name=FONT, color="0000FF")
BOLD = Font(name=FONT, bold=True)
TITLE = Font(name=FONT, bold=True, size=13)
NORMAL = Font(name=FONT)
THIN = Side(style="thin", color="A0A0A0")
BOX = Border(top=THIN, bottom=THIN, left=THIN, right=THIN)


def style_header(ws, row, c1, c2):
    for c in range(c1, c2 + 1):
        cell = ws.cell(row, c)
        cell.font, cell.fill, cell.border = BOLD, HEAD, BOX
        cell.alignment = Alignment(wrap_text=True, vertical="center", horizontal="center")


def scatter(title, ytitle, xref, series, anchor, ws, ylim=None):
    ch = ScatterChart(scatterStyle="lineMarker")
    ch.title, ch.style, ch.height, ch.width = title, 13, 7.5, 15
    if ylim:
        ch.y_axis.scaling.min, ch.y_axis.scaling.max = ylim
    ch.x_axis.title, ch.y_axis.title = "Time (min)", ytitle
    for ref, name, as_points in series:
        s = Series(ref, xref, title=name)
        if as_points:
            s.marker.symbol, s.marker.size = "circle", 4
            s.graphicalProperties.line.noFill = True
        else:
            s.marker.symbol = "none"
            s.smooth = False
            s.graphicalProperties.line.width = 28575    # 2.25 pt solid line
        ch.series.append(s)
    ws.add_chart(ch, anchor)


def main(dataset="real"):
    runs = load_runs(dataset)
    fit = json.loads((processed_path(dataset, "fitted_parameters.json")).read_text())
    kin = kin_from_theta(np.array(fit["theta"]), fit["T_ref"])
    wb = Workbook()

    # ------------------------------------------------------------------ Inputs
    ws = wb.active
    ws.title = "Inputs"
    ws["A1"], ws["A1"].font = "Bench reactor constants", TITLE
    ws["A2"] = "Blue values are inputs. Everything else in the workbook is calculated from them or from the data."
    ws["A2"].font = Font(name=FONT, italic=True)
    rows = [("V0", "Initial charge volume of A", C.BENCH["V0"], "L"),
            ("CA0", "Initial concentration of A", C.BENCH["CA0"], "mol/L"),
            ("CBf", "B concentration in feed", C.BENCH["CBf"], "mol/L"),
            ("rho", "Solution density", C.BENCH["rho"], "kg/L"),
            ("cp", "Heat capacity", C.BENCH["cp"], "J/(kg K)"),
            ("UA", "Bench jacket UA", C.BENCH["UA"], "W/K"),
            ("T_limit", "Safety limit", C.T_LIMIT, "K")]
    ws.append([])
    ws.append(["Symbol", "Quantity", "Value", "Units"])
    style_header(ws, 4, 1, 4)
    for r in rows:
        ws.append(list(r))
        ws.cell(ws.max_row, 3).font = INPUT_FONT
    ws.append(["NA0", "Initial moles of A", "=C5*C6", "mol"])
    ws["C5"].comment = Comment("Source: BenchtopParameters.pdf (ENCH 421 D2L)", "G33")
    for col, w in zip("ABCD", (10, 30, 12, 12)):
        ws.column_dimensions[col].width = w
    for row in ws.iter_rows(min_row=5, max_row=ws.max_row):
        for c in row:
            c.border = BOX
            if c.font != INPUT_FONT:
                c.font = NORMAL
    V0, CA0, CBF, NA0 = "Inputs!$C$5", "Inputs!$C$6", "Inputs!$C$7", "Inputs!$C$12"

    # ------------------------------------------------------------------ per-run tabs
    summary_refs = []
    for run in runs:
        rid, cond, d = run["run_id"], run["cond"], run["data"]
        ws = wb.create_sheet(f"Run {rid[1:]}")
        n = len(d)
        sim = simulate(bench_reactor(cond), kin, d["t"].max(), t_eval=d["t"].to_numpy())
        ws["A1"], ws["A1"].font = f"Run {rid[1:]}: conditions, data, calculations and fit", TITLE
        cond_rows = [("T0 (K)", cond["T0"]), ("Feed rate q (L/min)", cond["q"]),
                     ("Feed duration (min)", cond["t_feed"]), ("Coolant T (K)", cond["Tc"]),
                     ("Feed T (K)", cond["T_feed"]), ("Run length (min)", cond["t_final"])]
        for i, (k, v) in enumerate(cond_rows):
            ws.cell(3 + i, 1, k).font = BOLD
            ws.cell(3 + i, 2, v).font = INPUT_FONT
            ws.cell(3 + i, 1).border = ws.cell(3 + i, 2).border = BOX
        ws["B3"].comment = Comment("Source: request email to TA (requested conditions), Nov 26 2026", "G33")
        ws.cell(3, 4, "B fed (mol)").font = BOLD
        ws.cell(3, 5, f"=B4*B5*{CBF}")
        ws.cell(4, 4, "B fed / A charged").font = BOLD
        ws.cell(4, 5, f"=E3/{NA0}")
        ws.cell(5, 4, "Final volume (L)").font = BOLD
        ws.cell(5, 5, f"={V0}+B4*B5")
        q, tf = "$B$4", "$B$5"

        h = 11
        heads = ["t (min)", "CA data (mol/L)", "CB data (mol/L)", "CC data (mol/L)", "T data (K)",
                 "V (L)", "NA (mol)", "NB (mol)", "NC (mol)", "NA+NC (mol)", "B fed so far (mol)",
                 "NB+NC (mol)", "X_A = 1 - NA/NA0", "1 - CA/CA0 (ignores dilution)",
                 "CA model", "CB model", "CC model", "T model (K)",
                 "Resid CA", "Resid CB", "Resid CC", "Resid T (K)"]
        for j, hd in enumerate(heads, 1):
            ws.cell(h, j, hd)
        style_header(ws, h, 1, len(heads))
        ws.cell(h - 1, 1, "Measured (TA data)").font = BOLD
        ws.cell(h - 1, 6, "Mole balance and conversion (formulas)").font = BOLD
        ws.cell(h - 1, 15, "Fitted model at the same times").font = BOLD
        ws.cell(h - 1, 19, "Residuals = data - model").font = BOLD
        ws.cell(h, 1).comment = Comment(f"Source: {run['file']}, "
                                        f"{n} rows, returned by TA Nov 26 2026", "G33")
        ws.cell(h, 15).comment = Comment(f"Source: src/parameter_estimation.py fit on {fit['runs']}; "
                                         f"model solved with src/semi_batch_model.py", "G33")
        for i in range(n):
            r = h + 1 + i
            vals = [d["t"][i], d["CA"][i], d["CB"][i], d["CC"][i], d["T"][i]]
            for j, v in enumerate(vals, 1):
                ws.cell(r, j, float(v))
            ws.cell(r, 6, f"={V0}+{q}*MIN(A{r},{tf})")
            ws.cell(r, 7, f"=B{r}*F{r}")
            ws.cell(r, 8, f"=C{r}*F{r}")
            ws.cell(r, 9, f"=D{r}*F{r}")
            ws.cell(r, 10, f"=G{r}+I{r}")
            ws.cell(r, 11, f"={q}*MIN(A{r},{tf})*{CBF}")
            ws.cell(r, 12, f"=H{r}+I{r}")
            ws.cell(r, 13, f"=1-G{r}/{NA0}")
            ws.cell(r, 14, f"=1-B{r}/{CA0}")
            for j, v in enumerate(["CA", "CB", "CC", "T"]):
                ws.cell(r, 15 + j, float(sim[v][i]))
                ws.cell(r, 19 + j, f"={get_column_letter(2 + j)}{r}-{get_column_letter(15 + j)}{r}")
        last = h + n
        for row in ws.iter_rows(min_row=h + 1, max_row=last, max_col=len(heads)):
            for c in row:
                c.font = NORMAL
                c.number_format = "0.0000" if c.column not in (1, 5, 18, 22) else "0.00"
        for j in range(1, len(heads) + 1):
            ws.column_dimensions[get_column_letter(j)].width = 13
        ws.column_dimensions["A"].width = 22
        ws.column_dimensions["D"].width = 18
        ws.freeze_panes = ws.cell(h + 1, 2)

        # charts, to the right of the table
        x = Reference(ws, min_col=1, min_row=h + 1, max_row=last)
        col = lambda c: Reference(ws, min_col=c, min_row=h, max_row=last)
        a = len(heads) + 2
        scatter("Concentrations: data (points) and fitted model (lines)", "C (mol/L)", x,
                [(col(2), "CA data", True), (col(3), "CB data", True), (col(4), "CC data", True),
                 (col(15), "CA model", False), (col(16), "CB model", False), (col(17), "CC model", False)],
                f"{get_column_letter(a)}2", ws)
        tlo, thi = float(np.floor(d["T"].min() - 1)), float(np.ceil(d["T"].max() + 1))
        scatter("Temperature: data and fitted model", "T (K)", x,
                [(col(5), "T data", True), (col(18), "T model", False)], f"{get_column_letter(a)}24", ws,
                ylim=(tlo, thi))
        scatter("Conversion of A: moles basis vs concentration basis", "Conversion (-)", x,
                [(col(13), "X_A = 1 - NA/NA0 (correct)", False),
                 (col(14), "1 - CA/CA0 (ignores dilution)", False)], f"{get_column_letter(a)}46", ws)
        scatter("Residuals (data - model)", "Residual", x,
                [(col(19), "CA", True), (col(20), "CB", True), (col(21), "CC", True)],
                f"{get_column_letter(a)}68", ws)
        summary_refs.append((rid, ws.title, h + 1, last))

    # ------------------------------------------------------------------ Results summary
    ws = wb.create_sheet("Summary", 0)
    ws["A1"], ws["A1"].font = "ENCH 421 G33: results by run", TITLE
    ws["A3"], ws["A3"].font = "Parameter fit history (one row per fit; later fits add rows)", BOLD
    hd = ["Fit", "Runs used", "T_ref (K)", "k_ref (L/(mol min))", "k_ref 95% low", "k_ref 95% high",
          "Ea (kJ/mol)", "Ea 95% low", "Ea 95% high", "dH (kJ/mol)", "dH 95% low", "dH 95% high",
          "Data points", "s^2 (should be about 1)"]
    for j, t in enumerate(hd, 1):
        ws.cell(4, j, t)
    style_header(ws, 4, 1, len(hd))
    import pandas as pd
    tab = pd.read_csv(table_path(dataset, "part6_fitted_parameters"))
    vals = ["Fit 1", ", ".join(fit["runs"]), fit["T_ref"]]
    for _, r in tab.iterrows():
        vals += [r.estimate, r.ci95_low, r.ci95_high]
    vals += [fit["n_obs"], fit["s2"]]
    for j, v in enumerate(vals, 1):
        c = ws.cell(5, j, float(v) if isinstance(v, (int, float, np.floating)) else v)
        c.border, c.font = BOX, NORMAL
        c.number_format = "0.00000" if j in (4, 5, 6) else "0.00"
    ws["A5"].comment = Comment("Source: src/parameter_estimation.py, results/tables/part6_fitted_parameters.csv", "G33")

    ws["A8"], ws["A8"].font = "Key results per run (formulas on each run tab)", BOLD
    hd2 = ["Run", "Final X_A (moles basis)", "1 - CA/CA0 at end (wrong basis)", "Mean NA+NC (mol), expect NA0",
           "Mean NB+NC after feed (mol)", "B fed (mol)", "Max T data (K)", "Max T model (K)",
           "RMSE CA", "RMSE CB", "RMSE CC", "RMSE T (K)"]
    for j, t in enumerate(hd2, 1):
        ws.cell(9, j, t)
    style_header(ws, 9, 1, len(hd2))
    for i, (rid, sh, r0, r1) in enumerate(summary_refs):
        rr = 10 + i
        s = f"'{sh}'!"
        f = [rid, f"={s}M{r1}", f"={s}N{r1}", f"=AVERAGE({s}J{r0}:J{r1})",
             f"=AVERAGEIFS({s}L{r0}:L{r1},{s}A{r0}:A{r1},\">=\"&{s}B5)", f"={s}E3",
             f"=MAX({s}E{r0}:E{r1})", f"=MAX({s}R{r0}:R{r1})"]
        f += [f"=SQRT(SUMSQ({s}{c}{r0}:{c}{r1})/COUNT({s}{c}{r0}:{c}{r1}))" for c in "STUV"]
        for j, v in enumerate(f, 1):
            c = ws.cell(rr, j, v)
            c.border, c.font = BOX, NORMAL
            c.number_format = "0.0%" if j in (2, 3) else "0.000"
    for j in range(1, 15):
        ws.column_dimensions[get_column_letter(j)].width = 15
    ws.row_dimensions[4].height = ws.row_dimensions[9].height = 45

    # ------------------------------------------------------------------ Method
    ws = wb.create_sheet("Method")
    steps = [
        ("How each run is processed", None),
        ("1. Conditions", "The requested T0, feed rate, feed duration, coolant and feed temperature are entered "
         "in blue at the top of the run tab. Source: the request email to the TA."),
        ("2. Volume", "V(t) = V0 + q x min(t, t_feed). B solution is added at q L/min until the feed stops; "
         "nothing leaves, so V rises from 2 L and then stays constant."),
        ("3. Moles", "N_i = C_i x V for each species. Concentrations alone mislead in a semi-batch reactor "
         "because the volume changes."),
        ("4. Data check", "N_A + N_C must stay at N_A0 (A is only converted to C). N_B + N_C must equal the "
         "moles of B fed so far. Both are on the Summary tab."),
        ("5. Conversion", "X_A = 1 - N_A / N_A0, on a moles basis. Using 1 - C_A / C_A0 instead counts the "
         "dilution by the added B solution as if it were reaction, so it overstates conversion. Run 1: "
         "C_A fell from 2.05 to 0.59 mol/L, which looks like about 71 %, but the volume grew from 2 L to "
         "3 L, so N_A = 0.59 x 3 = 1.78 mol of 4.0 mol and X_A = 1 - 1.78/4.0 = 0.55."),
        ("6. Model", "For trial values of k_ref, Ea and dH the semi-batch mole and energy balances are solved "
         "for the run's exact conditions (src/semi_batch_model.py), giving predicted CA, CB, CC and T at each sample time."),
        ("7. Regression", "k_ref, Ea and dH are adjusted to minimise the sum over all runs and all sampled "
         "points of ((data - model) / sigma)^2, where sigma is each variable's noise level, estimated "
         "from the residuals (src/parameter_estimation.py). T_ref is the mean measured temperature. Eight "
         "starting guesses guard against local minima."),
        ("8. Uncertainty", "Cov = s^2 (J^T J)^-1, where J is how the predictions change with each parameter. "
         "95 % intervals use the t distribution. s^2 close to 1 means the model fits to within the noise."),
        ("9. Residuals", "Data minus model, plotted against time. Random scatter around zero means the model "
         "explains the data; a trend would point to a missing effect."),
    ]
    for i, (a, b) in enumerate(steps, 1):
        ws.cell(i, 1, a).font = TITLE if i == 1 else BOLD
        if b:
            ws.cell(i, 2, b).font = NORMAL
            ws.cell(i, 2).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(i, 1).alignment = Alignment(vertical="top")
    ws.column_dimensions["A"].width = 18
    ws.column_dimensions["B"].width = 110

    out = table_path(dataset, "ENCH421_Results_by_Run", "xlsx")
    wb.save(out)
    print("saved", out)


if __name__ == "__main__":
    main()
