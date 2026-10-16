# 本程序用于潜力结果分析：
# 情景：不允许贸易时最大化净效益
# 单年铺洒的全球叠加潜力曲线

import os
import sys
import pandas as pd
import numpy as np
from osgeo import gdal
import matplotlib.pyplot as plt
import importlib.util

# =============================================================================
# 1. 设置路径与导入核心模型
# =============================================================================
model_path = 'E:/wzy/1-CDR-Base/EW'
if model_path not in sys.path:
    sys.path.append(model_path)
import ERW_Core_Model

# =============================================================================
# 2. 参数设置
# =============================================================================
trade = False  # 是否考虑贸易
maxcb = True  # 是否最大化气候净效益
start_year = 2025  # 起始年份
end_year = 2200  # 结束年份

raster_row = 360
raster_col = 720
N_YEARS = end_year - start_year + 1  # 模拟时长
T_TO_GT = 1e-9  # 吨 -> Gt

# 定义物理/动力学参数字典 (与 ERW_Core_Model 中一致)
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

# =============================================================================
# 3. 数据读取与初始化
# =============================================================================
print("正在读取基础数据...")

# (1) 读取 PSD 字典 (粒径分布)
# 必须生成 psd_dict 才能传递给 get_annual_rate_curve
grain_size_distribution_file_path = r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
if os.path.exists(grain_size_distribution_file_path):
    spec_psd = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
    grain_size_distribution_py = importlib.util.module_from_spec(spec_psd)
    spec_psd.loader.exec_module(grain_size_distribution_py)

    # 生成 psd_dict
    psd_dict = grain_size_distribution_py.generate_psd_for_multiple_p80(
        sigma=0.5,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',  # 临时或实际输出目录
        plot=False,
        uncertainty=False
    )
else:
    raise FileNotFoundError(f"找不到粒径生成脚本: {grain_size_distribution_file_path}")

# (2) 读取栅格数据
Grid_Cropland_Area_km2 = gdal.Open('E:/wzy/2-Grid-based-MONET/Global Data/EW/Input/Global/Global_cropland_area_km2.tif').ReadAsArray()

PH = gdal.Open('E:/ArcGIS/Projects/GetData/T_PH_H20.tif')
PH_array = np.round(PH.ReadAsArray(), 2)

soil_temperature = gdal.Open('E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif')
soil_temperature_array = np.round(soil_temperature.ReadAsArray(), 2)

EW_raw_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/EW/EW.csv', encoding='gbk')

# (3) 读取场景数据 (技术选择地图)
if maxcb:
    folder = "maxclimatebenefit_withtrade" if trade else "maxclimatebenefit_notrade"
    prefix = "max_net_benefit"
else:
    folder = "mincost_withtrade" if trade else "mincost_notrade"
    prefix = "min_cost"

suffix_file = " (with trade)" if trade else ""
scenario_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/{start_year}/{folder}/EW_{prefix}_scenario_raster{suffix_file}.tif'
EW_scenario_array = gdal.Open(scenario_path).ReadAsArray()

# (4) 读取排放数据 (用于扣除第一年)
emission_arrays = {}
sizes = [2, 10, 20, 50]
for size in sizes:
    path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_total_emission_raster_Basalt_{size} μm{suffix_file}.tif'
    emission_arrays[size] = gdal.Open(path).ReadAsArray()

# =============================================================================
# 4. 主循环：计算全球叠加曲线
# =============================================================================
print("开始计算全球潜力叠加曲线...")
global_CO2_seq_curve = np.zeros(N_YEARS)

# 映射 Tech ID 到 p80 粒径
tech_id_map = {1: 2, 2: 10, 3: 20, 4: 50}

# 定义系数常量，避免循环内重复查找 dataframe
coeff_rock_purity = EW_raw_data.iloc[28, 2]  # Basalt purity?
coeff_r_max = EW_raw_data.iloc[26, 2]  # R_max (tCO2/tRock)?
coeff_app_rate = EW_raw_data.iloc[15, 2]  # Application Rate (t/ha)?

# 遍历网格
for row in range(raster_row):
    for col in range(raster_col):
        tech_id = EW_scenario_array[row, col]

        # 判断有效像元 (Tech ID 为 1, 2, 3, 4)
        if tech_id in [1, 2, 3, 4]:
            PH_val = PH_array[row, col]
            T_val = soil_temperature_array[row, col]
            p80_val = tech_id_map[tech_id]

            # --- 核心调用：从 ERW_Core_Model 获取风化速率曲线 ---
            # 返回的是 shape=(N_YEARS,) 的 numpy array，表示每年的风化比例增量
            annual_rate_curve = ERW_Core_Model.get_annual_rate_curve(
                rock_type='Basalt',
                pH_scalar=PH_val,
                temp_scalar=T_val,
                grain_size_psd_dict=psd_dict,  # 传入字典
                p80=p80_val,  # 传入目标粒径
                simulated_year=N_YEARS,
                params_dict=params_dict
            )

            # 计算该网格每年的 CO2 封存潜力 (GtCO2/yr)
            # 公式: 纯度 * R_max * 风化率曲线 * 施用率(t/ha) * 面积(km2->ha) * 转换系数
            # Grid_Cropland_Area_km2 单位是 km2，乘 100 转为公顷 (ha)
            grid_potential_curve = (
                    coeff_rock_purity * coeff_r_max * annual_rate_curve * coeff_app_rate * (
                        Grid_Cropland_Area_km2[row, col] * 100) * (T_TO_GT / 1000)  # 注意原代码里有一个除以1000，可能是单位调整
            )

            # 扣除生命周期排放 (仅在第一年扣除)
            # Emission raster 单位可能是 kg 或 t，需统一转为 Gt
            # 原代码逻辑: emission_val / 1000 * app_rate * area_ha * T_TO_GT
            emission_val = emission_arrays[p80_val][row, col]
            first_year_emission_gt = (
                    (emission_val / 1000) * coeff_app_rate * (Grid_Cropland_Area_km2[row, col] * 100) * T_TO_GT
            )

            grid_potential_curve[0] -= first_year_emission_gt

            # 累加到全球曲线
            global_CO2_seq_curve += grid_potential_curve

# =============================================================================
# 5. 绘图与保存
# =============================================================================
print("计算完成，正在绘图...")

years = np.arange(start_year, start_year + N_YEARS)

plt.figure(figsize=(8, 6))
plt.plot(years, global_CO2_seq_curve, color='green', linewidth=2)
plt.xlabel("Year", fontsize=15)
plt.ylabel("Annual Net Removal Potential (GtCO₂/yr)", fontsize=15)
plt.tick_params(axis='both', which='major', labelsize=14)
# plt.title(f"Global Annual Net CDR Potential ({start_year}-{end_year})", fontsize=14)
plt.grid(False)
ax = plt.gca()
ax.spines['right'].set_visible(False)
ax.spines['top'].set_visible(False)
plt.tight_layout()
plt.show()

# 保存结果
df_curve = pd.DataFrame({
    "Year": years,
    "Global_CDR_Potential_GtCO2": global_CO2_seq_curve
})

out_dir = f"E:/wzy/2-Grid-based-MONET/Output/EW/Global/Scenario 3/{start_year}/{folder}"
if not os.path.exists(out_dir):
    os.makedirs(out_dir)

save_path = os.path.join(out_dir, "Global_Annual_ERW_CDR_Potential.csv")
df_curve.to_csv(save_path, index=False)
print(f"数据已保存至: {save_path}")
