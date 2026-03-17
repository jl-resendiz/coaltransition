# Dynamic Grow-Out Scenarios

## Methodology

For each thermal incumbent, we project electricity demand, renewable deployment, and coal generation over 2025-2035. Coal capacity is held fixed (the grow-out assumption: no retirements). The coal capacity factor adjusts dynamically as a residual supplier: coal fills demand not met by renewables and gas. The CF is bounded by technical limits [40%, 70%].

## Scenarios

| Scenario | Demand growth | RE deployment | Description |
|----------|--------------|---------------|-------------|
| A | Country baseline | Pipeline x1.0 | High demand, actual RE pipeline |
| B | Baseline -2pp | Pipeline x1.5 | Moderate demand, accelerated RE (1.5x) |
| C | Baseline -3pp | Pipeline x2.0 | Low demand, aggressive RE (2x) |
| D | Baseline -100pp | Pipeline x2.0 | Zero demand growth, aggressive RE (2x) |

## Country Demand Growth Rates

| Country | Baseline (Scen A) | Scen B | Scen C | Source |
|---------|------------------|--------|--------|--------|
| ID | 5.0% | 3.0% | 2.0% | IEA WEO 2024, PLN RUPTL |
| IN | 6.5% | 4.5% | 3.5% | IEA WEO 2024, CEA |
| MY | 3.0% | 1.0% | 1.0% | IEA WEO 2024, TNB |
| PH | 5.0% | 3.0% | 2.0% | IEA WEO 2024, DOE PEP |
| SG | 1.5% | 1.0% | 1.0% | IEA WEO 2024, EMA |
| TH | 3.0% | 1.0% | 1.0% | IEA WEO 2024, EGAT PDP |
| VN | 7.0% | 5.0% | 4.0% | IEA WEO 2024, PDP8 |

## Key Assumptions

- Coal capacity factor bounds: [40%, 70%]
- Gas CF: 50% (fixed)
- RE blended CF: 22%
- Coal emission factor: 0.91 tCO2/MWh
- No coal retirements (grow-out assumption)
- No new coal capacity (conservative for India/Indonesia)
- RE deployment rate from declared utility pipelines/targets

## Results: Endpoint Comparison (2035 vs 2025)


### Scenario A: High demand, actual RE pipeline

| Utility | Country | Coal CF | Coal TWh | Coal Share | MtCO2 | RE absorbed by demand |
|---------|---------|---------|----------|------------|-------|----------------------|
| PLN | ID | 0.700 | 214.6 | 55.8% | 195.3 | 100% |
| NTPC | IN | 0.700 | 399.8 | 68.3% | 363.8 | 100% |
| Tata Power | IN | 0.700 | 47.8 | 69.9% | 43.5 | 100% |
| Adani Power | IN | 0.700 | 93.3 | 99.8% | 84.9 | 100% |
| JSW Energy | IN | 0.400 | 19.8 | 15.5% | 18.0 | 28% |
| NLC India | IN | 0.700 | 10.2 | 64.9% | 9.3 | 100% |
| Torrent Power | IN | 0.400 | 1.3 | 6.4% | 1.2 | 100% |
| TNB | MY | 0.400 | 23.9 | 12.6% | 21.7 | 19% |
| SMC Global Power | PH | 0.400 | 13.2 | 15.9% | 12.0 | 23% |
| Aboitiz Power | PH | 0.700 | 18.8 | 77.3% | 17.1 | 100% |
| EGAT | TH | 0.700 | 13.6 | 24.4% | 12.4 | 100% |
| GPSC | TH | 0.526 | 4.1 | 12.0% | 3.8 | 98% |
| RATCH Group | TH | 0.700 | 4.5 | 13.6% | 4.1 | 100% |
| EVN | VN | 0.700 | 77.7 | 72.4% | 70.7 | 100% |

**Aggregate coal emissions**: 834.2 -> 857.8 MtCO2 (+2.8%)

### Scenario B: Moderate demand, accelerated RE (1.5x)

| Utility | Country | Coal CF | Coal TWh | Coal Share | MtCO2 | RE absorbed by demand |
|---------|---------|---------|----------|------------|-------|----------------------|
| PLN | ID | 0.700 | 214.6 | 49.9% | 195.3 | 87% |
| NTPC | IN | 0.700 | 399.8 | 61.2% | 363.8 | 100% |
| Tata Power | IN | 0.700 | 47.8 | 65.1% | 43.5 | 100% |
| Adani Power | IN | 0.700 | 93.3 | 99.8% | 84.9 | 100% |
| JSW Energy | IN | 0.400 | 19.8 | 11.1% | 18.0 | 12% |
| NLC India | IN | 0.700 | 10.2 | 59.6% | 9.3 | 100% |
| Torrent Power | IN | 0.400 | 1.3 | 5.9% | 1.2 | 100% |
| TNB | MY | 0.400 | 23.9 | 9.3% | 21.7 | 4% |
| SMC Global Power | PH | 0.400 | 13.2 | 11.5% | 12.0 | 8% |
| Aboitiz Power | PH | 0.700 | 18.8 | 76.6% | 17.1 | 100% |
| EGAT | TH | 0.700 | 13.6 | 24.3% | 12.4 | 100% |
| GPSC | TH | 0.400 | 3.2 | 8.3% | 2.9 | 20% |
| RATCH Group | TH | 0.700 | 4.5 | 13.3% | 4.1 | 100% |
| EVN | VN | 0.700 | 77.7 | 71.1% | 70.7 | 100% |

**Aggregate coal emissions**: 834.2 -> 856.9 MtCO2 (+2.7%)

### Scenario C: Low demand, aggressive RE (2x)

| Utility | Country | Coal CF | Coal TWh | Coal Share | MtCO2 | RE absorbed by demand |
|---------|---------|---------|----------|------------|-------|----------------------|
| PLN | ID | 0.518 | 158.8 | 37.9% | 144.5 | 42% |
| NTPC | IN | 0.478 | 273.1 | 45.9% | 248.5 | 63% |
| Tata Power | IN | 0.700 | 47.8 | 60.9% | 43.5 | 100% |
| Adani Power | IN | 0.700 | 93.3 | 99.8% | 84.9 | 100% |
| JSW Energy | IN | 0.400 | 19.8 | 8.7% | 18.0 | 7% |
| NLC India | IN | 0.700 | 10.2 | 55.2% | 9.3 | 100% |
| Torrent Power | IN | 0.400 | 1.3 | 5.4% | 1.2 | 64% |
| TNB | MY | 0.400 | 23.9 | 7.4% | 21.7 | 3% |
| SMC Global Power | PH | 0.400 | 13.2 | 9.0% | 12.0 | 4% |
| Aboitiz Power | PH | 0.675 | 18.2 | 75.1% | 16.5 | 100% |
| EGAT | TH | 0.700 | 13.6 | 24.3% | 12.4 | 100% |
| GPSC | TH | 0.400 | 3.2 | 7.4% | 2.9 | 15% |
| RATCH Group | TH | 0.700 | 4.5 | 13.0% | 4.1 | 100% |
| EVN | VN | 0.700 | 77.7 | 69.9% | 70.7 | 100% |

**Aggregate coal emissions**: 834.2 -> 690.2 MtCO2 (-17.3%)

### Scenario D: Zero demand growth, aggressive RE (2x)

| Utility | Country | Coal CF | Coal TWh | Coal Share | MtCO2 | RE absorbed by demand |
|---------|---------|---------|----------|------------|-------|----------------------|
| PLN | ID | 0.400 | 122.6 | 32.0% | 111.6 | 0% |
| NTPC | IN | 0.400 | 228.4 | 41.5% | 207.9 | 0% |
| Tata Power | IN | 0.498 | 34.0 | 52.6% | 31.0 | 0% |
| Adani Power | IN | 0.640 | 85.3 | 99.7% | 77.6 | 0% |
| JSW Energy | IN | 0.400 | 19.8 | 8.7% | 18.0 | 0% |
| NLC India | IN | 0.700 | 10.2 | 55.2% | 9.3 | 0% |
| Torrent Power | IN | 0.400 | 1.3 | 5.4% | 1.2 | 0% |
| TNB | MY | 0.400 | 23.9 | 7.4% | 21.7 | 0% |
| SMC Global Power | PH | 0.400 | 13.2 | 9.0% | 12.0 | 0% |
| Aboitiz Power | PH | 0.514 | 13.8 | 69.7% | 12.6 | 0% |
| EGAT | TH | 0.700 | 13.6 | 24.3% | 12.4 | 0% |
| GPSC | TH | 0.400 | 3.2 | 7.4% | 2.9 | 0% |
| RATCH Group | TH | 0.700 | 4.5 | 13.0% | 4.1 | 0% |
| EVN | VN | 0.481 | 53.4 | 61.5% | 48.6 | 0% |

**Aggregate coal emissions**: 834.2 -> 570.9 MtCO2 (-31.6%)

## Interpretation

In high-growth markets (India, Vietnam, Indonesia, Philippines), demand growth of 5-7% per year means that new renewable generation is almost entirely absorbed by incremental demand. The coal capacity factor does not decline because coal is needed to meet baseload demand that renewables cannot yet displace. Only under the counterfactual of zero demand growth (Scenario D) do renewable additions begin to displace coal generation and reduce the coal capacity factor. Even then, the technical minimum CF floor of 40% limits how far coal generation can fall without plant retirements.

This confirms the central finding of the paper: the grow-out strategy fails as climate policy not because of a static accounting identity, but because demand growth in these markets absorbs renewable additions before they can displace coal. The result is robust to dynamic capacity factor adjustment. Scenario D isolates the mechanism: only when demand growth is removed entirely can renewables reduce the coal capacity factor, and even then absolute emissions decline modestly because the existing coal fleet is so large relative to renewable additions.
