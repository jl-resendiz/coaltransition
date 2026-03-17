"""
Generate more insightful visualization figures for ETCB Results Section
Version 2: More analytical depth
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

# Set style for academic publication - clean, minimalist
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.linewidth'] = 0.5
plt.rcParams['figure.dpi'] = 300
plt.rcParams['axes.spines.top'] = False
plt.rcParams['axes.spines.right'] = False

# Data paths
BASE_DIR = Path(__file__).parent.parent
UTILITY_DIR = BASE_DIR / "utility_results"
OUTPUT_DIR = BASE_DIR / "figures"
OUTPUT_DIR.mkdir(exist_ok=True)

# Carbon prices on power generation (USD/tCO2).
# India: CCTS excludes power sector; coal cess abolished Sep 2025.
# Thailand: petroleum excise only; coal/gas generation excluded.
# Singapore: SGD 25 / 1.3669 = $18.29.
CARBON_PRICES = {
    'IN': 0.0, 'TH': 0.0, 'VN': 0.0, 'PH': 0.0, 'MY': 0.0,
    'ID': 4.0, 'SG': 18.29,
}

def load_all_utilities():
    """Load all utility results from JSON files."""
    utilities = []
    for folder in UTILITY_DIR.iterdir():
        if folder.is_dir():
            json_file = folder / "etcb_results.json"
            if json_file.exists():
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    utilities.append(data)
    return utilities

def get_utility_metrics(u):
    """Extract key metrics from utility data."""
    b2 = u['benchmarks']['b2_carbon_cost_exposure']['details']
    b4 = u['benchmarks']['b4_transition_alignment']['details']
    b1 = u['benchmarks']['b1_stranded_asset_risk']['details']

    scope1 = b2.get('scope1_tco2', 0)
    ebitda = b2.get('ebitda_usd', 1) or 1

    # Coal share calculation
    b3 = u['benchmarks']['b3_lcoe_crossover']['details']
    coal_mw = b3.get('fuel_analysis', {}).get('coal', {}).get('capacity_mw', 0)
    gas_mw = b3.get('fuel_analysis', {}).get('gas', {}).get('capacity_mw', 0)
    thermal_mw = b3.get('thermal_mw', 0) or 1

    # Total capacity estimate (thermal + RE based on RE share)
    re_share = b4.get('re_share_pct', 0) or 0
    if re_share > 0 and re_share < 100:
        total_capacity = thermal_mw / (1 - re_share/100)
    else:
        total_capacity = thermal_mw if thermal_mw > 0 else 1000  # Default for pure RE

    return {
        'name': u['utility_name'],
        'country': u['country_code'],
        'scope1': scope1,
        'ebitda': ebitda,
        'clean_capex': b4.get('clean_capex_pct', 0) or 0,
        're_share': re_share,
        'coal_at_risk': b1.get('at_risk_share_pct', 0),
        'coal_mw': coal_mw,
        'gas_mw': gas_mw,
        'thermal_mw': thermal_mw,
        'total_capacity': total_capacity,
        'tier': u['summary']['tier'],
        'pass_count': u['summary']['pass_count'],
    }


def figure_carbon_threshold(utilities):
    """
    Carbon Price Threshold Analysis
    At what carbon price does each utility fail B2 (CCE > 20%)?
    """
    fig, ax = plt.subplots(figsize=(10, 7))

    data = []
    for u in utilities:
        m = get_utility_metrics(u)
        if m['scope1'] > 0 and m['ebitda'] > 0:
            # Threshold price where CCE = 20%
            # CCE = (scope1 * price) / ebitda = 0.20
            # price = 0.20 * ebitda / scope1
            threshold = (0.20 * m['ebitda']) / m['scope1']
            current_price = CARBON_PRICES.get(m['country'], 0)

            data.append({
                'name': m['name'],
                'threshold': threshold,
                'current': current_price,
                'country': m['country'],
                'headroom': threshold - current_price
            })

    # Sort by threshold (most vulnerable first)
    data.sort(key=lambda x: x['threshold'])

    names = [d['name'] for d in data]
    thresholds = [d['threshold'] for d in data]
    currents = [d['current'] for d in data]

    y_pos = np.arange(len(names))

    # Plot threshold bars
    bars = ax.barh(y_pos, thresholds, color='#fee08b', edgecolor='#666', linewidth=0.5, label='B2 Failure Threshold')

    # Overlay current price markers
    for i, (curr, thresh) in enumerate(zip(currents, thresholds)):
        if curr > 0:
            ax.plot(curr, i, 'ko', markersize=8, zorder=5)
            ax.plot([curr, curr], [i-0.3, i+0.3], 'k-', linewidth=2, zorder=5)

    # Add reference lines
    ax.axvline(x=15, color='#fdae61', linestyle='--', linewidth=1.5, label='Low scenario ($15)')
    ax.axvline(x=75, color='#d73027', linestyle='--', linewidth=1.5, label='High scenario ($75)')

    # Annotations for key utilities
    for i, d in enumerate(data):
        if d['threshold'] < 75:
            ax.text(d['threshold'] + 2, i, f"${d['threshold']:.0f}", va='center', fontsize=8)

    ax.set_yticks(y_pos)
    ax.set_yticklabels(names, fontsize=9)
    ax.set_xlabel('Carbon Price ($/tCO₂)', fontsize=11, fontweight='bold')
    ax.set_title('Carbon Price Threshold for B2 Failure\n(Price at which CCE exceeds 20% of EBITDA)',
                 fontsize=12, fontweight='bold')
    ax.set_xlim(0, 100)
    ax.legend(loc='lower right', fontsize=9)
    ax.invert_yaxis()

    # Add interpretation note
    ax.text(0.98, 0.02, 'Black markers = current carbon price\nLower threshold = higher vulnerability',
            transform=ax.transAxes, fontsize=8, ha='right', va='bottom', style='italic',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig_carbon_threshold.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig_carbon_threshold.pdf', bbox_inches='tight')
    plt.close()
    print("Figure: Carbon threshold analysis saved")


def figure_transition_authenticity(utilities):
    """
    Clean CapEx vs Coal Exposure quadrant analysis
    Minimalist design with blue color scheme, bubble size = utility capacity
    """
    fig, ax = plt.subplots(figsize=(8, 6.5))

    data = []
    for u in utilities:
        m = get_utility_metrics(u)
        data.append(m)

    # Colors: red (Low) to blue (Highest) gradient
    tier_colors = {
        'Highest': '#08519c',      # Dark blue
        'Medium-high': '#6baed6',  # Light blue
        'Medium': '#bdc3c7',       # Gray (neutral middle)
        'Low-medium': '#e59866',   # Light orange
        'Low': '#e74c3c',          # Red
    }

    # Calculate bubble sizes based on total capacity (normalized)
    capacities = [d['total_capacity'] for d in data]
    max_cap = max(capacities) if capacities else 1
    min_size, max_size = 60, 600

    for d in data:
        color = tier_colors.get(d['tier'], '#bdc3c7')
        # Scale bubble size by capacity
        size = min_size + (d['total_capacity'] / max_cap) * (max_size - min_size)

        ax.scatter(d['coal_at_risk'], d['clean_capex'],
                   c=color, s=size, alpha=0.75, edgecolors='#2c3e50', linewidths=0.6)

        # Label positioning
        offset = (5, 3)
        ha = 'left'
        if d['coal_at_risk'] > 85:
            offset = (-5, 3)
            ha = 'right'
        ax.annotate(d['name'], (d['coal_at_risk'], d['clean_capex']),
                   xytext=offset, textcoords='offset points', fontsize=7, ha=ha,
                   color='#2c3e50')

    # Subtle quadrant lines
    ax.axhline(y=50, color='#bdc3c7', linestyle='-', linewidth=0.6, alpha=0.5)
    ax.axvline(x=50, color='#bdc3c7', linestyle='-', linewidth=0.6, alpha=0.5)

    # Minimal quadrant labels (no italics, single words)
    ax.text(25, 96, 'Leaders', ha='center', fontsize=9, color='#34495e')
    ax.text(75, 96, 'Transitioning', ha='center', fontsize=9, color='#34495e')
    ax.text(25, 2, 'Non-thermal', ha='center', fontsize=9, color='#7f8c8d')
    ax.text(75, 2, 'Laggards', ha='center', fontsize=9, color='#34495e')

    ax.set_xlabel('Coal Capacity at Stranding Risk (%)', fontsize=10)
    ax.set_ylabel('Clean CapEx (%)', fontsize=10)
    ax.set_xlim(-5, 110)
    ax.set_ylim(-5, 105)

    # Clean tick marks
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_yticks([0, 25, 50, 75, 100])
    ax.tick_params(axis='both', labelsize=9)

    # Compact legend for tiers
    legend_elements = [plt.scatter([], [], c=color, s=50, label=tier, edgecolors='#2c3e50', linewidths=0.4)
                       for tier, color in tier_colors.items()]
    legend = ax.legend(handles=legend_elements, title='Credibility Tier', loc='upper right',
                       fontsize=7.5, title_fontsize=8, frameon=True, framealpha=0.95,
                       edgecolor='#ecf0f1')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig_transition_authenticity.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.savefig(OUTPUT_DIR / 'fig_transition_authenticity.pdf', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()
    print("Figure: Transition authenticity saved")


def figure_adani_comparison(utilities):
    """
    Corporate Siblings: Adani Green vs Adani Power
    Same corporate group, dramatically different outcomes
    """
    # Find Adani utilities
    adani_green = None
    adani_power = None
    for u in utilities:
        if u['utility_name'] == 'Adani Green Energy':
            adani_green = u
        elif u['utility_name'] == 'Adani Power':
            adani_power = u

    if not adani_green or not adani_power:
        print("Could not find Adani utilities")
        return

    fig, axes = plt.subplots(1, 2, figsize=(12, 6))

    # Metrics to compare
    metrics = ['Coal at Risk\n(%)', 'Clean CapEx\n(%)', 'RE Share\n(%)',
               'CCE at $75\n(% EBITDA)', 'Benchmarks\nPassed']

    def get_comparison_values(u):
        m = get_utility_metrics(u)
        cce_75 = (m['scope1'] * 75 / m['ebitda']) * 100 if m['ebitda'] > 0 else 0
        return [
            m['coal_at_risk'],
            m['clean_capex'],
            m['re_share'],
            min(cce_75, 200),  # Cap for display
            u['summary']['pass_count'] * 20  # Scale to 100
        ]

    green_vals = get_comparison_values(adani_green)
    power_vals = get_comparison_values(adani_power)

    # Left panel: Bar comparison
    ax1 = axes[0]
    x = np.arange(len(metrics))
    width = 0.35

    bars1 = ax1.bar(x - width/2, green_vals, width, label='Adani Green Energy', color='#1a9850', edgecolor='black')
    bars2 = ax1.bar(x + width/2, power_vals, width, label='Adani Power', color='#d73027', edgecolor='black')

    ax1.set_ylabel('Value', fontsize=11, fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(metrics, fontsize=9)
    ax1.legend(loc='upper right', fontsize=10)
    ax1.set_title('Same Corporate Group, Different Outcomes', fontsize=11, fontweight='bold')
    ax1.set_ylim(0, 120)

    # Add value labels
    for bar, val in zip(bars1, green_vals):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                f'{val:.0f}', ha='center', va='bottom', fontsize=8)
    for bar, val in zip(bars2, power_vals):
        label = f'{val:.0f}' if val <= 200 else '162%'
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 2,
                label, ha='center', va='bottom', fontsize=8)

    # Right panel: Benchmark pass/fail
    ax2 = axes[1]
    benchmarks = ['B1\nStranded\nAsset', 'B2\nCarbon\nCost', 'B3\nLCOE',
                  'B4\nTransition', 'B5\nBalance\nSheet']

    green_pass = [adani_green['benchmarks'][b]['passed'] for b in
                  ['b1_stranded_asset_risk', 'b2_carbon_cost_exposure', 'b3_lcoe_crossover',
                   'b4_transition_alignment', 'b5_balance_sheet_stress']]
    power_pass = [adani_power['benchmarks'][b]['passed'] for b in
                  ['b1_stranded_asset_risk', 'b2_carbon_cost_exposure', 'b3_lcoe_crossover',
                   'b4_transition_alignment', 'b5_balance_sheet_stress']]

    x = np.arange(len(benchmarks))

    for i, (g, p) in enumerate(zip(green_pass, power_pass)):
        # Adani Green (top row)
        color_g = '#1a9850' if g else '#fee08b'
        ax2.add_patch(plt.Rectangle((i-0.4, 0.55), 0.8, 0.4, facecolor=color_g, edgecolor='black'))
        ax2.text(i, 0.75, 'P' if g else 'F', ha='center', va='center', fontsize=12, fontweight='bold')

        # Adani Power (bottom row)
        color_p = '#1a9850' if p else '#d73027'
        ax2.add_patch(plt.Rectangle((i-0.4, 0.05), 0.8, 0.4, facecolor=color_p, edgecolor='black'))
        ax2.text(i, 0.25, 'P' if p else 'F', ha='center', va='center', fontsize=12, fontweight='bold')

    ax2.set_xlim(-0.6, 4.6)
    ax2.set_ylim(0, 1.1)
    ax2.set_xticks(x)
    ax2.set_xticklabels(benchmarks, fontsize=9)
    ax2.set_yticks([0.25, 0.75])
    ax2.set_yticklabels(['Adani Power\n(3/5)', 'Adani Green\n(4/5)'], fontsize=10)
    ax2.set_title('Benchmark Performance', fontsize=11, fontweight='bold')
    ax2.set_aspect('equal')

    fig.suptitle('Business Model Matters More Than Corporate Affiliation:\nThe Adani Comparison',
                 fontsize=13, fontweight='bold', y=1.02)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig_adani_comparison.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig_adani_comparison.pdf', bbox_inches='tight')
    plt.close()
    print("Figure: Adani comparison saved")


def figure_binding_constraints(utilities):
    """
    Which benchmarks are the binding constraints?
    Failure decomposition by tier
    """
    fig, ax = plt.subplots(figsize=(10, 6))

    benchmarks = ['B1', 'B2', 'B3', 'B4', 'B5']
    benchmark_keys = ['b1_stranded_asset_risk', 'b2_carbon_cost_exposure', 'b3_lcoe_crossover',
                      'b4_transition_alignment', 'b5_balance_sheet_stress']

    # Count failures by benchmark
    failures = {b: 0 for b in benchmarks}

    for u in utilities:
        for i, bkey in enumerate(benchmark_keys):
            # Recalculate B2 with updated carbon prices
            if bkey == 'b2_carbon_cost_exposure':
                m = get_utility_metrics(u)
                cce = (m['scope1'] * CARBON_PRICES.get(m['country'], 0) / m['ebitda']) * 100 if m['ebitda'] > 0 else 0
                if cce >= 20:
                    failures[benchmarks[i]] += 1
            else:
                if not u['benchmarks'][bkey]['passed']:
                    failures[benchmarks[i]] += 1

    # Create bar chart
    colors = ['#d73027', '#fc8d59', '#fee08b', '#91cf60', '#1a9850']
    bars = ax.bar(benchmarks, [failures[b] for b in benchmarks], color=colors, edgecolor='black')

    # Add value labels
    for bar, b in zip(bars, benchmarks):
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 0.3,
                f'{int(height)}/{len(utilities)}', ha='center', va='bottom', fontsize=11, fontweight='bold')

    # Add benchmark descriptions
    descriptions = [
        'Coal retirement\ntimelines',
        'Carbon cost\nexposure',
        'LCOE\ncrossover',
        'Transition\nalignment',
        'Balance\nsheet stress'
    ]
    for i, desc in enumerate(descriptions):
        ax.text(i, -2.5, desc, ha='center', va='top', fontsize=8, style='italic')

    ax.set_ylabel('Number of Utilities Failing', fontsize=11, fontweight='bold')
    ax.set_title('Binding Constraints: Which Benchmarks Cause Failures?', fontsize=12, fontweight='bold')
    ax.set_ylim(0, 18)
    ax.axhline(y=10.5, color='gray', linestyle=':', alpha=0.5)
    ax.text(4.5, 11, '50% failure rate', fontsize=9, style='italic', color='gray')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig_binding_constraints.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig_binding_constraints.pdf', bbox_inches='tight')
    plt.close()
    print("Figure: Binding constraints saved")


def figure_state_vs_private_b1(utilities):
    """
    State utilities universally fail B1 - striking visualization
    """
    fig, ax = plt.subplots(figsize=(9, 6))

    # Categorize utilities
    state_owned = ['NTPC', 'PLN', 'EVN', 'EGAT']
    state_linked = ['TNB', 'NLC India', 'RATCH Group', 'GPSC']
    private = ['Tata Power', 'Adani Power', 'JSW Energy', 'Torrent Power',
               'Gulf Energy', 'B.Grimm Power', 'Aboitiz Power', 'SMC Global Power']
    pure_play = ['Sembcorp', 'Adani Green Energy', 'NHPC', 'SJVN']

    categories = {
        'State-owned': state_owned,
        'State-linked': state_linked,
        'Private (diversified)': private,
        'Pure-play RE/Transmission': pure_play
    }

    # Calculate B1 pass rates
    results = {}
    for cat, names in categories.items():
        passes = 0
        total = 0
        for u in utilities:
            if u['utility_name'] in names:
                total += 1
                if u['benchmarks']['b1_stranded_asset_risk']['passed']:
                    passes += 1
        results[cat] = {'passes': passes, 'total': total, 'rate': passes/total*100 if total > 0 else 0}

    cats = list(results.keys())
    rates = [results[c]['rate'] for c in cats]
    colors = ['#d73027', '#fc8d59', '#91cf60', '#1a9850']

    bars = ax.bar(cats, rates, color=colors, edgecolor='black', linewidth=1.5)

    # Add pass/total labels
    for bar, cat in zip(bars, cats):
        r = results[cat]
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height + 2,
                f"{r['passes']}/{r['total']}", ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax.set_ylabel('B1 Pass Rate (%)', fontsize=11, fontweight='bold')
    ax.set_title('State Utilities Universally Fail B1 (Stranded Asset Risk)\nNo state-owned utility has disclosed coal retirement timelines',
                 fontsize=12, fontweight='bold')
    ax.set_ylim(0, 110)
    ax.set_xticklabels(cats, fontsize=10, rotation=15, ha='right')

    # Highlight the 0%
    ax.annotate('0%', (0, 5), fontsize=24, fontweight='bold', color='white', ha='center')
    ax.annotate('0%', (1, 5), fontsize=24, fontweight='bold', color='white', ha='center')

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / 'fig_state_b1_failure.png', dpi=300, bbox_inches='tight')
    plt.savefig(OUTPUT_DIR / 'fig_state_b1_failure.pdf', bbox_inches='tight')
    plt.close()
    print("Figure: State B1 failure saved")


def main():
    """Generate all analytical figures."""
    print("Loading utility data...")
    utilities = load_all_utilities()
    print(f"Loaded {len(utilities)} utilities")

    print("\nGenerating analytical figures...")
    figure_carbon_threshold(utilities)
    figure_transition_authenticity(utilities)
    figure_adani_comparison(utilities)
    figure_binding_constraints(utilities)
    figure_state_vs_private_b1(utilities)

    print(f"\nAll figures saved to: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
