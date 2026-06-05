# main.py
# 一键运行：FAIR模拟 -> R语言损害计算 -> Python栅格地图映射

import os
import sys
import subprocess
import numpy as np
import pandas as pd
from scipy.stats import truncnorm
from osgeo import gdal
import importlib.util

# ====== 0. 导入自定义模块 ======
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

# 从 FAIR 脚本中同时导入 计算函数 和 抽样函数
from EW_FAIR_only_efficiency_fast import run_fair_for_EW_only_efficiency, get_stratified_sample_indices

# 导入栅格计算函数
from EW_compute_only_efficiency_fast import build_EW_climate_benefit_rasters


# ====== 主控函数 ======
def compute_climate_benefit_workflow(
        EW_eff_basalt_2,
        EW_eff_basalt_10,
        EW_eff_basalt_20,
        EW_eff_basalt_50,
        EW_eff_dunite_2,
        EW_eff_dunite_10,
        EW_eff_dunite_20,
        EW_eff_dunite_50,
        scenario_sample,
        rffsp_co2_emissions,
        tcr,
        ecs,
        grain_size,
        rock_type,
        PH_array,
        soil_temperature_array,
        EW_land_array,
        start_year,
        end_year,
        selected_indices,  # 接收生成的50个索引
        psd_dict,
        scenario="TimeVarying_CES",
        pathway=1,
        trade=False,
        uncertainty=False
):
    """
    全流程串联：FAIR -> Howard(R) -> Raster Mapping
    """

    # === Step 1. 运行 FAIR 模拟 (Python) ===
    print("\n" + "=" * 50)
    print(f"[STEP 1] Running FAIR Model for year {start_year}...")
    print("=" * 50)

    run_fair_for_EW_only_efficiency(
        EW_eff_basalt_2=EW_eff_basalt_2,
        EW_eff_basalt_10=EW_eff_basalt_10,
        EW_eff_basalt_20=EW_eff_basalt_20,
        EW_eff_basalt_50=EW_eff_basalt_50,
        EW_eff_dunite_2=EW_eff_dunite_2,
        EW_eff_dunite_10=EW_eff_dunite_10,
        EW_eff_dunite_20=EW_eff_dunite_20,
        EW_eff_dunite_50=EW_eff_dunite_50,
        scenario_sample=scenario_sample,
        rffsp_co2_emissions=rffsp_co2_emissions,
        tcr=tcr,
        ecs=ecs,
        PH_array=PH_array,
        soil_temperature_array=soil_temperature_array,
        EW_land_array=EW_land_array,
        start_year=start_year,
        end_year=end_year,
        selected_indices=selected_indices,  # 传入计算好的索引
        psd_dict=psd_dict,
        trade=trade
    )
    print("[INFO] FAIR simulation completed.")

    # === Step 2. 运行 Howard 损害模型 (Rscript) ===
    print("\n" + "=" * 50)
    print(f"[STEP 2] Running Howard Damage Model (R) for year {start_year}...")
    print("=" * 50)

    # Rscript 路径 (根据实际情况修改)
    r_exe = r"C:\PROGRA~1\R\R-44~1.2\bin\x64\Rscript.exe"
    r_script_path = r"E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/EW_Howard_only_efficiency.R"
    r_cwd = r"E:/wzy/3-Climate-Benefit"  # R代码运行的根目录

    try:
        subprocess.run([r_exe, r_script_path], check=True, cwd=r_cwd)
        print("[INFO] Howard R script executed successfully.")
    except Exception as e:
        print(f"[ERROR] R script execution failed: {e}")
        sys.exit(1)

    # === Step 3. 构造气候效益栅格 (Python) ===
    print("\n" + "=" * 50)
    print(f"[STEP 3] Mapping Climate Benefit Raster for year {start_year}...")
    print("=" * 50)

    result = build_EW_climate_benefit_rasters(
        EW_eff_basalt_2=EW_eff_basalt_2,
        EW_eff_basalt_10=EW_eff_basalt_10,
        EW_eff_basalt_20=EW_eff_basalt_20,
        EW_eff_basalt_50=EW_eff_basalt_50,
        EW_eff_dunite_2=EW_eff_dunite_2,
        EW_eff_dunite_10=EW_eff_dunite_10,
        EW_eff_dunite_20=EW_eff_dunite_20,
        EW_eff_dunite_50=EW_eff_dunite_50,
        grain_size=grain_size,
        rock_type=rock_type,
        PH_array=PH_array,
        soil_temperature_array=soil_temperature_array,
        EW_land_array=EW_land_array,
        start_year=start_year,
        scenario=scenario,
        pathway=pathway,
        trade=trade,
        uncertainty=uncertainty
    )

    print("[INFO] All processes finished successfully.")
    return result


# ====== 程序入口 ======
if __name__ == '__main__':

    # 1. 参数配置
    scenario = 'TimeVarying_CES'
    pathway = 1
    trade = False
    uncertainty = False
    start_year = 2025
    end_year = 2200

    print(f"Workflow Config: Year={start_year}-{end_year}, Trade={trade}, Uncertainty={uncertainty}")

    # 2. 加载数据
    print("Loading datasets...")
    # 路径根据你的环境保持不变
    base_monet = 'E:/wzy/2-Grid-based-MONET'
    base_cb = 'E:/wzy/3-Climate-Benefit/Climate_Benefit'

    ecs_ar5_sample = pd.read_csv(f'{base_cb}/Sample/ecs_sample.csv')["x"]
    scenario_sample = pd.read_csv(f'{base_cb}/Sample/climate_scenario_sample.csv')["x"]
    rffsp_co2_emissions = pd.read_csv(f'{base_cb}/rffsps_v5/emissions/rffsp_co2_emissions.csv')

    ecs = np.array(ecs_ar5_sample)
    rwf = truncnorm.rvs(-3, 3, loc=0.6, scale=0.1, size=10000, random_state=301)
    tcr = rwf * ecs

    print("Performing stratified sampling...")
    selected_indices = get_stratified_sample_indices(ecs_ar5_sample, 50)
    print(f"Sample indices generated: {selected_indices[:5]} ...")

    # 3. 动态生成粒径分布字典
    print("Generating PSD Dictionary...")
    grain_size_distribution_file_path = r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
    spec_psd = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
    grain_size_distribution_py = importlib.util.module_from_spec(spec_psd)
    spec_psd.loader.exec_module(grain_size_distribution_py)

    psd_dict = grain_size_distribution_py.generate_psd_for_multiple_p80(
        sigma=0.5,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
        plot=False,
        uncertainty=False
    )

    # 4. 加载栅格数据
    def read_raster(p):
        ds = gdal.Open(p)
        if not ds: raise FileNotFoundError(p)
        return ds.ReadAsArray()

    # 效率图路径
    eff_dir = f'{base_monet}/Output/EW/Global/Removal Efficiency/{start_year}'

    # 读取后立即保留2位小数
    EW_eff_dunite_2 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_dunite_2 μm.tif'), 2)
    EW_eff_dunite_10 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_dunite_10 μm.tif'), 2)
    EW_eff_dunite_20 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_dunite_20 μm.tif'), 2)
    EW_eff_dunite_50 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_dunite_50 μm.tif'), 2)

    EW_eff_basalt_2 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_basalt_2 μm.tif'), 2)
    EW_eff_basalt_10 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_basalt_10 μm.tif'), 2)
    EW_eff_basalt_20 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_basalt_20 μm.tif'), 2)
    EW_eff_basalt_50 = np.round(read_raster(f'{eff_dir}/EW_removal_efficiency_raster_basalt_50 μm.tif'), 2)

    # 环境数据
    # PH 和 温度 也立即保留2位小数
    PH_array = np.round(read_raster('E:/ArcGIS/Projects/GetData/T_PH_H20.tif'), 2)
    soil_temperature_array = np.round(read_raster(
        'E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif'), 2)

    # 土地利用和电力因子
    EW_land_array = read_raster(f'{base_monet}/Global Data/EW/Input/Global/Global cropland map.tif')
    EEF_array = read_raster('E:/ArcGIS/Projects/Country/UNFCCC_Electricity_Factor.tif')

    # 元数据
    grain_size = pd.read_csv(f'{base_monet}/Input Data/EW/Grain Size.csv', encoding='gbk')
    rock_type = pd.read_csv(f'{base_monet}/Input Data/EW/Rock Type.csv', encoding='gbk')

    # 5. 执行工作流
    compute_climate_benefit_workflow(
        EW_eff_basalt_2=EW_eff_basalt_2,
        EW_eff_basalt_10=EW_eff_basalt_10,
        EW_eff_basalt_20=EW_eff_basalt_20,
        EW_eff_basalt_50=EW_eff_basalt_50,
        EW_eff_dunite_2=EW_eff_dunite_2,
        EW_eff_dunite_10=EW_eff_dunite_10,
        EW_eff_dunite_20=EW_eff_dunite_20,
        EW_eff_dunite_50=EW_eff_dunite_50,
        scenario_sample=scenario_sample,
        rffsp_co2_emissions=rffsp_co2_emissions,
        tcr=tcr,
        ecs=ecs,
        grain_size=grain_size,
        rock_type=rock_type,
        PH_array=PH_array,
        soil_temperature_array=soil_temperature_array,
        EW_land_array=EW_land_array,
        start_year=start_year,
        end_year=end_year,
        selected_indices=selected_indices,  # 传入上面生成的索引
        psd_dict=psd_dict,
        scenario=scenario,
        pathway=pathway,
        trade=trade,
        uncertainty=uncertainty
    )
