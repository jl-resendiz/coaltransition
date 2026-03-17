#!/usr/bin/env python3
"""
Calculate ETCB (Energy Transition Credibility Benchmark) results for utilities.

This script reads utility and country JSON files from the 'data' folder
and calculates all 5 ETCB benchmarks:
- B1: Stranded Asset Risk (coal exposure timing)
- B2: Carbon Cost Exposure (emissions * carbon price / EBITDA)
- B3: LCOE Crossover (thermal vs solar+storage competitiveness)
- B4: CAPEX/Transition Alignment (clean energy commitment)
- B5: Balance Sheet Stress (credit metrics)

TRANSMISSION COMPANY METHODOLOGY:
For transmission utilities (e.g., Power Grid Corporation), benchmarks are modified:
- B1: Auto-pass - transmission lines don't "strand" like thermal plants
- B2: Auto-pass with low threshold - minimal direct emissions (offices, vehicles, line losses)
- B3: Auto-pass - no generation assets
- B4: Modified - evaluates % of CapEx enabling RE integration (green corridors, smart grid)
- B5: Fully applicable - same financial health tests

Outputs results to the 'results' folder.
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


# Default assumptions
CARBON_PRICE_USD_PER_TCO2 = {"low": 15.0, "medium": 40.0, "high": 75.0}
DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH = {"coal": 0.91, "gas": 0.40, "oil": 0.78}
DEFAULT_CAPACITY_FACTORS = {"coal": 0.55, "gas": 0.50, "oil": 0.20, "solar": 0.20, "wind": 0.30}
DEFAULT_THERMAL_BASE_COST_USD_PER_MWH = {"coal": 20.0, "gas": 35.0, "oil": 65.0}
SOLAR_PLUS_STORAGE_ADDER_USD_PER_MWH = 30.0


@dataclass
class BenchmarkResult:
    """Result of a single benchmark evaluation."""
    passed: bool
    score: Optional[float] = None
    details: dict = field(default_factory=dict)
    notes: str = ""
    data_available: bool = True


@dataclass
class ETCBResults:
    """Complete ETCB evaluation results for a utility."""
    utility_id: str
    utility_name: str
    country_code: str

    b1: BenchmarkResult = field(default_factory=lambda: BenchmarkResult(passed=False))
    b2: BenchmarkResult = field(default_factory=lambda: BenchmarkResult(passed=False))
    b3: BenchmarkResult = field(default_factory=lambda: BenchmarkResult(passed=False))
    b4: BenchmarkResult = field(default_factory=lambda: BenchmarkResult(passed=False))
    b5: BenchmarkResult = field(default_factory=lambda: BenchmarkResult(passed=False))

    pass_count: int = 0
    tier: str = "Not Evaluated"

    def calculate_tier(self, no_coal_policy: bool = False, declining_intensity: bool = False):
        """Calculate tier based on pass count and additional signals."""
        self.pass_count = sum(1 for b in [self.b1, self.b2, self.b3, self.b4, self.b5] if b.passed)

        if self.pass_count == 5:
            self.tier = "Highest"
        elif self.pass_count == 4 and no_coal_policy and declining_intensity:
            self.tier = "Highest"
        elif self.pass_count == 4:
            self.tier = "Medium-high"
        elif self.pass_count == 3:
            self.tier = "Medium"
        elif self.pass_count == 2:
            self.tier = "Low-medium"
        elif self.pass_count == 1:
            self.tier = "Low"
        else:
            self.tier = "Lowest"

    def to_dict(self) -> dict:
        return {
            "utility_id": self.utility_id,
            "utility_name": self.utility_name,
            "country_code": self.country_code,
            "benchmarks": {
                "b1_stranded_asset_risk": {
                    "passed": self.b1.passed,
                    "score": self.b1.score,
                    "details": self.b1.details,
                    "notes": self.b1.notes,
                    "data_available": self.b1.data_available
                },
                "b2_carbon_cost_exposure": {
                    "passed": self.b2.passed,
                    "score": self.b2.score,
                    "details": self.b2.details,
                    "notes": self.b2.notes,
                    "data_available": self.b2.data_available
                },
                "b3_lcoe_crossover": {
                    "passed": self.b3.passed,
                    "score": self.b3.score,
                    "details": self.b3.details,
                    "notes": self.b3.notes,
                    "data_available": self.b3.data_available
                },
                "b4_transition_alignment": {
                    "passed": self.b4.passed,
                    "score": self.b4.score,
                    "details": self.b4.details,
                    "notes": self.b4.notes,
                    "data_available": self.b4.data_available
                },
                "b5_balance_sheet_stress": {
                    "passed": self.b5.passed,
                    "score": self.b5.score,
                    "details": self.b5.details,
                    "notes": self.b5.notes,
                    "data_available": self.b5.data_available
                }
            },
            "summary": {
                "pass_count": self.pass_count,
                "tier": self.tier,
                "benchmarks_passed": [
                    f"B{i}" for i, b in enumerate([self.b1, self.b2, self.b3, self.b4, self.b5], 1) if b.passed
                ],
                "benchmarks_failed": [
                    f"B{i}" for i, b in enumerate([self.b1, self.b2, self.b3, self.b4, self.b5], 1) if not b.passed
                ]
            }
        }


def safe_float(value: Any) -> Optional[float]:
    """Safely convert value to float."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value.replace(",", "").replace("%", "").strip())
        except ValueError:
            return None
    return None


def is_transmission_company(utility: dict) -> bool:
    """Check if utility is a transmission company (not a generator)."""
    utility_type = get_nested(utility, "utility_type", default="").lower()
    if "transmission" in utility_type:
        return True

    # Also check if total generation capacity is 0
    total_mw = safe_float(get_nested(utility, "capacity", "total_mw"))
    if total_mw == 0:
        # Check if they have transmission infrastructure
        transmission_ckm = safe_float(get_nested(utility, "infrastructure", "transmission_ckm"))
        if transmission_ckm and transmission_ckm > 0:
            return True

    return False


def get_nested(data: dict, *keys, default=None) -> Any:
    """Safely get nested dictionary value."""
    current = data
    for key in keys:
        if not isinstance(current, dict):
            return default
        current = current.get(key, default)
        if current is None:
            return default
    return current


def load_json(filepath: Path) -> Optional[dict]:
    """Load JSON file with error handling."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError) as e:
        print(f"Error loading {filepath}: {e}")
        return None


def calculate_b1_stranded_asset_risk(utility: dict) -> BenchmarkResult:
    """
    B1: Stranded Asset Risk
    Pass if <20% of coal capacity is "at risk" (retirement >2040 or unknown).
    If no coal, automatically passes.
    """
    coal_plants = get_nested(utility, "coal_plants", "plants", default=[])
    coal_status = get_nested(utility, "coal_plants", "status", default="")

    # Check if verified zero coal
    if coal_status == "verify_zero" or coal_status == "zero":
        # Check coal_exit_date in transition
        coal_exit = get_nested(utility, "transition", "coal_policy", "coal_exit_date")
        if coal_exit:
            return BenchmarkResult(
                passed=True,
                score=0.0,
                details={"coal_mw": 0, "at_risk_share_pct": 0, "coal_exit_date": coal_exit},
                notes=f"Coal exit completed: {coal_exit}"
            )

    # Check capacity by fuel
    coal_mw = safe_float(get_nested(utility, "capacity", "by_fuel", "coal", "value_mw"))

    if coal_mw is None or coal_mw == 0:
        return BenchmarkResult(
            passed=True,
            score=0.0,
            details={"coal_mw": 0, "at_risk_share_pct": 0},
            notes="No coal capacity"
        )

    # If we have coal plants list, calculate at-risk share
    if coal_plants:
        total_coal_mw = 0.0
        at_risk_mw = 0.0

        for plant in coal_plants:
            plant_mw = safe_float(plant.get("capacity_mw") or plant.get("equity_mw"))
            if plant_mw is None:
                continue
            total_coal_mw += plant_mw

            retirement = plant.get("retirement_date") or plant.get("ppa_expiry")
            if retirement:
                try:
                    year = int(str(retirement)[:4])
                    if year > 2040:
                        at_risk_mw += plant_mw
                except ValueError:
                    at_risk_mw += plant_mw  # Unknown = at risk
            else:
                at_risk_mw += plant_mw  # No retirement date = at risk

        if total_coal_mw > 0:
            # Use the authoritative coal_mw from capacity.by_fuel if available
            # and greater than the plant-list sum (plant list may be incomplete)
            effective_coal_mw = max(total_coal_mw, coal_mw) if coal_mw else total_coal_mw
            if effective_coal_mw > total_coal_mw:
                # Plant list incomplete; scale at-risk proportionally
                at_risk_mw = effective_coal_mw  # all MW at risk (no retirement dates)
            at_risk_share = at_risk_mw / effective_coal_mw
            passed = at_risk_share < 0.20
            return BenchmarkResult(
                passed=passed,
                score=at_risk_share,
                details={
                    "coal_mw": effective_coal_mw,
                    "at_risk_mw": at_risk_mw,
                    "at_risk_share_pct": round(at_risk_share * 100, 1),
                    "threshold_pct": 20
                },
                notes=f"At-risk coal: {at_risk_share*100:.1f}% (threshold: <20%)"
            )

    # If coal exists but no plant details, assume at risk
    return BenchmarkResult(
        passed=False,
        score=1.0,
        details={"coal_mw": coal_mw, "at_risk_share_pct": 100},
        notes="Coal capacity exists but no retirement details available",
        data_available=False
    )


def calculate_b2_carbon_cost_exposure(utility: dict, country: dict) -> BenchmarkResult:
    """
    B2: Carbon Cost Exposure
    Pass if (Scope 1 emissions × carbon price) / EBITDA < 20% at medium carbon price scenario.
    """
    # Get emissions
    scope1_tco2 = safe_float(get_nested(utility, "emissions", "scope1", "value_tco2"))
    scope1_mtco2 = safe_float(get_nested(utility, "emissions", "scope1", "value_mtco2"))

    if scope1_tco2 is None and scope1_mtco2 is not None:
        scope1_tco2 = scope1_mtco2 * 1_000_000

    # Get EBITDA - check both value_local and value_usd
    ebitda_local = safe_float(get_nested(utility, "financial", "income_statement", "ebitda", "value_local"))
    ebitda_usd = safe_float(get_nested(utility, "financial", "income_statement", "ebitda", "value_usd"))

    # Convert to USD if needed
    if ebitda_usd is None and ebitda_local is not None:
        fx = safe_float(get_nested(utility, "financial", "fx_to_usd"))
        if fx and fx > 0:
            ebitda_usd = ebitda_local / fx

    # Handle units (millions)
    if ebitda_usd is not None:
        unit = get_nested(utility, "financial", "income_statement", "ebitda", "unit", default="")
        if "million" in str(unit).lower():
            ebitda_usd *= 1_000_000

    if scope1_tco2 is None:
        return BenchmarkResult(
            passed=False,
            notes="Scope 1 emissions data not available",
            data_available=False
        )

    if ebitda_usd is None or ebitda_usd <= 0:
        return BenchmarkResult(
            passed=False,
            notes="EBITDA data not available or non-positive",
            data_available=False
        )

    # Get carbon price from country data
    carbon_price_medium = safe_float(get_nested(country, "carbon_pricing", "current_price_usd_tco2"))
    if carbon_price_medium is None:
        carbon_price_medium = CARBON_PRICE_USD_PER_TCO2["medium"]

    # Calculate CCE for all scenarios
    cce_results = {}
    for scenario, price in CARBON_PRICE_USD_PER_TCO2.items():
        if scenario == "medium":
            price = carbon_price_medium
        cce = (scope1_tco2 * price) / ebitda_usd
        cce_results[scenario] = round(cce * 100, 1)

    medium_cce = cce_results["medium"] / 100
    passed = medium_cce < 0.20

    return BenchmarkResult(
        passed=passed,
        score=medium_cce,
        details={
            "scope1_tco2": scope1_tco2,
            "ebitda_usd": ebitda_usd,
            "carbon_price_usd_tco2": carbon_price_medium,
            "cce_low_pct": cce_results["low"],
            "cce_medium_pct": cce_results["medium"],
            "cce_high_pct": cce_results["high"],
            "threshold_pct": 20
        },
        notes=f"CCE at medium carbon price: {cce_results['medium']:.1f}% (threshold: <20%)"
    )


def calculate_b3_lcoe_crossover(utility: dict, country: dict) -> BenchmarkResult:
    """
    B3: LCOE Crossover
    Pass if <30% of thermal capacity would be displaced by solar+storage at current carbon prices.
    """
    # Get solar+storage LCOE from country data
    solar_lcoe = safe_float(get_nested(country, "lcoe_benchmarks", "solar_plus_storage", "value_mid"))
    if solar_lcoe is None:
        solar_lcoe = safe_float(get_nested(country, "lcoe_benchmarks", "solar_pv", "value_mid"))
        if solar_lcoe:
            solar_lcoe += SOLAR_PLUS_STORAGE_ADDER_USD_PER_MWH

    if solar_lcoe is None:
        return BenchmarkResult(
            passed=False,
            notes="Solar/storage LCOE benchmark not available in country data",
            data_available=False
        )

    # Get carbon price
    carbon_price = safe_float(get_nested(country, "carbon_pricing", "current_price_usd_tco2"))
    if carbon_price is None:
        carbon_price = CARBON_PRICE_USD_PER_TCO2["medium"]

    # Calculate thermal costs vs solar+storage
    capacity = get_nested(utility, "capacity", "by_fuel", default={})

    thermal_mw = 0.0
    displaced_mw = 0.0
    fuel_analysis = {}

    for fuel in ["coal", "gas", "oil"]:
        fuel_data = capacity.get(fuel, {})
        mw = safe_float(fuel_data.get("value_mw"))

        if mw is None or mw <= 0:
            continue

        thermal_mw += mw

        # Calculate fuel cost with carbon
        base_cost = DEFAULT_THERMAL_BASE_COST_USD_PER_MWH.get(fuel, 40.0)
        emissions_factor = DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH.get(fuel, 0.5)
        total_cost = base_cost + (carbon_price * emissions_factor)

        fuel_analysis[fuel] = {
            "capacity_mw": mw,
            "base_cost_usd_mwh": base_cost,
            "carbon_cost_usd_mwh": round(carbon_price * emissions_factor, 2),
            "total_cost_usd_mwh": round(total_cost, 2),
            "displaced": total_cost > solar_lcoe
        }

        if total_cost > solar_lcoe:
            displaced_mw += mw

    if thermal_mw <= 0:
        return BenchmarkResult(
            passed=True,
            score=0.0,
            details={"thermal_mw": 0, "displaced_share_pct": 0},
            notes="No thermal capacity"
        )

    displaced_share = displaced_mw / thermal_mw
    passed = displaced_share < 0.30

    return BenchmarkResult(
        passed=passed,
        score=displaced_share,
        details={
            "thermal_mw": thermal_mw,
            "displaced_mw": displaced_mw,
            "displaced_share_pct": round(displaced_share * 100, 1),
            "solar_plus_storage_lcoe": solar_lcoe,
            "carbon_price_usd_tco2": carbon_price,
            "fuel_analysis": fuel_analysis,
            "threshold_pct": 30
        },
        notes=f"Displaced thermal: {displaced_share*100:.1f}% (threshold: <30%)"
    )


def calculate_b4_transition_alignment(utility: dict) -> BenchmarkResult:
    """
    B4: Transition/CAPEX Alignment
    Pass if: SBTi validated OR net-zero target ≤2050 with RE share >30% OR clean CAPEX >50%.
    """
    transition = get_nested(utility, "transition", default={})

    # Check SBTi status
    sbti_validated = get_nested(transition, "sbti", "validated", default=False)

    if sbti_validated:
        return BenchmarkResult(
            passed=True,
            score=1.0,
            details={"sbti_validated": True},
            notes="SBTi targets validated"
        )

    # Check net-zero commitment
    net_zero_year = safe_float(get_nested(transition, "net_zero", "target_year"))
    has_net_zero_2050 = net_zero_year is not None and net_zero_year <= 2050

    # Check RE share
    re_share_pct = safe_float(get_nested(utility, "capacity", "re_share_pct"))

    # Check clean CAPEX share
    clean_capex_pct = safe_float(get_nested(transition, "capex_allocation", "clean_capex_share_pct"))

    # Check RE targets
    re_target_pct = safe_float(get_nested(transition, "re_targets", "target_pct"))

    details = {
        "sbti_validated": sbti_validated,
        "sbti_committed": get_nested(transition, "sbti", "committed", default=False),
        "net_zero_year": net_zero_year,
        "re_share_pct": re_share_pct,
        "clean_capex_pct": clean_capex_pct,
        "re_target_pct": re_target_pct
    }

    # Evaluation criteria
    passed = False
    notes_parts = []

    if has_net_zero_2050:
        notes_parts.append(f"Net-zero by {int(net_zero_year)}")
        if re_share_pct is not None and re_share_pct > 30:
            passed = True
            notes_parts.append(f"RE share {re_share_pct:.0f}%")

    if clean_capex_pct is not None and clean_capex_pct >= 50:
        passed = True
        notes_parts.append(f"Clean CAPEX {clean_capex_pct:.0f}%")

    if not passed and not notes_parts:
        notes_parts.append("Insufficient transition commitments")

    return BenchmarkResult(
        passed=passed,
        score=clean_capex_pct / 100 if clean_capex_pct else None,
        details=details,
        notes="; ".join(notes_parts),
        data_available=any([net_zero_year, re_share_pct, clean_capex_pct])
    )


def calculate_b4_transmission_alignment(utility: dict) -> BenchmarkResult:
    """
    B4: Transition/CAPEX Alignment for TRANSMISSION COMPANIES
    Modified criteria - evaluates % of CapEx enabling RE integration:
    - Pass if: Net-zero target ≤2050 OR RE integration CapEx >50% OR facilitates >50 GW RE
    """
    transition = get_nested(utility, "transition", default={})
    infrastructure = get_nested(utility, "infrastructure", default={})
    re_projects = get_nested(utility, "re_integration_projects", default={})

    # Check net-zero commitment
    net_zero_year = safe_float(get_nested(transition, "net_zero", "target_year"))
    has_net_zero_2050 = net_zero_year is not None and net_zero_year <= 2050

    # Check RE integration metrics
    re_capacity_facilitated_gw = safe_float(get_nested(infrastructure, "non_fossil_capacity_facilitated_gw"))
    if re_capacity_facilitated_gw is None:
        re_capacity_facilitated_gw = safe_float(get_nested(transition, "re_targets", "re_capacity_facilitated_gw"))

    # Check Green Energy Corridor investment
    gec_re_capacity_gw = safe_float(get_nested(re_projects, "total_gec_re_capacity_gw"))
    gec_investment = safe_float(get_nested(re_projects, "total_gec_investment_inr_crore"))

    # Check clean/RE integration CAPEX share
    clean_capex_pct = safe_float(get_nested(transition, "capex_allocation", "clean_capex_share_pct"))
    re_integration_capex_pct = safe_float(get_nested(transition, "capex_allocation", "re_integration_capex_pct"))

    # Use whichever is available
    effective_clean_capex = clean_capex_pct or re_integration_capex_pct

    details = {
        "utility_type": "transmission",
        "net_zero_year": net_zero_year,
        "re_capacity_facilitated_gw": re_capacity_facilitated_gw,
        "gec_re_capacity_gw": gec_re_capacity_gw,
        "gec_investment_inr_crore": gec_investment,
        "clean_capex_pct": effective_clean_capex
    }

    # Evaluation criteria for transmission companies
    passed = False
    notes_parts = []

    if has_net_zero_2050:
        passed = True
        notes_parts.append(f"Net-zero by {int(net_zero_year)}")

    if effective_clean_capex is not None and effective_clean_capex >= 50:
        passed = True
        notes_parts.append(f"RE integration CapEx {effective_clean_capex:.0f}%")

    if re_capacity_facilitated_gw is not None and re_capacity_facilitated_gw >= 50:
        passed = True
        notes_parts.append(f"Facilitates {re_capacity_facilitated_gw:.0f} GW RE")

    if gec_re_capacity_gw is not None and gec_re_capacity_gw >= 30:
        passed = True
        notes_parts.append(f"GEC enables {gec_re_capacity_gw:.0f} GW RE")

    if not passed and not notes_parts:
        notes_parts.append("Insufficient RE integration commitments for transmission company")

    return BenchmarkResult(
        passed=passed,
        score=effective_clean_capex / 100 if effective_clean_capex else None,
        details=details,
        notes="; ".join(notes_parts),
        data_available=any([net_zero_year, effective_clean_capex, re_capacity_facilitated_gw, gec_re_capacity_gw])
    )


def calculate_b5_balance_sheet_stress(utility: dict) -> BenchmarkResult:
    """
    B5: Balance Sheet Stress Test
    Pass if at least 4 of 5 credit metrics pass:
    - Debt/EBITDA < 4.0x
    - Interest Coverage > 2.5x
    - FFO/Debt > 20%
    - Current Ratio > 1.0x
    - Debt/Capital < 60%
    """
    b5_metrics = get_nested(utility, "credit_metrics_b5", "metrics", default={})
    financial = get_nested(utility, "financial", default={})

    # Extract metrics from either b5_metrics or calculate from financials
    metrics = {}
    checks = {}

    # Debt/EBITDA
    debt_to_ebitda = safe_float(get_nested(b5_metrics, "debt_to_ebitda", "value"))
    if debt_to_ebitda is None:
        # Calculate from financials
        total_debt = safe_float(get_nested(financial, "balance_sheet", "total_debt", "value_local"))
        ebitda = safe_float(get_nested(financial, "income_statement", "ebitda", "value_local"))
        if total_debt and ebitda and ebitda > 0:
            debt_to_ebitda = total_debt / ebitda
    if debt_to_ebitda is not None:
        metrics["debt_to_ebitda"] = debt_to_ebitda
        checks["debt_to_ebitda"] = debt_to_ebitda < 4.0

    # Interest Coverage (EBITDA / Interest Expense)
    interest_coverage = safe_float(get_nested(b5_metrics, "interest_coverage", "value"))
    if interest_coverage is None:
        ebitda = safe_float(get_nested(financial, "income_statement", "ebitda", "value_local"))
        interest_exp = safe_float(get_nested(financial, "income_statement", "interest_expense", "value_local"))
        if ebitda and interest_exp and interest_exp > 0:
            interest_coverage = ebitda / interest_exp
    if interest_coverage is not None:
        metrics["interest_coverage"] = interest_coverage
        checks["interest_coverage"] = interest_coverage > 2.5

    # FFO/Debt (Operating Cash Flow / Total Debt)
    ffo_to_debt = safe_float(get_nested(b5_metrics, "ffo_to_debt_pct", "value"))
    if ffo_to_debt is None:
        ocf = safe_float(get_nested(financial, "cash_flow", "operating_cash_flow", "value_local"))
        total_debt = safe_float(get_nested(financial, "balance_sheet", "total_debt", "value_local"))
        if ocf and total_debt and total_debt > 0:
            ffo_to_debt = (ocf / total_debt) * 100
    if ffo_to_debt is not None:
        metrics["ffo_to_debt_pct"] = ffo_to_debt
        checks["ffo_to_debt"] = ffo_to_debt > 20

    # Current Ratio
    current_ratio = safe_float(get_nested(b5_metrics, "current_ratio", "value"))
    if current_ratio is None:
        current_assets = safe_float(get_nested(financial, "balance_sheet", "current_assets", "value_local"))
        current_liab = safe_float(get_nested(financial, "balance_sheet", "current_liabilities", "value_local"))
        if current_assets and current_liab and current_liab > 0:
            current_ratio = current_assets / current_liab
    if current_ratio is not None:
        metrics["current_ratio"] = current_ratio
        checks["current_ratio"] = current_ratio > 1.0

    # Debt/Capital
    debt_to_capital = safe_float(get_nested(b5_metrics, "debt_to_capital_pct", "value"))
    if debt_to_capital is None:
        total_debt = safe_float(get_nested(financial, "balance_sheet", "total_debt", "value_local"))
        total_equity = safe_float(get_nested(financial, "balance_sheet", "total_equity", "value_local"))
        if total_debt and total_equity and (total_debt + total_equity) > 0:
            debt_to_capital = (total_debt / (total_debt + total_equity)) * 100
    if debt_to_capital is not None:
        metrics["debt_to_capital_pct"] = debt_to_capital
        checks["debt_to_capital"] = debt_to_capital < 60

    # Calculate pass/fail
    available = len(checks)
    passes = sum(1 for v in checks.values() if v)
    fails = available - passes

    # Need at least 4 of 5 to pass (allow 1 fail)
    if available >= 4:
        passed = fails <= 1
    elif available == 3:
        passed = fails == 0
    else:
        passed = False

    return BenchmarkResult(
        passed=passed,
        score=passes / 5 if available > 0 else None,
        details={
            "metrics": metrics,
            "checks": checks,
            "metrics_available": available,
            "metrics_passed": passes,
            "metrics_failed": fails,
            "thresholds": {
                "debt_to_ebitda": "< 4.0x",
                "interest_coverage": "> 2.5x",
                "ffo_to_debt_pct": "> 20%",
                "current_ratio": "> 1.0x",
                "debt_to_capital_pct": "< 60%"
            }
        },
        notes=f"{passes}/{available} metrics pass (need at least 4/5)",
        data_available=available >= 3
    )


def evaluate_utility(utility: dict, country: dict) -> ETCBResults:
    """Evaluate all benchmarks for a utility."""
    results = ETCBResults(
        utility_id=utility.get("id", "unknown"),
        utility_name=utility.get("name", "Unknown"),
        country_code=utility.get("country_code", "??")
    )

    # Check if transmission company - use modified methodology
    is_transmission = is_transmission_company(utility)

    if is_transmission:
        # TRANSMISSION COMPANY METHODOLOGY
        # B1: Auto-pass - transmission lines don't strand like thermal plants
        results.b1 = BenchmarkResult(
            passed=True,
            score=0.0,
            details={"utility_type": "transmission", "stranded_asset_risk": "not_applicable"},
            notes="Transmission company - no generation assets to strand"
        )

        # B2: Auto-pass - minimal direct emissions (offices, vehicles, line losses)
        results.b2 = BenchmarkResult(
            passed=True,
            score=0.0,
            details={"utility_type": "transmission", "primary_emissions": "scope2_grid_losses"},
            notes="Transmission company - minimal direct emissions; Scope 2 from grid losses"
        )

        # B3: Auto-pass - no generation assets
        results.b3 = BenchmarkResult(
            passed=True,
            score=0.0,
            details={"utility_type": "transmission", "lcoe_crossover": "not_applicable"},
            notes="Transmission company - no generation capacity"
        )

        # B4: Modified - evaluate RE integration CapEx
        results.b4 = calculate_b4_transmission_alignment(utility)

        # B5: Fully applicable - same financial health tests
        results.b5 = calculate_b5_balance_sheet_stress(utility)
    else:
        # GENERATION COMPANY METHODOLOGY (standard)
        results.b1 = calculate_b1_stranded_asset_risk(utility)
        results.b2 = calculate_b2_carbon_cost_exposure(utility, country)
        results.b3 = calculate_b3_lcoe_crossover(utility, country)
        results.b4 = calculate_b4_transition_alignment(utility)
        results.b5 = calculate_b5_balance_sheet_stress(utility)

    # Check additional signals
    no_coal = get_nested(utility, "transition", "coal_policy", "no_new_coal", default=False)
    coal_exit = get_nested(utility, "transition", "coal_policy", "coal_exit_date")
    if coal_exit:
        no_coal = True

    # Check declining intensity
    intensity_trend = get_nested(utility, "emissions", "intensity_trend", "direction")
    declining = intensity_trend == "declining" if intensity_trend else False

    # Calculate tier
    results.calculate_tier(no_coal_policy=no_coal, declining_intensity=declining)

    return results


def main():
    """Main entry point."""
    # Set paths
    base_dir = Path(__file__).parent.parent
    data_dir = base_dir / "data"
    results_dir = base_dir / "utility_results"

    utilities_dir = data_dir / "utilities"
    countries_dir = data_dir / "countries"

    # Ensure results directory exists
    results_dir.mkdir(parents=True, exist_ok=True)

    # Load country data
    countries = {}
    if countries_dir.exists():
        for country_file in countries_dir.glob("*.json"):
            country_data = load_json(country_file)
            if country_data:
                code = country_data.get("country_code", country_file.stem)
                countries[code] = country_data
                print(f"Loaded country: {code}")

    # Process utilities
    all_results = []

    if utilities_dir.exists():
        for utility_file in utilities_dir.glob("*.json"):
            utility_data = load_json(utility_file)
            if not utility_data:
                continue

            utility_name = utility_data.get("name", utility_file.stem)
            country_code = utility_data.get("country_code", "??")

            print(f"\nEvaluating: {utility_name} ({country_code})")

            # Get country data
            country_data = countries.get(country_code, {})
            if not country_data:
                print(f"  Warning: No country data found for {country_code}")

            # Evaluate
            results = evaluate_utility(utility_data, country_data)
            all_results.append(results.to_dict())

            # Print summary
            print(f"  B1 (Stranded Asset): {'PASS' if results.b1.passed else 'FAIL'}")
            print(f"  B2 (Carbon Cost):    {'PASS' if results.b2.passed else 'FAIL'}")
            print(f"  B3 (LCOE Crossover): {'PASS' if results.b3.passed else 'FAIL'}")
            print(f"  B4 (Transition):     {'PASS' if results.b4.passed else 'FAIL'}")
            print(f"  B5 (Balance Sheet):  {'PASS' if results.b5.passed else 'FAIL'}")
            print(f"  Overall: {results.pass_count}/5 - Tier: {results.tier}")

    # Write results - one subfolder per utility
    for result in all_results:
        utility_id = result["utility_id"]
        utility_name = result["utility_name"]

        # Create utility subfolder
        utility_folder = results_dir / f"{utility_id}_{utility_name}"
        utility_folder.mkdir(parents=True, exist_ok=True)

        # Write detailed results
        result_file = utility_folder / "etcb_results.json"
        utility_output = {
            "generated_at": datetime.now().isoformat(),
            "utility_id": utility_id,
            "utility_name": utility_name,
            **result
        }
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump(utility_output, f, indent=2, ensure_ascii=False)

        # Write summary markdown
        summary_file = utility_folder / "summary.md"
        b = result["benchmarks"]
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(f"# ETCB Results: {utility_name}\n\n")
            f.write(f"**Score: {result['summary']['pass_count']}/5 - {result['summary']['tier']} Tier**\n\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
            f.write("## Benchmark Results\n\n")
            f.write("| Benchmark | Result | Details |\n")
            f.write("|-----------|--------|--------|\n")
            f.write(f"| B1 Stranded Asset | {'PASS' if b['b1_stranded_asset_risk']['passed'] else 'FAIL'} | {b['b1_stranded_asset_risk']['notes']} |\n")
            f.write(f"| B2 Carbon Cost | {'PASS' if b['b2_carbon_cost_exposure']['passed'] else 'FAIL'} | {b['b2_carbon_cost_exposure']['notes']} |\n")
            f.write(f"| B3 LCOE Crossover | {'PASS' if b['b3_lcoe_crossover']['passed'] else 'FAIL'} | {b['b3_lcoe_crossover']['notes']} |\n")
            f.write(f"| B4 Transition | {'PASS' if b['b4_transition_alignment']['passed'] else 'FAIL'} | {b['b4_transition_alignment']['notes']} |\n")
            f.write(f"| B5 Balance Sheet | {'PASS' if b['b5_balance_sheet_stress']['passed'] else 'FAIL'} | {b['b5_balance_sheet_stress']['notes']} |\n")

        print(f"  Results written to: {utility_folder}/")

    # Also write consolidated results
    output = {
        "generated_at": datetime.now().isoformat(),
        "utilities_evaluated": len(all_results),
        "results": all_results
    }

    output_file = base_dir / "results" / "etcb_results_all.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*60}")
    print(f"Consolidated results: {output_file}")
    print(f"Utilities evaluated: {len(all_results)}")

    # Summary table
    if all_results:
        print(f"\n{'='*60}")
        print("SUMMARY TABLE")
        print(f"{'='*60}")
        print(f"{'Utility':<25} {'B1':>4} {'B2':>4} {'B3':>4} {'B4':>4} {'B5':>4} {'Score':>6} {'Tier':<12}")
        print("-" * 70)

        for r in sorted(all_results, key=lambda x: -x["summary"]["pass_count"]):
            b = r["benchmarks"]
            print(f"{r['utility_name'][:24]:<25} "
                  f"{'Y' if b['b1_stranded_asset_risk']['passed'] else 'N':>4} "
                  f"{'Y' if b['b2_carbon_cost_exposure']['passed'] else 'N':>4} "
                  f"{'Y' if b['b3_lcoe_crossover']['passed'] else 'N':>4} "
                  f"{'Y' if b['b4_transition_alignment']['passed'] else 'N':>4} "
                  f"{'Y' if b['b5_balance_sheet_stress']['passed'] else 'N':>4} "
                  f"{r['summary']['pass_count']}/5".center(6) + " "
                  f"{r['summary']['tier']:<12}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
