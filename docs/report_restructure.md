# Report restructure, explanation standard, and who edits what

This is the task-level plan that `CLAUDE.md` refers to. It answers three questions:

1. What actually moves in the report.
2. What "explain it better" means, sentence by sentence.
3. Which files you edit, which Claude edits, and which nobody edits by hand.

---

## 1. Target architecture

Keep the Part numbers. Do not renumber this close to the deadline. The restructure is rebalancing, moving, and adding interpretation, not renumbering.

| Section | Pages | Was | Change |
|---|---|---|---|
| Title + Executive summary | 1.0 | 1 page of bullet prompts | Rewrite as a numbers page; add a "Results at a glance" table |
| Roadmap (brief A–D → sections) | 0.25 | Rubric map with weights | Replace; no weights |
| 1 Introduction | 0.5 | 0.5 | Keep |
| 2 Design basis | 1.0 | 1.0 | Add B:A rationale; define margins |
| 3 Model | 2.5 | 3.0 | Keep; tighten assumptions |
| 4 Verification | 1.5 | 2.0 | Cut detail to Appendix E |
| 5 Experimental design | 2.0 | 1.5 | Add stopping-rule verdict and Run 1 rationale |
| 6 Parameters | 2.5 | 1.5 | Add interpretation subsection |
| 7 Validation | 1.0 | 0.5 | Fill when data arrives |
| 8 Nominal and scale-up | 2.0 | 0.5 | Add interpretation subsection |
| 9 Safety | 3.0 | 0.5 | Assemble; add risk subsection |
| 10 Design | 2.5 | 0.5 | Assemble; add matrix and decision record |
| 11 Sensitivity | 1.0 | 0.25 | Add "fragile vs stable" |
| 12 Instrumentation | 1.0 | 0.25 | Alarm/trip table, layers |
| 13 Conclusions and limitations | 1.0 | 0.5 | Bound the conclusions |
| Appendix A Code + how to run | 3–5 | marker | Assemble |
| Appendix B AI log | 10–15 | marker | Full transcripts |
| Appendix C Requests + data | 1 | 3 pages of raw CSV | 10-row excerpt + file pointer |
| Appendix D Nomenclature | 1 | 1 | Keep |
| Appendix E Verification derivations | 3–5 | 3 | Keep; this is now proportionate |
| Appendix F Decision record | 1 | none | Add |

Body ≈ 22 pages. Appendices are not counted.

---

## 2. The ten structural moves

Do these before writing any new analysis. They are mechanical and can be done in one session.

1. **Delete the rubric map** on page 1 and add a roadmap: `Part A → §8`, `Part B → §5–7`, `Part C → §9`, `Part D → §10–12`. No weights.
2. **Replace the executive-summary bullets** with a one-page summary of numbers, then a compact "Results at a glance" table (quantity, value, source).
3. **Compress Part 4 to 1.5 pages.** Keep the implementation paragraph, the approach paragraph, one sentence per check, and Table 3. Move all derivations and worked examples to Appendix E.
4. **Remove the three pages of raw Run 1 CSV.** Put a 10-row excerpt in Appendix C and point to `data/raw/G33_run_20261126_140647.csv`.
5. **Add Appendix F, the decision record.** One table: decision, alternatives, evidence, choice, reason, residual risk. This is the clearest evidence that the alternatives were weighed.
6. **Add an interpretation subsection to Parts 6, 8, 9, 10 and 11**, each following the four-question standard in §3.
7. **Add cross-references** where one result drives another: §6 parameters → §9 safety; §8 nominal → §9 design; §9 criterion → §10 recommendation; §10 design → §12 setpoints.
8. **Add a "what changes at Fit 2" paragraph** to Parts 6, 9, 10 and 11. It costs three sentences and protects every provisional number.
9. **Replace figure placeholders with the actual PNGs**, each with a caption that states the finding. One figure per claim; if a figure carries two claims, split the sentence.
10. **Run the consistency pass:** margins labelled (normal 14.6 K to 85 °C; MTSR 13.2 K to 95 °C), TMR from the design case (not the nominal 59 min), source paths that exist (`model_verification.py`, `part4_verification_checks.csv`, `part10_trip_sweep.csv`), 800 vs 400 output times, MSTR → MTSR, "Sign convection" → "Sign convention".

---

## 3. The explanation standard

Every key result gets four sentences, in this order. This is the difference between "reporting" and "interpreting", and it is what B2, B3, B4 and B6 grade.

1. **What is the number?** Value, units, where it comes from.
2. **Why is it that value?** The mechanism, in physics or chemistry, not a restatement.
3. **So what?** The consequence for safety, design or operation.
4. **What would change it?** The uncertainty or sensitivity that matters.

**Worked example (92 % design):**

> The normal peak is 70.4 °C and the worst MTSR is 81.8 °C (Figure 11, `part10_design_summary.json`). The lower target allows a slower feed (125 min instead of 99 min) and a colder coolant (40 °C instead of 50 °C), so less unreacted B accumulates; because MTSR is the operating temperature plus the adiabatic rise of the accumulated B, both terms fall. That leaves 13.2 K to the 95 °C cooling-failure limit and a 75/80 °C alarm/trip window, with no loss of throughput or capital. The numbers are provisional until Fit 2 narrows Ea; a higher Ea raises the peak and MTSR together.

That is 4 sentences, 3 numbers, 1 mechanism, 1 consequence, 1 uncertainty. Write every results paragraph to that shape.

**Rules that follow from it:**

- **No naked numbers.** A number without a source or a meaning is not a result.
- **Mechanism before consequence.** Say *why* it is 70.4 °C before saying it is safe.
- **One claim per paragraph.** If a paragraph has two claims, split it.
- **No "it can be seen that".** Say what is seen.
- **No adjective without a number.** "Significant", "large", "close" need a value.

---

## 4. Who edits what

| File | You | Claude | Rule |
|---|---|---|---|
| `src/config.py` | Decide the value | Edits after your ledger entry | Claude never changes a decision without a written reason |
| `src/*.py` | Review the diff | Implements, tests | You approve anything that changes a reported number |
| `results/` | Read | Regenerates | Nobody hand-edits; it is output |
| `data/raw/` | Saves the TA file unedited | Reads | Never edited by anyone |
| `docs/decision_ledger.md` | **Writes the reasons** | Formats, updates status | The reason is yours; Claude cannot write it for you |
| `docs/design_decisions.md` | Approves wording | Updates status and values | Keep it consistent with the ledger |
| `report/` (Google Doc) | **Writes the analysis** | Structure moves, tables, captions, consistency edits | Claude may edit text, not author analysis |
| `CLAUDE.md` | Installs; changes rules | Follows | If a rule is wrong, change it once here |
| AI log | Verifies nothing was trimmed | Appends verbatim | Never edit, never condense, never trim your prompts |
| Appendix A/C | Checks paths | Assembles | Every source line must point to a real file |

**The one-line version:** you own decisions and analysis; Claude owns code, calculations, structure and consistency. The ledger is the handover point between you.

---

## 5. What to instruct Claude to do, in order

Paste these one at a time. Each says what output you expect and where it stops.

### Prompt 1 — load the plan (no edits)

```
Read CLAUDE.md and docs/report_restructure.md. Summarise:
1. the ten structural moves,
2. the four-question explanation standard,
3. who edits which files.
Do not edit anything.
```

### Prompt 2 — produce the move plan (no edits)

```
Audit the current report against docs/report_restructure.md.
For each section, say: what stays, what moves, what is cut, and the page estimate.
Flag every placeholder, rubric note and source line that points to a missing file.
Output a table, not prose. Do not edit.
```

### Prompt 3 — execute the structural moves

```
Apply moves 1-5 only: remove the rubric map and add the roadmap, replace the
executive-summary bullets with a numbers page plus a results-at-a-glance table,
compress Part 4 to 1.5 pages, replace the raw data pages with a 10-row excerpt
in Appendix C, and add Appendix F with the decision-record table.
Do not touch analysis prose. Report file and line for each change.
```

### Prompt 4 — implement J1 and J2

```
I have decided: J1 = 0.92 at 240 min; J2 = alarm 75 C, trip 80 C, shutdown cuts
the B feed. Set TARGET_X, T_TRIP and T_ALARM in src/config.py, update
docs/design_decisions.md P1/P2/S5 to "Settled 27 Nov", rerun the pipeline, and
give me one table: quantity | old | new | why. Do not write report prose.
```

### Prompt 5 — evidence table for a section

```
Build the evidence table for Part 9: claim | number | source file or workbook
cell | what it means | provisional? No paragraphs. Flag any claim with no number.
```

### Prompt 6 — edit your prose, not rewrite it

```
I wrote this paragraph. Check it against the four-question standard and the B4
anchor. Numbered edits only: unsupported claim, missing number, wrong unit,
overstated conclusion, missing limitation. Do not rewrite it.
```

### Prompt 7 — captions

```
For fig01-fig12, give one caption each: the finding in one sentence, the
condition it applies to, and the report part it belongs to. Do not describe
the axes.
```

### Prompt 8 — consistency and pre-submit lint

```
Run the consistency pass in docs/report_restructure.md §2 move 10 and the
pre-submit checklist in ENCH421_MASTER_PLAN.md §7.1. List every failure with
file and line. Do not fix anything without telling me first.
```

---

## 6. What not to ask Claude

- "Write Part 9" or "rewrite this section". Ask for the evidence table, write it, then ask for numbered edits.
- "Make it sound more professional." That produces consultant register, which reads as not-yours.
- "Fix the AI log." It only gets appended, never repaired.
- "Make the report longer." The target is 22 pages of argument, not 30 pages of text.
- "Just decide it." The decision brief exists to stop that.

---

## 7. Definition of done per section

| Section | Done when |
|---|---|
| 4 | Seven checks, one sentence each, Table 3, no derivations in the body |
| 5 | Every run has objective, result, next-run link; stopping-rule verdict quoted |
| 6 | Four-question interpretation; correlation and Ea identifiability explained |
| 8 | Nominal vs design; phases; UA/V; heat split; four-question interpretation |
| 9 | Criterion, max q, failure, TMR, maps, risk, Stoessel/TD24; four-question interpretation |
| 10 | Matrix, mechanism, rejected cases, UA framing, residual risk, decision record |
| 11 | What changes, what is stable, which conclusion is fragile |
| 12 | Hierarchy with numbers, response time, sensor, layers, trip cuts feed only |
| 13 | Each limitation has a direction and bounds a conclusion |
