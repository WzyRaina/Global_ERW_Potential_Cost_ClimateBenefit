# Global enhanced rock weathering: potential, cost and climate benefit

Code accompanying *Climate-benefit valuation reshapes the economic potential of enhanced rock weathering*. It contains the ERW weathering model, global spatial assessment, FaIR–Howard climate-benefit calculations, and analysis scripts for the basalt-only main scenario. The principal spatial unit is a 0.5° × 0.5° grid cell.

The code is in the `Global_ERW_Potential_Cost_ClimateBenefit/` directory. Its four main components are `1-CDR-Base/` (weathering model), `2-Grid-based-MONET/` (spatial inputs, removal and cost), `3-Climate-Benefit/` (climate-benefit valuation), and `Scenario 3-only basalt/` (material selection, statistics and figures).

## System requirements

- Reference workstation: Windows 11, Python 3.11.11, and R 4.2.2. The small demo below was tested in this environment.
- Python packages present in that environment: `numpy 1.26.4`, `pandas 2.2.3`, `GDAL 3.4.3`, `rasterio 1.4.3`, `matplotlib 3.10.0`, `geopy 2.4.1`, `tqdm 4.67.1`, `scipy 1.17.1`, `joblib 1.4.2`, and `fair 1.3.1`.
- R packages used by the Howard calculation: `data.table 1.14.8`, `doParallel 1.0.17`, and `foreach 1.5.2`; `parallel` is included with R.
- No non-standard hardware is needed for the demo. Full global calculations require substantially more memory and processing time; these requirements have not been benchmarked on a standard desktop.

## Installation

Install [Miniconda](https://docs.conda.io/projects/miniconda/en/latest/) (or Anaconda) and R. One way to create a compatible Python environment is:

```bash
conda create -n global-erw -c conda-forge python=3.11 numpy pandas gdal rasterio matplotlib geopy tqdm scipy joblib
conda activate global-erw
python -m pip install fair==1.3.1
```

Install the R packages with `Rscript -e "install.packages(c('data.table','doParallel','foreach'))"`. Ensure that `python` and `Rscript` are available on your command line. Allow approximately 15–30 minutes for environment setup on a standard desktop (estimate; package download and GDAL installation may take longer). The package versions above document the inspected author environment; the installation commands may resolve newer compatible versions.

## Small demo

From the repository root, run:

```bash
python Global_ERW_Potential_Cost_ClimateBenefit/demo/run_demo.py
```

`demo/sample_conditions.csv` contains three **synthetic** soil-pH and temperature conditions. The script uses `1-CDR-Base/` to calculate the fraction of basalt weathered after 10 years for a 20-µm P80 grain size. It writes `demo/output.csv` and checks the results against `demo/expected_output.csv`. A successful run prints `PASS`; the expected fractions are approximately 0.358169, 0.766149 and 0.970516. Runtime was about 1 second on the reference workstation. This demo tests a model component, not the global assessment.

## Full-analysis inputs and workflow

The global workflow uses the cropland, lithology, soil, emissions-factor, cost, climate and socioeconomic inputs described in the manuscript Methods, Supplementary Information and Data availability statement. Source data are available through the cited publications and repositories; the full set of processed model inputs is not included here. Global rasters have 0.5° resolution (360 × 720 cells). The scripts use author-machine paths, including `E:/wzy/...` and `E:/ArcGIS/...`; replace these paths and the working-directory settings with locations on your computer. The spatial assessment expects input folders including `Global Data/EW/Input/Global/` and `Input Data/EW/`.

For the manuscript's principal case—single basalt application in 2025, no trade, soil-bicarbonate pathway and maximum net-benefit selection—the analysis proceeds as follows:

1. Use the spatial-assessment scripts in `2-Grid-based-MONET/5-Assessment/`, including `No-Trade-Pathway-1.py`, and the FaIR–Howard scripts in `3-Climate-Benefit/` to generate removal-potential, cost and climate-benefit rasters for the four basalt grain sizes. The basalt-only choice is made in the selection step.
2. In `Scenario 3-only basalt/1-Material Selection.py`, set `trade = False`, `maxcb = True` and `start_year = 2025`, then run the script. Its checked-in `start_year` value is 2050. The selected rasters are written to `Output/EW/Global/Scenario 3/2025/maxclimatebenefit_notrade/` under the spatial-model working directory.
3. Run `4-1-Region statistic of potential.py`, `5-1-Region statistic of cost.py`, `6-1-Region statistic of climate benefit.py` and `7-1-Region statistic of net benefit.py` in `Scenario 3-only basalt/` for regional grid-level summaries. The associated R scripts produce charts from the summary CSVs. Set the intended year and trade setting in each figure script; some checked-in scripts use 2050 or `trade = True` by default.

The two selected rasters `EW_potential_maxnetbenefit_raster.tif` and `EW_max_net_benefit_raster.tif` provide a direct check of the global grid-level totals. Sum positive, valid potential across all cells for technical potential, and sum potential only in cells with positive net benefit for economically viable potential. Divide the raster sums (MtCO₂) by 1,000 to obtain GtCO₂. The reported baseline values are approximately **5.02 GtCO₂** and **2.12 GtCO₂**, respectively. The viability test is applied to individual grid cells, not to country-average costs and benefits.

`Scenario 3-only basalt/Grid-level manuscript summary.py` calculates grid-level summaries for implementation years and social-cost-of-carbon values from the selected scenario rasters. Set its `SCENARIO_ROOT` to the local `Output/EW/Global/Scenario 3/` directory and provide `--output-dir` when running it. It writes `Table_S10_grid_level.csv` and `Table_S11_grid_level.csv`. The implementation-year summary reads the `2025`, `2030`, `2035`, `2040`, `2050` and `2025_Extreme` scenario directories. Other scenario definitions and results are given in the manuscript and Supplementary Information.

The small demo was tested in the environment above. The full global workflow requires the cited input datasets and has not been benchmarked here for runtime or hardware requirements. For data not available through the cited sources, see the manuscript's Data availability statement.

## Repository

<https://github.com/WzyRaina/Global_ERW_Potential_Cost_ClimateBenefit>
