# 本程序用于最优技术组合选择：只考虑basalt，pathway 1，单年铺洒
# 情景：不考虑贸易最大化净效益 and 考虑贸易最大化净效益 and 不考虑贸易最小化成本
# 任务：
# （1）在三种颗粒大小中选择符合当前情景下的技术组合，并保存
# （加权平均净效益的意思是：每个网格在某技术组合下的成本 a $/tCO2 removed，累积净移除潜力 b tCO2 removed，此时该网格的成本为 ab $，
# 在a1b1，a2b2，...，a8b8种选择最小的那种技术组合作为最优技术组合）；
# （2）保存此情景下每个网格的其他指标（潜力、成本、气候效益），从而手动计算全球加权平均气候效益、全球加权平均净效益和全球加权平均净成本；
# （3）计算每个国家可以提供的加权平均气候效益、加权平均净效益和加权平均净成本，保存csv文件；
# （4）计算每个网格的“效益/成本”比率，绘制全球地图，并且将其分为三类，一类比率大于1，一类比率等于1，一类比率小于1（这一步可以直接用arcgis的con函数做）；
# （5）汇总所有三类情景(一类比率大于1，一类比率等于1，一类比率小于1)的国家和全球总潜力、加权平均净效益、加权平均净成本。

import os
import pandas as pd
import numpy as np
from osgeo import gdal, osr
import sys
import matplotlib.pyplot as plt

os.chdir('E:/wzy/2-Grid-based-MONET')

def save_raster(
    output_path,
    array,
    geotransform=(-180, 0.5, 0, 90, 0, -0.5),
    epsg=4326,
    dtype=gdal.GDT_Float32,
    nodata=-9999.0      # 默认给一个 NoData 值
):
    """
    轻量通用的GeoTIFF保存函数。
    - output_path: 输出tif路径
    - array: 2D numpy数组
    - geotransform: (originX, pixelWidth, 0, originY, 0, -pixelHeight)
    - epsg: 坐标参考系EPSG，默认4326
    - dtype: gdal数据类型，默认Float32
    - nodata: NoData值（会将 np.nan 统一写成这个值）
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    # 保证是二维数组
    arr = np.array(array, copy=True)
    rows, cols = arr.shape

    # 如果设置了 nodata，把 NaN 替换为 nodata
    if nodata is not None:
        nan_mask = np.isnan(arr)
        arr[nan_mask] = nodata

    driver = gdal.GetDriverByName("GTiff")
    ds = driver.Create(output_path, xsize=cols, ysize=rows, bands=1, eType=dtype)

    ds.SetGeoTransform(geotransform)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    ds.SetProjection(srs.ExportToWkt())

    band = ds.GetRasterBand(1)
    if nodata is not None:
        band.SetNoDataValue(nodata)

    band.WriteArray(arr)
    band.FlushCache()
    band = None
    ds = None

trade = False  # 是否考虑贸易
maxcb = True  # True表示最大化净效益，False表示最小化成本
start_year = 2050  # 2025, 2030, 2035, 2040, 2050

raster_row = 360
raster_col = 720

# 定义常量
Grid_Cropland_Area_km2 = gdal.Open('./Global Data/EW/Input/Global/Global_cropland_area_km2.tif').ReadAsArray()  # 每个网格的农田面积（km2）（0.5° 分辨率的网格面积不一定是为 55km x 55km，要提前根据经纬度换算，并且乘网格的农田比例），后面用为公顷时需要*100
T_TO_GT = 1e-9  # 吨到千兆吨的转换系数

# 读入数据
if trade:
    EW_net_benefit_basalt_2 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_2 μm (with trade).tif').ReadAsArray()
    EW_net_benefit_basalt_10 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_10 μm (with trade).tif').ReadAsArray()
    EW_net_benefit_basalt_20 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_20 μm (with trade).tif').ReadAsArray()
    EW_net_benefit_basalt_50 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_50 μm (with trade).tif').ReadAsArray()

    EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_2 μm (MtCO2) (with trade).tif').ReadAsArray()
    EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_10 μm (MtCO2) (with trade).tif').ReadAsArray()
    EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_20 μm (MtCO2) (with trade).tif').ReadAsArray()
    EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_50 μm (MtCO2) (with trade).tif').ReadAsArray()

    EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_2 μm (with trade).tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_10 μm (with trade).tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_20 μm (with trade).tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_50 μm (with trade).tif').ReadAsArray()

    EW_remove_cost_basalt_2 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_2 μm (with trade).tif').ReadAsArray()
    EW_remove_cost_basalt_10 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_10 μm (with trade).tif').ReadAsArray()
    EW_remove_cost_basalt_20 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_20 μm (with trade).tif').ReadAsArray()
    EW_remove_cost_basalt_50 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_50 μm (with trade).tif').ReadAsArray()

    EW_climate_benefit_basalt_2 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_2um (with trade).tif').ReadAsArray()
    EW_climate_benefit_basalt_10 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_10um (with trade).tif').ReadAsArray()
    EW_climate_benefit_basalt_20 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_20um (with trade).tif').ReadAsArray()
    EW_climate_benefit_basalt_50 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_50um (with trade).tif').ReadAsArray()
else:
    EW_net_benefit_basalt_2 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_2 μm.tif').ReadAsArray()
    EW_net_benefit_basalt_10 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_10 μm.tif').ReadAsArray()
    EW_net_benefit_basalt_20 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_20 μm.tif').ReadAsArray()
    EW_net_benefit_basalt_50 = gdal.Open(f'./Output/EW/Global/Net Benefit/{start_year}/EW_net_benefit_raster_Basalt_50 μm.tif').ReadAsArray()

    EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_2 μm (MtCO2).tif').ReadAsArray()
    EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_10 μm (MtCO2).tif').ReadAsArray()
    EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_20 μm (MtCO2).tif').ReadAsArray()
    EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_50 μm (MtCO2).tif').ReadAsArray()

    EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_2 μm.tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_10 μm.tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_20 μm.tif').ReadAsArray()
    EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/EW_remove_potential_raster_Basalt_50 μm.tif').ReadAsArray()

    EW_remove_cost_basalt_2 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_2 μm.tif').ReadAsArray()
    EW_remove_cost_basalt_10 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_10 μm.tif').ReadAsArray()
    EW_remove_cost_basalt_20 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_20 μm.tif').ReadAsArray()
    EW_remove_cost_basalt_50 = gdal.Open(f'./Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_Basalt_50 μm.tif').ReadAsArray()

    EW_climate_benefit_basalt_2 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_2um.tif').ReadAsArray()
    EW_climate_benefit_basalt_10 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_10um.tif').ReadAsArray()
    EW_climate_benefit_basalt_20 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_20um.tif').ReadAsArray()
    EW_climate_benefit_basalt_50 = gdal.Open(f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/outputs/{start_year}/Actual_Climate_Benefit/EW_Actual_CB_raster_Basalt_50um.tif').ReadAsArray()

# 读入岩石类型和颗粒大小
grain_size = pd.read_csv('Input Data/EW/Grain Size.csv', encoding='gbk')
rock_type = pd.read_csv('Input Data/EW/Rock Type.csv', encoding='gbk')

# 国家边界栅格，每个网格的值是国家代码
country_code_array = gdal.Open('E:/ArcGIS/Projects/Country/Country_code.tif').ReadAsArray()

if maxcb:
    # 构建一个表示每个网格最大净效益的地图（$）
    EW_max_net_benefit_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最大净效益所选岩石类型和颗粒大小组合的地图
    EW_max_net_benefit_scenario_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最大净效益所选岩石类型和颗粒大小组合下的潜力的地图（MtCO2 removed）
    EW_potential_maxnetbenefit_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存最大净效益所选组合下的强度潜力地图（tCO2/ha）
    EW_potential_maxnetbenefit_tCO2_ha_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最大净效益所选岩石类型和颗粒大小组合下的成本的地图（$）
    EW_cost_maxnetbenefit_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最大净效益所选岩石类型和颗粒大小组合下的气候效益的地图（$）
    EW_climate_benefit_maxnetbenefit_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最大净效益所选岩石类型和颗粒大小组合下的效益成本比地图
    EW_benefit_to_cost_maxnetbenefit_array = np.full((raster_row, raster_col), np.nan)

    # 记录每个网格的最大净效益和技术选择
    EW_max_net_benefit_csv = np.full((360*720, 1), np.nan)  # $
    EW_max_net_benefit_material_selection_csv = np.full((360*720, 1), np.nan)
    EW_potential_maxnetbenefit_csv = np.full((360*720, 1), np.nan)  # MtCO2
    EW_cost_maxnetbenefit_csv = np.full((360*720, 1), np.nan)  # $
    EW_climate_benefit_maxnetbenefit_csv = np.full((360*720, 1), np.nan)  # $
    EW_benefit_to_cost_maxnetbenefit_csv = np.full((360*720, 1), np.nan)

    # （1）在两种岩石类型和三种颗粒大小中选择最大净效益的组合，得到相应的潜力、成本、气候效益、最优技术组合;
    # （4）计算每个网格的“效益/成本”比率，绘制全球地图，并且将其分为三类，一类比率大于1，一类比率等于1，一类比率小于1（这一步可以直接用arcgis的con函数做）;
    for row in range(raster_row):
        for col in range(raster_col):
            # 将8种气候效益放入一个列表
            remove_potential = [EW_remove_potential_basalt_2[row, col], EW_remove_potential_basalt_10[row, col],
                                EW_remove_potential_basalt_20[row, col], EW_remove_potential_basalt_50[row, col]]

            remove_potential_intensity = [EW_remove_potential_intensity_basalt_2[row, col], EW_remove_potential_intensity_basalt_10[row, col],
                                          EW_remove_potential_intensity_basalt_20[row, col], EW_remove_potential_intensity_basalt_50[row, col]]

            net_benefit = [EW_net_benefit_basalt_2[row, col], EW_net_benefit_basalt_10[row, col],
                           EW_net_benefit_basalt_20[row, col], EW_net_benefit_basalt_50[row, col]]

            climate_benefit = [EW_climate_benefit_basalt_2[row, col], EW_climate_benefit_basalt_10[row, col],
                               EW_climate_benefit_basalt_20[row, col], EW_climate_benefit_basalt_50[row, col]]

            remove_cost = [EW_remove_cost_basalt_2[row, col], EW_remove_cost_basalt_10[row, col],
                           EW_remove_cost_basalt_20[row, col], EW_remove_cost_basalt_50[row, col]]

            total_net_benefit = [EW_net_benefit_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_net_benefit_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                                 EW_net_benefit_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_net_benefit_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]

            total_cost = [EW_remove_cost_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_remove_cost_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                          EW_remove_cost_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_remove_cost_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]

            total_climate_benefit = [EW_climate_benefit_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_climate_benefit_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                                     EW_climate_benefit_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_climate_benefit_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]

            # 检查 total_net_benefit 是否全为 NaN
            if np.all(np.isnan(total_net_benefit)):
                EW_max_net_benefit_array[row, col] = np.nan
                EW_max_net_benefit_scenario_array[row, col] = np.nan
                EW_max_net_benefit_csv[row * 720 + col, 0] = np.nan
                EW_max_net_benefit_material_selection_csv[row * 720 + col, 0] = np.nan

                EW_potential_maxnetbenefit_array[row, col] = np.nan
                EW_potential_maxnetbenefit_tCO2_ha_array[row, col] = np.nan
                EW_cost_maxnetbenefit_array[row, col] = np.nan
                EW_climate_benefit_maxnetbenefit_array[row, col] = np.nan
                EW_benefit_to_cost_maxnetbenefit_array[row, col] = np.nan

                EW_potential_maxnetbenefit_csv[row * 720 + col, 0] = np.nan
                EW_cost_maxnetbenefit_csv[row * 720 + col, 0] = np.nan
                EW_climate_benefit_maxnetbenefit_csv[row * 720 + col, 0] = np.nan
                EW_benefit_to_cost_maxnetbenefit_csv[row * 720 + col, 0] = np.nan

                continue
            else:
                # 否则，计算最大值及其对应的索引
                EW_max_net_benefit_array[row, col] = np.nanmax(net_benefit)  # $/tCO2 removed, 如果8个数中有nan，则忽略nan（如果用max()则会把nan看作最大值）
                EW_max_net_benefit_scenario_array[row, col] = np.nanargmax(net_benefit) + 1  # 找到最大净效益对应的索引（注意：Python 索引从 0 开始，所以需要 +1）

                EW_max_net_benefit_csv[row * 720 + col, 0] = total_net_benefit[np.nanargmax(net_benefit)]  # $
                EW_max_net_benefit_material_selection_csv[row * 720 + col, 0] = EW_max_net_benefit_scenario_array[row, col]

                EW_potential_maxnetbenefit_array[row, col] = remove_potential[np.nanargmax(net_benefit)]  # MtCO2
                EW_potential_maxnetbenefit_tCO2_ha_array[row, col] = remove_potential_intensity[np.nanargmax(net_benefit)]  # tCO2/ha
                EW_cost_maxnetbenefit_array[row, col] = remove_cost[np.nanargmax(net_benefit)]  # $/tCO2 removed
                EW_climate_benefit_maxnetbenefit_array[row, col] = climate_benefit[np.nanargmax(net_benefit)]  # $/tCO2 removed
                EW_benefit_to_cost_maxnetbenefit_array[row, col] = EW_climate_benefit_maxnetbenefit_array[row, col] / EW_cost_maxnetbenefit_array[row, col]

                EW_potential_maxnetbenefit_csv[row * 720 + col, 0] = remove_potential[np.nanargmax(net_benefit)]  # MtCO2
                EW_cost_maxnetbenefit_csv[row * 720 + col, 0] = total_cost[np.nanargmax(net_benefit)]  # $
                EW_climate_benefit_maxnetbenefit_csv[row * 720 + col, 0] = total_climate_benefit[np.nanargmax(net_benefit)]  # $
                EW_benefit_to_cost_maxnetbenefit_csv[row * 720 + col, 0] = EW_benefit_to_cost_maxnetbenefit_array[row, col]


    if trade:
        # 储存地图
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_raster (with trade).tif', EW_max_net_benefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_scenario_raster (with trade).tif', EW_max_net_benefit_scenario_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit_raster (with trade).tif', EW_potential_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit_raster_tCO2_ha (with trade).tif', EW_potential_maxnetbenefit_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_maxnetbenefit_raster (with trade).tif', EW_cost_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_climate_benefit_maxnetbenefit_raster (with trade).tif', EW_climate_benefit_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_benefit_to_cost_maxnetbenefit_raster (with trade).tif', EW_benefit_to_cost_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)

        # 保存为csv文件
        EW_max_net_benefit_material_selection_csv_df = pd.DataFrame(EW_max_net_benefit_material_selection_csv)
        EW_max_net_benefit_material_selection_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_scenario (with trade).csv')

        EW_max_net_benefit_csv_df = pd.DataFrame(EW_max_net_benefit_csv)
        EW_max_net_benefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit (with trade).csv')

        EW_potential_maxnetbenefit_csv_df = pd.DataFrame(EW_potential_maxnetbenefit_csv)
        EW_potential_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit (with trade).csv')

        EW_cost_maxnetbenefit_csv_df = pd.DataFrame(EW_cost_maxnetbenefit_csv)
        EW_cost_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_maxnetbenefit (with trade).csv')

        EW_climate_benefit_maxnetbenefit_csv_df = pd.DataFrame(EW_climate_benefit_maxnetbenefit_csv)
        EW_climate_benefit_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_climate_benefit_maxnetbenefit (with trade).csv')

        EW_benefit_to_cost_maxnetbenefit_csv_df = pd.DataFrame(EW_benefit_to_cost_maxnetbenefit_csv)
        EW_benefit_to_cost_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_benefit_to_cost_maxnetbenefit (with trade).csv')
    else:
        # 储存地图
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_raster.tif', EW_max_net_benefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_scenario_raster.tif', EW_max_net_benefit_scenario_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit_raster.tif', EW_potential_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit_raster_tCO2_ha.tif', EW_potential_maxnetbenefit_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_maxnetbenefit_raster.tif', EW_cost_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_climate_benefit_maxnetbenefit_raster.tif', EW_climate_benefit_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_benefit_to_cost_maxnetbenefit_raster.tif', EW_benefit_to_cost_maxnetbenefit_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)

        # 保存为csv文件
        EW_max_net_benefit_material_selection_csv_df = pd.DataFrame(EW_max_net_benefit_material_selection_csv)
        EW_max_net_benefit_material_selection_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_scenario.csv')

        EW_max_net_benefit_csv_df = pd.DataFrame(EW_max_net_benefit_csv)
        EW_max_net_benefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit.csv')

        EW_potential_maxnetbenefit_csv_df = pd.DataFrame(EW_potential_maxnetbenefit_csv)
        EW_potential_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit.csv')

        EW_cost_maxnetbenefit_csv_df = pd.DataFrame(EW_cost_maxnetbenefit_csv)
        EW_cost_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_maxnetbenefit.csv')

        EW_climate_benefit_maxnetbenefit_csv_df = pd.DataFrame(EW_climate_benefit_maxnetbenefit_csv)
        EW_climate_benefit_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_climate_benefit_maxnetbenefit.csv')

        EW_benefit_to_cost_maxnetbenefit_csv_df = pd.DataFrame(EW_benefit_to_cost_maxnetbenefit_csv)
        EW_benefit_to_cost_maxnetbenefit_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_benefit_to_cost_maxnetbenefit.csv')

    # （3）计算每个国家的加权平均净效益、净成本以及此时的总潜力、有价值ERW面积
    country_codes = np.unique(country_code_array[~np.isnan(country_code_array)])  # 获取所有国家代码
    country_net_benefit = {}
    country_cost = {}
    country_potential = {}
    country_valid_potential = {}
    country_climate_benefit = {}
    country_area = {}

    for code in country_codes:
        mask = (country_code_array == code) & ~np.isnan(EW_potential_maxnetbenefit_array)
        # 净效益/成本/气候效益的单位：$/tCO2
        country_net_benefit[code] = np.nansum(EW_max_net_benefit_array[mask] * EW_potential_maxnetbenefit_array[mask]) / np.nansum(EW_potential_maxnetbenefit_array[mask])
        country_cost[code] = np.nansum(EW_cost_maxnetbenefit_array[mask] * EW_potential_maxnetbenefit_array[mask]) / np.nansum(EW_potential_maxnetbenefit_array[mask])
        country_climate_benefit[code] = np.nansum(EW_climate_benefit_maxnetbenefit_array[mask] * EW_potential_maxnetbenefit_array[mask]) / np.nansum(EW_potential_maxnetbenefit_array[mask])
        # 总潜力：GtCO2
        country_potential[code] = np.nansum(EW_potential_maxnetbenefit_array[mask]) / 1000
        # 净效益大于 0 的有效潜力：GtCO2
        pos_nb_mask = mask & (EW_max_net_benefit_array > 0)
        country_valid_potential[code] = np.nansum(EW_potential_maxnetbenefit_array[pos_nb_mask]) / 1000
        # 总面积：km2
        country_area[code] = np.nansum(Grid_Cropland_Area_km2[mask])

    # 将结果转换为DataFrame并排序
    country_net_benefit_df = pd.DataFrame(list(country_net_benefit.items()), columns=['Country Code', 'Net benefit'])
    country_net_benefit_df = country_net_benefit_df.sort_values(by='Net benefit', ascending=False)
    country_cost_df = pd.DataFrame(list(country_cost.items()), columns=['Country Code', 'Cost'])
    country_cost_df = country_cost_df.sort_values(by='Cost', ascending=False)
    country_potential_df = pd.DataFrame(list(country_potential.items()), columns=['Country Code', 'Potential'])
    country_potential_df = country_potential_df.sort_values(by='Potential', ascending=False)
    country_valid_potential_df = pd.DataFrame(list(country_valid_potential.items()), columns=['Country Code', 'Cost-effective Potential'])
    country_valid_potential_df = country_valid_potential_df.sort_values(by='Cost-effective Potential', ascending=False)
    country_climate_benefit_df = pd.DataFrame(list(country_climate_benefit.items()), columns=['Country Code', 'Climate Benefit'])
    country_climate_benefit_df = country_climate_benefit_df.sort_values(by='Climate Benefit', ascending=False)
    country_area_df = pd.DataFrame(list(country_area.items()), columns=['Country Code', 'Cropland Area'])
    country_area_df = country_area_df.sort_values(by='Cropland Area', ascending=False)

    # 保存csv文件
    if trade:
        country_net_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Net Benefit Rank (with trade).csv')
        country_cost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Cost Rank (with trade).csv')
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Potential Rank (with trade).csv')
        country_valid_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Cost-effective Potential Rank (with trade).csv')
        country_climate_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Climate Benefit Rank (with trade).csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Area Rank (with trade).csv')
    else:
        country_net_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Net Benefit Rank.csv')
        country_cost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Cost Rank.csv')
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Potential Rank.csv')
        country_valid_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Cost-effective Potential Rank.csv')
        country_climate_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Climate Benefit Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Area Rank.csv')

    # （5）汇总所有三类情景(一类比率大于1，一类比率等于1，一类比率小于1)的国家和全球总潜力、平均成本、平均气候效益、平均净效益。
    def summarize_by_ratio_class(ratio_array, cost_array, benefit_array, potential_array, net_benefit_array, country_code_array):
        # 分类比率
        ratio_class = np.zeros_like(ratio_array, dtype=int)
        ratio_class[ratio_array > 1] = 1  # 比率大于1
        ratio_class[ratio_array == 1] = 2  # 比率等于1
        ratio_class[ratio_array < 1] = 3  # 比率小于1

        # 初始化汇总结果
        summary = {
            'global': {
                'ratio_gt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_eq_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_lt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0}
            },
            'countries': {}
        }

        # 初始化全局总权重
        global_total_weights = {
            'ratio_gt_1': 0,
            'ratio_eq_1': 0,
            'ratio_lt_1': 0
        }

        # 按国家汇总
        unique_countries = np.unique(country_code_array[~np.isnan(country_code_array)])
        for country in unique_countries:
            mask = (country_code_array == country)
            country_summary = {
                'ratio_gt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_eq_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_lt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0}
            }

            for class_id, class_name in zip([1, 2, 3], ['ratio_gt_1', 'ratio_eq_1', 'ratio_lt_1']):
                class_mask = (ratio_class == class_id) & mask
                if np.any(class_mask):
                    country_summary[class_name]['total_potential'] = np.nansum(potential_array[class_mask]) / 1000  # GtCO2
                    country_summary[class_name]['avg_cost'] = np.nansum(cost_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])
                    country_summary[class_name]['avg_benefit'] = np.nansum(benefit_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])
                    country_summary[class_name]['avg_net_benefit'] = np.nansum(net_benefit_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])

                    # 累加到全球汇总
                    summary['global'][class_name]['total_potential'] += country_summary[class_name]['total_potential']
                    summary['global'][class_name]['avg_cost'] += np.nansum(cost_array[class_mask] * potential_array[class_mask])
                    summary['global'][class_name]['avg_benefit'] += np.nansum(benefit_array[class_mask] * potential_array[class_mask])
                    summary['global'][class_name]['avg_net_benefit'] += np.nansum(net_benefit_array[class_mask] * potential_array[class_mask])

                    global_total_weights[class_name] += np.nansum(potential_array[class_mask])

            summary['countries'][int(country)] = country_summary

        # 计算全球平均值
        for class_name in ['ratio_gt_1', 'ratio_eq_1', 'ratio_lt_1']:
            if global_total_weights[class_name] > 0:
                summary['global'][class_name]['avg_cost'] /= global_total_weights[class_name]
                summary['global'][class_name]['avg_benefit'] /= global_total_weights[class_name]
                summary['global'][class_name]['avg_net_benefit'] /= global_total_weights[class_name]

        return summary

    maxnetbenefit_summary = summarize_by_ratio_class(EW_benefit_to_cost_maxnetbenefit_array, EW_cost_maxnetbenefit_array, EW_climate_benefit_maxnetbenefit_array, EW_potential_maxnetbenefit_array, EW_max_net_benefit_array, country_code_array)

    # 保存结果
    # 将 mincost_summary 转换为 DataFrame
    def summary_to_dataframe(summary):
        data = []
        for country, country_data in summary['countries'].items():
            for ratio_class, class_data in country_data.items():
                row = {
                    'country': country,
                    'ratio_class': ratio_class,
                    'total_potential': class_data['total_potential'],
                    'avg_cost': class_data['avg_cost'],
                    'avg_benefit': class_data['avg_benefit'],
                    'avg_net_benefit': class_data['avg_net_benefit']
                }
                data.append(row)

        # 添加全球汇总数据
        for ratio_class, class_data in summary['global'].items():
            row = {
                'country': 'global',
                'ratio_class': ratio_class,
                'total_potential': class_data['total_potential'],
                'avg_cost': class_data['avg_cost'],
                'avg_benefit': class_data['avg_benefit'],
                'avg_net_benefit': class_data['avg_net_benefit']
            }
            data.append(row)

        return pd.DataFrame(data)

    maxnetbenefit_df = summary_to_dataframe(maxnetbenefit_summary)

    if trade:
        maxnetbenefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/maxnetbenefit_summary (with trade).csv', index=False)
    else:
        maxnetbenefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/maxnetbenefit_summary.csv', index=False)


else:
    # 构建一个表示每个网格最小成本的地图（$/tCO2 removed）
    EW_min_cost_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最小成本所选岩石类型和颗粒大小组合的地图
    EW_min_cost_scenario_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最小成本所选岩石类型和颗粒大小组合下的潜力的地图（MtCO2 removed）
    EW_potential_mincost_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存最小成本所选组合下的强度潜力地图（tCO2/ha）
    EW_potential_mincost_tCO2_ha_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最小成本所选岩石类型和颗粒大小组合下的净效益的地图（$/tCO2 removed）
    EW_net_benefit_mincost_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最小成本所选岩石类型和颗粒大小组合下的气候效益的地图（$/tCO2 removed）
    EW_climate_benefit_mincost_array = np.full((raster_row, raster_col), np.nan)
    # 构建一个储存每个网格最小成本所选岩石类型和颗粒大小组合下的效益成本比地图
    EW_benefit_to_cost_mincost_array = np.full((raster_row, raster_col), np.nan)

    # 记录每个网格的最小成本和技术选择
    EW_min_cost_csv = np.full((360*720, 1), np.nan)  # $
    EW_min_cost_material_selection_csv = np.full((360*720, 1), np.nan)
    EW_potential_mincost_csv = np.full((360*720, 1), np.nan)  # MtCO2
    EW_net_benefit_mincost_csv = np.full((360*720, 1), np.nan)  # $
    EW_climate_benefit_mincost_csv = np.full((360*720, 1), np.nan)  # $
    EW_benefit_to_cost_mincost_csv = np.full((360*720, 1), np.nan)

    # （1）在两种岩石类型和三种颗粒大小中选择最小成本的组合，得到相应的潜力、成本、气候效益、最优技术组合;
    # （4）计算每个网格的“效益/成本”比率，绘制全球地图，并且将其分为三类，一类比率大于1，一类比率等于1，一类比率小于1（这一步可以直接用arcgis的con函数做）;
    for row in range(raster_row):
        for col in range(raster_col):
            # 将8种气候效益放入一个列表
            remove_potential = [EW_remove_potential_basalt_2[row, col], EW_remove_potential_basalt_10[row, col],
                                EW_remove_potential_basalt_20[row, col], EW_remove_potential_basalt_50[row, col]]

            remove_potential_intensity = [EW_remove_potential_intensity_basalt_2[row, col], EW_remove_potential_intensity_basalt_10[row, col],
                                          EW_remove_potential_intensity_basalt_20[row, col], EW_remove_potential_intensity_basalt_50[row, col]]

            net_benefit = [EW_net_benefit_basalt_2[row, col], EW_net_benefit_basalt_10[row, col],
                           EW_net_benefit_basalt_20[row, col], EW_net_benefit_basalt_50[row, col]]

            climate_benefit = [EW_climate_benefit_basalt_2[row, col], EW_climate_benefit_basalt_10[row, col],
                               EW_climate_benefit_basalt_20[row, col], EW_climate_benefit_basalt_50[row, col]]

            remove_cost = [EW_remove_cost_basalt_2[row, col], EW_remove_cost_basalt_10[row, col],
                           EW_remove_cost_basalt_20[row, col], EW_remove_cost_basalt_50[row, col]]

            total_net_benefit = [EW_net_benefit_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_net_benefit_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                                 EW_net_benefit_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_net_benefit_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]

            total_cost = [EW_remove_cost_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_remove_cost_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                          EW_remove_cost_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_remove_cost_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]

            total_climate_benefit = [EW_climate_benefit_basalt_2[row, col] * EW_remove_potential_basalt_2[row, col], EW_climate_benefit_basalt_10[row, col] * EW_remove_potential_basalt_10[row, col],
                                     EW_climate_benefit_basalt_20[row, col] * EW_remove_potential_basalt_20[row, col], EW_climate_benefit_basalt_50[row, col] * EW_remove_potential_basalt_50[row, col]]


            # 检查 total_cost 是否全为 NaN
            if np.all(np.isnan(total_cost)):
                EW_min_cost_array[row, col] = np.nan
                EW_min_cost_scenario_array[row, col] = np.nan
                EW_min_cost_csv[row * 720 + col, 0] = np.nan
                EW_min_cost_material_selection_csv[row * 720 + col, 0] = np.nan

                EW_potential_mincost_array[row, col] = np.nan
                EW_potential_mincost_tCO2_ha_array[row, col] = np.nan
                EW_net_benefit_mincost_array[row, col] = np.nan
                EW_climate_benefit_mincost_array[row, col] = np.nan
                EW_benefit_to_cost_mincost_array[row, col] = np.nan

                EW_potential_mincost_csv[row * 720 + col, 0] = np.nan
                EW_net_benefit_mincost_csv[row * 720 + col, 0] = np.nan
                EW_climate_benefit_mincost_csv[row * 720 + col, 0] = np.nan
                EW_benefit_to_cost_mincost_csv[row * 720 + col, 0] = np.nan

                continue
            else:
                # if np.all(np.isnan(total_net_benefit)):
                #     print(row * 720 + col)
                #     print(remove_cost)
                #     print(total_cost)
                #     print(remove_potential)
                # 否则，计算最小值及其对应的索引
                EW_min_cost_array[row, col] = np.nanmin(remove_cost)  # $/tCO2 removed, 如果8个数中有nan，则忽略nan（如果用min()则会把nan看作最小值）
                EW_min_cost_scenario_array[row, col] = np.nanargmin(remove_cost) + 1  # 找到最小成本对应的索引（注意：Python 索引从 0 开始，所以需要 +1）

                EW_min_cost_csv[row * 720 + col, 0] = total_cost[np.nanargmin(remove_cost)]  # $
                EW_min_cost_material_selection_csv[row * 720 + col, 0] = EW_min_cost_scenario_array[row, col]

                EW_potential_mincost_array[row, col] = remove_potential[np.nanargmin(remove_cost)]  # MtCO2
                EW_potential_mincost_tCO2_ha_array[row, col] = remove_potential_intensity[np.nanargmin(remove_cost)]  # tCO2/ha
                EW_net_benefit_mincost_array[row, col] = net_benefit[np.nanargmin(remove_cost)]  # $/tCO2 removed
                EW_climate_benefit_mincost_array[row, col] = climate_benefit[np.nanargmin(remove_cost)]  # $/tCO2 removed
                EW_benefit_to_cost_mincost_array[row, col] = EW_climate_benefit_mincost_array[row, col] / EW_min_cost_array[row, col]

                EW_potential_mincost_csv[row * 720 + col, 0] = remove_potential[np.nanargmin(remove_cost)]  # MtCO2
                EW_net_benefit_mincost_csv[row * 720 + col, 0] = total_net_benefit[np.nanargmin(remove_cost)]  # $
                EW_climate_benefit_mincost_csv[row * 720 + col, 0] = total_climate_benefit[np.nanargmin(remove_cost)]  # $
                EW_benefit_to_cost_mincost_csv[row * 720 + col, 0] = EW_benefit_to_cost_mincost_array[row, col]

    if trade:
        # 储存地图
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_raster (with trade).tif', EW_min_cost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_scenario_raster (with trade).tif', EW_min_cost_scenario_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost_raster (with trade).tif', EW_potential_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost_raster_tCO2_ha (with trade).tif', EW_potential_mincost_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_net_benefit_mincost_raster (with trade).tif', EW_net_benefit_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_climate_benefit_mincost_raster (with trade).tif', EW_climate_benefit_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_benefit_to_cost_mincost_raster (with trade).tif', EW_benefit_to_cost_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)

        # 保存为csv文件
        EW_min_cost_material_selection_csv_df = pd.DataFrame(EW_min_cost_material_selection_csv)
        EW_min_cost_material_selection_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_scenario (with trade).csv')

        EW_min_cost_csv_df = pd.DataFrame(EW_min_cost_csv)
        EW_min_cost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost (with trade).csv')

        EW_potential_mincost_csv_df = pd.DataFrame(EW_potential_mincost_csv)
        EW_potential_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost (with trade).csv')

        EW_net_benefit_mincost_csv_df = pd.DataFrame(EW_net_benefit_mincost_csv)
        EW_net_benefit_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_net_benefit_mincost (with trade).csv')

        EW_climate_benefit_mincost_csv_df = pd.DataFrame(EW_climate_benefit_mincost_csv)
        EW_climate_benefit_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_climate_benefit_mincost (with trade).csv')

        EW_benefit_to_cost_mincost_csv_df = pd.DataFrame(EW_benefit_to_cost_mincost_csv)
        EW_benefit_to_cost_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_benefit_to_cost_mincost (with trade).csv')
    else:
        # 储存地图
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_raster.tif', EW_min_cost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_scenario_raster.tif', EW_min_cost_scenario_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost_raster.tif', EW_potential_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost_raster_tCO2_ha.tif', EW_potential_mincost_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_net_benefit_mincost_raster.tif', EW_net_benefit_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_climate_benefit_mincost_raster.tif', EW_climate_benefit_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_benefit_to_cost_mincost_raster.tif', EW_benefit_to_cost_mincost_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)

        # 保存为csv文件
        EW_min_cost_material_selection_csv_df = pd.DataFrame(EW_min_cost_material_selection_csv)
        EW_min_cost_material_selection_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_scenario.csv')

        EW_min_cost_csv_df = pd.DataFrame(EW_min_cost_csv)
        EW_min_cost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost.csv')

        EW_potential_mincost_csv_df = pd.DataFrame(EW_potential_mincost_csv)
        EW_potential_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost.csv')

        EW_net_benefit_mincost_csv_df = pd.DataFrame(EW_net_benefit_mincost_csv)
        EW_net_benefit_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_net_benefit_mincost.csv')

        EW_climate_benefit_mincost_csv_df = pd.DataFrame(EW_climate_benefit_mincost_csv)
        EW_climate_benefit_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_climate_benefit_mincost.csv')

        EW_benefit_to_cost_mincost_csv_df = pd.DataFrame(EW_benefit_to_cost_mincost_csv)
        EW_benefit_to_cost_mincost_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_benefit_to_cost_mincost.csv')

    # （3）计算每个国家的加权平均净效益、净成本以及此时的总潜力
    country_codes = np.unique(country_code_array[~np.isnan(country_code_array)])  # 获取所有国家代码
    country_net_benefit = {}
    country_cost = {}
    country_potential = {}
    country_valid_potential = {}
    country_climate_benefit = {}
    country_area = {}

    for code in country_codes:
        mask = (country_code_array == code) & ~np.isnan(EW_potential_mincost_array)
        # 净效益/成本/气候效益的单位：$/tCO2
        country_net_benefit[code] = np.nansum(EW_net_benefit_mincost_array[mask] * EW_potential_mincost_array[mask]) / np.nansum(EW_potential_mincost_array[mask])
        country_cost[code] = np.nansum(EW_min_cost_array[mask] * EW_potential_mincost_array[mask]) / np.nansum(EW_potential_mincost_array[mask])
        country_climate_benefit[code] = np.nansum(EW_climate_benefit_mincost_array[mask] * EW_potential_mincost_array[mask]) / np.nansum(EW_potential_mincost_array[mask])
        # 总潜力：GtCO2
        country_potential[code] = np.nansum(EW_potential_mincost_array[mask]) / 1000
        # 净效益大于 0 的有效潜力
        pos_nb_mask = mask & (EW_net_benefit_mincost_array > 0)
        country_valid_potential[code] = np.nansum(EW_potential_mincost_array[pos_nb_mask]) / 1000
        # 总面积：万km2
        country_area[code] = np.nansum(Grid_Cropland_Area_km2[mask])

    # 将结果转换为DataFrame并排序
    country_net_benefit_df = pd.DataFrame(list(country_net_benefit.items()), columns=['Country Code', 'Net benefit'])
    country_net_benefit_df = country_net_benefit_df.sort_values(by='Net benefit', ascending=False)
    country_cost_df = pd.DataFrame(list(country_cost.items()), columns=['Country Code', 'Cost'])
    country_cost_df = country_cost_df.sort_values(by='Cost', ascending=False)
    country_potential_df = pd.DataFrame(list(country_potential.items()), columns=['Country Code', 'Potential'])
    country_potential_df = country_potential_df.sort_values(by='Potential', ascending=False)
    country_valid_potential_df = pd.DataFrame(list(country_valid_potential.items()), columns=['Country Code', 'Cost-effective Potential'])
    country_valid_potential_df = country_valid_potential_df.sort_values(by='Cost-effective Potential', ascending=False)
    country_climate_benefit_df = pd.DataFrame(list(country_climate_benefit.items()), columns=['Country Code', 'Climate Benefit'])
    country_climate_benefit_df = country_climate_benefit_df.sort_values(by='Climate Benefit', ascending=False)
    country_area_df = pd.DataFrame(list(country_area.items()), columns=['Country Code', 'Cropland Area'])
    country_area_df = country_area_df.sort_values(by='Cropland Area', ascending=False)

    # 保存csv文件
    if trade:
        country_net_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Net Benefit Rank (with trade).csv')
        country_cost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Cost Rank (with trade).csv')
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Potential Rank (with trade).csv')
        country_valid_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Cost-effective Potential Rank (with trade).csv')
        country_climate_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Climate Benefit Rank (with trade).csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Area Rank (with trade).csv')
    else:
        country_net_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Net Benefit Rank.csv')
        country_cost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Cost Rank.csv')
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Potential Rank.csv')
        country_valid_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Cost-effective Potential Rank.csv')
        country_climate_benefit_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Climate Benefit Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Area Rank.csv')

    # （5）汇总所有三类情景(一类比率大于1，一类比率等于1，一类比率小于1)的国家和全球总潜力、平均成本、平均气候效益、平均净效益。
    def summarize_by_ratio_class(ratio_array, cost_array, benefit_array, potential_array, net_benefit_array, country_code_array):
        # 分类比率
        ratio_class = np.zeros_like(ratio_array, dtype=int)
        ratio_class[ratio_array > 1] = 1  # 比率大于1
        ratio_class[ratio_array == 1] = 2  # 比率等于1
        ratio_class[ratio_array < 1] = 3  # 比率小于1

        # 初始化汇总结果
        summary = {
            'global': {
                'ratio_gt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_eq_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_lt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0}
            },
            'countries': {}
        }

        # 初始化全局总权重
        global_total_weights = {
            'ratio_gt_1': 0,
            'ratio_eq_1': 0,
            'ratio_lt_1': 0
        }

        # 按国家汇总
        unique_countries = np.unique(country_code_array[~np.isnan(country_code_array)])
        for country in unique_countries:
            mask = (country_code_array == country)
            country_summary = {
                'ratio_gt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_eq_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0},
                'ratio_lt_1': {'total_potential': 0, 'avg_cost': 0, 'avg_benefit': 0, 'avg_net_benefit': 0}
            }

            for class_id, class_name in zip([1, 2, 3], ['ratio_gt_1', 'ratio_eq_1', 'ratio_lt_1']):
                class_mask = (ratio_class == class_id) & mask
                if np.any(class_mask):
                    country_summary[class_name]['total_potential'] = np.nansum(potential_array[class_mask]) / 1000  # GtCO2
                    country_summary[class_name]['avg_cost'] = np.nansum(cost_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])
                    country_summary[class_name]['avg_benefit'] = np.nansum(benefit_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])
                    country_summary[class_name]['avg_net_benefit'] = np.nansum(net_benefit_array[class_mask] * potential_array[class_mask]) / np.nansum(potential_array[class_mask])

                    # 累加到全球汇总
                    summary['global'][class_name]['total_potential'] += country_summary[class_name]['total_potential']
                    summary['global'][class_name]['avg_cost'] += np.nansum(cost_array[class_mask] * potential_array[class_mask])
                    summary['global'][class_name]['avg_benefit'] += np.nansum(benefit_array[class_mask] * potential_array[class_mask])
                    summary['global'][class_name]['avg_net_benefit'] += np.nansum(net_benefit_array[class_mask] * potential_array[class_mask])

                    global_total_weights[class_name] += np.nansum(potential_array[class_mask])

            summary['countries'][int(country)] = country_summary

        # 计算全球平均值
        for class_name in ['ratio_gt_1', 'ratio_eq_1', 'ratio_lt_1']:
            if global_total_weights[class_name] > 0:
                summary['global'][class_name]['avg_cost'] /= global_total_weights[class_name]
                summary['global'][class_name]['avg_benefit'] /= global_total_weights[class_name]
                summary['global'][class_name]['avg_net_benefit'] /= global_total_weights[class_name]

        return summary

    mincost_summary = summarize_by_ratio_class(EW_benefit_to_cost_mincost_array, EW_min_cost_array, EW_climate_benefit_mincost_array, EW_potential_mincost_array, EW_net_benefit_mincost_array, country_code_array)

    # 保存结果
    # 将 mincost_summary 转换为 DataFrame
    def summary_to_dataframe(summary):
        data = []
        for country, country_data in summary['countries'].items():
            for ratio_class, class_data in country_data.items():
                row = {
                    'country': country,
                    'ratio_class': ratio_class,
                    'total_potential': class_data['total_potential'],
                    'avg_cost': class_data['avg_cost'],
                    'avg_benefit': class_data['avg_benefit'],
                    'avg_net_benefit': class_data['avg_net_benefit']
                }
                data.append(row)

        # 添加全球汇总数据
        for ratio_class, class_data in summary['global'].items():
            row = {
                'country': 'global',
                'ratio_class': ratio_class,
                'total_potential': class_data['total_potential'],
                'avg_cost': class_data['avg_cost'],
                'avg_benefit': class_data['avg_benefit'],
                'avg_net_benefit': class_data['avg_net_benefit']
            }
            data.append(row)

        return pd.DataFrame(data)

    mincost_df = summary_to_dataframe(mincost_summary)

    if trade:
        mincost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/mincost_summary (with trade).csv', index=False)
    else:
        mincost_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/mincost_summary.csv', index=False)
