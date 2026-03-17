# Capacity Factor Sensitivity Analysis

## Purpose

Tests sensitivity of results to the uniform 55% coal capacity factor assumption by comparing against country-specific and utility-specific CFs derived from operational data.

## Capacity Factors Used

| Entity | CF | Source |
|--------|----|--------|
| Uniform (paper) | 55% | Paper assumption |
| ID (national) | 49% | Derived from coal gen%/cap% shares |
| IN (national) | 69% | Derived from coal gen%/cap% shares |
| MY (national) | 67% | Derived from coal gen%/cap% shares |
| PH (national) | 60% | Derived from coal gen%/cap% shares |
| SG (national) | 55% | Derived from coal gen%/cap% shares |
| TH (national) | 55% | Derived from coal gen%/cap% shares |
| VN (national) | 64% | Derived from coal gen%/cap% shares |
| PLN | 49.0% | PLN reported coal_capacity_factor_pct |
| NTPC | 77.0% | NTPC Sustainability Report (Coal PLF 77%) |
| Adani Power | 64.7% | Adani Power Annual Report (PLF 64.7%) |
| NLC India | 65.0% | NLC India (NNTPS PLF 98.2%) |
| Torrent Power | 81.0% | Torrent Power (Coal PLF 81%) |

## Results

| Utility | Country | Coal MW | CF uni | CF used | MtCO2 (uni) | MtCO2 (adj) | Error |
|---------|---------|---------|--------|---------|-------------|-------------|-------|
| PLN | ID | 35,000 | 55% | 49% | 153.4 | 136.7 | -10.9% |
| NTPC | IN | 65,194 | 55% | 77% | 285.8 | 400.2 | +40.0% |
| Tata Power | IN | 7,800 | 55% | 69% | 34.2 | 42.9 | +25.4% |
| Adani Power | IN | 15,210 | 55% | 65% | 66.7 | 78.5 | +17.6% |
| JSW Energy | IN | 5,658 | 55% | 69% | 24.8 | 31.1 | +25.4% |
| NLC India | IN | 1,660 | 55% | 65% | 7.3 | 8.6 | +18.1% |
| Torrent Power | IN | 362 | 55% | 81% | 1.6 | 2.3 | +47.2% |
| TNB | MY | 6,810 | 55% | 67% | 29.9 | 36.4 | +21.8% |
| SMC Global Power | PH | 3,756 | 55% | 60% | 16.5 | 18.0 | +9.0% |
| Aboitiz Power | PH | 3,073 | 55% | 60% | 13.5 | 14.7 | +9.1% |
| EGAT | TH | 2,220 | 55% | 55% | 9.7 | 9.7 | +0.0% |
| GPSC | TH | 900 | 55% | 55% | 4.0 | 4.0 | +0.0% |
| RATCH Group | TH | 742 | 55% | 55% | 3.2 | 3.2 | +0.0% |
| EVN | VN | 12,678 | 55% | 64% | 55.6 | 64.7 | +16.4% |
| **AGGREGATE** | | | | | **706.2** | **850.9** | **+20.5%** |

## Variance Statistics

- Uniform CF: 0.55
- Utility-specific CF mean: 0.636 (SD: 0.085, range: 0.49-0.81)
- Coal-MW-weighted mean CF: 0.663 (vs uniform 0.55, diff: +20.5%)

## Interpretation

The uniform 55% CF assumption is conservative. Using operational data, the coal-MW-weighted mean CF is 66%, which is +21% higher than assumed. Aggregate coal emissions under utility-specific CFs are +20.5% higher than the paper reports. The central finding that absolute emissions remain unchanged under grow-out is therefore a lower bound: actual emissions are likely higher, not lower, than reported.

Indonesia (PLN, CF=49%) is the only market where the uniform assumption overstates coal generation. For India (CF=69-77%), Malaysia (CF=67%), and Vietnam (CF=64%), the uniform assumption materially understates coal output.
