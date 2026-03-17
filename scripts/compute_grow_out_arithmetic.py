"""
Grow-Out Arithmetic: MW vs TWh Analysis
========================================
Step 1 of the reframing analysis.

For each utility, computes:
- Coal/gas/oil generation (TWh) from capacity × capacity factor × 8760
- RE generation (TWh) from estimated RE capacity × CF
- RE/Coal generation ratio
- Coal share of total generation
- Absolute emissions (MtCO2) under grow-out (unchanged)
- Coal share under demand growth scenarios

Also computes Step 2 (coal drag) and Step 3 (absolute emissions test).

Reads from:
  - data_replication/data/utilities/*.json (capacity breakdowns — primary source)
  - utility_results/*/etcb_results.json (ETCB scores, financial data)
Outputs: CSV, summary table, LaTeX table rows
"""

import json
import os
import csv
from pathlib import Path

# --- Configuration ---
SCRIPT_DIR = Path(__file__).parent
ETCB_DIR = SCRIPT_DIR.parent / "utility_results"
INPUT_DIR = SCRIPT_DIR.parent / "data" / "utilities"
OUTPUT_DIR = SCRIPT_DIR.parent / "results"

# Default capacity factors (from calculate_etcb.py)
CF_COAL = 0.55      # Conservative for India/ASEAN (range 0.50-0.65)
CF_GAS = 0.50
CF_OIL = 0.20
CF_SOLAR = 0.20
CF_WIND = 0.30
CF_RE_BLENDED = 0.22  # Weighted blend for solar-dominated RE mix

# Emission factors (tCO2/MWh, from IPCC defaults)
EF_COAL = 0.91
EF_GAS = 0.40
EF_OIL = 0.78

# Hours per year
HOURS = 8760


def load_input_data():
    """Load capacity data from data/utilities/*.json (primary source)."""
    input_data = {}
    for json_path in sorted(INPUT_DIR.glob("*.json")):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        uid = data.get("id", json_path.stem.split("_")[0])
        input_data[uid] = data
    return input_data


def load_etcb_results():
    """Load ETCB benchmark results from utility_results/*/etcb_results.json."""
    etcb_data = {}
    for folder in sorted(ETCB_DIR.iterdir()):
        if not folder.is_dir():
            continue
        json_path = folder / "etcb_results.json"
        if not json_path.exists():
            continue
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        uid = data.get("utility_id", "")
        etcb_data[uid] = data
    return etcb_data


def extract_capacity(uid, input_rec, etcb_rec):
    """Extract capacity breakdown from input data + ETCB financial data."""
    # --- Capacity from input data (primary source) ---
    cap_data = input_rec.get("capacity", {})
    by_fuel = cap_data.get("by_fuel", {})

    coal_mw = by_fuel.get("coal", {}).get("value_mw", 0) or 0
    gas_mw = by_fuel.get("gas", {}).get("value_mw", 0) or 0
    oil_mw = by_fuel.get("oil", {}).get("value_mw", 0) or 0
    hydro_mw = by_fuel.get("hydro", {}).get("value_mw", 0) or 0
    solar_mw = by_fuel.get("solar", {}).get("value_mw", 0) or 0
    wind_mw = by_fuel.get("wind", {}).get("value_mw", 0) or 0
    other_re_mw = by_fuel.get("other_re", {}).get("value_mw", 0) or 0
    storage_mw = by_fuel.get("storage", {}).get("value_mw", 0) or 0

    thermal_mw = coal_mw + gas_mw + oil_mw
    re_mw = solar_mw + wind_mw + other_re_mw  # Excludes hydro for consistency
    re_plus_hydro_mw = re_mw + hydro_mw
    total_mw = cap_data.get("total_mw", thermal_mw + re_plus_hydro_mw + storage_mw)

    re_share_pct = cap_data.get("re_share_pct", 0) or 0
    is_pure_re = (thermal_mw == 0)

    # --- Financial/benchmark data from ETCB results ---
    benchmarks = etcb_rec.get("benchmarks", {})
    b2 = benchmarks.get("b2_carbon_cost_exposure", {}).get("details", {})
    b4 = benchmarks.get("b4_transition_alignment", {}).get("details", {})
    b5 = benchmarks.get("b5_balance_sheet_stress", {}).get("details", {})
    b1 = benchmarks.get("b1_stranded_asset_risk", {})

    scope1_tco2 = b2.get("scope1_tco2", 0) or 0
    ebitda_usd = b2.get("ebitda_usd", 0) or 0
    cce_low = b2.get("cce_low_pct", 0) or 0
    cce_med = b2.get("cce_medium_pct", 0) or 0
    cce_high = b2.get("cce_high_pct", 0) or 0

    clean_capex_pct = b4.get("clean_capex_pct")

    metrics = b5.get("metrics", {})
    debt_to_ebitda = metrics.get("debt_to_ebitda")
    interest_coverage = metrics.get("interest_coverage")
    ffo_to_debt = metrics.get("ffo_to_debt_pct")

    details_b1 = b1.get("details", {})
    at_risk_mw = details_b1.get("at_risk_mw", details_b1.get("coal_mw", 0)) or 0
    at_risk_share = details_b1.get("at_risk_share_pct", 0) or 0

    return {
        "coal_mw": coal_mw,
        "gas_mw": gas_mw,
        "oil_mw": oil_mw,
        "thermal_mw": thermal_mw,
        "solar_mw": solar_mw,
        "wind_mw": wind_mw,
        "hydro_mw": hydro_mw,
        "other_re_mw": other_re_mw,
        "re_mw": re_mw,
        "re_plus_hydro_mw": re_plus_hydro_mw,
        "total_mw": total_mw,
        "re_share_pct": re_share_pct,
        "is_pure_re": is_pure_re,
        "clean_capex_pct": clean_capex_pct,
        "scope1_tco2": scope1_tco2,
        "ebitda_usd": ebitda_usd,
        "cce_low_pct": cce_low,
        "cce_medium_pct": cce_med,
        "cce_high_pct": cce_high,
        "debt_to_ebitda": debt_to_ebitda,
        "interest_coverage": interest_coverage,
        "ffo_to_debt_pct": ffo_to_debt,
        "at_risk_mw": at_risk_mw,
        "at_risk_share_pct": at_risk_share,
        "b1_passed": b1.get("passed", False),
        "pass_count": etcb_rec.get("summary", {}).get("pass_count", 0),
        "tier": etcb_rec.get("summary", {}).get("tier", ""),
    }


def compute_generation(cap):
    """Compute generation (TWh) and emissions (MtCO2) from capacity."""
    coal_twh = cap["coal_mw"] * CF_COAL * HOURS / 1_000_000
    gas_twh = cap["gas_mw"] * CF_GAS * HOURS / 1_000_000
    oil_twh = cap["oil_mw"] * CF_OIL * HOURS / 1_000_000
    thermal_twh = coal_twh + gas_twh + oil_twh
    # Use fuel-specific CFs when available
    solar_twh = cap["solar_mw"] * CF_SOLAR * HOURS / 1_000_000
    wind_twh = cap["wind_mw"] * CF_WIND * HOURS / 1_000_000
    other_re_twh = cap["other_re_mw"] * CF_RE_BLENDED * HOURS / 1_000_000
    re_twh = solar_twh + wind_twh + other_re_twh

    total_twh = thermal_twh + re_twh

    # Emissions
    coal_mtco2 = coal_twh * EF_COAL
    gas_mtco2 = gas_twh * EF_GAS
    oil_mtco2 = oil_twh * EF_OIL
    total_mtco2 = coal_mtco2 + gas_mtco2 + oil_mtco2

    # Shares
    coal_share_gen = (coal_twh / total_twh * 100) if total_twh > 0 else 0
    re_share_gen = (re_twh / total_twh * 100) if total_twh > 0 else 0
    re_coal_ratio = (re_twh / coal_twh) if coal_twh > 0 else float('inf')

    # Coal share under demand growth (coal flat, total grows)
    # 5% annual demand growth for 5 years
    demand_growth_5yr = 1.05 ** 5
    coal_share_5yr = (coal_twh / (total_twh * demand_growth_5yr) * 100) if total_twh > 0 else 0

    return {
        "coal_twh": round(coal_twh, 1),
        "gas_twh": round(gas_twh, 1),
        "oil_twh": round(oil_twh, 1),
        "thermal_twh": round(thermal_twh, 1),
        "re_twh": round(re_twh, 1),
        "total_twh": round(total_twh, 1),
        "coal_mtco2": round(coal_mtco2, 1),
        "gas_mtco2": round(gas_mtco2, 1),
        "total_mtco2": round(total_mtco2, 1),
        "coal_share_gen_pct": round(coal_share_gen, 1),
        "re_share_gen_pct": round(re_share_gen, 1),
        "re_coal_ratio": round(re_coal_ratio, 3) if re_coal_ratio != float('inf') else None,
        "coal_share_5yr_pct": round(coal_share_5yr, 1),
    }


def compute_coal_drag(cap, gen):
    """Compute coal drag indicator (Step 2)."""
    # Coal EBITDA dependency (proxy): coal generation share × EBITDA
    coal_ebitda_proxy = gen["coal_share_gen_pct"] / 100 * cap["ebitda_usd"] if cap["ebitda_usd"] else 0

    # Debt headroom: 4.0x threshold - actual
    debt_headroom = None
    if cap["debt_to_ebitda"] is not None:
        debt_headroom = 4.0 - cap["debt_to_ebitda"]

    # Coal drag composite: high if coal dominates EBITDA AND no debt headroom
    high_coal_dependency = gen["coal_share_gen_pct"] > 50
    no_debt_headroom = debt_headroom is not None and debt_headroom < 0
    low_clean_capex = cap["clean_capex_pct"] is not None and cap["clean_capex_pct"] < 30

    coal_drag_score = sum([high_coal_dependency, no_debt_headroom, low_clean_capex])

    return {
        "coal_ebitda_proxy_usd": round(coal_ebitda_proxy),
        "debt_headroom_x": round(debt_headroom, 2) if debt_headroom is not None else None,
        "high_coal_dependency": high_coal_dependency,
        "no_debt_headroom": no_debt_headroom,
        "low_clean_capex": low_clean_capex,
        "coal_drag_score": coal_drag_score,  # 0-3
        "coal_drag_level": ["None", "Low", "Medium", "High"][coal_drag_score],
    }


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    input_data = load_input_data()
    etcb_data = load_etcb_results()
    print(f"Loaded {len(input_data)} input files, {len(etcb_data)} ETCB results\n")

    # Merge on utility ID
    all_uids = sorted(set(input_data.keys()) | set(etcb_data.keys()))

    results = []

    for uid in all_uids:
        input_rec = input_data.get(uid)
        etcb_rec = etcb_data.get(uid)

        if not input_rec:
            print(f"  {uid}: No input data, skipping")
            continue
        if not etcb_rec:
            print(f"  {uid} {input_rec.get('name', '')}: No ETCB results, skipping")
            continue

        name = input_rec.get("name", etcb_rec.get("utility_name", uid))
        country = input_rec.get("country_code", etcb_rec.get("country_code", ""))

        # Skip transmission company
        if name == "Power Grid Corporation" or name == "Power Grid":
            print(f"  {uid} {name}: Transmission company, skipping")
            continue

        cap = extract_capacity(uid, input_rec, etcb_rec)

        gen = compute_generation(cap)
        drag = compute_coal_drag(cap, gen)

        results.append({
            "utility_id": uid,
            "utility_name": name,
            "country": country,
            "tier": cap["tier"],
            "pass_count": cap["pass_count"],
            "is_pure_re": cap["is_pure_re"],
            "b1_passed": cap["b1_passed"],
            # Capacity (MW)
            "coal_mw": cap["coal_mw"],
            "gas_mw": cap["gas_mw"],
            "oil_mw": cap["oil_mw"],
            "thermal_mw": cap["thermal_mw"],
            "re_mw": round(cap["re_mw"]),
            "re_share_pct": cap["re_share_pct"],
            # Generation (TWh)
            "coal_twh": gen["coal_twh"],
            "gas_twh": gen["gas_twh"],
            "re_twh": gen["re_twh"],
            "total_twh": gen["total_twh"],
            # The key ratios
            "coal_share_gen_pct": gen["coal_share_gen_pct"],
            "re_share_gen_pct": gen["re_share_gen_pct"],
            "re_coal_ratio": gen["re_coal_ratio"],
            # Emissions
            "coal_mtco2": gen["coal_mtco2"],
            "total_mtco2": gen["total_mtco2"],
            # Under demand growth
            "coal_share_5yr_pct": gen["coal_share_5yr_pct"],
            # Coal drag (Step 2)
            "ebitda_usd_m": round(cap["ebitda_usd"] / 1e6) if cap["ebitda_usd"] else 0,
            "clean_capex_pct": cap["clean_capex_pct"],
            "debt_to_ebitda": cap["debt_to_ebitda"],
            "debt_headroom_x": drag["debt_headroom_x"],
            "coal_drag_score": drag["coal_drag_score"],
            "coal_drag_level": drag["coal_drag_level"],
            # Carbon cost exposure
            "cce_high_pct": cap["cce_high_pct"],
        })

    # --- Print summary table ---
    print("=" * 140)
    print("GROW-OUT ARITHMETIC: MW vs TWh")
    print("=" * 140)
    header = f"{'Utility':<20} {'Country':>3} {'Coal MW':>9} {'RE MW':>8} {'Coal TWh':>9} {'RE TWh':>8} {'Coal%Gen':>8} {'RE%Gen':>7} {'RE/Coal':>7} {'CoalMt':>7} {'Share5y':>7} {'Drag':>6}"
    print(header)
    print("-" * 140)

    # Sort: thermal incumbents first (by coal_mw desc), then pure-play
    thermal = [r for r in results if r["coal_mw"] > 0]
    pure_re = [r for r in results if r["coal_mw"] == 0]
    thermal.sort(key=lambda x: x["coal_mw"], reverse=True)

    for r in thermal + pure_re:
        re_coal = f"{r['re_coal_ratio']:.2f}" if r['re_coal_ratio'] is not None else "n/a"
        print(f"{r['utility_name']:<20} {r['country']:>3} {r['coal_mw']:>9,.0f} {r['re_mw']:>8,.0f} "
              f"{r['coal_twh']:>9.1f} {r['re_twh']:>8.1f} {r['coal_share_gen_pct']:>7.1f}% "
              f"{r['re_share_gen_pct']:>6.1f}% {re_coal:>7} {r['coal_mtco2']:>7.1f} "
              f"{r['coal_share_5yr_pct']:>6.1f}% {r['coal_drag_level']:>6}")

    # --- Print key findings ---
    print("\n" + "=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)

    thermal_results = [r for r in results if r["coal_mw"] > 0]
    total_coal_twh = sum(r["coal_twh"] for r in thermal_results)
    total_re_twh = sum(r["re_twh"] for r in thermal_results)
    total_coal_mtco2 = sum(r["coal_mtco2"] for r in thermal_results)

    print(f"\nThermal incumbents ({len(thermal_results)} utilities):")
    print(f"  Total coal generation:  {total_coal_twh:,.1f} TWh")
    print(f"  Total RE generation:    {total_re_twh:,.1f} TWh")
    print(f"  RE/Coal ratio:          {total_re_twh/total_coal_twh:.2f}" if total_coal_twh > 0 else "")
    print(f"  Total coal emissions:   {total_coal_mtco2:,.1f} MtCO2")
    print(f"  Under grow-out:         {total_coal_mtco2:,.1f} MtCO2 (unchanged — no retirements)")

    high_drag = [r for r in thermal_results if r["coal_drag_score"] >= 2]
    print(f"\nHigh/Medium coal drag: {len(high_drag)} of {len(thermal_results)} thermal utilities")
    for r in high_drag:
        print(f"  {r['utility_name']}: drag={r['coal_drag_level']}, "
              f"coal%gen={r['coal_share_gen_pct']:.0f}%, "
              f"debt_headroom={r['debt_headroom_x']:.1f}x" if r['debt_headroom_x'] is not None else
              f"  {r['utility_name']}: drag={r['coal_drag_level']}, "
              f"coal%gen={r['coal_share_gen_pct']:.0f}%")

    # --- CAPACITY vs GENERATION: The Two Stories ---
    print("\n" + "=" * 100)
    print("CAPACITY vs GENERATION: Why MW and TWh Tell Different Stories")
    print("=" * 100)

    total_coal_mw = sum(r["coal_mw"] for r in thermal_results)
    total_gas_mw = sum(r["gas_mw"] for r in thermal_results)
    total_thermal_mw = sum(r["thermal_mw"] for r in thermal_results)
    total_re_mw_thermal = sum(r["re_mw"] for r in thermal_results)
    total_gas_twh = sum(r["gas_twh"] for r in thermal_results)
    total_thermal_twh = total_coal_twh + total_gas_twh + sum(r.get("oil_twh", 0) for r in thermal_results)

    re_share_mw = total_re_mw_thermal / (total_thermal_mw + total_re_mw_thermal) * 100 if (total_thermal_mw + total_re_mw_thermal) > 0 else 0
    re_share_twh = total_re_twh / (total_thermal_twh + total_re_twh) * 100 if (total_thermal_twh + total_re_twh) > 0 else 0

    print(f"\n  Panel A: The Capacity Story (MW)")
    print(f"  {'':30} {'Coal':>10} {'Gas':>10} {'RE':>10} {'RE share':>10}")
    print(f"  {'Aggregate (14 thermal)':30} {total_coal_mw:>10,.0f} {total_gas_mw:>10,.0f} {total_re_mw_thermal:>10,.0f} {re_share_mw:>9.1f}%")

    print(f"\n  Panel B: The Generation Story (TWh)")
    print(f"  {'':30} {'Coal':>10} {'Gas':>10} {'RE':>10} {'RE share':>10}")
    print(f"  {'Aggregate (14 thermal)':30} {total_coal_twh:>10,.1f} {total_gas_twh:>10,.1f} {total_re_twh:>10,.1f} {re_share_twh:>9.1f}%")

    print(f"\n  Panel C: The Capacity Factor Wedge")
    print(f"  {'':30} {'MW share':>10} {'TWh share':>10} {'Ratio':>10}")
    print(f"  {'RE in thermal portfolios':30} {re_share_mw:>9.1f}% {re_share_twh:>9.1f}% {re_share_twh/re_share_mw:>9.2f}x" if re_share_mw > 0 else "")

    # Per-utility comparison: who has the biggest MW vs TWh gap?
    print(f"\n  Panel D: Per-Utility MW vs TWh Gap (thermal incumbents)")
    print(f"  {'Utility':<20} {'RE%MW':>7} {'RE%TWh':>8} {'Gap':>6} {'Coal%MW':>8} {'Coal%TWh':>9}")
    print(f"  {'-'*60}")
    for r in thermal:
        total_mw_u = r["coal_mw"] + r["gas_mw"] + r["re_mw"]
        re_pct_mw = r["re_mw"] / total_mw_u * 100 if total_mw_u > 0 else 0
        coal_pct_mw = r["coal_mw"] / total_mw_u * 100 if total_mw_u > 0 else 0
        gap = re_pct_mw - r["re_share_gen_pct"]
        print(f"  {r['utility_name']:<20} {re_pct_mw:>6.1f}% {r['re_share_gen_pct']:>7.1f}% {gap:>+5.1f} {coal_pct_mw:>7.1f}% {r['coal_share_gen_pct']:>8.1f}%")

    # --- The generation growth scenario ---
    print(f"\n  Panel E: Can RE Generation Growth Catch Up?")
    print(f"  Scenario: Double RE capacity (MW x2), coal stays flat")
    print(f"  {'Utility':<20} {'Coal TWh':>9} {'RE now':>8} {'RE x2':>8} {'Coal%now':>9} {'Coal%x2':>8} {'MtCO2':>8}")
    print(f"  {'-'*75}")
    for r in thermal:
        re_twh_doubled = r["re_twh"] * 2
        total_doubled = r["coal_twh"] + r["gas_twh"] + re_twh_doubled
        coal_share_doubled = r["coal_twh"] / total_doubled * 100 if total_doubled > 0 else 0
        print(f"  {r['utility_name']:<20} {r['coal_twh']:>9.1f} {r['re_twh']:>8.1f} {re_twh_doubled:>8.1f} "
              f"{r['coal_share_gen_pct']:>8.1f}% {coal_share_doubled:>7.1f}% {r['coal_mtco2']:>8.1f}")

    total_re_doubled = total_re_twh * 2
    total_gen_doubled = total_coal_twh + total_gas_twh + total_re_doubled
    coal_share_agg_doubled = total_coal_twh / total_gen_doubled * 100
    print(f"  {'AGGREGATE':<20} {total_coal_twh:>9.1f} {total_re_twh:>8.1f} {total_re_doubled:>8.1f} "
          f"{total_coal_twh/(total_thermal_twh+total_re_twh)*100:>8.1f}% {coal_share_agg_doubled:>7.1f}% {total_coal_mtco2:>8.1f}")
    print(f"\n  Key insight: Even doubling RE capacity, coal remains {coal_share_agg_doubled:.0f}% of generation.")
    print(f"  Absolute coal emissions: {total_coal_mtco2:,.1f} MtCO2 — unchanged in ALL scenarios without retirement.")

    # --- Panel F: What RE multiple is needed to reach coal parity in generation? ---
    print(f"\n  Panel F: RE Multiples Required for Generation Parity")
    print(f"  How many times must RE MW multiply to match coal TWh?")
    print(f"  {'Utility':<20} {'Coal TWh':>9} {'RE TWh':>8} {'Multiple':>9} {'RE MW needed':>13}")
    print(f"  {'-'*65}")
    for r in thermal:
        if r["re_twh"] > 0:
            multiple = r["coal_twh"] / r["re_twh"]
            re_mw_needed = r["re_mw"] * multiple
            print(f"  {r['utility_name']:<20} {r['coal_twh']:>9.1f} {r['re_twh']:>8.1f} {multiple:>8.1f}x {re_mw_needed:>12,.0f}")
        else:
            print(f"  {r['utility_name']:<20} {r['coal_twh']:>9.1f} {r['re_twh']:>8.1f}      inf           n/a")
    if total_re_twh > 0:
        agg_multiple = total_coal_twh / total_re_twh
        print(f"  {'AGGREGATE':<20} {total_coal_twh:>9.1f} {total_re_twh:>8.1f} {agg_multiple:>8.1f}x {total_re_mw_thermal * agg_multiple:>12,.0f}")

    # --- NTPC case study ---
    ntpc = next((r for r in results if r["utility_id"] == "IN001"), None)
    if ntpc:
        print("\n" + "=" * 80)
        print("NTPC CASE STUDY: The Best Case That Doesn't Work")
        print("=" * 80)
        print(f"  Coal capacity:          {ntpc['coal_mw']:,.0f} MW")
        print(f"  RE capacity (current):  {ntpc['re_mw']:,.0f} MW  ({ntpc['re_share_pct']:.1f}% of portfolio)")
        print(f"  Coal generation:        {ntpc['coal_twh']:,.1f} TWh  (at {CF_COAL*100:.0f}% PLF)")
        print(f"  RE generation:          {ntpc['re_twh']:,.1f} TWh  (at {CF_RE_BLENDED*100:.0f}% PLF)")
        print(f"  Coal share of gen:      {ntpc['coal_share_gen_pct']:.1f}%")
        print(f"  RE/Coal gen ratio:      {ntpc['re_coal_ratio']:.3f}")
        print(f"  Coal emissions:         {ntpc['coal_mtco2']:,.1f} MtCO2/yr (unchanged under grow-out)")
        print(f"  Coal share at +5%/yr:   {ntpc['coal_share_5yr_pct']:.1f}% (after 5 years demand growth)")
        print(f"  Clean CapEx:            {ntpc['clean_capex_pct']}%")
        print(f"  Debt/EBITDA:            {ntpc['debt_to_ebitda']:.1f}x (headroom: {ntpc['debt_headroom_x']:.1f}x)")
        print(f"  CCE at $75/tCO2:        {ntpc['cce_high_pct']:.0f}%")
        print(f"  Coal drag:              {ntpc['coal_drag_level']}")
        print(f"\n  Even with 60 GW RE pipeline fully built:")
        # Compute full pipeline scenario
        ntpc_full_re_mw = 60000
        ntpc_full_re_twh = ntpc_full_re_mw * CF_RE_BLENDED * HOURS / 1_000_000
        ntpc_total_full = ntpc["coal_twh"] + ntpc["gas_twh"] + ntpc_full_re_twh
        ntpc_coal_share_full = ntpc["coal_twh"] / ntpc_total_full * 100
        print(f"    RE generation:        {ntpc_full_re_twh:,.1f} TWh")
        print(f"    Coal generation:      {ntpc['coal_twh']:,.1f} TWh (unchanged)")
        print(f"    Coal share:           {ntpc_coal_share_full:.1f}%")
        print(f"    Coal emissions:       {ntpc['coal_mtco2']:,.1f} MtCO2/yr (unchanged)")
        print(f"    Conclusion: Coal still {ntpc_coal_share_full:.0f}% of generation. "
              f"Absolute emissions unchanged.")

    # --- Write CSV ---
    csv_path = OUTPUT_DIR / "grow_out_arithmetic.csv"
    fieldnames = list(results[0].keys())
    with open(csv_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    print(f"\nCSV written to: {csv_path}")

    # --- Write LaTeX table ---
    latex_path = OUTPUT_DIR / "table_grow_out_arithmetic.tex"
    with open(latex_path, 'w', encoding='utf-8') as f:
        f.write("% Grow-Out Arithmetic: MW vs TWh\n")
        f.write("% Auto-generated by compute_grow_out_arithmetic.py\n")
        for r in thermal + pure_re:
            re_coal = f"{r['re_coal_ratio']:.2f}" if r['re_coal_ratio'] is not None else "--"
            coal_mw_str = f"{r['coal_mw']:,.0f}" if r['coal_mw'] > 0 else "--"
            coal_twh_str = f"{r['coal_twh']:.1f}" if r['coal_twh'] > 0 else "--"
            coal_mt_str = f"{r['coal_mtco2']:.1f}" if r['coal_mtco2'] > 0 else "--"
            coal_share_str = f"{r['coal_share_gen_pct']:.0f}" if r['coal_share_gen_pct'] > 0 else "--"
            re_mw_str = f"{r['re_mw']:,.0f}" if r['re_mw'] > 0 else "--"
            re_twh_str = f"{r['re_twh']:.1f}" if r['re_twh'] > 0 else "--"

            f.write(f"{r['utility_name']} & {r['country']} & "
                    f"{coal_mw_str} & {re_mw_str} & "
                    f"{coal_twh_str} & {re_twh_str} & "
                    f"{coal_share_str} & {re_coal} & "
                    f"{coal_mt_str} \\\\\n")
    print(f"LaTeX table written to: {latex_path}")

    # --- Write JSON summary ---
    summary_path = OUTPUT_DIR / "grow_out_summary.json"
    summary = {
        "analysis": "Grow-Out Arithmetic",
        "assumptions": {
            "cf_coal": CF_COAL,
            "cf_gas": CF_GAS,
            "cf_oil": CF_OIL,
            "cf_re_blended": CF_RE_BLENDED,
            "ef_coal_tco2_mwh": EF_COAL,
            "ef_gas_tco2_mwh": EF_GAS,
            "demand_growth_annual": 0.05,
            "demand_growth_horizon_years": 5,
        },
        "aggregates": {
            "thermal_utilities": len(thermal_results),
            "total_coal_twh": round(total_coal_twh, 1),
            "total_re_twh": round(total_re_twh, 1),
            "total_coal_mtco2": round(total_coal_mtco2, 1),
            "re_coal_ratio": round(total_re_twh / total_coal_twh, 3) if total_coal_twh > 0 else None,
        },
        "utilities": results,
    }
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2)
    print(f"JSON summary written to: {summary_path}")


if __name__ == "__main__":
    main()
