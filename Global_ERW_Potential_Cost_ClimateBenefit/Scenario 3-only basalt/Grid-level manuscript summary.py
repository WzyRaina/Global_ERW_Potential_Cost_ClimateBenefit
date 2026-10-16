from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from osgeo import gdal


SCENARIO_ROOT = Path(r"E:\wzy\2-Grid-based-MONET\Output\EW\Global\Scenario 3")
BASE_SCC = 183.84
IMPLEMENTATION_CASES = ["2025", "2030", "2035", "2040", "2050", "2025_Extreme"]
TARGET_SCCS = [100.0, 150.0, BASE_SCC, 200.0, 250.0, 300.0, 350.0, 400.0]


def read_raster(path: Path) -> np.ndarray:
    dataset = gdal.Open(str(path))
    if dataset is None:
        raise FileNotFoundError(path)
    array = dataset.ReadAsArray().astype(float)
    nodata = dataset.GetRasterBand(1).GetNoDataValue()
    if nodata is not None:
        array[array == nodata] = np.nan
    array[array <= -9999] = np.nan
    return array


def implementation_summary(case: str) -> dict[str, float | int | str]:
    folder = SCENARIO_ROOT / case / "maxclimatebenefit_notrade"
    potential = read_raster(folder / "EW_potential_maxnetbenefit_raster.tif")
    cost = read_raster(folder / "EW_cost_maxnetbenefit_raster.tif")
    benefit = read_raster(folder / "EW_climate_benefit_maxnetbenefit_raster.tif")
    net_benefit = read_raster(folder / "EW_max_net_benefit_raster.tif")

    valid = np.isfinite(potential) & (potential > 0)
    positive = valid & np.isfinite(net_benefit) & (net_benefit > 0)
    total_mt = float(np.nansum(potential[valid]))
    economic_mt = float(np.nansum(potential[positive]))

    return {
        "case": case,
        "implementation_year": 2025 if case == "2025_Extreme" else int(case),
        "technical_potential_gtco2": total_mt / 1000.0,
        "weighted_cost_usd_per_tco2": float(np.nansum(cost[valid] * potential[valid]) / total_mt),
        "weighted_climate_benefit_usd_per_tco2": float(
            np.nansum(benefit[valid] * potential[valid]) / total_mt
        ),
        "weighted_net_benefit_usd_per_tco2": float(
            np.nansum(net_benefit[valid] * potential[valid]) / total_mt
        ),
        "grid_cost_effective_potential_gtco2": economic_mt / 1000.0,
        "positive_net_benefit_grid_cells": int(np.count_nonzero(positive)),
        "grid_cost_effective_share_percent": economic_mt / total_mt * 100.0,
        "scc_usd_per_tco2": BASE_SCC,
    }


def scc_summary() -> pd.DataFrame:
    folder = SCENARIO_ROOT / "2025" / "maxclimatebenefit_notrade"
    potential = read_raster(folder / "EW_potential_maxnetbenefit_raster.tif")
    cost = read_raster(folder / "EW_cost_maxnetbenefit_raster.tif")
    base_benefit = read_raster(folder / "EW_climate_benefit_maxnetbenefit_raster.tif")
    valid = np.isfinite(potential) & (potential > 0) & np.isfinite(cost) & np.isfinite(base_benefit)
    total_mt = float(np.nansum(potential[valid]))

    rows = []
    for scc in TARGET_SCCS:
        benefit = base_benefit * (scc / BASE_SCC)
        positive = valid & (benefit > cost)
        economic_mt = float(np.nansum(potential[positive]))
        rows.append(
            {
                "scc_usd_per_tco2": scc,
                "grid_cost_effective_potential_gtco2": economic_mt / 1000.0,
                "positive_net_benefit_grid_cells": int(np.count_nonzero(positive)),
                "grid_cost_effective_share_percent": economic_mt / total_mt * 100.0,
                "technical_potential_gtco2": total_mt / 1000.0,
            }
        )
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reproduce manuscript implementation-year and SCC summaries using a grid-level net-benefit criterion."
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    timing = pd.DataFrame(implementation_summary(case) for case in IMPLEMENTATION_CASES)
    scc = scc_summary()
    timing_path = args.output_dir / "Table_S10_grid_level.csv"
    scc_path = args.output_dir / "Table_S11_grid_level.csv"
    timing.to_csv(timing_path, index=False)
    scc.to_csv(scc_path, index=False)
    print(timing.to_string(index=False))
    print()
    print(scc.to_string(index=False))
    print(f"\nSaved: {timing_path}")
    print(f"Saved: {scc_path}")


if __name__ == "__main__":
    main()
