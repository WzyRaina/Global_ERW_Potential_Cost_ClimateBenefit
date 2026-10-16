# 本程序用于计算最优技术组合选择下多年铺洒的潜力：
# 情景：每个该网格的最优技术组合选择
# 任务：计算并保存在情景下每个网格多年铺洒的潜力（包含总潜力与单位面积潜力 tCO2/ha/yr）

import os
import pandas as pd
import numpy as np
from osgeo import gdal, osr
import matplotlib.pyplot as plt

os.chdir('E:/wzy/2-Grid-based-MONET')

trade = False
maxcb = True
start_year = 2025  # 2025, 2030, 2035, 2040, 2050

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

raster_row = 360
raster_col = 720

# 定义常量
Grid_Cropland_Area_km2 = gdal.Open('./Global Data/EW/Input/Global/Global_cropland_area_km2.tif').ReadAsArray()  # 每个网格的农田面积（km2）（0.5° 分辨率的网格面积不一定是为 55km x 55km，要提前根据经纬度换算，并且乘网格的农田比例），后面用为公顷时需要*100
T_TO_GT = 1e-9  # 吨到千兆吨的转换系数

# 读入数据（多年铺洒得到的结果直接是GtCO2/yr）
if maxcb:
    if trade:
        EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()

        EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (with trade).tif').ReadAsArray()

        EW_max_net_benefit_scenario_array = gdal.Open(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_scenario_raster (with trade).tif').ReadAsArray()
    else:
        EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (GtCO2 yr-1).tif').ReadAsArray()

        EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm.tif').ReadAsArray()

        EW_max_net_benefit_scenario_array = gdal.Open(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_scenario_raster.tif').ReadAsArray()
else:
    if trade:
        EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()
        EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (GtCO2 yr-1) (with trade).tif').ReadAsArray()

        EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (with trade).tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (with trade).tif').ReadAsArray()

        EW_max_net_benefit_scenario_array = gdal.Open(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_scenario_raster (with trade).tif').ReadAsArray()
    else:
        EW_remove_potential_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm (GtCO2 yr-1).tif').ReadAsArray()
        EW_remove_potential_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm (GtCO2 yr-1).tif').ReadAsArray()

        EW_remove_potential_intensity_basalt_2 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_2 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_10 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_10 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_20 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_20 μm.tif').ReadAsArray()
        EW_remove_potential_intensity_basalt_50 = gdal.Open(f'./Output/EW/Global/Removal Potential/{start_year}/multi-year/EW_multi_year_remove_potential_raster_basalt_50 μm.tif').ReadAsArray()

        EW_max_net_benefit_scenario_array = gdal.Open(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_scenario_raster.tif').ReadAsArray()

# 读入岩石类型和颗粒大小
grain_size = pd.read_csv('Input Data/EW/Grain Size.csv', encoding='gbk')
rock_type = pd.read_csv('Input Data/EW/Rock Type.csv', encoding='gbk')

# 构建一个储存每个网格scenario 4情景下所选岩石类型和颗粒大小组合下多年铺洒的潜力的地图（MtCO2/yr）
EW_multi_year_potential_scenario_4_array = np.full((raster_row, raster_col), np.nan)

# 构建一个储存最大净效益所选组合下的强度潜力地图（tCO2/ha/yr）
EW_potential_tCO2_ha_array = np.full((raster_row, raster_col), np.nan)

# 记录每个网格的潜力
EW_multi_year_potential_scenario_4_csv = np.full((360*720, 1), np.nan)  # MtCO2/yr

# 国家边界栅格，每个网格的值是国家代码
country_code_array = gdal.Open('E:/ArcGIS/Projects/Country/Country_code.tif').ReadAsArray()

SCENARIO_NODATA = -9999  # ✅ 你的 scenario 栅格 NoData

for row in range(raster_row):
    for col in range(raster_col):
        remove_potential = [EW_remove_potential_basalt_2[row, col], EW_remove_potential_basalt_10[row, col],
                            EW_remove_potential_basalt_20[row, col], EW_remove_potential_basalt_50[row, col]]

        remove_potential_intensity = [EW_remove_potential_intensity_basalt_2[row, col],
                                      EW_remove_potential_intensity_basalt_10[row, col],
                                      EW_remove_potential_intensity_basalt_20[row, col],
                                      EW_remove_potential_intensity_basalt_50[row, col]]

        v = EW_max_net_benefit_scenario_array[row, col]
        if (not np.isfinite(v)) or (v == SCENARIO_NODATA) or (v <= 0):
            EW_multi_year_potential_scenario_4_array[row, col] = np.nan
            EW_potential_tCO2_ha_array[row, col] = np.nan  # <--- 加入 tCO2/ha 的空值处理
            EW_multi_year_potential_scenario_4_csv[row * 720 + col, 0] = np.nan
            if ~np.all(np.isnan(remove_potential)):  # scenario 4情景在该网格没有技术选择，但是多年铺洒在该网格有潜力，原因可能是单年铺洒在该网格的净移除量小于0，但是多年铺洒就可以大于0
                print("1", row, col)
            continue
        else:
            chosen_idx = int(v) - 1
            EW_multi_year_potential_scenario_4_array[row, col] = remove_potential[chosen_idx] * 1000  # 将GtCO2/yr转化为MtCO2/yr
            EW_potential_tCO2_ha_array[row, col] = remove_potential_intensity[chosen_idx]  # <--- 提取对应技术组合下的 tCO2/ha 强度
            EW_multi_year_potential_scenario_4_csv[row * 720 + col, 0] = EW_multi_year_potential_scenario_4_array[row, col]
            if np.all(np.isnan(remove_potential)):  # scenario 4情景在该网格有技术选择，但是多年铺洒在该网格没有潜力，原因可能是单年铺洒在该网格的净移除量大于0，但是多年铺洒导致小于0
                print("2", row, col)
                print(EW_multi_year_potential_scenario_4_csv[row * 720 + col, 0])

# 储存
if maxcb:
    if trade:
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_multi_year_potential_raster.tif', EW_multi_year_potential_scenario_4_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_multi_year_potential_raster_tCO2_ha.tif', EW_potential_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)  # <--- 保存 tCO2/ha 栅格

        EW_multi_year_potential_scenario_4_csv_df = pd.DataFrame(EW_multi_year_potential_scenario_4_csv)
        EW_multi_year_potential_scenario_4_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_multi_year_potential.csv')
    else:
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_multi_year_potential_raster.tif', EW_multi_year_potential_scenario_4_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_multi_year_potential_raster_tCO2_ha.tif', EW_potential_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)  # <--- 保存 tCO2/ha 栅格

        EW_multi_year_potential_scenario_4_csv_df = pd.DataFrame(EW_multi_year_potential_scenario_4_csv)
        EW_multi_year_potential_scenario_4_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_multi_year_potential.csv')
else:
    if trade:
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_multi_year_potential_raster.tif', EW_multi_year_potential_scenario_4_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_multi_year_potential_raster_tCO2_ha.tif', EW_potential_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)  # <--- 保存 tCO2/ha 栅格

        EW_multi_year_potential_scenario_4_csv_df = pd.DataFrame(EW_multi_year_potential_scenario_4_csv)
        EW_multi_year_potential_scenario_4_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_multi_year_potential.csv')
    else:
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_multi_year_potential_raster.tif', EW_multi_year_potential_scenario_4_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)
        save_raster(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_multi_year_potential_raster_tCO2_ha.tif', EW_potential_tCO2_ha_array, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)  # <--- 保存 tCO2/ha 栅格

        EW_multi_year_potential_scenario_4_csv_df = pd.DataFrame(EW_multi_year_potential_scenario_4_csv)
        EW_multi_year_potential_scenario_4_csv_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_multi_year_potential.csv')

# 计算每个国家的总潜力、有价值ERW面积
country_codes = np.unique(country_code_array[~np.isnan(country_code_array)])  # 获取所有国家代码
country_potential = {}
country_area = {}

for code in country_codes:
    mask = (country_code_array == code) & ~np.isnan(EW_multi_year_potential_scenario_4_array)
    # 总潜力：GtCO2/yr
    country_potential[code] = np.nansum(EW_multi_year_potential_scenario_4_array[mask]) / 1000  # 刚刚EW_multi_year_potential_scenario_4_array变为了MtCO2/yr，再变为GtCO2/yr
    # 总面积：km2
    country_area[code] = np.nansum(Grid_Cropland_Area_km2[mask])

# 将结果转换为DataFrame并排序
country_potential_df = pd.DataFrame(list(country_potential.items()), columns=['Country Code', 'Potential'])
country_potential_df = country_potential_df.sort_values(by='Potential', ascending=False)
country_area_df = pd.DataFrame(list(country_area.items()), columns=['Country Code', 'Cropland Area'])
country_area_df = country_area_df.sort_values(by='Cropland Area', ascending=False)

# 保存csv文件
if maxcb:
    if trade:
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Multi-year Potential Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Multi-year Area Rank.csv')
    else:
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Multi-year Potential Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Multi-year Area Rank.csv')
else:
    if trade:
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Multi-year Potential Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Multi-year Area Rank.csv')
    else:
        country_potential_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Multi-year Potential Rank.csv')
        country_area_df.to_csv(f'./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Multi-year Area Rank.csv')
