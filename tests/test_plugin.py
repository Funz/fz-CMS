#!/usr/bin/env python3
"""
Test suite for the fz-CMS plugin (CASMO5, CMSLINK5, SIMULATE5).

These tests verify:
- Model and calculator files
- Variable parsing (fzi) and input compilation (fzc), including formulas and context lines
- Output extraction on trimmed real outputs (tests/fixtures): normal and aborted runs of the 3 codes
- Real runs of the examples, only when CMSHOME points to a CMS installation (bin/cas5)
"""

import os
import json
import tempfile
import sys

MODELS = ["CASMO5", "SIMULATE5", "CMSLINK5"]


def test_model_files():
    """Test that all model JSON files are valid and have required fields."""
    print("Testing model files...")

    required_fields = ["id", "varprefix", "formulaprefix", "delim", "commentline", "output"]

    for model in MODELS:
        model_file = f".fz/models/{model}.json"
        print(f"  Checking {model_file}...", end=" ")

        assert os.path.exists(model_file), f"File not found: {model_file}"
        with open(model_file, 'r') as f:
            data = json.load(f)
        for field in required_fields:
            assert field in data, f"Missing field '{field}' in {model_file}"
        assert data["id"] == model, f"id is not {model} in {model_file}"
        assert "normal_termination" in data["output"], f"No normal_termination output in {model_file}"
        assert "fatal_message" in data["output"], f"No fatal_message output in {model_file}"
        # 'error' and 'status' are columns of fz itself
        assert "error" not in data["output"] and "status" not in data["output"], f"Reserved output name in {model_file}"

        print("✓")

    print("  All model files valid!\n")


def test_calculator_files():
    """Test that calculator JSON files are valid and reference existing scripts."""
    print("Testing calculator configuration files...")

    calc_file = ".fz/calculators/localhost_CMS.json"
    print(f"  Checking {calc_file}...", end=" ")
    assert os.path.exists(calc_file), f"File not found: {calc_file}"
    with open(calc_file, 'r') as f:
        calc = json.load(f)
    assert "uri" in calc, f"Missing 'uri' field in {calc_file}"
    assert "models" in calc, f"Missing 'models' field in {calc_file}"
    for model in MODELS:
        assert model in calc["models"], f"Model {model} missing in {calc_file}"
        script = calc["models"][model].split()[-1]
        assert os.path.exists(script), f"Script not found: {script}"
    print("✓")

    print("  All calculator files valid!\n")


def test_calculator_scripts():
    """Test that calculator shell scripts exist and are executable."""
    print("Testing calculator shell scripts...")

    for script_file in [".fz/calculators/CMS.sh"] + [f".fz/calculators/{m}.sh" for m in MODELS]:
        print(f"  Checking {script_file}...", end=" ")
        assert os.path.exists(script_file), f"File not found: {script_file}"
        assert os.access(script_file, os.X_OK), f"Script not executable: {script_file}"
        print("✓")

    print("  All calculator scripts valid!\n")


def test_example_files():
    """Test that example files exist."""
    print("Testing example files...")

    examples = [
        "examples/CASMO5/pincell.inp",
        "examples/CASMO5/assembly_dep.inp",
        "examples/SIMULATE5/quarter_core.inp",
        "examples/CMSLINK5/library.inp",
        "examples/example_pincell.py",
    ]
    for example_file in examples:
        print(f"  Checking {example_file}...", end=" ")
        assert os.path.exists(example_file), f"File not found: {example_file}"
        print("✓")

    print("  All example files present!\n")


def _compile(fz, path, values, model):
    """Compile one case and return the compiled content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        fz.fzc(path, values, model, output_dir=tmpdir)
        for root, dirs, files in os.walk(tmpdir):
            if os.path.basename(path) in files:
                with open(os.path.join(root, os.path.basename(path))) as f:
                    return f.read()
    raise AssertionError(f"Compiled file not created for {path}")


def test_with_fz():
    """Test variable parsing and compilation with the fz framework (if available)."""
    print("Testing fz framework integration...")

    try:
        import fz
    except ImportError:
        print("  fz module not installed - skipping integration tests")
        print("  (Install with: pip install git+https://github.com/Funz/fz.git)\n")
        return
    print("  fz module found ✓")

    print("  Testing fz.fzi() on the examples...", end=" ")
    variables = fz.fzi("examples/CASMO5/pincell.inp", "CASMO5")
    assert set(variables) == {"enrichment", "pitch", "tfu", "tmo", "boron"}, f"Variables: {variables}"
    variables = fz.fzi("examples/SIMULATE5/quarter_core.inp", "SIMULATE5")
    assert set(variables) == {"power", "tin_c"}, f"Variables: {variables}"
    variables = fz.fzi("examples/CMSLINK5/library.inp", "CMSLINK5")
    assert set(variables) == {"library", "groups"}, f"Variables: {variables}"
    print("✓")

    print("  Testing fz.fzc() compilation (CASMO5 formula)...", end=" ")
    content = _compile(fz, "examples/CASMO5/pincell.inp", {"enrichment": 3.1, "pitch": 1.30}, "CASMO5")
    assert "FUE 1 10.45/3.1" in content, "Variable enrichment not substituted"
    assert "PIC .4096 .4178 .4750 0.73345/" in content, "Formula cell_radius not evaluated"
    assert "$(" not in content and "@(" not in content, "Variable or formula marker still present"
    print("✓")

    print("  Testing fz.fzc() compilation (SIMULATE5 'COM' context)...", end=" ")
    content = _compile(fz, "examples/SIMULATE5/quarter_core.inp", {"power": 50, "tin_c": 286}, "SIMULATE5")
    assert "'COR.OPE' 50 100. 2250. /" in content, "Variable power not substituted"
    assert "'COR.TIN' 546.8 /" in content, "Formula degF not evaluated"
    print("✓")

    print("  fz integration tests passed!\n")


# expected values of the trimmed real outputs of tests/fixtures
FIXTURES = {
    ("CASMO5", "casmo5_dep"): {
        "normal_termination": 1, "fatal_message": None, "warnings": 0,
        "kinf": (0, 1.29077), "burnup": (-1, 20.0), "u235_wt": (-1, 1.907), "pin_peak": (0, 1.046),
    },
    ("CASMO5", "casmo5_abort"): {
        "normal_termination": 0, "kinf": [],
        "fatal_message": "INPUT1 Power density < 0.05 W/gU and depletion > 0.0 MWd/KgU requested.",
    },
    ("SIMULATE5", "simulate5_3d"): {
        "normal_termination": 1, "fatal_message": None,
        "boron": [1029.39, 820.48, 629.7, 422.82], "keff": (-1, 1.0), "cycle_efpd": (-1, 155.6),
        "fdh": (-1, 1.348), "peak_nodal_power": (-1, 1.442), "axial_offset": (-1, -0.019),
        "exposure": (-1, 6.0), "power_pct": (0, 100.0), "leakage": (-1, 0.033),
    },
    ("SIMULATE5", "simulate5_abort"): {
        "normal_termination": 0, "keff": [],
        "fatal_message": "0003 1 FATAL Cross section data absent from XS library: PWRU320C0",
    },
    ("CMSLINK5", "cmslink5_lib"): {
        "normal_termination": 1, "fatal_message": None, "library": "pwr_hot.lib",
        "segments": ["PWRU200C00", "RADREF", "BOTREF", "TOPREF"],
    },
    ("CMSLINK5", "cmslink5_abort"): {
        "normal_termination": 0, "segments": [], "library": None,
        "fatal_message": "SIMCRD FATAL CASMO SIM CARDS ARE NOT ALL EQUAL",
    },
}


def test_output_parsing():
    """Test the output expressions of the models on trimmed real outputs."""
    print("Testing output extraction on tests/fixtures...")

    try:
        from fz.outparsers import evaluate_python_output
    except ImportError:
        print("  fz module not installed (or without python:// outputs) - skipping\n")
        return

    for (model, fixture), expected in FIXTURES.items():
        print(f"  Checking {model} on {fixture}...", end=" ")
        with open(f".fz/models/{model}.json") as f:
            outputs = json.load(f)["output"]
        d = os.path.join("tests", "fixtures", fixture)
        values = {k: evaluate_python_output(spec, d) for k, spec in outputs.items()}
        for key, exp in expected.items():
            got = values[key]
            if isinstance(exp, tuple):  # (index, value) in a list
                assert isinstance(got, list) and got, f"{fixture}: {key} empty: {got}"
                assert abs(got[exp[0]] - exp[1]) < 1e-9, f"{fixture}: {key}[{exp[0]}] = {got[exp[0]]}, expected {exp[1]}"
            else:
                assert got == exp, f"{fixture}: {key} = {got}, expected {exp}"
        lengths = {k: len(v) for k, v in values.items() if isinstance(v, list)}
        assert len(set(lengths.values())) <= 1, f"{fixture}: lists of different lengths {lengths}"
        print("✓")

    print("  Output extraction tests passed!\n")


def test_run_examples():
    """Run the examples with the real codes (only if CMSHOME is a CMS installation)."""
    print("Testing real runs...")

    cmshome = os.environ.get("CMSHOME", "")
    if not os.path.exists(os.path.join(cmshome, "bin", "cas5")):
        print("  CMSHOME not set or no bin/cas5 - skipping real runs\n")
        return
    import fz

    with tempfile.TemporaryDirectory() as tmpdir:
        print("  CASMO5 pin cell...", end=" ")
        r = fz.fzr("examples/CASMO5/pincell.inp", {"enrichment": 4.45}, "CASMO5",
                   calculators="localhost_CMS", results_dir=os.path.join(tmpdir, "c5"))
        assert r["status"][0] == "done", r.to_dict("records")
        assert abs(r["kinf"][0][0] - 1.30945) < 1e-5, r["kinf"][0]
        print("✓")

        print("  CASMO5 aborted run...", end=" ")
        r = fz.fzr("examples/CASMO5/pincell.inp", {"tmo": 58}, "CASMO5",
                   calculators="localhost_CMS", results_dir=os.path.join(tmpdir, "c5bad"))
        assert r["status"][0] == "failed", r.to_dict("records")
        assert r["fatal_message"][0] == "INPUT1 Incorrect moderator temperature.", r["fatal_message"][0]
        print("✓")

        print("  CMSLINK5 library...", end=" ")
        r = fz.fzr("examples/CMSLINK5/library.inp", {}, "CMSLINK5",
                   calculators="localhost_CMS", results_dir=os.path.join(tmpdir, "clnk"))
        assert r["status"][0] == "done", r.to_dict("records")
        assert r["segments"][0] == ["PWRU200C00", "RADREF", "BOTREF", "TOPREF"], r["segments"][0]
        print("✓")

        print("  SIMULATE5 quarter core...", end=" ")
        r = fz.fzr("examples/SIMULATE5/quarter_core.inp", {"power": 0}, "SIMULATE5",
                   calculators="localhost_CMS", results_dir=os.path.join(tmpdir, "s5"))
        assert r["status"][0] == "done", r.to_dict("records")
        assert abs(r["boron"][0][0] - 2143.15) < 0.1, r["boron"][0]
        print("✓")

    print("  Real runs passed!\n")


def main():
    """Run all tests."""
    print("=" * 70)
    print("fz-CMS Plugin Test Suite")
    print("=" * 70)
    print()

    # Change to repository root if needed
    if not os.path.exists(".fz"):
        root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if os.path.exists(os.path.join(root, ".fz")):
            os.chdir(root)
        else:
            print("Error: Could not find .fz directory")
            print("Please run this script from the fz-CMS repository root")
            return 1

    try:
        test_model_files()
        test_calculator_files()
        test_calculator_scripts()
        test_example_files()
        test_with_fz()
        test_output_parsing()
        test_run_examples()

        print("=" * 70)
        print("All tests passed! ✓")
        print("=" * 70)
        return 0

    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
