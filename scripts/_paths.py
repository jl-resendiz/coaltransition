"""Shared path helpers for the EP submission package.

All paths are anchored relative to this file's location:
  scripts/              <- this file
  data/utilities/       <- raw utility JSON inputs
  data/countries/       <- raw country JSON inputs
  country_parameters/   <- country-specific benchmark parameters
  utility_results/      <- per-utility ETCB results
  results/              <- aggregated analysis outputs
  figures/              <- generated figures
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(BASE_DIR, ".."))

UTILITY_DATA_DIR = os.path.join(ROOT, "data", "utilities")
COUNTRY_DATA_DIR = os.path.join(ROOT, "data", "countries")
COUNTRY_PARAMS_DIR = os.path.join(ROOT, "country_parameters")
UTILITY_RESULTS_DIR = os.path.join(ROOT, "utility_results")
RESULTS_DIR = os.path.join(ROOT, "results")
FIGURES_DIR = os.path.join(ROOT, "figures")


def utility_data_path(*parts):
    return os.path.join(UTILITY_DATA_DIR, *parts)


def country_data_path(*parts):
    return os.path.join(COUNTRY_DATA_DIR, *parts)


def country_params_path(*parts):
    return os.path.join(COUNTRY_PARAMS_DIR, *parts)


def utility_results_path(*parts):
    return os.path.join(UTILITY_RESULTS_DIR, *parts)


def results_path(*parts):
    return os.path.join(RESULTS_DIR, *parts)


def figures_path(*parts):
    return os.path.join(FIGURES_DIR, *parts)
