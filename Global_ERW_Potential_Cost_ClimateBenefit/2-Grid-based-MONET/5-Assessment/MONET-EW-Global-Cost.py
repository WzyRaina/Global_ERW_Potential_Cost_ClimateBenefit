import os
import pandas as pd
import numpy as np
from osgeo import gdal, osr
import sys
import matplotlib.pyplot as plt
import importlib.util

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

def compute_removal_cost(
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
    mining_diesel,
    crushing_electricity,
    road_transport_diesel,
    rail_transport_diesel,
    ship_transport_HFO,
    rock_application_diesel,
    road_transport_price,
    rail_transport_price,
    ship_transport_price,
    rock_application_price,
    CO2_seq_potential_dict,
    pathway,
    uncertainty=False,
    trade=False
):
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

    # construct cost structure of EW in MONET, as well as output we want to get
    EW_cost_structure = pd.DataFrame(columns=['Energy cost ($/t rock)',
                                              'Machinery cost ($/t rock)',
                                              'Labour Cost ($/t rock)',
                                              'Material cost ($/t rock)',
                                              'CAPEX and OPEX of the mining facility ($/t rock)'],
                                     index=['Mining',
                                            'Crushing & Grinding',
                                            'Transport',
                                            'Application on Soil'])
    # construct total cost structure of EW, $/t rock
    EW_total_cost_structure = pd.DataFrame(columns=['Region', 'Mining ($/t rock)', 'Crushing & Grinding ($/t rock)',
                                                    'Transport ($/t rock)', 'Application on Soil ($/t rock)',
                                                    'Total costs ($/t rock)'],
                                           index=range(500))  # 500 is a large number for five regions' sub-regions

    # construct cost raster data ($/tCO2 captured)
    # 不归一化
    EW_cost_raster_array_rock_cap = np.full((raster_row, raster_col), np.nan)

    # construct cost raster data ($/tCO2 removed)
    # 不归一化
    EW_cost_raster_array_rock_rem = np.full((raster_row, raster_col), np.nan)
    # 记录每个网格的成本
    EW_rem_cost_csv = np.full((360*720, 8), np.nan)

    # compute carbon emissions
    # compute carbon emissions (tCO2e/t rock)
    # row 1
    EW_emission_structure.iloc[0, 0] = mining_diesel / 1000 * 3600 / Energy_data.iloc[2, 2] * Carbon_data.iloc[2, 2] / 1000  # kWh/t rock / 1000 = MWh/t rock, MWh/t rock * 3600 = MJ/t rock
    EW_emission_structure.iloc[0, 1] = mining_diesel / 1000 * 3600 / Energy_data.iloc[2, 2] * Carbon_data.iloc[14, 2] / 1000
    EW_emission_structure.iloc[0, 2] = EW_data.iloc[9, 2] * EW_data.iloc[10, 2] * EW_data.iloc[24, 2] * (Carbon_data.iloc[26, 2] + (Carbon_data.iloc[46, 2] + Carbon_data.iloc[47, 2] * Carbon_data.iloc[48, 2] + Carbon_data.iloc[49, 2] * Carbon_data.iloc[50, 2]) * EW_data.iloc[23, 2] * other_data.iloc[0, 2]) / 1000
    # row 2
    EW_emission_structure.iloc[1, 0] = 0
    EW_emission_structure.iloc[1, 2] = 0
    # row 3
    EW_emission_structure.iloc[2, 2] = 0
    # row 4
    EW_emission_structure.iloc[3, 0] = rock_application_diesel / 1000 * 3600 / Energy_data.iloc[2, 2] * Carbon_data.iloc[2, 2] / 1000
    EW_emission_structure.iloc[3, 1] = rock_application_diesel / 1000 * 3600 / Energy_data.iloc[2, 2] * Carbon_data.iloc[14, 2] / 1000
    EW_emission_structure.iloc[3, 2] = 0

    EW_total_emission_structure.iloc[0, 1] = EW_emission_structure.iloc[0, 0] + EW_emission_structure.iloc[0, 1] + EW_emission_structure.iloc[0, 2]
    EW_total_emission_structure.iloc[0, 4] = EW_emission_structure.iloc[3, 0] + EW_emission_structure.iloc[3, 1] + EW_emission_structure.iloc[3, 2]

    # compute cost ($/t rock)
    # row 1
    EW_cost_structure.iloc[0, 1] = 0
    EW_cost_structure.iloc[0, 2] = 0
    EW_cost_structure.iloc[0, 3] = 0
    EW_cost_structure.iloc[0, 4] = 0  # 采矿成本统一为矿石价格，不区分能源还是投资和运维，统一在EW_cost_structure.iloc[0, 0]中计算
    # row 2
    EW_cost_structure.iloc[1, 1] = 0
    EW_cost_structure.iloc[1, 2] = 0
    EW_cost_structure.iloc[1, 3] = 0
    EW_cost_structure.iloc[1, 4] = 0
    # row 3
    EW_cost_structure.iloc[2, 1] = 0
    EW_cost_structure.iloc[2, 2] = 0
    EW_cost_structure.iloc[2, 3] = 0
    EW_cost_structure.iloc[2, 4] = 0
    # row 4
    EW_cost_structure.iloc[3, 2] = 0
    EW_cost_structure.iloc[3, 3] = 0
    EW_cost_structure.iloc[3, 4] = 0

    for r in range(num_of_type):
        # print(rock_type.iloc[r, 0])
        for s in range(num_of_grain_size):
            # print(grain_size.iloc[s, 0])

            # 统一从字典读取 Gross Potential 数据
            # 无论 uncertainty 真假，都从传入的 dict 中获取数据
            rock_key = rock_type.iloc[r, 0].lower()
            grain_key = f"{grain_size.iloc[s, 0]}μm"
            if pathway == 2:
                grain_key += "_1"

            dict_key = (rock_key, grain_key)

            # 获取 1D 数组并 Reshape
            CO2_seq_potential_rock = CO2_seq_potential_dict[dict_key].reshape(raster_row, raster_col)

            # transport distance
            if trade:
                EW_global_transport_distance_array_rock = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Global Data/EW/Output/Global/EW_global_transport_distance_{rock_type.iloc[r, 0]} (with trade).tif').ReadAsArray()  # with trade
            else:
                EW_global_transport_distance_array_rock = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Global Data/EW/Output/Global/EW_global_transport_distance_{rock_type.iloc[r, 0]}.tif').ReadAsArray()  # no trade

            for row in range(raster_row):
                for col in range(raster_col):
                    if country_code_array[row, col] >= 0:  # 中国省份代码都大于0
                        if EW_land_array[row, col] > 0:  # available for EW
                            if not np.isnan(EW_global_transport_distance_array_rock[row, col]):  # no rock source in this country
                                if EEF_array[row, col] >= 0:
                                    # compute carbon emissions (tCO2e/t rock)
                                    EW_emission_structure.iloc[1, 1] = (crushing_electricity + 10 * work_index[r] * (1 / np.sqrt(grain_size.iloc[s, 0]) - 1 / np.sqrt(F_80))) * EEF_array[row, col] / 1000000

                                    if start_year == 2025:  # 2025 or 1990
                                        EW_emission_structure.iloc[2, 0] = ((road_transport_diesel * transport_mode.iloc[0, 2] + rail_transport_diesel * transport_mode.iloc[1, 2]) * 3.6 / Energy_data.iloc[2, 2] * Carbon_data.iloc[2, 2] + ship_transport_HFO * transport_mode.iloc[2, 2] * 3.6 / Energy_data.iloc[6, 2] * Carbon_data.iloc[7, 2]) * EW_global_transport_distance_array_rock[row, col] / 1000
                                        EW_emission_structure.iloc[2, 1] = ((road_transport_diesel * transport_mode.iloc[0, 2] + rail_transport_diesel * transport_mode.iloc[1, 2]) * 3.6 / Energy_data.iloc[2, 2] * Carbon_data.iloc[14, 2] + ship_transport_HFO * transport_mode.iloc[2, 2] * 3.6 / Energy_data.iloc[6, 2] * Carbon_data.iloc[19, 2]) * EW_global_transport_distance_array_rock[row, col] / 1000
                                    else:
                                        if start_year not in shares_by_year:
                                            raise ValueError(f"year_target={start_year} not in shares_by_year. Available: {list(shares_by_year.keys())}")
                                        road_share_foss = shares_by_year[start_year]["road_foss"]
                                        road_share_elec = shares_by_year[start_year]["road_elec"]
                                        ship_share_foss = shares_by_year[start_year]["ship_foss"]

                                        e_rr = road_transport_diesel * transport_mode.iloc[0, 2] + rail_transport_diesel * transport_mode.iloc[1, 2]  # kWh/km/t
                                        e_ship = ship_transport_HFO * transport_mode.iloc[2, 2]  # kWh/km/t

                                        # road+rail diesel (fossil share)
                                        rr_direct_kg_per_km = (e_rr * road_share_foss) * 3.6 / Energy_data.iloc[2, 2] * Carbon_data.iloc[2, 2]
                                        rr_indir_kg_per_km  = (e_rr * road_share_foss) * 3.6 / Energy_data.iloc[2, 2] * Carbon_data.iloc[14, 2]

                                        # road+rail electricity (electricity share) — count as indirect
                                        rr_elec_kg_per_km = (e_rr * road_share_elec) * (EEF_array[row, col] / 1000.0)  # g/kWh -> kg/kWh

                                        # shipping HFO (fossil share)
                                        ship_direct_kg_per_km = (e_ship * ship_share_foss) * 3.6 / Energy_data.iloc[6, 2] * Carbon_data.iloc[7, 2]
                                        ship_indir_kg_per_km  = (e_ship * ship_share_foss) * 3.6 / Energy_data.iloc[6, 2] * Carbon_data.iloc[19, 2]

                                        # write back (tCO2eq/t rock)
                                        EW_emission_structure.iloc[2, 0] = (rr_direct_kg_per_km + ship_direct_kg_per_km) * EW_global_transport_distance_array_rock[row, col] / 1000.0
                                        EW_emission_structure.iloc[2, 1] = (rr_indir_kg_per_km  + ship_indir_kg_per_km + rr_elec_kg_per_km) * EW_global_transport_distance_array_rock[row, col] / 1000.0

                                    # compute total emissions
                                    EW_total_emission_structure.iloc[0, 2] = EW_emission_structure.iloc[1, 0] + EW_emission_structure.iloc[1, 1] + EW_emission_structure.iloc[1, 2]
                                    EW_total_emission_structure.iloc[0, 3] = EW_emission_structure.iloc[2, 0] + EW_emission_structure.iloc[2, 1] + EW_emission_structure.iloc[2, 2]
                                    EW_total_emission_structure.iloc[0, 5] = (EW_total_emission_structure.iloc[0, 1] + EW_total_emission_structure.iloc[0, 2] +
                                                                              EW_total_emission_structure.iloc[0, 3] + EW_total_emission_structure.iloc[0, 4])

                                    # compute cost ($/t rock)
                                    # row 1
                                    EW_cost_structure.iloc[0, 0] = rock_price_array[row, col]  # 采矿成本为砂石骨料价格
                                    # row 2
                                    EW_cost_structure.iloc[1, 0] = (crushing_electricity + 10 * work_index[r] * (1 / np.sqrt(grain_size.iloc[s, 0]) - 1 / np.sqrt(F_80))) * electricity_price_array[row, col] / 1000  # energy for grinding is different for grain size
                                    # row 3
                                    EW_cost_structure.iloc[2, 0] = EW_global_transport_distance_array_rock[row, col] * (road_transport_price * transport_mode.iloc[0, 2] + rail_transport_price * transport_mode.iloc[1, 2] + ship_transport_price * transport_mode.iloc[2, 2])
                                    # row 4
                                    EW_cost_structure.iloc[3, 0] = rock_application_diesel / 1000 * 3600 / Energy_data.iloc[2, 2] * diesel_cost_array[row, col]
                                    EW_cost_structure.iloc[3, 1] = rock_application_price * hourly_compensation_costs_array[row, col]

                                    # compute total costs
                                    EW_total_cost_structure.iloc[0, 1] = EW_cost_structure.iloc[0, 0] + EW_cost_structure.iloc[0, 1] + EW_cost_structure.iloc[0, 2] + EW_cost_structure.iloc[0, 3] + EW_cost_structure.iloc[0, 4]
                                    EW_total_cost_structure.iloc[0, 2] = EW_cost_structure.iloc[1, 0] + EW_cost_structure.iloc[1, 1] + EW_cost_structure.iloc[1, 2] + EW_cost_structure.iloc[1, 3] + EW_cost_structure.iloc[1, 4]
                                    EW_total_cost_structure.iloc[0, 3] = EW_cost_structure.iloc[2, 0] + EW_cost_structure.iloc[2, 1] + EW_cost_structure.iloc[2, 2] + EW_cost_structure.iloc[2, 3] + EW_cost_structure.iloc[2, 4]
                                    EW_total_cost_structure.iloc[0, 4] = EW_cost_structure.iloc[3, 0] + EW_cost_structure.iloc[3, 1] + EW_cost_structure.iloc[3, 2] + EW_cost_structure.iloc[3, 3] + EW_cost_structure.iloc[3, 4]
                                    EW_total_cost_structure.iloc[0, 5] = (EW_total_cost_structure.iloc[0, 1] + EW_total_cost_structure.iloc[0, 2] +
                                                                          EW_total_cost_structure.iloc[0, 3] + EW_total_cost_structure.iloc[0, 4])

                                    # 不归一化
                                    CO2_removal_potential_rock = CO2_seq_potential_rock[row, col] - EW_total_emission_structure.iloc[0, 5]
                                    if CO2_removal_potential_rock > 0:
                                        EW_cost_raster_array_rock_cap[row, col] = EW_total_cost_structure.iloc[0, 5] / CO2_seq_potential_rock[row, col]
                                        EW_cost_raster_array_rock_rem[row, col] = EW_total_cost_structure.iloc[0, 5] / CO2_removal_potential_rock
                                        # if EW_cost_raster_array_rock_rem[row, col] <= 1000:
                                        EW_rem_cost_csv[row * 720 + col, r * 4 + s] = EW_cost_raster_array_rock_rem[row, col]
                                    else:
                                        EW_cost_raster_array_rock_cap[row, col] = np.nan
                                        EW_cost_raster_array_rock_rem[row, col] = np.nan
                                else:
                                    EW_cost_raster_array_rock_cap[row, col] = np.nan
                                    EW_cost_raster_array_rock_rem[row, col] = np.nan
                            else:
                                EW_cost_raster_array_rock_cap[row, col] = np.nan
                                EW_cost_raster_array_rock_rem[row, col] = np.nan
                        else:
                            EW_cost_raster_array_rock_cap[row, col] = np.nan
                            EW_cost_raster_array_rock_rem[row, col] = np.nan
                    else:
                        EW_cost_raster_array_rock_cap[row, col] = np.nan
                        EW_cost_raster_array_rock_rem[row, col] = np.nan

            # 仅当 uncertainty=False 时保存 TIFF
            if not uncertainty:
                if pathway == 1:
                    if trade:
                        out_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm (with trade).tif'
                    else:
                        out_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm.tif'
                if pathway == 2:
                    if trade:
                        out_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm (with trade)_1.tif'
                    else:
                        out_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/EW_remove_cost_raster_{rock_type.iloc[r, 0]}_{grain_size.iloc[s, 0]} μm_1.tif'

                save_raster(out_path, EW_cost_raster_array_rock_rem, geotransform=(-180, 0.5, 0, 90, 0, -0.5), epsg=4326, dtype=gdal.GDT_Float32)

    # 准备返回数据
    results = {
        "EW_rem_cost_csv": EW_rem_cost_csv
    }

    # 仅当 uncertainty=False 时保存 CSV
    if not uncertainty:
        if pathway == 1:
            if trade:
                csv_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/Removal Cost (with trade).csv'
            else:
                csv_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/Removal Cost.csv'
        if pathway == 2:
            if trade:
                csv_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/Removal Cost (with trade)_1.csv'
            else:
                csv_path = f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Cost/{start_year}/Removal Cost_1.csv'

        pd.DataFrame(EW_rem_cost_csv).to_csv(csv_path, index=False)

    # 始终返回结果
    return results


# 主函数
if __name__ == "__main__":
    os.chdir('E:/wzy/2-Grid-based-MONET')

    # 1. 加载参数 (立即修约)
    print("[TEST] Loading basic parameters...")

    # read electricity emission factors (from ArcGISPro)
    EEF_array = gdal.Open('E:/ArcGIS/Projects/Country/UNFCCC_Electricity_Factor.tif').ReadAsArray()  # 0.5°*0.5°; unit: gCO2eq/kWh; /3600 (kgCO2e/MJ)
    # land available for EW
    EW_land_array = gdal.Open('./Global Data/EW/Input/Global/Global cropland map.tif').ReadAsArray()
    # 国家代码，大于等于0
    country_code_array = gdal.Open('E:/ArcGIS/Projects/Country/Country_code.tif').ReadAsArray()

    PH_array = np.round(gdal.Open('E:/ArcGIS/Projects/GetData/T_PH_H20.tif').ReadAsArray(), 2)
    soil_temperature_array = np.round(gdal.Open('E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif').ReadAsArray(), 2)

    start_year = 2025
    raster_row, raster_col = 360, 720
    pathway = 1

    params_dict_core = {
        "k_H_dunite": 5.55e-8, "n_H_dunite": 0.372,
        "k_H_basalt": 588, "n_H_basalt": 1.16,
        "k_OH_basalt": 0.0822, "n_OH_basalt": 0.16,
        "E_a": 47500, "b": 5.2, "m": -1
    }

    work_index = [17.93, 12.38]  # basalt=17.93, dunite=12.38
    F_80 = 1000  # μm

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
    transport_cost = pd.read_csv('Raw Data/Common Data/Transport Mode Cost.csv', encoding='gbk')

    # read cost data
    # diesel cost
    diesel_cost_array = gdal.Open('E:/ArcGIS/Projects/Country/Diesel_Cost_Raster.tif').ReadAsArray()  # $/l
    # Hourly Compensation Costs
    hourly_compensation_costs_array = gdal.Open('E:/ArcGIS/Projects/Country/GNI_Raster.tif').ReadAsArray()  # %, USA: 1
    # electricity price
    electricity_price_array = gdal.Open('E:/ArcGIS/Projects/Country/Electricity_Price_Raster.tif').ReadAsArray()  # $/MWh; /3600 ($/MJ)
    # rock price
    rock_price_array = gdal.Open('E:/ArcGIS/Projects/Country/Rock_Price.tif').ReadAsArray()  # $/t rock

    # 2. 动态加载粒径生成函数 -> 获取 psd_dict
    print("[TEST] Generating PSD Dict...")
    gs_spec = importlib.util.spec_from_file_location("grain_size", r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py")
    gs_module = importlib.util.module_from_spec(gs_spec)
    gs_spec.loader.exec_module(gs_module)
    psd_dict = gs_module.generate_psd_for_multiple_p80(sigma=0.5, plot=False, uncertainty=False)

    # 3. 动态加载碳封存函数 -> 计算并获取 Gross Potential results
    print("[TEST] Calculating Potential Maps...")
    core_spec = importlib.util.spec_from_file_location("core_model", r"E:/wzy/1-CDR-Base/EW/ERW_Core_Model.py")
    core_module = importlib.util.module_from_spec(core_spec)
    core_spec.loader.exec_module(core_module)

    # 这里的 pot_results 包含的是 Gross Potential (CO2_seq_potential)
    pot_results = core_module.carbon_sequestration_potential(
        EW_raw_data=EW_data, grain_size=grain_size, PH_array=PH_array,
        soil_temperature_array=soil_temperature_array, start_year=start_year, end_year=2200,
        simulated_year=200, **params_dict_core, pathway=pathway,
        grain_size_psd_dict=psd_dict, uncertainty=False
    )

    # 4. [关键步骤] 重组数据格式 (CSV Columns -> Dict Keys)
    print("[TEST] Restructuring data for Cost calculation...")
    seq_dict_input = {}

    sizes = [2, 10, 20, 50]

    # Dunite
    for i, size in enumerate(sizes):
        key_suffix = f"{size}μm" if pathway == 1 else f"{size}μm_1"
        key = ('dunite', key_suffix)
        seq_dict_input[key] = pot_results["CO2_seq_potential_dunite_csv"][:, i]

    # Basalt
    for i, size in enumerate(sizes):
        key_suffix = f"{size}μm" if pathway == 1 else f"{size}μm_1"
        key = ('basalt', key_suffix)
        seq_dict_input[key] = pot_results["CO2_seq_potential_basalt_csv"][:, i]

    # 5. 调用移除成本函数
    print("[TEST] Running compute_removal_cost...")
    cost_results = compute_removal_cost(
        start_year=start_year,
        shares_by_year={},
        EEF_array=EEF_array,
        EW_land_array=EW_land_array,
        country_code_array=country_code_array,
        hourly_compensation_costs_array=hourly_compensation_costs_array,
        raster_row=raster_row,
        raster_col=raster_col,
        rock_type=rock_type,
        grain_size=grain_size,
        EW_data=EW_data,
        Energy_data=Energy_data,
        Carbon_data=Carbon_data,
        transport_mode=transport_mode,
        other_data=other_data,
        work_index=work_index,
        F_80=F_80,
        diesel_cost_array=diesel_cost_array,
        electricity_price_array=electricity_price_array,
        rock_price_array=rock_price_array,
        mining_diesel=EW_data.iloc[3, 2],
        crushing_electricity=EW_data.iloc[4, 2],
        road_transport_diesel=Energy_data.iloc[18, 2],
        rail_transport_diesel=Energy_data.iloc[19, 2],
        ship_transport_HFO=Energy_data.iloc[20, 2],
        rock_application_diesel=EW_data.iloc[7, 2],
        road_transport_price=transport_cost.iloc[0, 2],
        rail_transport_price=transport_cost.iloc[1, 2],
        ship_transport_price=transport_cost.iloc[2, 2],
        rock_application_price=23.383,
        CO2_seq_potential_dict=seq_dict_input,  # 传入重组后的 Gross Potential 字典
        pathway=pathway,
        uncertainty=False,
        trade=False
    )

    print("[TEST] Success! Returned keys:", cost_results.keys())
