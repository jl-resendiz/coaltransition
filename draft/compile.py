#!/usr/bin/env python3
"""Compile GrowOut_Energy_Policy.tex using MiKTeX.

Usage:
  python EP_submission_package/draft/compile.py

Runs pdflatex -> bibtex -> pdflatex -> pdflatex.
Requires MiKTeX installed at the default Windows location.
"""
import os
import subprocess
import sys

DRAFT_DIR = os.path.dirname(os.path.abspath(__file__))
TEX_FILE = "GrowOut_Energy_Policy"

MIKTEX_BIN = os.path.join(
    "C:", os.sep, "Users", "jlres", "AppData", "Local",
    "Programs", "MiKTeX", "miktex", "bin", "x64",
)
PDFLATEX = os.path.join(MIKTEX_BIN, "pdflatex.exe")
BIBTEX = os.path.join(MIKTEX_BIN, "bibtex.exe")


def run(cmd):
    print(f"  >> {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=DRAFT_DIR)
    return result.returncode


def main():
    if not os.path.isfile(PDFLATEX):
        print(f"ERROR: pdflatex not found at {PDFLATEX}")
        return 1

    latex_cmd = [PDFLATEX, "-interaction=nonstopmode", TEX_FILE]
    bibtex_cmd = [BIBTEX, TEX_FILE]

    steps = [
        ("pdflatex (pass 1)", latex_cmd),
        ("bibtex", bibtex_cmd),
        ("pdflatex (pass 2)", latex_cmd),
        ("pdflatex (pass 3)", latex_cmd),
    ]

    for name, cmd in steps:
        print(f"\n--- {name} ---")
        rc = run(cmd)
        if rc != 0 and name == "bibtex":
            print(f"  WARNING: {name} returned {rc} (may be non-fatal)")
        elif rc != 0:
            print(f"  ERROR: {name} failed (exit code {rc})")
            return rc

    pdf = os.path.join(DRAFT_DIR, f"{TEX_FILE}.pdf")
    if os.path.isfile(pdf):
        print(f"\nSuccess: {pdf}")
    else:
        print("\nWARNING: PDF not found after compilation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
