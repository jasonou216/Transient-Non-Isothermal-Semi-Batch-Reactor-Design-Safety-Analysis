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
| `data/experiments/` | Raw CSVs returned from the virtual-lab experiment requests (5-run budget) |
| `data/validation/` | Held-out validation dataset (released after parameters are submitted) |
| `src/` | Project code: reactor model, parameter regression, safety analysis, design studies |
| `report/` | Technical report drafts, figures and final submission |
| `ai_log/` | Record of AI-tool prompts and responses (required for the report appendix) |

## Project parts

- **A:** Transient mole and energy balances (bench and 1000 L), solved numerically
- **B:** Experimental design and nonlinear regression for k_ref, E_a and ΔH_rxn, with uncertainty and validation
- **C:** Maximum safe feed rate, cooling-failure scenario, runaway map
- **D:** Feed policy and jacket UA recommendation, sensitivity (E_a ±10 %, UA −20 %), instrumentation and control

## Requirements

Python 3 with the packages in `requirements.txt`:

```bash
pip install -r requirements.txt
```
