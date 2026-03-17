#!/usr/bin/env python3
"""
Compute ETCB benchmark results from the updated raw JSON utility files.

Inputs (default): `data/raw/*_utilities_etcb_data.json` (relative to data_replication/)
Outputs (default): `results/` (relative to data_replication/)

Note: This script expects country-bundled JSON files (e.g., IN_utilities_etcb_data.json).
For individual utility processing, use calculate_etcb.py instead.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from statistics import mean
from typing import Any, Iterable


CARBON_PRICE_USD_PER_TCO2 = {"low": 15.0, "medium": 40.0, "high": 75.0}

DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH = {"coal": 0.91, "gas": 0.40, "oil": 0.78}
DEFAULT_CAPACITY_FACTORS = {"coal": 0.55, "gas": 0.50, "oil": 0.20}

# Simplified variable-cost model (USD/MWh) for B3 screening when plant-level
# disclosure is unavailable. This is an indicative screen, not a dispatch model.
DEFAULT_THERMAL_BASE_COST_USD_PER_MWH = {"coal": 20.0, "gas": 35.0, "oil": 65.0}

# Solar LCOE defaults (USD/MWh) used only when country-specific values are absent.
DEFAULT_SOLAR_LCOE_USD_PER_MWH = {"TH": 50.0, "ID": 55.0, "SG": 70.0}
SOLAR_PLUS_STORAGE_ADDER_USD_PER_MWH = 30.0


def unwrap(value: Any) -> Any:
    if isinstance(value, dict) and "value" in value:
        return value.get("value")
    return value


def coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace("%", "").replace(",", "").lstrip("~")
        if not text:
            return None
        m = re.match(r"^(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)$", text)
        if m:
            return (float(m.group(1)) + float(m.group(2))) / 2.0
        try:
            return float(text)
        except ValueError:
            return None
    return None


def parse_year(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    m = re.search(r"\\b(20\\d{2})\\s*/\\s*(\\d{2})\\b", text)
    if m:
        base = int(m.group(1))
        suffix = int(m.group(2))
        return (base // 100) * 100 + suffix
    years = [int(y) for y in re.findall(r"\\b(20\\d{2})\\b", text)]
    return max(years) if years else None


@dataclass(frozen=True)
class Fx:
    value: float
    unit: str

    def local_to_usd(self, local_amount: float) -> float:
        unit_lc = (self.unit or "").lower()
        if "usd per" in unit_lc:
            return local_amount * self.value
        if "per usd" in unit_lc:
            return local_amount / self.value
        return local_amount / self.value


def unit_multiplier(unit: str | None) -> float:
    if not unit:
        return 1.0
    unit_lc = unit.lower()
    if "billion" in unit_lc or re.search(r"\\bbn\\b", unit_lc):
        return 1e9
    if "million" in unit_lc or re.search(r"\\bmn\\b", unit_lc) or "millions" in unit_lc:
        return 1e6
    return 1.0


def amount_usd(field: Any, fx: Fx) -> float | None:
    if field is None:
        return None
    if isinstance(field, (int, float)):
        return float(field)
    if not isinstance(field, dict):
        return None
    if field.get("value_usd") is not None:
        return coerce_float(field.get("value_usd"))
    if field.get("value_usd_mn") is not None:
        v = coerce_float(field.get("value_usd_mn"))
        return None if v is None else v * 1e6
    val = coerce_float(field.get("value"))
    if val is None:
        return None
    unit = str(field.get("unit") or "")
    amount_local = val * unit_multiplier(unit)
    if "usd" in unit.lower():
        return amount_local
    return fx.local_to_usd(amount_local)


def capacity_mw(utility: dict[str, Any], key: str) -> float | None:
    cap = utility.get("capacity") or {}
    if not isinstance(cap, dict):
        return None
    return coerce_float(unwrap(cap.get(key)))


def ownership_category(utility: dict[str, Any]) -> str:
    ownership_val = ""
    ownership = utility.get("ownership")
    if isinstance(ownership, dict):
        ownership_val = str(ownership.get("value") or "")
    elif isinstance(ownership, str):
        ownership_val = ownership

    ownership_lc = ownership_val.lower()
    listed = utility.get("listed") is True

    if "state-linked" in ownership_lc:
        return "State-linked"
    if ownership_lc.startswith("state") or "government" in ownership_lc or "ministry" in ownership_lc:
        return "State-linked" if listed else "State"
    if any(term in ownership_lc for term in ["petrovietnam", "ptt", "egat", "khazanah", "temasek"]):
        return "State-linked" if listed else "State"
    return "Private"


def extract_solar_lcoe_usd_mwh(country_code: str, root_obj: dict[str, Any]) -> float:
    country_ctx = root_obj.get("country_context") or {}
    for k in ["solar_lcoe_usd_mwh", "solar_lcoe"]:
        v = country_ctx.get(k)
        if isinstance(v, dict):
            val = coerce_float(v.get("value"))
            if val is not None:
                return val

    if country_code == "MY":
        utilities = root_obj.get("utilities") or []
        if utilities and isinstance(utilities[0], dict):
            b3 = (utilities[0].get("benchmark_inputs") or {}).get("b3_lcoe_crossover") or {}
            if isinstance(b3, dict):
                bm = b3.get("malaysia_lcoe_benchmarks") or {}
                if isinstance(bm, dict):
                    val = coerce_float(bm.get("solar_usd_mwh"))
                    if val is not None:
                        return val

    return DEFAULT_SOLAR_LCOE_USD_PER_MWH.get(country_code, 55.0)


def extract_emissions_scope1_tco2(country_code: str, root_obj: dict[str, Any], utility: dict[str, Any]) -> tuple[float | None, str]:
    emissions = utility.get("emissions") or {}
    if isinstance(emissions, dict):
        if "scope1_mt_co2" in emissions:
            val = coerce_float(unwrap(emissions.get("scope1_mt_co2")))
            if val is not None:
                return val * 1e6, "reported_scope1_mt"
        if "scope_1_tco2e" in emissions:
            val = coerce_float(unwrap(emissions.get("scope_1_tco2e")))
            if val is not None:
                return val, "reported_scope1_t"
        if "scope1_tco2" in emissions:
            v = emissions.get("scope1_tco2")
            if isinstance(v, dict):
                unit = str(v.get("unit") or "").lower()
                val = coerce_float(v.get("value"))
                if val is not None:
                    return (val * 1e6, "reported_scope1_mt") if "mt" in unit else (val, "reported_scope1_t")

        est = emissions.get("estimated_scope1")
        if isinstance(est, dict) and isinstance(est.get("value"), str):
            m = re.match(r"^\\s*(\\d+(?:\\.\\d+)?)\\s*-\\s*(\\d+(?:\\.\\d+)?)\\s*$", est["value"])
            if m:
                return (float(m.group(1)) + float(m.group(2))) / 2.0, "estimated_scope1_range_t"

    binputs = utility.get("benchmark_inputs") or {}
    b2 = binputs.get("b2") or binputs.get("b2_carbon_cost_exposure") or {}
    if isinstance(b2, dict):
        val = coerce_float(b2.get("scope_1_emissions_tco2e") or b2.get("scope1_emissions_tco2e"))
        if val is not None:
            return val, "benchmark_inputs_scope1_t"
        scope1_for = b2.get("scope1_for_carbon_cost")
        if isinstance(scope1_for, dict):
            val = coerce_float(scope1_for.get("estimated_value"))
            if val is not None:
                return val, "benchmark_inputs_scope1_estimated_t"

    gen = utility.get("generation") or {}
    if isinstance(gen, dict):
        total_tco2 = 0.0
        used = False
        for gwh_key, fuel in [("coal_gwh", "coal"), ("gas_gwh", "gas"), ("oil_gwh", "oil")]:
            gwh = coerce_float(unwrap(gen.get(gwh_key)))
            if gwh is None:
                continue
            ef = DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH.get(fuel)
            if ef is None:
                continue
            total_tco2 += (gwh * 1000.0) * ef
            used = True
        if used:
            return total_tco2, "estimated_from_generation"

    total_tco2 = 0.0
    used = False
    for cap_key, fuel in [("coal_mw", "coal"), ("gas_mw", "gas"), ("oil_mw", "oil")]:
        mw = capacity_mw(utility, cap_key)
        if mw is None or mw <= 0:
            continue
        cf = DEFAULT_CAPACITY_FACTORS.get(fuel, 0.5)
        ef = DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH.get(fuel)
        if ef is None:
            continue
        total_tco2 += mw * cf * 8760.0 * ef
        used = True
    if used:
        return total_tco2, "estimated_from_capacity_mix"

    return None, "missing"


def extract_ebitda_usd(root_obj: dict[str, Any], utility: dict[str, Any], fx: Fx) -> tuple[float | None, str]:
    fin = utility.get("financial") or {}
    if not isinstance(fin, dict):
        return None, "missing"

    if "ebitda" in fin:
        v = amount_usd(fin.get("ebitda"), fx)
        if v is not None:
            return v, "financial.ebitda"

    if "ebitda_idr_millions" in fin:
        v = amount_usd(fin.get("ebitda_idr_millions"), fx)
        if v is not None:
            return v, "financial.ebitda_idr_millions"

    if fin.get("ebit") is not None and fin.get("total_assets") is not None:
        ebit = amount_usd(fin.get("ebit"), fx)
        assets = amount_usd(fin.get("total_assets"), fx)
        if ebit is not None and assets is not None:
            return max(0.0, ebit + 0.04 * assets), "estimated_from_ebit_plus_da_assets_4pct"

    for rev_key, margin in [("revenue", 0.15), ("revenue_idr_millions", 0.15)]:
        if rev_key in fin:
            rv = amount_usd(fin.get(rev_key), fx)
            if rv is not None:
                return rv * margin, f"estimated_from_{rev_key}_{int(margin*100)}pct_margin"

    if "revenue_estimate_usd_millions" in fin:
        rv = coerce_float(unwrap(fin.get("revenue_estimate_usd_millions")))
        if rv is not None:
            return rv * 1e6 * 0.20, "estimated_from_revenue_estimate_20pct_margin"

    return None, "missing"


def extract_generation_gwh(utility: dict[str, Any]) -> tuple[float | None, str]:
    gen = utility.get("generation") or {}
    if not isinstance(gen, dict):
        return None, "missing"
    val = coerce_float(unwrap(gen.get("total_gwh")))
    if val is not None:
        return val, "generation.total_gwh"
    if "value" in gen and isinstance(gen.get("value"), (int, float)):
        return float(gen["value"]), "generation.value"
    return None, "missing"


def estimate_generation_gwh_from_capacity(utility: dict[str, Any]) -> tuple[float | None, str]:
    total_gwh = 0.0
    used = False

    for cap_key, fuel in [("coal_mw", "coal"), ("gas_mw", "gas"), ("oil_mw", "oil")]:
        mw = capacity_mw(utility, cap_key)
        if mw is None or mw <= 0:
            continue
        total_gwh += mw * DEFAULT_CAPACITY_FACTORS.get(fuel, 0.5) * 8760.0 / 1000.0
        used = True

    for cap_key, cf in [
        ("hydro_mw", 0.45),
        ("solar_mw", 0.20),
        ("wind_mw", 0.30),
        ("geothermal_mw", 0.85),
        ("other_re_mw", 0.35),
    ]:
        mw = capacity_mw(utility, cap_key)
        if mw is None or mw <= 0:
            continue
        total_gwh += mw * cf * 8760.0 / 1000.0
        used = True

    return (total_gwh, "estimated_from_capacity_mix") if used else (None, "missing")


def b1_stranded_asset_risk_pass(utility: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    """
    Proxy implementation of B1 using coal exposure timing.

    Pass rule: <20% of coal capacity is "at risk", where at-risk coal is coal
    capacity with (i) retirement/expiry >2040 or (ii) unknown retirement/expiry.
    """
    binputs = utility.get("benchmark_inputs") or {}
    b1 = binputs.get("b1_stranded_asset_risk") or binputs.get("b1") or {}

    coal_assets: list[dict[str, Any]] = []
    if isinstance(b1, dict):
        if isinstance(b1.get("coal_plant_list"), list):
            coal_assets.extend([a for a in b1["coal_plant_list"] if isinstance(a, dict)])
        if isinstance(b1.get("plant_list"), list):
            for a in b1["plant_list"]:
                if not isinstance(a, dict):
                    continue
                fuel = str(a.get("fuel") or "").lower()
                if "coal" in fuel or "lignite" in fuel:
                    coal_assets.append(a)
        if isinstance(b1.get("coal_exposure_post_alinta"), dict):
            coal_assets.append(b1["coal_exposure_post_alinta"])

        coal_fleet_gw = coerce_float(b1.get("coal_fleet_on_grid_gw"))
        if not coal_assets and coal_fleet_gw:
            coal_assets.append({"capacity_mw": coal_fleet_gw * 1000.0})

    if not coal_assets:
        coal_mw = capacity_mw(utility, "coal_mw")
        if coal_mw is not None and coal_mw > 0:
            coal_assets.append({"capacity_mw": coal_mw})

    total_coal_mw = 0.0
    at_risk_coal_mw = 0.0
    for a in coal_assets:
        cap = coerce_float(a.get("capacity_mw") or a.get("equity_mw") or a.get("total_capacity_mw"))
        if cap is None:
            continue
        ownership_pct = coerce_float(a.get("ownership_pct") or a.get("equity_pct") or a.get("equity_stake_pct"))
        if ownership_pct is not None and 0 < ownership_pct <= 100:
            cap = cap * (ownership_pct / 100.0)
        total_coal_mw += cap

        end_year = parse_year(
            a.get("retirement_date")
            or a.get("planned_retirement")
            or a.get("ppa_expiry")
            or a.get("expected_operation_until")
        )
        if end_year is None or end_year > 2040:
            at_risk_coal_mw += cap

    if total_coal_mw <= 0:
        return True, {"total_coal_mw": 0.0, "at_risk_share": 0.0}

    share = at_risk_coal_mw / total_coal_mw
    return share < 0.20, {
        "total_coal_mw": total_coal_mw,
        "at_risk_coal_mw": at_risk_coal_mw,
        "at_risk_share": share,
        "threshold": 0.20,
    }


def b2_carbon_cost_exposure_ratio(emissions_tco2: float | None, ebitda_usd: float | None) -> dict[str, float | None]:
    cce: dict[str, float | None] = {}
    for scenario, price in CARBON_PRICE_USD_PER_TCO2.items():
        if emissions_tco2 is None or ebitda_usd is None or ebitda_usd <= 0:
            cce[scenario] = None
        else:
            cce[scenario] = (emissions_tco2 * price) / ebitda_usd
    return cce


def b3_lcoe_crossover_pass(utility: dict[str, Any], solar_lcoe_usd_mwh: float) -> tuple[bool, dict[str, Any]]:
    thermal_mw = 0.0
    displaced_mw = 0.0
    # Use solar LCOE directly as benchmark -- country data already includes
    # storage costs in solar_plus_storage figures.  The adder is only needed
    # when starting from standalone solar PV, which is handled upstream.
    benchmark = solar_lcoe_usd_mwh

    for cap_key, fuel in [("coal_mw", "coal"), ("gas_mw", "gas"), ("oil_mw", "oil")]:
        mw = capacity_mw(utility, cap_key)
        if mw is None or mw <= 0:
            continue
        thermal_mw += mw
        base = DEFAULT_THERMAL_BASE_COST_USD_PER_MWH.get(fuel, 40.0)
        ef = DEFAULT_EMISSIONS_FACTORS_TCO2_PER_MWH.get(fuel, 0.5)
        cost = base + CARBON_PRICE_USD_PER_TCO2["medium"] * ef
        if cost > benchmark:
            displaced_mw += mw

    if thermal_mw <= 0:
        return True, {"lcx": 0.0, "thermal_mw": 0.0, "benchmark_usd_mwh": benchmark}

    lcx = displaced_mw / thermal_mw
    return lcx < 0.30, {
        "thermal_mw": thermal_mw,
        "displaced_mw": displaced_mw,
        "lcx": lcx,
        "threshold": 0.30,
        "benchmark_usd_mwh": benchmark,
    }


def b4_capex_alignment_pass(utility: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    transition = utility.get("transition") or {}
    binputs = utility.get("benchmark_inputs") or {}
    b4 = binputs.get("b4_capex_alignment") or binputs.get("b4") or {}

    raw = None
    if isinstance(transition, dict):
        c = transition.get("clean_capex_share_pct")
        if isinstance(c, dict):
            raw = c.get("value") or c.get("benchmark_value") or c.get("claimed_value")
        elif c is not None:
            raw = c

    if raw is None and isinstance(b4, dict):
        for k in ["clean_capex_share_pct", "clean_share_pct", "clean_allocation_pct", "clean_capex_share"]:
            if k in b4:
                raw = b4.get(k)
                break

        capex_by_tech = b4.get("capex_by_technology")
        if raw is None and isinstance(capex_by_tech, dict) and isinstance(capex_by_tech.get("known_investments"), list):
            clean = 0.0
            total = 0.0
            for item in capex_by_tech["known_investments"]:
                if not isinstance(item, dict):
                    continue
                amt = coerce_float(item.get("amount_vnd") or item.get("amount"))
                if amt is None:
                    continue
                total += amt
                category = str(item.get("category") or "").lower()
                if any(term in category for term in ["renew", "grid", "storage"]):
                    clean += amt
            if total > 0:
                raw = (clean / total) * 100.0

    value_pct = coerce_float(unwrap(raw))
    if value_pct is None:
        total_mw = capacity_mw(utility, "total_mw")
        if total_mw is not None and total_mw > 0:
            clean_mw = 0.0
            for k in ["hydro_mw", "solar_mw", "wind_mw", "geothermal_mw", "other_re_mw"]:
                mw = capacity_mw(utility, k)
                if mw is not None and mw > 0:
                    clean_mw += mw
            value_pct = (clean_mw / total_mw) * 100.0

    passed = value_pct is not None and value_pct >= 50.0
    return passed, {"clean_capex_share_pct": value_pct, "threshold_pct": 50.0}


def b5_balance_sheet_stress_pass(utility: dict[str, Any]) -> tuple[bool, dict[str, Any]]:
    binputs = utility.get("benchmark_inputs") or {}
    b5 = binputs.get("b5_balance_sheet_stress") or binputs.get("b5") or {}

    metrics: dict[str, float] = {}
    checks: dict[str, bool] = {}

    def put(name: str, raw: Any) -> None:
        v = coerce_float(unwrap(raw))
        if v is not None:
            metrics[name] = v

    if isinstance(b5, dict):
        put("debt_to_ebitda", (b5.get("debt_to_ebitda") or {}).get("value") if isinstance(b5.get("debt_to_ebitda"), dict) else b5.get("debt_to_ebitda"))
        put("debt_to_ebitda", (b5.get("debt_ebitda") or {}).get("value") if isinstance(b5.get("debt_ebitda"), dict) else b5.get("debt_ebitda"))
        put("debt_to_ebitda", (b5.get("net_debt_to_ebitda") or {}).get("value") if isinstance(b5.get("net_debt_to_ebitda"), dict) else b5.get("net_debt_to_ebitda"))
        put("interest_coverage", (b5.get("interest_coverage") or {}).get("value") if isinstance(b5.get("interest_coverage"), dict) else b5.get("interest_coverage"))
        put("interest_coverage", (b5.get("interest_coverage_ebit") or {}).get("value") if isinstance(b5.get("interest_coverage_ebit"), dict) else b5.get("interest_coverage_ebit"))
        put("interest_coverage", (b5.get("interest_coverage_ebitda") or {}).get("value") if isinstance(b5.get("interest_coverage_ebitda"), dict) else b5.get("interest_coverage_ebitda"))
        put(
            "interest_coverage",
            (b5.get("interest_coverage_ebitda_minus_capex") or {}).get("value")
            if isinstance(b5.get("interest_coverage_ebitda_minus_capex"), dict)
            else b5.get("interest_coverage_ebitda_minus_capex"),
        )
        put("ffo_to_debt", (b5.get("ffo_to_debt") or {}).get("value") if isinstance(b5.get("ffo_to_debt"), dict) else b5.get("ffo_to_debt"))
        put("ffo_to_debt", (b5.get("cfo_to_debt") or {}).get("value") if isinstance(b5.get("cfo_to_debt"), dict) else b5.get("cfo_to_debt"))
        put("current_ratio", (b5.get("current_ratio") or {}).get("value") if isinstance(b5.get("current_ratio"), dict) else b5.get("current_ratio"))
        put("debt_to_capital", (b5.get("debt_to_capital") or {}).get("value") if isinstance(b5.get("debt_to_capital"), dict) else b5.get("debt_to_capital"))
        put("debt_to_capital", (b5.get("debt_capital") or {}).get("value") if isinstance(b5.get("debt_capital"), dict) else b5.get("debt_capital"))

        # Philippines-style variants
        if isinstance(b5.get("debt_to_capitalization_pct"), dict):
            put(
                "debt_to_capital",
                (b5["debt_to_capitalization_pct"].get("value") or b5["debt_to_capitalization_pct"].get("benchmark_value")),
            )

        deq = b5.get("debt_equity_total_liabilities_basis") or b5.get("debt_equity")
        if isinstance(deq, dict) and "debt_to_capital" not in metrics:
            deq_val = coerce_float(deq.get("value") or deq.get("benchmark_value"))
            if deq_val is not None and deq_val >= 0:
                metrics["debt_to_capital"] = deq_val / (1.0 + deq_val)

        ratios = b5.get("ratios")
        if isinstance(ratios, dict):
            put("debt_to_ebitda", (ratios.get("debt_ebitda") or {}).get("value") if isinstance(ratios.get("debt_ebitda"), dict) else ratios.get("debt_ebitda"))
            put("interest_coverage", (ratios.get("interest_coverage") or {}).get("value") if isinstance(ratios.get("interest_coverage"), dict) else ratios.get("interest_coverage"))
            put("ffo_to_debt", (ratios.get("ffo_debt") or {}).get("value") if isinstance(ratios.get("ffo_debt"), dict) else ratios.get("ffo_debt"))
            put("debt_to_capital", (ratios.get("debt_capital") or {}).get("value") if isinstance(ratios.get("debt_capital"), dict) else ratios.get("debt_capital"))

    # Derive missing ratios from financial statements where possible (same-currency ratios).
    fin = utility.get("financial") or {}
    if isinstance(fin, dict):
        def fin_val(key: str) -> float | None:
            v = fin.get(key)
            if isinstance(v, dict):
                return coerce_float(v.get("value"))
            return coerce_float(v)

        if "debt_to_ebitda" not in metrics:
            debt = fin_val("interest_bearing_liabilities") or fin_val("gross_debt")
            ebitda = fin_val("ebitda")
            if debt is not None and ebitda is not None and ebitda > 0:
                metrics["debt_to_ebitda"] = debt / ebitda

        if "ffo_to_debt" not in metrics:
            debt = fin_val("interest_bearing_liabilities") or fin_val("gross_debt")
            cfo = fin_val("operating_cash_flow")
            if debt is not None and cfo is not None and debt > 0:
                metrics["ffo_to_debt"] = cfo / debt

        if "debt_to_capital" not in metrics:
            debt = fin_val("interest_bearing_liabilities") or fin_val("gross_debt") or fin_val("total_liabilities")
            equity = fin_val("equity")
            if debt is not None and equity is not None and (debt + equity) > 0:
                metrics["debt_to_capital"] = debt / (debt + equity)

    if "debt_to_capital" in metrics and metrics["debt_to_capital"] > 1.5:
        metrics["debt_to_capital"] = metrics["debt_to_capital"] / 100.0
    if "ffo_to_debt" in metrics and metrics["ffo_to_debt"] > 1.5:
        metrics["ffo_to_debt"] = metrics["ffo_to_debt"] / 100.0

    if "debt_to_ebitda" in metrics:
        checks["debt_to_ebitda"] = metrics["debt_to_ebitda"] < 4.0
    if "interest_coverage" in metrics:
        checks["interest_coverage"] = metrics["interest_coverage"] > 2.5
    if "ffo_to_debt" in metrics:
        checks["ffo_to_debt"] = metrics["ffo_to_debt"] > 0.20
    if "current_ratio" in metrics:
        checks["current_ratio"] = metrics["current_ratio"] > 1.0
    if "debt_to_capital" in metrics:
        checks["debt_to_capital"] = metrics["debt_to_capital"] < 0.60

    available = len(checks)
    passes = sum(1 for v in checks.values() if v)
    fails = available - passes
    if available >= 4:
        overall_pass = fails <= 1
    elif available == 3:
        overall_pass = fails == 0
    else:
        overall_pass = False

    return overall_pass, {"metrics": metrics, "checks": checks, "available": available, "passes": passes, "fails": fails}


def no_coal_policy(utility: dict[str, Any]) -> bool:
    transition = utility.get("transition") or {}
    if not isinstance(transition, dict):
        return False
    v = transition.get("no_coal_policy")
    raw = v.get("value") if isinstance(v, dict) else v
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        return "no coal" in raw.lower() or raw.strip().lower() == "true"
    return False


def declining_intensity(utility: dict[str, Any]) -> bool:
    emissions = utility.get("emissions") or {}
    if not isinstance(emissions, dict):
        return False
    trend = emissions.get("intensity_trend")
    if isinstance(trend, dict):
        series = []
        for k, v in trend.items():
            y = parse_year(k)
            val = coerce_float(v)
            if y is not None and val is not None:
                series.append((y, val))
        series.sort()
        if len(series) >= 2:
            return series[-1][1] < series[-2][1]
    intensity = emissions.get("intensity_tco2_mwh")
    if isinstance(intensity, dict):
        cur = coerce_float(intensity.get("value"))
        prev = coerce_float(intensity.get("fy2023_value") or intensity.get("prior_year_value"))
        if cur is not None and prev is not None:
            return cur < prev
    return False


def tier(pass_count: int, no_coal: bool, declining: bool) -> str:
    if pass_count == 5:
        return "Highest"
    if pass_count == 4 and no_coal and declining:
        return "Highest"
    if pass_count == 4:
        return "Medium-high"
    if pass_count == 3:
        return "Medium"
    if pass_count == 2:
        return "Low-medium"
    if pass_count == 1:
        return "Low"
    return "Lowest"


def safe_mean(values: Iterable[float | None]) -> float | None:
    vals = [v for v in values if v is not None and not math.isnan(v)]
    return mean(vals) if vals else None


def latex_check(passed: bool) -> str:
    return "\\checkmark" if passed else "$\\times$"


def format_pct(ratio: float | None) -> str:
    if ratio is None or math.isnan(ratio):
        return "NA"
    pct = ratio * 100.0
    if pct > 1000:
        return ">1000\\%"
    return f"{pct:.0f}\\%"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser()
    base = Path(__file__).parent.parent
    parser.add_argument("--raw-dir", default=str(base / "data" / "raw"))
    parser.add_argument("--out-dir", default=str(base / "results"))
    parser.add_argument("--include-india", action="store_true")
    args = parser.parse_args()

    raw_dir = Path(args.raw_dir)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    raw_files = sorted(raw_dir.glob("*_utilities_etcb_data.json"))
    if not args.include_india:
        raw_files = [p for p in raw_files if p.name != "IN_utilities_etcb_data.json"]

    computed: list[dict[str, Any]] = []

    for path in raw_files:
        root_obj = json.loads(path.read_text(encoding="utf-8"))
        meta = root_obj.get("metadata") or {}
        country_code = str(meta.get("country_code") or "")
        fx_raw = meta.get("fx_to_usd_default") or {}
        fx = Fx(
            value=coerce_float(unwrap(fx_raw.get("value"))) or 1.0,
            unit=str(fx_raw.get("unit") or ""),
        )

        solar_lcoe = extract_solar_lcoe_usd_mwh(country_code, root_obj)

        for utility in root_obj.get("utilities") or []:
            if not isinstance(utility, dict):
                continue

            uid = utility.get("id") or utility.get("utility_id") or utility.get("utilityId")
            name = utility.get("name") or ""
            owner_cat = ownership_category(utility)

            b1_pass, b1_meta = b1_stranded_asset_risk_pass(utility)

            emissions_t, emissions_method = extract_emissions_scope1_tco2(country_code, root_obj, utility)
            ebitda_usd, ebitda_method = extract_ebitda_usd(root_obj, utility, fx)
            cce = b2_carbon_cost_exposure_ratio(emissions_t, ebitda_usd)
            b2_pass = cce.get("medium") is not None and cce["medium"] < 0.20

            b3_pass, b3_meta = b3_lcoe_crossover_pass(utility, solar_lcoe)
            b4_pass, b4_meta = b4_capex_alignment_pass(utility)
            b5_pass, b5_meta = b5_balance_sheet_stress_pass(utility)

            pass_count = sum(1 for x in [b1_pass, b2_pass, b3_pass, b4_pass, b5_pass] if x)

            no_coal = no_coal_policy(utility)
            declining = declining_intensity(utility)
            tier_str = tier(pass_count, no_coal, declining)

            gen_gwh, gen_method = extract_generation_gwh(utility)
            if gen_gwh is None:
                gen_gwh, gen_method = estimate_generation_gwh_from_capacity(utility)
            intensity = None
            if emissions_t is not None and gen_gwh is not None and gen_gwh > 0:
                intensity = emissions_t / (gen_gwh * 1000.0)

            computed.append(
                {
                    "country_code": country_code,
                    "utility_id": uid,
                    "name": name,
                    "ownership_category": owner_cat,
                    "signals": {"no_coal_policy": no_coal, "declining_intensity": declining},
                    "derived": {
                        "solar_lcoe_usd_mwh": solar_lcoe,
                        "generation_gwh": gen_gwh,
                        "generation_method": gen_method,
                        "intensity_tco2_mwh": intensity,
                    },
                    "inputs": {
                        "scope1_emissions_tco2": emissions_t,
                        "scope1_emissions_method": emissions_method,
                        "ebitda_usd": ebitda_usd,
                        "ebitda_method": ebitda_method,
                    },
                    "benchmarks": {
                        "b1": {"pass": b1_pass, **b1_meta},
                        "b2": {"pass": b2_pass, "cce": cce},
                        "b3": {"pass": b3_pass, **b3_meta},
                        "b4": {"pass": b4_pass, **b4_meta},
                        "b5": {"pass": b5_pass, **b5_meta},
                    },
                    "pass_count": pass_count,
                    "tier": tier_str,
                }
            )

    computed.sort(key=lambda r: (-r["pass_count"], str(r["name"]).lower()))

    summary_path = out_dir / "etcb_results_summary.json"
    summary_path.write_text(json.dumps({"utilities": computed}, indent=2, ensure_ascii=False), encoding="utf-8")

    (out_dir / "table_results_rows.tex").write_text(
        "\n".join(
            "{} & {} & {} & {} & {} & {} & {}/5 & {} \\\\".format(
                r["name"],
                latex_check(r["benchmarks"]["b1"]["pass"]),
                latex_check(r["benchmarks"]["b2"]["pass"]),
                latex_check(r["benchmarks"]["b3"]["pass"]),
                latex_check(r["benchmarks"]["b4"]["pass"]),
                latex_check(r["benchmarks"]["b5"]["pass"]),
                r["pass_count"],
                r["tier"],
            )
            for r in computed
        )
        + "\n",
        encoding="utf-8",
    )

    (out_dir / "table_cce_sensitivity_rows.tex").write_text(
        "\n".join(
            "{} & {} & {} & {} \\\\".format(
                r["name"],
                format_pct(r["benchmarks"]["b2"]["cce"].get("low")),
                format_pct(r["benchmarks"]["b2"]["cce"].get("medium")),
                format_pct(r["benchmarks"]["b2"]["cce"].get("high")),
            )
            for r in computed
        )
        + "\n",
        encoding="utf-8",
    )

    groups: dict[str, list[dict[str, Any]]] = {"Private": [], "State-linked": [], "State": []}
    for r in computed:
        groups.setdefault(r["ownership_category"], []).append(r)

    own_rows = []
    for group_name in ["Private", "State-linked", "State"]:
        items = groups.get(group_name, [])
        clean_capex_avg = safe_mean([i["benchmarks"]["b4"].get("clean_capex_share_pct") for i in items])
        intensity_avg = safe_mean([i["derived"].get("intensity_tco2_mwh") for i in items])
        pass_rate_avg = safe_mean([float(i["pass_count"]) for i in items])

        own_rows.append(
            "{} & {} & {} & {} & {} \\\\".format(
                group_name,
                len(items),
                "NA" if clean_capex_avg is None else f"{clean_capex_avg:.0f}\\%",
                "NA" if intensity_avg is None else f"{intensity_avg:.2f}",
                "NA" if pass_rate_avg is None else f"{pass_rate_avg:.1f}/5",
            )
        )

    (out_dir / "table_ownership_rows.tex").write_text("\n".join(own_rows) + "\n", encoding="utf-8")

    print(f"Wrote {summary_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
