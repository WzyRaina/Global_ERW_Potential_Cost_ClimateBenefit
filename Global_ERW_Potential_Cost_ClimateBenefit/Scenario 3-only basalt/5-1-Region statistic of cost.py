# 按区域、次区域计算加权平均成本 + 输出全球加权平均成本（不保存全球结果）

import os
import numpy as np
import pandas as pd
from osgeo import gdal

trade = False       # 是否考虑贸易
maxcb = True       # 是否最大化气候净效益（否则是最小成本）
start_year = 2025  # Primary scenario. Use grid_scope_summary.py for the multi-year Table S10 series.

# ==== 1. 基本路径 ====
os.chdir(r"E:/wzy/2-Grid-based-MONET")

if maxcb:
    if trade:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_maxnetbenefit_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit_raster (with trade).tif"

        output_csv_sub = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_by_region_subregion.csv"
        output_csv_reg = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_by_region.csv"
    else:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_maxnetbenefit_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit_raster.tif"

        output_csv_sub = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_by_region_subregion.csv"
        output_csv_reg = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_by_region.csv"
else:
    if trade:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost_raster (with trade).tif"

        output_csv_sub = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_cost_by_region_subregion.csv"
        output_csv_reg = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_cost_by_region.csv"
    else:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost_raster.tif"

        output_csv_sub = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_cost_by_region_subregion.csv"
        output_csv_reg = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_cost_by_region.csv"

region_path    = r"E:/ArcGIS/Projects/Country/Region.tif"
subregion_path = r"E:/ArcGIS/Projects/Country/Subregion.tif"

NODATA_VALUE = -9999.0

# ==== 2. 读取栅格 ====
cost_ds      = gdal.Open(cost_path)
potential_ds = gdal.Open(potential_path)
region_ds    = gdal.Open(region_path)
subregion_ds = gdal.Open(subregion_path)

if cost_ds is None or potential_ds is None or region_ds is None or subregion_ds is None:
    raise RuntimeError("成本/潜力/区域/次区域栅格读取失败，请检查路径。")

cost_arr      = cost_ds.ReadAsArray().astype(float)
potential_arr = potential_ds.ReadAsArray().astype(float)
region_arr    = region_ds.ReadAsArray().astype(int)
subregion_arr = subregion_ds.ReadAsArray().astype(int)

print("成本栅格 shape:", cost_arr.shape)
print("潜力栅格 shape:", potential_arr.shape)
print("Region 栅格 shape:", region_arr.shape)
print("Subregion 栅格 shape:", subregion_arr.shape)

if not (cost_arr.shape == potential_arr.shape == region_arr.shape == subregion_arr.shape):
    raise ValueError("成本、潜力、区域、次区域栅格的行列数不一致，请检查对齐。")

# ==== 3. 构造有效像元掩膜 ====
valid_mask = (
    np.isfinite(cost_arr) &
    np.isfinite(potential_arr) &
    (cost_arr != NODATA_VALUE) &
    (potential_arr != NODATA_VALUE) &
    (potential_arr > 0) &
    (region_arr > 0) &
    (subregion_arr > 0)
)

n_valid = int(np.sum(valid_mask))
print("有效像元数量：", n_valid)

# ==== 3.5 输出全球潜力加权平均成本（只输出，不保存） ====
pot_glb  = potential_arr[valid_mask]  # MtCO2
cost_glb = cost_arr[valid_mask]       # $/tCO2

total_potential_glb_mt = float(np.nansum(pot_glb))
if total_potential_glb_mt > 0:
    weighted_cost_glb = float(np.nansum(cost_glb * pot_glb) / total_potential_glb_mt)
else:
    weighted_cost_glb = np.nan

print("\n========== Global (Potential-weighted) ==========")
print(f"Global total potential: {total_potential_glb_mt:.6f} MtCO2  ({total_potential_glb_mt/1000.0:.6f} GtCO2)")
print(f"Global weighted average cost: {weighted_cost_glb:.6f} $/tCO2")
print("=================================================\n")

# ==== 4A. Region + Subregion：加权平均成本 + 总潜力 ====
rows_sub = []
unique_regions = np.unique(region_arr[valid_mask])

for reg_id in unique_regions:
    reg_mask = valid_mask & (region_arr == reg_id)
    unique_subregions = np.unique(subregion_arr[reg_mask])

    for sub_id in unique_subregions:
        sub_mask = reg_mask & (subregion_arr == sub_id)

        pot_sub  = potential_arr[sub_mask]
        cost_sub = cost_arr[sub_mask]

        total_potential_mt = float(np.nansum(pot_sub))
        if total_potential_mt > 0:
            weighted_cost = float(np.nansum(cost_sub * pot_sub) / total_potential_mt)
        else:
            weighted_cost = np.nan

        rows_sub.append({
            "Region_ID": int(reg_id),
            "Subregion_ID": int(sub_id),
            "Weighted_Cost_USD_per_tCO2": weighted_cost,
            "Total_Potential_MtCO2": total_potential_mt,
            "Total_Potential_GtCO2": total_potential_mt / 1000.0
        })

df_sub = pd.DataFrame(rows_sub).sort_values(["Region_ID", "Subregion_ID"]).reset_index(drop=True)
os.makedirs(os.path.dirname(output_csv_sub), exist_ok=True)
df_sub.to_csv(output_csv_sub, index=False, float_format="%.6f")
print("已保存次区域 CSV:", output_csv_sub)

# ==== 4B. 只按 Region 汇总：加权平均成本 + 总潜力 ====
rows_reg = []

for reg_id in unique_regions:
    reg_mask = valid_mask & (region_arr == reg_id)

    pot_reg  = potential_arr[reg_mask]
    cost_reg = cost_arr[reg_mask]

    total_potential_mt = float(np.nansum(pot_reg))
    if total_potential_mt > 0:
        weighted_cost = float(np.nansum(cost_reg * pot_reg) / total_potential_mt)
    else:
        weighted_cost = np.nan

    rows_reg.append({
        "Region_ID": int(reg_id),
        "Weighted_Cost_USD_per_tCO2": weighted_cost,
        "Total_Potential_MtCO2": total_potential_mt,
        "Total_Potential_GtCO2": total_potential_mt / 1000.0
    })

df_reg = pd.DataFrame(rows_reg).sort_values(["Region_ID"]).reset_index(drop=True)
os.makedirs(os.path.dirname(output_csv_reg), exist_ok=True)
df_reg.to_csv(output_csv_reg, index=False, float_format="%.6f")
print("已保存区域 CSV:", output_csv_reg)
