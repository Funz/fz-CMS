#!/usr/bin/env python3
"""
Example script for running CASMO5 parametric studies with fz.

This example demonstrates how to use the fz-CMS plugin to run a parametric study
on a UO2 pin cell, varying the enrichment and the pin pitch (moderation ratio):
the outer radius of the PIC card is computed from the pitch by a formula of the input.
"""

import os
import sys

try:
    import fz
except ImportError:
    print("Error: fz framework not found.")
    print("Please install it from: https://github.com/Funz/fz")
    sys.exit(1)


def main():
    """Run a parametric study on a CASMO5 pin cell."""

    # Check if CMSHOME is set
    if 'CMSHOME' not in os.environ:
        print("Error: CMSHOME environment variable is not set.")
        print("Please set it to your Studsvik CMS installation directory:")
        print("  export CMSHOME=/path/to/CMSCODES")
        print("  export LM_LICENSE_FILE=port@license_server")
        sys.exit(1)

    # Define the input file (in the same directory as this script)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_file = os.path.join(script_dir, "CASMO5", "pincell.inp")

    print("=" * 60)
    print("CASMO5 Parametric Study: UO2 pin cell")
    print("=" * 60)
    print()

    # Variables of the input file, with their default values
    print("Variables:", fz.fzi(input_file, "CASMO5"))

    # Define parameter values to study (other variables keep their defaults)
    input_variables = {
        "enrichment": [3.0, 4.0, 5.0],  # U-235 w/o
        "pitch": [1.20, 1.26, 1.32],    # pin pitch, cm
    }

    print("Running calculations...")
    print("-" * 60)

    results = fz.fzr(
        input_path=input_file,
        input_variables=input_variables,
        model="CASMO5",
        calculators="localhost_CMS",
        results_dir="results_pincell"
    )

    print()
    print(results[["enrichment", "pitch", "status", "kinf", "m2", "fatal_message"]])
    print()

    # k-inf of the single state point of each case (kinf is the list of all state points)
    print("k-inf vs pitch (moderation ratio):")
    print("-" * 60)
    for _, row in results.iterrows():
        if row["status"] == "done" and row["kinf"]:
            print(f"  e={row['enrichment']:.1f} w/o  pitch={row['pitch']:.2f} cm  k-inf={row['kinf'][0]:.5f}")
        else:
            print(f"  e={row['enrichment']:.1f} w/o  pitch={row['pitch']:.2f} cm  failed: {row['fatal_message']}")


if __name__ == "__main__":
    main()
