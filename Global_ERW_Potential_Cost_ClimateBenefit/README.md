# Global enhanced rock weathering: potential, cost and climate benefit

Code accompanying *Climate-benefit valuation reshapes the economic potential of enhanced rock weathering*. The repository contains ERW weathering functions, global spatial preprocessing and assessment scripts, and a FaIR-Howard climate-benefit workflow. The principal spatial unit is a 0.5° × 0.5° grid cell.

## System requirements

- Reference workstation: Windows 11, Python 3.11.11, and R 4.2.2. The small demo below was tested in this environment; the complete global workflow was not re-run for this README.
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
python demo/run_demo.py
```

`demo/sample_conditions.csv` contains three **synthetic** soil-pH and temperature conditions. The script calls the unmodified functions in the repository's `1-CDR-Base/` code directory to calculate the basalt fraction weathered after 10 years for a 20-µm P80 grain size. It writes `demo/output.csv` and checks it against `demo/expected_output.csv`. A successful run prints `PASS`; the expected fractions are approximately 0.358169, 0.766149 and 0.970516. The calculation took about 1 second including Python startup on the reference workstation. This demo checks one core-model component; it does **not** reproduce the global potential or economic results.

## Running the full analysis on other data

1. Obtain the cropland, lithology, soil, emissions-factor, cost and climate/socioeconomic inputs described in the manuscript Methods and Supplementary Information. These large inputs are not bundled with this code repository. Global rasters are processed at 0.5° resolution (360 × 720 cells).
2. Adjust the hard-coded input/output paths in the scripts (`E:/wzy/...` and `E:/ArcGIS/...`) to point to your local data and output directories. Set the desired year, rock type, pathway and trade assumptions in the relevant driver script.
3. The main code groups, currently inside `Global_ERW_Potential_Cost_ClimateBenefit/`, are `1-CDR-Base/` (weathering functions), `2-Grid-based-MONET/` (spatial preparation, removal and cost assessment), and `3-Climate-Benefit/` (FaIR and Howard valuation). After preparing the inputs and paths, run the applicable driver under `2-Grid-based-MONET/5-Assessment/` (for example, `No-Trade-Pathway-1.py`). Outputs are GeoTIFF and CSV files at the paths specified in the scripts.

The current public repository is **not yet a portable, end-to-end reproduction package** for the manuscript's basalt-only Scenario 3 and figures: it does not include the full input datasets or the local Scenario 3 result-analysis scripts. The demo above is runnable independently of those datasets. Please add the relevant analysis scripts and data/access instructions before claiming that all manuscript results can be reproduced from this repository alone.

## Repository and license

Repository: <https://github.com/WzyRaina/Global_ERW_Potential_Cost_ClimateBenefit>. The code's functionality and modelling assumptions are described in the manuscript Methods and Supplementary Information. No software license is currently specified in the public repository; the authors should add a license if they intend to grant reuse rights.
