# 计算每年铺洒 20 t rock/ha，直到达到 150 t rock/ha 的上限停止铺洒，然后计算年平均风化速率
# 潜力：tCO2 rem 或 tCO2 cap （每个网格的tCO2 rem/ha * ha）

import os
import pandas as pd
import numpy as np
from osgeo import gdal, osr
import sys
import matplotlib.pyplot as plt
import importlib.util

model_path = 'C:/wzy/1-CDR-Base/EW'
if model_path not in sys.path:
    sys.path.append(model_path)
import ERW_Core_Model

os.chdir('C:/wzy/2-Grid-based-MONET')

round_number = 2  # 保留2位小数

# 定义物理参数字典 (必须与模型中的一致)
params_dict = {
    "k_H_dunite": 5.55e-8,
    "n_H_dunite": 0.372,
    "k_H_basalt": 588,
    "n_H_basalt": 1.16,
    "k_OH_basalt": 0.0822,
    "n_OH_basalt": 0.16,
    "E_a": 47500,
    "b": 5.2,
    "m": -1
}

def save_raster(output_path, array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32, nodata=None):
    """
    轻量通用的GeoTIFF保存函数。
    - output_path: 输出tif路径
    - array: 2D numpy数组
    - geotransform: (originX, pixelWidth, 0, originY, 0, -pixelHeight)
    - epsg: 坐标参考系EPSG，默认4326
    - dtype: gdal数据类型，默认Float32
    - nodata: 可选NoData值
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rows, cols = array.shape
    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(output_path, xsize=cols, ysize=rows, bands=1, eType=dtype)
    ds.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())
    band = ds.GetRasterBand(1)
    if nodata is not None:
        band.SetNoDataValue(nodata)
    band.WriteArray(array)
    band.FlushCache()
    band = None
    ds = None

# =============================================================================
# 1. 导入粒径分布生成函数并获取字典
# =============================================================================
print("[INFO] Loading Grain Size Generation Module...")
grain_size_distribution_file_path = r"C:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
spec_psd = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
grain_size_distribution_py = importlib.util.module_from_spec(spec_psd)
spec_psd.loader.exec_module(grain_size_distribution_py)

print("[INFO] Generating PSD Dictionary...")
# 调用函数获取 psd_dict，sigma 设定为默认的 0.5 (根据之前代码推断)
psd_dict = grain_size_distribution_py.generate_psd_for_multiple_p80(
    sigma=0.5,
    save_folder='C:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
    plot=False,
    uncertainty=False
)

# =============================================================================
# 2. 读取数据
# =============================================================================

# read electricity emission factors (from ArcGISPro)
EEF = gdal.Open('C:/Users/WangZeyu/Documents/ArcGIS/Projects/Country/UNFCCC_Electricity_Factor.tif')  # 0.5°*0.5°; unit: gCO2eq/kWh; /3600 (kgCO2e/MJ)
EEF_array = EEF.ReadAsArray()  # turn tif to array
np.set_printoptions(threshold=sys.maxsize)

# PH data
PH = gdal.Open('C:/Users/WangZeyu/Documents/ArcGIS/Projects/GetData/T_PH_H20.tif')  # 360*720
PH_array = np.round(PH.ReadAsArray(), round_number)  # turn tif to array
# Soil temperature
soil_temperature = gdal.Open('C:/Users/WangZeyu/Documents/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif')  # 360*720
soil_temperature_array = np.round(soil_temperature.ReadAsArray(), round_number)  # turn tif to array
# land available for EW
EW_land_array = gdal.Open('./Global Data/EW/Input/Global/Global cropland map.tif').ReadAsArray()

# 国家代码，大于等于0
country_code_array = gdal.Open('C:/Users/WangZeyu/Documents/ArcGIS/Projects/Country/Country_code.tif').ReadAsArray()

# raster's row and col depend on EEF_array
raster_row = 360
raster_col = 720

# read specific EW data
EW_data = pd.read_csv('Raw Data/EW/EW.csv', encoding='gbk')
# read common data
Energy_data = pd.read_csv('Raw Data/Common Data/Energy.csv')  # parameters about energy
Carbon_data = pd.read_csv('Raw Data/Common Data/Carbon.csv', encoding='gbk')  # parameters about carbon
# read input data by myself
grain_size = pd.read_csv('Input Data/EW/Grain Size.csv', encoding='gbk')  # grain size settings
# read rock type
rock_type = pd.read_csv('Input Data/EW/Rock Type.csv', encoding='gbk')  # rock type settings
# read other parameters
other_data = pd.read_csv('Input Data/EW/Other Data.csv', encoding='gbk')  # other parameters
transport_mode = pd.read_csv('Raw Data/Common Data/Transport Mode.csv', encoding='gbk')

# grain sizes and rock type number
num_of_grain_size = len(grain_size)  # grain size: 2, 10, 20, 50μm （ From: Strefler, J., Amann, T., Bauer, N., Kriegler, E., & Hartmann, J. (2018). Potential and costs of carbon dioxide removal by enhanced weathering of rocks. Environmental Research Letters, 13.)
num_of_type = len(rock_type)  # rock type: basalt, dunite

# construct carbon emissions structure of EW in MONET, as well as output we want to get, tCO2e/t rock
EW_emission_structure = pd.DataFrame(columns=['Direct CO2 emissions from the combustion of fuels (diesel) for rocks mining/extraction, transport, and application on soil, and natural gas and/or wood for drying biomass (tCO2e/t rock)',
                                              'Indirect CO2 emissions due to the production of these fuels (diesel), and the generation of electricity for rocks crushing and grinding (tCO2e/t rock)',
                                              'Indirect CO2 emissions due to the manufacture of materials, i.e., ammonium nitrate-based explosives (tCO2e/t rock)'],
                                     index=['Mining',
                                            'Crushing & Grinding',
                                            'Transport',
                                            'Application on Soil'])
# construct total carbon emission structure of EW, tCO2e/t rock
EW_total_emission_structure = pd.DataFrame(columns=['Region', 'Mining (tCO2e/t rock)', 'Crushing & Grinding (tCO2e/t rock)',
                                                    'Transport (tCO2e/t rock)', 'Application on Soil (tCO2e/t rock)',
                                                    'Total emissions (tCO2e/t rock)'],
                                           index=range(1))  # 500 is a large number for five regions' sub-regions

# construct potential raster data (GtCO2 rem/yr)
EW_potential_raster_array_rock_rem = np.full((raster_row, raster_col), np.nan)
# 记录每个网格的累积潜力
EW_rem_potential_csv = np.full((360*720, 8), np.nan)

# settings
start_year = 2025
end_year = 2200

work_index = [17.93, 12.38]  # basalt=17.93, dunite=12.38
F_80 = 1000  # μm

# 定义常量
Grid_Cropland_Area_km2 = gdal.Open('./Global Data/EW/Input/Global/Global_cropland_area_km2.tif').ReadAsArray()  # 每个网格的农田面积（km2）（0.5° 分辨率的网格面积不一定是为 55km x 55km，要提前根据经纬度换算，并且乘网格的农田比例），后面用为公顷时需要*100
T_TO_GT = 1e-9  # 吨到千兆吨的转换系数

pathway = 1  # 1 or 2
trade = True  # False or True

ph_round = 2  # ph保留2位小数
temp_round = 2  # 温度保留2位小数

# =============================================================================
# 3. 主循环计算 (深度优化版)
# =============================================================================
print("[INFO] Starting Multi-year Calculation (Optimized)...")

# --- 优化1: 在循环外提取所有 Pandas 常量 (极大提升速度) ---
# 将 .iloc 读取转为 float 变量，避免在几十万次循环中反复查询 Pandas
val_mining_diesel_energy = EW_data.iloc[3, 2] / 1000 * 3600 / Energy_data.iloc[2, 2]  # MJ/t rock
val_carbon_diesel = Carbon_data.iloc[2, 2] / 1000
val_carbon_diesel_indirect = Carbon_data.iloc[14, 2] / 1000

# Mining & Crushing 常量部分
emission_mining_direct = val_mining_diesel_energy * val_carbon_diesel
emission_mining_indirect = val_mining_diesel_energy * val_carbon_diesel_indirect

# Explosives (Materials)
val_explosives = EW_data.iloc[9, 2] * EW_data.iloc[10, 2] * EW_data.iloc[24, 2] * (
        Carbon_data.iloc[26, 2] + (Carbon_data.iloc[46, 2] + Carbon_data.iloc[47, 2] * Carbon_data.iloc[48, 2] +
                                   Carbon_data.iloc[49, 2] * Carbon_data.iloc[50, 2]) * EW_data.iloc[23, 2] *
        other_data.iloc[0, 2]
) / 1000

# Application 常量部分
val_app_diesel_energy = EW_data.iloc[7, 2] / 1000 * 3600 / Energy_data.iloc[2, 2]
emission_app_direct = val_app_diesel_energy * val_carbon_diesel
emission_app_indirect = val_app_diesel_energy * val_carbon_diesel_indirect

# Crushing 变量系数 (提取出来)
crushing_base = EW_data.iloc[4, 2]
F_80_sqrt_inv = 1 / np.sqrt(F_80)

# Transport 变量系数
energy_road = Energy_data.iloc[18, 2] * transport_mode.iloc[0, 2] + Energy_data.iloc[19, 2] * transport_mode.iloc[1, 2]
energy_rail = Energy_data.iloc[20, 2] * transport_mode.iloc[2, 2]
carbon_road_direct = Carbon_data.iloc[2, 2]
carbon_rail_direct = Carbon_data.iloc[7, 2]
carbon_road_indirect = Carbon_data.iloc[14, 2]
carbon_rail_indirect = Carbon_data.iloc[19, 2]
energy_diesel_val = Energy_data.iloc[2, 2]
energy_elect_val = Energy_data.iloc[6, 2]

# Multi-year constants
annual_spread_amount = EW_data.iloc[15, 2]  # 20 t
limit_amount = 150
seq_factor_path1 = EW_data.iloc[28, 2]
seq_factor_path2 = EW_data.iloc[29, 2]

# --- 预处理 Mask (避免无效循环) ---
# 找出所有需要计算的 (row, col) 索引
valid_mask = (country_code_array >= 0) & (EW_land_array > 0) & (EEF_array >= 0) & (PH_array > 0) & (
            soil_temperature_array > -256)
valid_rows, valid_cols = np.where(valid_mask)
print(f"[INFO] Valid pixels to process: {len(valid_rows)}")

for r in range(num_of_type):
    current_rock_type = rock_type.iloc[r, 0]
    # Rock specific factors
    val_rock_cao_path1 = EW_data.iloc[26 + r, 2]  # index 26 or 27 (Basalt/Dunite?) check index logic carefully
    # 注意：原代码中 basalt r=0 -> iloc[26], dunite r=1 -> iloc[27]?
    # 原代码写的是 EW_data.iloc[26 + r, 2]，请确保 csv 顺序一致

    print(f"Processing Rock: {current_rock_type}")

    for s in range(num_of_grain_size):
        current_p80 = int(grain_size.iloc[s, 0])
        print(f"  -> Grain Size P80: {current_p80} μm")

        # --- 优化2: 物理曲线缓存 (Dictionary Cache) ---
        # 只要 (pH, T) 相同，物理风化曲线就相同，不需要重复调用 ERW_Core_Model
        curve_cache = {}

        # 读取运输距离
        if trade:
            dist_path = f'./Global Data/EW/Output/Global/EW_global_transport_distance_{rock_type.iloc[r, 0]} (with trade).tif'
        else:
            dist_path = f'./Global Data/EW/Output/Global/EW_global_transport_distance_{rock_type.iloc[r, 0]}.tif'

        dist_array = gdal.Open(dist_path).ReadAsArray()

        # 重置结果数组
        EW_potential_raster_array_rock_rem.fill(np.nan)

        # 遍历有效像素 (Vectorized Loop)
        # 使用 zip 遍历预先筛选出的坐标，而不是两层大循环
        for i in range(len(valid_rows)):
            row, col = valid_rows[i], valid_cols[i]

            # 检查距离是否有效
            dist_val = dist_array[row, col]
            if np.isnan(dist_val):
                continue

            # 获取环境参数
            PH_val = PH_array[row, col]
            T_val = soil_temperature_array[row, col]
            EEF_val = EEF_array[row, col]

            # --- 核心优化: 查表获取风化曲线 ---
            curve_key = (PH_val, T_val)
            if curve_key in curve_cache:
                CO2_seq_potential_annual = curve_cache[curve_key]
            else:
                CO2_seq_potential_annual = ERW_Core_Model.get_annual_rate_curve(
                    rock_type=current_rock_type,
                    pH_scalar=PH_val,
                    temp_scalar=T_val,
                    grain_size_psd_dict=psd_dict,
                    p80=current_p80,
                    simulated_year=end_year - start_year + 50,
                    params_dict=params_dict
                )
                curve_cache[curve_key] = CO2_seq_potential_annual

            # --- 计算排放 (使用预提取的变量) ---
            # Crushing
            term_grain = (1 / np.sqrt(current_p80) - F_80_sqrt_inv)
            emission_crushing = (crushing_base + 10 * work_index[r] * term_grain) * EEF_val / 1000000

            # Transport
            trans_direct = ((energy_road * 3.6 / energy_diesel_val * carbon_road_direct) +
                            (energy_rail * 3.6 / energy_elect_val * carbon_rail_direct)) * dist_val / 1000

            trans_indirect = ((energy_road * 3.6 / energy_diesel_val * carbon_road_indirect) +
                              (energy_rail * 3.6 / energy_elect_val * carbon_rail_indirect)) * dist_val / 1000

            # Total Emission (tCO2e/t rock)
            # Sum of Mining + Crushing + Transport + Application
            # 注意：mining_indirect 包含了 explosives (row 0, col 2 in original df)
            total_emission_per_ton = (
                    (emission_mining_direct + emission_mining_indirect + val_explosives) +
                    emission_crushing +
                    (trans_direct + trans_indirect) +
                    (emission_app_direct + emission_app_indirect)
            )

            # --- 优化3: 多年铺洒模拟 (纯 Python 逻辑优化) ---
            num_years = end_year - start_year + 1

            # 初始化状态变量
            rock_volume = annual_spread_amount  # 第一年铺洒后的量
            potential_list = []  # 用于存储每年的净潜力

            # 第一年
            first_year_emission = total_emission_per_ton * annual_spread_amount
            # 第一年无风化收益(根据原逻辑 potential[0] = 0 - emission)，假设铺洒发生在年初或风化滞后
            # 原逻辑: potential[0] = 0 - emission
            potential_list.append(-first_year_emission)

            # 记录哪一年铺洒了 (用列表代替 numpy where)
            applied_years_indices = [0]  # 第0年铺洒了

            # 从第2年开始循环 (index=1)
            for yr in range(1, num_years):
                # 计算当年的总风化量 (Convolution)
                # weathering_volume[yr] += sum(20 * rate[yr - t]) for t in applied_years

                # 这是一个瓶颈，但比 np.where 快
                current_weathering = 0.0
                for t_idx in applied_years_indices:
                    # t_idx 是铺洒的那一年 (相对于 start_year 的 offset)
                    # decay_year = yr - t_idx
                    current_weathering += annual_spread_amount * CO2_seq_potential_annual[yr - t_idx]

                # 更新岩石存量
                # Logic: check if we can add more rock?
                # 原逻辑: if rock_volume[yr-1] - weathering_volume[yr] <= 150
                # 注意：原代码逻辑是先判断 "上一年的存量 - 本年风化量" 是否 < 150

                remaining_rock = rock_volume - current_weathering

                net_sequestration = 0.0
                if pathway == 1:
                    gross_seq = seq_factor_path1 * val_rock_cao_path1 * current_weathering / 1000
                else:
                    gross_seq = seq_factor_path2 * val_rock_cao_path1 * current_weathering / 1000

                if remaining_rock <= limit_amount:
                    # 可以铺洒
                    applied_years_indices.append(yr)
                    rock_volume = remaining_rock + annual_spread_amount  # 补充 20
                    # 净潜力 = 总封存 - 此次铺洒排放
                    net_sequestration = gross_seq - first_year_emission
                else:
                    # 停止铺洒
                    rock_volume = remaining_rock
                    net_sequestration = gross_seq  # 无排放

                potential_list.append(net_sequestration)

            # 计算平均年潜力
            avg_potential = sum(potential_list) / num_years

            if avg_potential > 0:
                # 单位换算: tCO2/ha -> GtCO2 (Grid Total)
                grid_total_gt = avg_potential * Grid_Cropland_Area_km2[row, col] * 100 * T_TO_GT
                EW_potential_raster_array_rock_rem[row, col] = grid_total_gt

                # 填入 CSV 缓存
                idx = row * raster_col + col
                EW_rem_potential_csv[idx, r * 4 + s] = grid_total_gt


        if pathway == 1:
            if trade:
                out_path = f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm (with trade).tif'
                save_raster(out_path, EW_potential_raster_array_rock_rem, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
            else:
                out_path = f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm.tif'
                save_raster(out_path, EW_potential_raster_array_rock_rem, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        if pathway == 2:
            if trade:
                out_path = f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm (with trade)_1.tif'
                save_raster(out_path, EW_potential_raster_array_rock_rem, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
            else:
                out_path = f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm_1.tif'
                save_raster(out_path, EW_potential_raster_array_rock_rem, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)


if pathway == 1:
    if trade:
        # 保存为csv文件
        EW_rem_potential_csv_df = pd.DataFrame(EW_rem_potential_csv)
        EW_rem_potential_csv_df.to_csv(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/Multi Year Removal Potential (with trade).csv')
    else:
        EW_rem_potential_csv_df = pd.DataFrame(EW_rem_potential_csv)
        EW_rem_potential_csv_df.to_csv(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/Multi Year Removal Potential.csv')
if pathway == 2:
    if trade:
        # 保存为csv文件
        EW_rem_potential_csv_df = pd.DataFrame(EW_rem_potential_csv)
        EW_rem_potential_csv_df.to_csv(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/Multi Year Removal Potential (with trade)_1.csv')
    else:
        EW_rem_potential_csv_df = pd.DataFrame(EW_rem_potential_csv)
        EW_rem_potential_csv_df.to_csv(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/Multi Year Removal Potential_1.csv')
print("[INFO] Calculation Finished.")
