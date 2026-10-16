"""Small, synthetic-input demonstration of the published ERW weathering model."""

import argparse
import importlib.util
from pathlib import Path
import sys
import time

sys.dont_write_bytecode = True

import numpy as np
import pandas as pd


PARAMETERS = {
    "k_H_dunite": 5.55e-8,
    "n_H_dunite": 0.372,
    "k_H_basalt": 588,
    "n_H_basalt": 1.16,
    "k_OH_basalt": 0.0822,
    "n_OH_basalt": 0.16,
    "E_a": 47500,
    "b": 5.2,
    "m": -1,
}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def find_model_dir():
    root = Path(__file__).resolve().parents[1]
    candidates = [
        root / "1-CDR-Base",
        root / "Global_ERW_Potential_Cost_ClimateBenefit" / "1-CDR-Base",
    ]
    for candidate in candidates:
        if (candidate / "ERW_Core_Model.py").is_file():
            return candidate
    raise FileNotFoundError(
        "1-CDR-Base/ERW_Core_Model.py was not found. "
        "Place demo/ beside 1-CDR-Base/ or pass --model-dir."
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model-dir", type=Path, help="Directory containing the two model files")
    args = parser.parse_args()
    started = time.perf_counter()

    model_dir = args.model_dir or find_model_dir()
    psd_module = load_module("erw_psd_demo", model_dir / "Grain_Size_Distribution.py")
    core_module = load_module("erw_core_demo", model_dir / "ERW_Core_Model.py")
    psd = psd_module.generate_psd_for_multiple_p80(
        sigma=0.5, plot=False, uncertainty=True
    )[20]

    demo_dir = Path(__file__).resolve().parent
    sample = pd.read_csv(demo_dir / "sample_conditions.csv")
    rows = []
    for row in sample.itertuples(index=False):
        curve = core_module.core_weathering_calculation(
            pH=row.pH,
            temp_c=row.soil_temperature_C,
            diameters=psd["Diameter"].to_numpy(),
            fractions=psd["Fraction"].to_numpy(),
            simulated_year=11,
            **PARAMETERS,
        )
        rows.append((row.cell_id, float(curve[10, 1])))

    result = pd.DataFrame(
        rows, columns=["cell_id", "basalt_weathered_fraction_after_10_years"]
    )
    output = demo_dir / "output.csv"
    result.to_csv(output, index=False, float_format="%.10f")

    expected = pd.read_csv(demo_dir / "expected_output.csv")
    if result["cell_id"].tolist() != expected["cell_id"].tolist() or not np.allclose(
        result.iloc[:, 1], expected.iloc[:, 1], rtol=0, atol=1e-9
    ):
        raise AssertionError("Demo output does not match expected_output.csv")
    print(result.to_string(index=False))
    print(f"PASS: output matches expected_output.csv; elapsed {time.perf_counter() - started:.2f} s")


if __name__ == "__main__":
    main()
