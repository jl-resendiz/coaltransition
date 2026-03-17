#!/usr/bin/env python3
"""Run the full coal_transition analysis pipeline.

Executes scripts in dependency order and writes outputs to results/.

Usage:
  python coal_transition/scripts/run_all.py

Note: generate_figures_v2.py requires matplotlib and numpy (optional).
All other scripts are stdlib-only.
"""
import os
import subprocess
import sys
import time

SCRIPTS = [
    ('calculate_etcb.py', 'ETCB benchmark calculation (all 21 utilities)'),
    ('compute_cf_sensitivity.py', 'Capacity factor sensitivity analysis'),
    ('compute_grow_out_arithmetic.py', 'MW vs TWh grow-out arithmetic'),
    ('compute_dynamic_scenarios.py', 'Dynamic demand-growth scenarios'),
]

# Figure generation requires matplotlib + numpy; skip if unavailable.
try:
    import matplotlib  # noqa: F401
    import numpy  # noqa: F401
    SCRIPTS.append(('generate_figures_v2.py', 'Generate figures (matplotlib)'))
except ImportError:
    print('NOTE: matplotlib/numpy not available; skipping figure generation.')
    print('      Pre-generated figures in figures/ are used for manuscript compilation.\n')


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    print('=' * 60)
    print('Coal Transition: Full Pipeline')
    print('=' * 60)

    t0 = time.time()
    failed = []

    for script, description in SCRIPTS:
        print(f'\n{"-" * 60}')
        print(f'>> {description}')
        print(f'   Running: {script}')
        print(f'{"-" * 60}')

        result = subprocess.run(
            [sys.executable, script],
            cwd=script_dir,
        )

        if result.returncode != 0:
            print(f'\n  FAILED (exit code {result.returncode})')
            failed.append(script)
        else:
            print(f'\n  OK')

    elapsed = time.time() - t0
    print(f'\n{"=" * 60}')
    print(f'Pipeline complete in {elapsed:.1f}s')
    if failed:
        print(f'FAILED: {", ".join(failed)}')
        return 1
    else:
        print('All scripts succeeded.')
        return 0


if __name__ == '__main__':
    sys.exit(main())
