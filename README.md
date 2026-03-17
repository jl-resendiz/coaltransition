# Coal Transition

Self-contained replication package for:

**"Can Utilities Grow Out of Coal? A Firm-Level Test in Emerging Asia"**
Jose Luis Resendiz, Gireesh Shrimali
Smith School of Enterprise and the Environment, University of Oxford
Target journal: *Energy Policy*

## Structure

```
coal_transition/
├── draft/                      Manuscript sources
│   ├── GrowOut_Energy_Policy.tex
│   ├── references.bib
│   └── compile.py              LaTeX compilation script
├── data/
│   ├── utilities/              21 utility JSON files (capacity, financials)
│   └── countries/              7 country JSON files (carbon pricing, LCOE, targets)
├── country_parameters/         7 country-specific benchmark parameter files
├── scripts/
│   ├── _paths.py               Shared path resolution
│   ├── run_all.py              Pipeline orchestrator
│   ├── calculate_etcb.py       Core ETCB benchmark engine (5-benchmark framework)
│   ├── compute_etcb_results.py Batch ETCB computation (reference; uses country-bundled format)
│   ├── compute_grow_out_arithmetic.py   MW vs TWh grow-out analysis
│   ├── compute_dynamic_scenarios.py     Demand-growth scenario projections
│   ├── compute_cf_sensitivity.py        Capacity factor sensitivity analysis
│   └── generate_figures_v2.py           Figure generation (requires matplotlib + numpy)
├── utility_results/            Per-utility ETCB results (21 folders)
├── results/                    Aggregated outputs (CSV, JSON, LaTeX tables)
└── figures/                    Publication figures (PDF + PNG)
```

## Sample

21 utilities across 7 markets (~310 GW):
- **India (10):** NTPC, Tata Power, Adani Power, Adani Green, JSW Energy, Power Grid, NHPC, NLC India, SJVN, Torrent Power
- **Thailand (5):** EGAT, Gulf Energy, GPSC, RATCH Group, B.Grimm Power
- **Indonesia:** PLN | **Malaysia:** TNB | **Philippines:** SMC Global Power, Aboitiz Power | **Singapore:** Sembcorp | **Vietnam:** EVN

## Requirements

- Python 3.8+ (standard library only for core scripts)
- Optional: `matplotlib`, `numpy` for figure regeneration
- Optional: MiKTeX for manuscript compilation

## Replication

### Run the analysis pipeline
```bash
python coal_transition/scripts/run_all.py
```
Runs capacity factor sensitivity, grow-out arithmetic, and dynamic scenarios in order. Outputs are written to `results/`. Figure generation is included if matplotlib is available; otherwise pre-generated figures in `figures/` are used.

### Run a single script
```bash
python coal_transition/scripts/compute_grow_out_arithmetic.py
```

### Compile the manuscript
```bash
python coal_transition/draft/compile.py
```

## Table/Figure Map

| Manuscript element | Script |
|---|---|
| Table: Grow-out arithmetic (MW vs TWh) | `compute_grow_out_arithmetic.py` |
| Table: Dynamic demand-growth scenarios | `compute_dynamic_scenarios.py` |
| Table: Capacity factor sensitivity | `compute_cf_sensitivity.py` |
| Figure 1: Benchmark heatmap | `generate_figures_v2.py` |
| Figure 3: Ownership scatter | `generate_figures_v2.py` |
| Figure 4: Carbon cost exposure | `generate_figures_v2.py` |

## Data Sources

| File | Source |
|---|---|
| `data/utilities/*.json` | Utility annual reports (FY2023-2024), GEM trackers |
| `data/countries/*.json` | National energy plans, World Bank Carbon Pricing Dashboard |
| `country_parameters/*.json` | IRENA, national tariff commissions, LCOE benchmarks |
| `utility_results/*/etcb_results.json` | Computed by `calculate_etcb.py` |
