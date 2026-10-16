# 按区域/次区域统计潜力：求和
# 同时统计“总潜力”与“净效益>0的有效潜力”，并保存在同一个 CSV 中

import os
import numpy as np
import pandas as pd
from osgeo import gdal

trade = False       # 是否考虑贸易
maxcb = True       # 是否最大化气候净效益（否则是最小成本）
start_year = 2025  # Primary scenario. Use grid_scope_summary.py for the multi-year Table S10 series.

# ==== 1. 基本路径 ====
os.chdir(r"E:/wzy/2-Grid-based-MONET")

# 潜力栅格（单位：MtCO2）
if maxcb:
    if trade:
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit_raster (with trade).tif"
        output_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_by_region_subregion.csv"
    else:
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit_raster.tif"
        output_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_by_region_subregion.csv"
else:
    if trade:
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_net_benefit_mincost_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost_raster (with trade).tif"
        output_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_by_region_subregion.csv"
    else:
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_net_benefit_mincost_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost_raster.tif"
        output_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_by_region_subregion.csv"

# 全球区域 / 次区域栅格
region_path    = r"E:/ArcGIS/Projects/Country/Region.tif"
subregion_path = r"E:/ArcGIS/Projects/Country/Subregion.tif"

# ==== 2. 读取栅格 ====
potential_ds   = gdal.Open(potential_path)
net_benefit_ds = gdal.Open(net_benefit_path)
region_ds      = gdal.Open(region_path)
subregion_ds   = gdal.Open(subregion_path)

potential_arr  = potential_ds.ReadAsArray().astype(float)
net_benefit_arr = net_benefit_ds.ReadAsArray().astype(float)
region_arr     = region_ds.ReadAsArray().astype(float)
subregion_arr  = subregion_ds.ReadAsArray().astype(float)

print("潜力栅格 shape:", potential_arr.shape)
print("净效益栅格 shape:", net_benefit_arr.shape)
print("Region 栅格 shape:", region_arr.shape)
print("Subregion 栅格 shape:", subregion_arr.shape)

# 确保尺寸一致
if potential_arr.shape != region_arr.shape or potential_arr.shape != subregion_arr.shape or potential_arr.shape != net_benefit_arr.shape:
    raise ValueError("潜力、区域、次区域栅格的行列数不一致，请检查。")

# ==== 2.5 处理 NoData ====
# 在写栅格时用的是 nodata = -9999
nodata_val = -9999

# 把潜力中的 nodata 替换为 NaN，顺便把极小负数裁掉
potential_arr[potential_arr <= nodata_val] = np.nan
# 如果有数值误差产生的轻微负值，也可以设为 0
potential_arr[potential_arr < 0] = 0

# 处理净效益地图的 NoData
net_benefit_arr[net_benefit_arr <= nodata_val] = np.nan

# 如果 Region / Subregion 栅格也用了 -9999 作为 nodata，可以一并处理：
region_arr[region_arr <= nodata_val] = np.nan
subregion_arr[subregion_arr <= nodata_val] = np.nan

# ==== 3. 构造有效像元掩膜 ====
# 掩膜 1：全局总潜力掩膜（只要有潜力就统计）
valid_mask_all = (
    (~np.isnan(potential_arr)) &
    (~np.isnan(region_arr)) & (region_arr > 0) &
    (~np.isnan(subregion_arr)) & (subregion_arr > 0)
)

# 掩膜 2：有效潜力掩膜（在总潜力基础上，额外要求净效益 > 0）
valid_mask_pos_nb = valid_mask_all & (~np.isnan(net_benefit_arr)) & (net_benefit_arr > 0)

print(f"总有效像元数量: {np.sum(valid_mask_all)}")
print(f"净效益>0 的有效像元数量: {np.sum(valid_mask_pos_nb)}")

# ==== 4. 循环汇总 Region / Subregion ====
rows = []

# 找出所有有数据的区域 ID
unique_regions = np.unique(region_arr[valid_mask_all])

for reg_id in unique_regions:
    # 构建当前 Region 的双重掩膜
    reg_mask_all = valid_mask_all & (region_arr == reg_id)
    reg_mask_pos_nb = valid_mask_pos_nb & (region_arr == reg_id)

    # 找出该区域内所有次区域 ID
    unique_subregions = np.unique(subregion_arr[reg_mask_all])

    for sub_id in unique_subregions:
        # 构建当前 Subregion 的双重掩膜
        sub_mask_all = reg_mask_all & (subregion_arr == sub_id)
        sub_mask_pos_nb = reg_mask_pos_nb & (subregion_arr == sub_id)

        # 统计总潜力
        sub_total_all_mt = np.nansum(potential_arr[sub_mask_all])

        # 统计净效益大于 0 的有效潜力
        sub_total_pos_nb_mt = np.nansum(potential_arr[sub_mask_pos_nb])

        rows.append({
            "Region_ID": int(reg_id),
            "Subregion_ID": int(sub_id),
            "Total_Potential_MtCO2": float(sub_total_all_mt),
            "Positive_NetBenefit_Potential_MtCO2": float(sub_total_pos_nb_mt),
            "Total_Potential_GtCO2": float(sub_total_all_mt / 1000.0),
            "Positive_NetBenefit_Potential_GtCO2": float(sub_total_pos_nb_mt / 1000.0)
        })

# 转为 DataFrame
df = pd.DataFrame(rows)

# 按 Region / Subregion 排序一下（可选）
df = df.sort_values(by=["Region_ID", "Subregion_ID"]).reset_index(drop=True)

# 保存 CSV
os.makedirs(os.path.dirname(output_csv), exist_ok=True)
df.to_csv(output_csv, index=False, float_format="%.6f")

print("已保存 CSV:", output_csv)
