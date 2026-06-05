# 本程序用于确定参数下的计算（考虑贸易，路径1）
# 写成调用函数的形式，可以一次性运行所有代码

import os
import pandas as pd
import numpy as np
from osgeo import gdal, osr
import sys
import matplotlib.pyplot as plt
import importlib.util
from multiprocessing import Pool
from scipy.stats import truncnorm

# ==== 1. 导入各函数 ====
# 函数1：计算粒径分布
grain_size_distribution_file_path = r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
spec_1 = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
grain_size_distribution_py = importlib.util.module_from_spec(spec_1)
spec_1.loader.exec_module(grain_size_distribution_py)
# 函数2：计算到目标年份的碳封存潜力
carbon_sequestration_file_path = r"E:/wzy/1-CDR-Base/EW/ERW_Core_Model.py"
spec_2 = importlib.util.spec_from_file_location("carbon_sequestration", carbon_sequestration_file_path)
carbon_sequestration_py = importlib.util.module_from_spec(spec_2)
spec_2.loader.exec_module(carbon_sequestration_py)
# 函数3：计算移除效率
removal_efficiency_file_path = r"E:/wzy/2-Grid-based-MONET/Code/EW/Global/5-Assessment/MONET-EW-Global-Removal Efficiency.py"
spec_3 = importlib.util.spec_from_file_location("removal_efficiency", removal_efficiency_file_path)
removal_efficiency_py = importlib.util.module_from_spec(spec_3)
spec_3.loader.exec_module(removal_efficiency_py)
# 函数4：计算碳移除潜力
removal_potential_file_path = r"E:/wzy/2-Grid-based-MONET/Code/EW/Global/5-Assessment/MONET-EW-Global-Potential.py"
spec_4 = importlib.util.spec_from_file_location("removal_potential", removal_potential_file_path)
removal_potential_py = importlib.util.module_from_spec(spec_4)
spec_4.loader.exec_module(removal_potential_py)
# 函数5：计算碳移成本
removal_cost_file_path = r"E:/wzy/2-Grid-based-MONET/Code/EW/Global/5-Assessment/MONET-EW-Global-Cost.py"
spec_5 = importlib.util.spec_from_file_location("removal_cost", removal_cost_file_path)
removal_cost_py = importlib.util.module_from_spec(spec_5)
spec_5.loader.exec_module(removal_cost_py)
# 函数6：计算气候效益
climate_benefit_file_path = r"E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/EW_main_only_efficiency.py"
spec_6 = importlib.util.spec_from_file_location("climate_benefit", climate_benefit_file_path)
climate_benefit_py = importlib.util.module_from_spec(spec_6)
spec_6.loader.exec_module(climate_benefit_py)
# 其他函数：分层抽样函数
fair_fast_path = r"E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/EW_FAIR_only_efficiency_fast.py"
spec_fair = importlib.util.spec_from_file_location("fair_fast", fair_fast_path)
fair_fast_py = importlib.util.module_from_spec(spec_fair)
spec_fair.loader.exec_module(fair_fast_py)
get_stratified_sample_indices = fair_fast_py.get_stratified_sample_indices

# ==== 2. 导入数据 ====
# 关键设置
uncertainty = False
scenario = 'TimeVarying_CES'
pathway = 1
trade = True
round_number = 2  # 保留2位小数

start_year = 2025
end_year = 2200
sample_num = 10000  # 气候效益的蒙卡模拟数

raster_row = 360
raster_col = 720

num_grain_sizes = 4
num_rock_types = 2

Grid_Cropland_Area_km2 = gdal.Open('E:/wzy/2-Grid-based-MONET/Global Data/EW/Input/Global/Global_cropland_area_km2.tif').ReadAsArray()  # 每个网格的耕地面积（km2）（0.5° 分辨率的网格面积不一定是为 55km x 55km，要提前根据经纬度换算，并且乘网格的耕地比例）
T_TO_GT = 1e-9  # 吨到千兆吨的转换系数

work_index = [17.93, 12.38]  # basalt=17.93, dunite=12.38
F_80 = 1000  # μm

# read electricity emission factors (from ArcGISPro)
EEF_array = gdal.Open('E:/ArcGIS/Projects/Country/UNFCCC_Electricity_Factor.tif').ReadAsArray()  # 0.5°*0.5°; unit: gCO2eq/kWh; /3600 (kgCO2e/MJ)
# land available for EW
EW_land_array = gdal.Open('E:/wzy/2-Grid-based-MONET/Global Data/EW/Input/Global/Global cropland map.tif').ReadAsArray()
# 国家代码，大于等于0
country_code_array = gdal.Open('E:/ArcGIS/Projects/Country/Country_code.tif').ReadAsArray()

# read specific EW data
EW_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/EW/EW.csv', encoding='gbk')
# read common data
Energy_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/Common Data/Energy.csv')  # parameters about energy
Carbon_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/Common Data/Carbon.csv', encoding='gbk')  # parameters about carbon
# read input data by myself
grain_size = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Grain Size.csv', encoding='gbk')  # grain size settings
# read rock type
rock_type = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Rock Type.csv', encoding='gbk')  # rock type settings
# read other parameters
other_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Other Data.csv', encoding='gbk')  # other parameters
transport_mode = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/Common Data/Transport Mode.csv', encoding='gbk')
transport_cost = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/Common Data/Transport Mode Cost.csv', encoding='gbk')

PH = gdal.Open('E:/ArcGIS/Projects/GetData/T_PH_H20.tif')
PH_array = np.round(PH.ReadAsArray(), round_number)
soil_temperature = gdal.Open('E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif')
soil_temperature_array = np.round(soil_temperature.ReadAsArray(), round_number)

# 读入电气化参数
shares_path = r"E:/wzy/2-Grid-based-MONET/Global Data/Common Data/Output/IEA_NZE_2023update_transport_shares_world.csv"
shares_df = pd.read_csv(shares_path)
shares_by_year = {
    int(r["year"]): {
        "road_foss": float(r["road_share_fossil_liquids"]),
        "road_elec": float(r["road_share_electricity"]),
        "ship_foss": float(r["shipping_share_fossil"]),
    }
    for _, r in shares_df.iterrows()
}

# 与计算气候效益有关的输入
ecs_ar5_sample = pd.read_csv('E:/wzy/3-Climate-Benefit/Climate_Benefit/Sample/ecs_sample.csv')  # 气候敏感性参数：FaIR通常需要代表地球气候敏感性的参数，包括平衡气候敏感性（ECS）和瞬态气候响应（TCR）。ECS是大气中CO2浓度翻倍导致的长期温度升高，而TCR是CO2逐渐增加引起的短期温度响应。
ecs_ar5_sample = ecs_ar5_sample["x"]

scenario_sample = pd.read_csv('E:/wzy/3-Climate-Benefit/Climate_Benefit/Sample/climate_scenario_sample.csv')
scenario_sample = scenario_sample["x"]

ecs = np.array(ecs_ar5_sample)  # ECS
rwf = truncnorm.rvs(-3, 3, loc=0.6, scale=0.1, size=10000, random_state=301)  # 截断于-3,3,期望为loc,标准差为scale,size参数指定输出的数组大小
tcr = rwf*ecs  # TCR

rffsp_co2_emissions = pd.read_csv("E:/wzy/3-Climate-Benefit/Climate_Benefit/rffsps_v5/emissions/rffsp_co2_emissions.csv")  # 气体的预计全球年排放量

# 计算分层抽样的索引 (用于 FAIR 和 R 代码的对应)
print("Generating stratified sample indices...")
selected_indices = get_stratified_sample_indices(ecs_ar5_sample, 50)
print(f"Sample indices generated: {selected_indices[:5]} ...")

# read cost data
# diesel cost
diesel_cost_array = gdal.Open('E:/ArcGIS/Projects/Country/Diesel_Cost_Raster.tif').ReadAsArray()  # $/l
# electricity price
electricity_price_array = gdal.Open('E:/ArcGIS/Projects/Country/Electricity_Price_Raster.tif').ReadAsArray()  # $/MWh; /3600 ($/MJ)
rock_price_array = gdal.Open('E:/ArcGIS/Projects/Country/Rock_Price.tif').ReadAsArray()  # $/t rock
hourly_compensation_costs_array = gdal.Open('E:/ArcGIS/Projects/Country/GNI_Raster.tif').ReadAsArray()  # %, USA: 1

# ==== 3. 设定参数不确定性范围以及蒙特卡洛模拟参数 ====
param = {
    'sigma': 0.5,
    'k_H_dunite': 5.55e-8,
    'n_H_dunite': 0.372,
    'k_H_basalt': 558,
    'n_H_basalt': 1.16,
    'k_OH_basalt': 0.0822,
    'n_OH_basalt': 0.16,
    'E_a': 47500,
    'b': 5.2,
    'm': -1.0,
    'mining_diesel': 4.17,
    'crushing_electricity': 3.25,
    'road_transport_diesel': 0.1146,
    'rail_transport_diesel': 0.0177,
    'ship_transport_HFO': 0.0303,
    'rock_application_diesel': 4.92,
    'road_transport_price': 0.06,
    'rail_transport_price': 0.03,
    'ship_transport_price': 0.0012,
    'rock_application_price': 23.383
}

# ==== 4. 按步骤使用函数计算 ====
# ==== 步骤：生成粒径分布，计算到2200年的碳封存潜力、计算移除效率、碳移除潜力、碳移除成本 ====
# --- Step 1: 生成粒径分布 (返回字典) ---
print("[Step 1] Generating PSD Dictionary...")
psd_dict =grain_size_distribution_py.generate_psd_for_multiple_p80(
    sigma=param['sigma'],
    save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
    plot=False,
    uncertainty=uncertainty
)

# --- Step 2: 计算碳封存潜力 (返回字典) ---
print("[Step 2] Calculating Carbon Sequestration Potential...")
pot_results = carbon_sequestration_py.carbon_sequestration_potential(
    EW_raw_data=EW_data,
    grain_size=grain_size,
    PH_array=PH_array,
    soil_temperature_array=soil_temperature_array,
    start_year=2025,
    end_year=2200,
    simulated_year=200,
    k_H_dunite=param['k_H_dunite'],
    n_H_dunite=param['n_H_dunite'],
    k_H_basalt=param['k_H_basalt'],
    n_H_basalt=param['n_H_basalt'],
    k_OH_basalt=param['k_OH_basalt'],
    n_OH_basalt=param['n_OH_basalt'],
    E_a=param['E_a'],
    b=param['b'],
    m=param['m'],
    raster_row=raster_row,
    raster_col=raster_col,
    pathway=pathway,
    grain_size_psd_dict=psd_dict,
    output_folder="E:/wzy/1-CDR-Base/EW/Output/Raster Data/",
    uncertainty=uncertainty
)

# --- 中间步骤: 数据重组 (CSV Columns -> Dict Keys) ---
# 将 pot_results 转换为下游函数需要的格式 {(rock, size): 1D_Array}
print("[Info] Restructuring potential data for downstream steps...")
seq_dict_input = {}
rate_dict_input = {}
sizes = [2, 10, 20, 50]

# Dunite (列 0-3)
for i, size in enumerate(sizes):
    key_suffix = f"{size}μm" if pathway == 1 else f"{size}μm_1"
    seq_dict_input[('dunite', key_suffix)] = pot_results["CO2_seq_potential_dunite_csv"][:, i]
    rate_dict_input[('dunite', key_suffix)] = pot_results["weathering_rate_dunite_csv"][:, i]

# Basalt (列 0-3)
for i, size in enumerate(sizes):
    key_suffix = f"{size}μm" if pathway == 1 else f"{size}μm_1"
    seq_dict_input[('basalt', key_suffix)] = pot_results["CO2_seq_potential_basalt_csv"][:, i]
    rate_dict_input[('basalt', key_suffix)] = pot_results["weathering_rate_basalt_csv"][:, i]

# --- Step 3: 计算移除效率 (返回字典) ---
print("[Step 3] Calculating Removal Efficiency...")
eff_results = removal_efficiency_py.compute_removal_efficiency(
    start_year,
    shares_by_year,
    EEF_array,
    EW_land_array,
    country_code_array,
    raster_row,
    raster_col,
    rock_type,
    grain_size,
    EW_data,
    Energy_data,
    Carbon_data,
    transport_mode,
    other_data,
    work_index,
    F_80,
    mining_diesel=param['mining_diesel'],
    crushing_electricity=param['crushing_electricity'],
    road_transport_diesel=param['road_transport_diesel'],
    rail_transport_diesel=param['rail_transport_diesel'],
    ship_transport_HFO=param['ship_transport_HFO'],
    rock_application_diesel=param['rock_application_diesel'],
    CO2_seq_potential_dict=seq_dict_input,
    weathering_rate_dict=rate_dict_input,
    pathway=pathway,
    uncertainty=uncertainty,
    trade=trade
)

# --- Step 4: 计算碳移除潜力 (返回字典) ---
print("[Step 4] Calculating Removal Potential...")
rem_results = removal_potential_py.compute_removal_potential(
    start_year,
    shares_by_year,
    EEF_array,
    EW_land_array,
    country_code_array,
    raster_row,
    raster_col,
    rock_type,
    grain_size,
    EW_data,
    Energy_data,
    Carbon_data,
    transport_mode,
    other_data,
    Grid_Cropland_Area_km2,
    T_TO_GT,
    work_index,
    F_80,
    mining_diesel=param['mining_diesel'],
    crushing_electricity=param['crushing_electricity'],
    road_transport_diesel=param['road_transport_diesel'],
    rail_transport_diesel=param['rail_transport_diesel'],
    ship_transport_HFO=param['ship_transport_HFO'],
    rock_application_diesel=param['rock_application_diesel'],
    CO2_seq_potential_dict=seq_dict_input,
    pathway=pathway,
    uncertainty=uncertainty,
    trade=trade
)

# --- Step 5: 计算碳移除成本 (返回字典) ---
print("[Step 5] Calculating Removal Cost...")
cost_results = removal_cost_py.compute_removal_cost(
    start_year,
    shares_by_year,
    EEF_array,
    EW_land_array,
    country_code_array,
    hourly_compensation_costs_array,
    raster_row,
    raster_col,
    rock_type,
    grain_size,
    EW_data,
    Energy_data,
    Carbon_data,
    transport_mode,
    other_data,
    work_index,
    F_80,
    diesel_cost_array,
    electricity_price_array,
    rock_price_array,
    mining_diesel=param['mining_diesel'],
    crushing_electricity=param['crushing_electricity'],
    road_transport_diesel=param['road_transport_diesel'],
    rail_transport_diesel=param['rail_transport_diesel'],
    ship_transport_HFO=param['ship_transport_HFO'],
    rock_application_diesel=param['rock_application_diesel'],
    road_transport_price=param['road_transport_price'],
    rail_transport_price=param['rail_transport_price'],
    ship_transport_price=param['ship_transport_price'],
    rock_application_price=param['rock_application_price'],
    CO2_seq_potential_dict=seq_dict_input,
    pathway=pathway,
    uncertainty=uncertainty,
    trade=trade
)

# --- Step 6: 计算气候效益 (FAIR -> R -> Mapping) ---
print("[Step 6] Calculating Climate Benefit (Workflow)...")

# 提取效率数据用于 Step 6 (从 eff_results 字典中提取列并 reshape)
eff_csv = eff_results['EW_removal_efficiency_csv']  # Shape (N, 8)
# 列顺序假设为: Basalt(2,10,20,50) + Dunite(2,10,20,50)
# 注意：需要确认 compute_removal_efficiency 中 r 的循环顺序。
# 原代码中 r=0 是 rock_type.iloc[0,0]，通常是 Basalt。r=1 是 Dunite。
# 所以顺序是 Basalt(0-3), Dunite(4-7)。

def get_eff_layer(col_idx):
    return eff_csv[:, col_idx].reshape(raster_row, raster_col)

EW_eff_basalt_2 = get_eff_layer(0)
EW_eff_basalt_10 = get_eff_layer(1)
EW_eff_basalt_20 = get_eff_layer(2)
EW_eff_basalt_50 = get_eff_layer(3)

EW_eff_dunite_2 = get_eff_layer(4)
EW_eff_dunite_10 = get_eff_layer(5)
EW_eff_dunite_20 = get_eff_layer(6)
EW_eff_dunite_50 = get_eff_layer(7)

climate_benefit_py.compute_climate_benefit_workflow(
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
    selected_indices=selected_indices,  # 传入50个索引
    psd_dict=psd_dict,
    scenario=scenario,  # "TimeVarying_CES"
    pathway=pathway,
    trade=trade,
    uncertainty=uncertainty
)

print("[SUCCESS] All steps completed.")
