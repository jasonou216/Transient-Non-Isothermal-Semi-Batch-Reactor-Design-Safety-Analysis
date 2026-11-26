# Transient Non-Isothermal Semi-Batch Reactor Design & Safety Analysis

ENCH 421 (Chemical Reaction Engineering) design project: scale-up of the
exothermic, second-order liquid-phase reaction A + B → C from a bench reactor
to a 1000 L jacketed semi-batch reactor, including kinetic/thermal parameter
estimation, runaway and cooling-failure analysis, and a final design
recommendation.

## Repository layout

| Folder | Contents |
| --- | --- |
| `docs/project_brief/` | Project statement, benchtop parameters, report grading rubric |
| `references/tutorial_01_collision_theory/` | Tutorial #1 handout and molecular-collision simulations (background on collision theory / Arrhenius behaviour) |
| `references/computational_labs/` | Computational Labs 1–7 handouts (batch, semi-batch with variable volume, reactors in series, reversible PFR, rate-data analysis, NH₃ decomposition kinetics, adiabatic PBR feed temperature) |
| `data/experiments/` | Data returned by the TA + `runs.csv` (requested conditions); 5-run budget |
| `data/validation/` | Held-out validation dataset (released after parameters are submitted) |
| `data/synthetic/` | Invented test data used only to check the pipeline |
| `src/` | Analysis pipeline: model, regression, verification, safety, design (see HOW_TO_RUN.md) |
| `results/` | Figures and tables written by the pipeline (`real/`, `synthetic/`) |
| `report/` | Report skeleton (Word) and drafts |
| `ai_log/` | Record of AI-tool prompts and responses (required for the report appendix) |

See **PROJECT_PLAN.md** for the schedule and open decisions, **HOW_TO_RUN.md** to run the code.

## Project parts

- **A:** Transient mole and energy balances (bench and 1000 L), solved numerically
- **B:** Experimental design and nonlinear regression for k_ref, E_a and ΔH_rxn, with uncertainty and validation
- **C:** Maximum safe feed rate, cooling-failure scenario, runaway map
- **D:** Feed policy and jacket UA recommendation, sensitivity (E_a ±10 %, UA −20 %), instrumentation and control

## Requirements

Python 3.10+ with the packages in `requirements.txt`:

```bash
pip install -r requirements.txt
```
