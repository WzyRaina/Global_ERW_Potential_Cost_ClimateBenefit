import os
import pandas as pd
import numpy as np
from osgeo import gdal

os.chdir('E:/wzy/2-Grid-based-MONET')

trade = False       # 是否考虑贸易
maxcb = True       # 是否最大化气候净效益（否则是最小成本）
start_year = 2050  # 2025, 2030, 2035, 2040, 2050

# ========= 1. 读取基础栅格 =========

# 农田面积（km2）
Grid_Cropland_Area_km2 = gdal.Open(
    './Global Data/EW/Input/Global/Global_cropland_area_km2.tif'
).ReadAsArray().astype(float)

# 区域 & 次区域（像素值为区域编码）
region_array = gdal.Open(
    r'E:/ArcGIS/Projects/Country/Region.tif'
).ReadAsArray()

subregion_array = gdal.Open(
    r'E:/ArcGIS/Projects/Country/Subregion.tif'
).ReadAsArray()

# ========= 2. 读取情景下的技术选择栅格（1–4） =========

if maxcb:
    if trade:
        scenario_1 = gdal.Open(
            f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/'
            'EW_max_net_benefit_scenario_raster (with trade).tif'
        ).ReadAsArray()
    else:
        scenario_1 = gdal.Open(
            f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/'
            'EW_max_net_benefit_scenario_raster.tif'
        ).ReadAsArray()
else:
    if trade:
        scenario_1 = gdal.Open(
            f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/'
            'EW_min_cost_scenario_raster (with trade).tif'
        ).ReadAsArray()
    else:
        scenario_1 = gdal.Open(
            f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/'
            'EW_min_cost_scenario_raster.tif'
        ).ReadAsArray()

# ========= 3. 全局汇总：技术面积占比（和你原来一样） =========

def summarize_scenario(scenario_array, area_array, scenario_name):
    summary = []

    # 有效网格：技术在 1–4 且面积非 NaN
    valid_mask = np.isin(scenario_array, np.arange(1, 5)) & ~np.isnan(area_array)
    total_area = np.nansum(area_array[valid_mask])

    for tech_id in range(1, 5):  # 技术 1–4
        mask = (scenario_array == tech_id) & ~np.isnan(area_array)
        grid_count = int(np.sum(mask))
        tech_area = float(np.nansum(area_array[mask]))
        area_share = tech_area / total_area if total_area > 0 else np.nan

        summary.append({
            "Scenario": scenario_name,
            "Technology_ID": tech_id,
            "Grid_Count": grid_count,
            "Total_Area_km2": tech_area,
            "Area_Share_percent": round(area_share * 100, 2)
        })
    return summary

results = []
results.extend(summarize_scenario(scenario_1, Grid_Cropland_Area_km2, "Scenario 3"))

df_global = pd.DataFrame(results)

# 输出路径前缀（方便后面继续用）
if maxcb:
    if trade:
        out_dir = f"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade"
    else:
        out_dir = f"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade"
else:
    if trade:
        out_dir = f"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade"
    else:
        out_dir = f"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade"

os.makedirs(out_dir, exist_ok=True)

df_global.to_csv(os.path.join(out_dir, "EW_summary_by_technology_area.csv"), index=False)

# ========= 4. 分区域 + 次区域 + 技术 汇总 =========
# 目标：输出列 Region_ID, Subregion_ID, Technology_ID, Total_Area_km2, Share_in_region_percent, Share_in_subregion_percent

def summarize_by_region_subregion(scenario_array, area_array, region_array, subregion_array):
    summary = []

    # 基础有效掩膜：有技术、有面积、有区域、有次区域
    valid_mask = (
        np.isin(scenario_array, np.arange(1, 5)) &
        ~np.isnan(area_array) &
        (region_array > 0) &
        (subregion_array > 0)
    )

    # 所有有效区域编码
    region_codes = np.unique(region_array[valid_mask])
    region_codes = region_codes[region_codes > 0]

    for reg in region_codes:
        # 当前大区域掩膜
        region_mask = valid_mask & (region_array == reg)

        # 区域总农田面积（所有技术 + 所有次区域）
        region_total_area = float(np.nansum(area_array[region_mask]))

        # 当前大区域下的次区域编码
        sub_codes = np.unique(subregion_array[region_mask])
        sub_codes = sub_codes[sub_codes > 0]

        for sub in sub_codes:
            # 当前次区域掩膜
            sub_mask = region_mask & (subregion_array == sub)

            # 次区域总农田面积（所有技术）
            subregion_total_area = float(np.nansum(area_array[sub_mask]))

            for tech_id in range(1, 5):
                tech_mask = sub_mask & (scenario_array == tech_id)

                tech_area = float(np.nansum(area_array[tech_mask]))

                if tech_area == 0:
                    # 不产生记录也可以；如果想保留 0 也可以删掉这个判断
                    continue

                share_region = tech_area / region_total_area if region_total_area > 0 else np.nan
                share_sub    = tech_area / subregion_total_area if subregion_total_area > 0 else np.nan

                summary.append({
                    "Region_ID": int(reg),
                    "Subregion_ID": int(sub),
                    "Technology_ID": int(tech_id),
                    "Total_Area_km2": tech_area,
                    "Share_in_region_percent": round(share_region * 100, 2),
                    "Share_in_subregion_percent": round(share_sub * 100, 2)
                })

    return pd.DataFrame(summary)

df_region_sub = summarize_by_region_subregion(
    scenario_1,
    Grid_Cropland_Area_km2,
    region_array,
    subregion_array
)

# 保存结果：用于后续画“区域 × 次区域 × 技术”的堆积柱状图
out_path_region_sub = os.path.join(out_dir, "EW_summary_by_region_subregion_technology.csv")
df_region_sub.to_csv(out_path_region_sub, index=False)

print("全局技术汇总已保存：", os.path.join(out_dir, "EW_summary_by_technology_area.csv"))
print("分区域+次区域+技术汇总已保存：", out_path_region_sub)
