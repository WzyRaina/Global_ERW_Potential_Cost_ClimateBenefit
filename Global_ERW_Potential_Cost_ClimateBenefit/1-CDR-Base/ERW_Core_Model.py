# 定义了很多ERW需要的功能：计算碳封存潜力、风化速率曲线

import numpy as np
import pandas as pd
from osgeo import gdal, osr
import math
import os
import importlib.util


# =============================================================================
# 1. 核心物理计算函数 (底层逻辑，通用)
# =============================================================================
def core_weathering_calculation(
        pH,
        temp_c,
        diameters,  # numpy array
        fractions,  # numpy array
        simulated_year,
        # 动力学参数 (全部显式传入，确保一致性)
        k_H_dunite, n_H_dunite,
        k_H_basalt, n_H_basalt,
        k_OH_basalt, n_OH_basalt,
        E_a, b, m
):
    """
    基础物理引擎：计算给定条件下的累积风化比例。
    此函数保持接收纯数值数组(numpy array)，以保证底层运算的高效和解耦。
    返回: (simulated_year, 2) 数组，列0为Dunite，列1为Basalt。
    """
    # Constants
    T_std = 298.15  # K (25°C)
    R = 8.314472  # J·mol-1·K-1
    density_basalt = 3  # g·cm-3
    density_dunite = 3.27  # g·cm-3
    basalt_molar_volume = 4.167e-5  # m³/mol
    dunite_molar_volume = 4.302e-5  # m³/mol
    seconds_per_year = 365 * 24 * 60 * 60
    μm_per_m = 1e6

    yr = np.arange(0, simulated_year, 1)

    # 1. 几何参数 (Size-dependent)
    # diameters 和 fractions 必须是 numpy array
    SSA_BET_array = 10 ** (b + m * np.log10(diameters))
    SSA_GEO_basalt = 6 / (diameters * 1e-4 * density_basalt)
    SSA_GEO_dunite = 6 / (diameters * 1e-4 * density_dunite)

    Rf_basalt_array = SSA_BET_array / SSA_GEO_basalt
    Rf_dunite_array = SSA_BET_array / SSA_GEO_dunite

    # 2. 温度修正 (Arrhenius)
    temp_k = temp_c + 273.15
    delta_T = (1 / temp_k) - (1 / T_std)
    correction_factor = math.exp(-E_a * delta_T / R)

    k_H_dunite_mod = k_H_dunite * correction_factor
    k_H_basalt_mod = k_H_basalt * correction_factor
    k_OH_basalt_mod = k_OH_basalt * correction_factor

    # 3. 溶解速率 (Rate Laws)
    # Dunite
    R_diss_dunite = k_H_dunite_mod * pow(10, -n_H_dunite * pH)

    # Basalt (Acid + Base + Temp correction on total structure per original logic)
    term_acid = k_H_basalt_mod * pow(10, -n_H_basalt * pH)
    term_base = k_OH_basalt_mod * pow(10, n_OH_basalt * (pH - 14))

    R_diss_basalt = (term_acid + term_base) * math.exp(-E_a / (R * T_std))

    # 4. 粗糙度与收缩核
    R_diss_dunite_vec = R_diss_dunite * Rf_dunite_array
    R_diss_basalt_vec = R_diss_basalt * Rf_basalt_array

    # Depth dissolved (μm)
    # shape: (n_diameter, simulated_year)
    # Broadcasting: (n_diam, 1) * (1, n_year) -> (n_diam, n_year)
    depth_dissolved_dunite = (2 * R_diss_dunite_vec[:, None] * dunite_molar_volume * yr * seconds_per_year * μm_per_m)
    depth_dissolved_basalt = (2 * R_diss_basalt_vec[:, None] * basalt_molar_volume * yr * seconds_per_year * μm_per_m)

    d0_array = diameters[:, None]

    # New diameters
    d_new_dunite = np.maximum(d0_array - depth_dissolved_dunite, 0)
    d_new_basalt = np.maximum(d0_array - depth_dissolved_basalt, 0)

    # Conversion Ratio (fraction dissolved)
    CR_part_dunite = (d0_array ** 3 - d_new_dunite ** 3) / d0_array ** 3
    CR_part_basalt = (d0_array ** 3 - d_new_basalt ** 3) / d0_array ** 3

    # Weighted Sum
    # fractions shape: (n_diam,) -> (n_diam, 1)
    CR_weighted_dunite = np.sum(fractions[:, None] * CR_part_dunite, axis=0)
    CR_weighted_basalt = np.sum(fractions[:, None] * CR_part_basalt, axis=0)

    # Cap at 1.0
    CR_weighted_dunite = np.minimum(CR_weighted_dunite, 1)
    CR_weighted_basalt = np.minimum(CR_weighted_basalt, 1)

    return np.stack((CR_weighted_dunite, CR_weighted_basalt), axis=-1)


# =============================================================================
# 2. 外部接口函数 (给 FAIR 等气候模型调用年风化速率曲线)
# =============================================================================
def get_annual_rate_curve(
        rock_type,  # 'Basalt' 或 'Dunite'
        pH_scalar,
        temp_scalar,
        grain_size_psd_dict,  # 传入 PSD 字典
        p80,  # 传入 p80 值 (int)
        simulated_year,
        params_dict  # 包含 k_H, E_a 等所有参数的字典
):
    """
    专门给 FAIR 等气候模型模型调用的接口。
    输入：
        - rock_type: 岩石类型字符串
        - pH_scalar: pH 值 (浮点数)
        - temp_scalar: 温度 (浮点数，摄氏度)
        - grain_size_psd_dict: {p80: dataframe} 字典
        - p80: 目标粒径 (int, 如 2, 10, 20, 50)
        - simulated_year: 模拟年限
        - params_dict: 参数字典
    输出：
        - annual_rates: 一维数组 (Annual Weathering Rate), 长度为 simulated_year
    """

    grain_size_distribution = grain_size_psd_dict[int(p80)]
    diameters = grain_size_distribution['Diameter'].values
    fractions = grain_size_distribution['Fraction'].values

    # 1. 调用核心计算
    cumulative_curves = core_weathering_calculation(
        pH=pH_scalar,
        temp_c=temp_scalar,
        diameters=diameters,
        fractions=fractions,
        simulated_year=simulated_year,
        # 从字典解包参数，确保与主文件参数一致
        k_H_dunite=params_dict['k_H_dunite'],
        n_H_dunite=params_dict['n_H_dunite'],
        k_H_basalt=params_dict['k_H_basalt'],
        n_H_basalt=params_dict['n_H_basalt'],
        k_OH_basalt=params_dict['k_OH_basalt'],
        n_OH_basalt=params_dict['n_OH_basalt'],
        E_a=params_dict['E_a'],
        b=params_dict['b'],
        m=params_dict['m']
    )

    # 2. 提取指定岩石的累积曲线
    if rock_type.lower() == 'dunite':
        cumulative_curve = cumulative_curves[:, 0]
    elif rock_type.lower() == 'basalt':
        cumulative_curve = cumulative_curves[:, 1]
    else:
        raise ValueError(f"Unknown rock type: {rock_type}")

    # 3. 转为年度增量 (Annual Rate)
    # Annual[i] = Cumulative[i] - Cumulative[i-1]
    annual_rates = np.zeros_like(cumulative_curve)
    annual_rates[0] = cumulative_curve[0]
    annual_rates[1:] = cumulative_curve[1:] - cumulative_curve[:-1]

    return annual_rates


# =============================================================================
# 3. 保存数据函数 (提前计算碳封存潜力地图并保存供后面读取)
# =============================================================================
def carbon_sequestration_potential(
        EW_raw_data,
        grain_size,
        PH_array,
        soil_temperature_array,
        start_year,
        end_year,
        simulated_year,
        # 不确定性参数
        k_H_dunite, n_H_dunite,
        k_H_basalt, n_H_basalt,
        k_OH_basalt, n_OH_basalt,
        E_a, b, m,
        # 其他参数
        raster_row=360,
        raster_col=720,
        pathway=1,
        grain_size_psd_dict=None,
        output_folder="E:/wzy/1-CDR-Base/EW/Output/Raster Data/",
        uncertainty=False,
):
    """
    计算全球碳封存潜力地图。
    """

    # Initialize output arrays (Flattened for CSV export)
    total_pixels = raster_row * raster_col

    num_sizes = len(grain_size)

    CO2_seq_potential_dunite_csv = np.full((total_pixels, num_sizes), np.nan)
    CO2_seq_potential_basalt_csv = np.full((total_pixels, num_sizes), np.nan)
    weathering_rate_dunite_csv = np.full((total_pixels, num_sizes), np.nan)
    weathering_rate_basalt_csv = np.full((total_pixels, num_sizes), np.nan)

    # Loop over grain sizes (assuming 4 files based on original code)
    for s in range(num_sizes):
        # Load grain size distribution
        p80 = int(grain_size.iloc[s, 0])
        s_distribution = grain_size_psd_dict[p80]

        # 在这里直接提取 numpy array，传递给 core 函数
        diameters = s_distribution['Diameter'].values
        fractions = s_distribution['Fraction'].values

        current_size_label = grain_size.iloc[s, 0]
        print(f"Processing Grain Size: {current_size_label} μm...")

        # Initialize Raster Grids for this grain size
        CO2_seq_grid_dunite = np.full((raster_row, raster_col), np.nan)
        CO2_seq_grid_basalt = np.full((raster_row, raster_col), np.nan)
        rate_grid_dunite = np.full((raster_row, raster_col), np.nan)
        rate_grid_basalt = np.full((raster_row, raster_col), np.nan)

        # Loop pixels
        for row in range(raster_row):
            for col in range(raster_col):
                ph_val = PH_array[row, col]
                temp_val = soil_temperature_array[row, col]

                # Valid pixel check
                if ph_val > 0 and temp_val > -256:

                    # Call Core Physics Function
                    # 这里 diameters 和 fractions 已经是 numpy array 了，符合 core 函数要求
                    CR_weighted = core_weathering_calculation(
                        pH=ph_val,
                        temp_c=temp_val,
                        diameters=diameters,
                        fractions=fractions,
                        simulated_year=simulated_year,
                        k_H_dunite=k_H_dunite, n_H_dunite=n_H_dunite,
                        k_H_basalt=k_H_basalt, n_H_basalt=n_H_basalt,
                        k_OH_basalt=k_OH_basalt, n_OH_basalt=n_OH_basalt,
                        E_a=E_a, b=b, m=m
                    )

                    # Extract the value at the target year index
                    # Note: Original code used [end_year - start_year] as index
                    target_idx = end_year - start_year
                    # Ensure index is within bounds
                    if target_idx >= simulated_year:
                        target_idx = simulated_year - 1

                    rate_dunite = CR_weighted[target_idx, 0]
                    rate_basalt = CR_weighted[target_idx, 1]

                    # CO2 Sequestration Calculation (Tonnes CO2)
                    if pathway == 1:
                        seq_dunite = (EW_raw_data.iloc[28, 2] * EW_raw_data.iloc[27, 2] * rate_dunite / 1000)
                        seq_basalt = (EW_raw_data.iloc[28, 2] * EW_raw_data.iloc[26, 2] * rate_basalt / 1000)
                    elif pathway == 2:
                        seq_dunite = (EW_raw_data.iloc[29, 2] * EW_raw_data.iloc[27, 2] * rate_dunite / 1000)
                        seq_basalt = (EW_raw_data.iloc[29, 2] * EW_raw_data.iloc[26, 2] * rate_basalt / 1000)
                    else:
                        seq_dunite, seq_basalt = np.nan, np.nan

                    # Assign to Grids
                    CO2_seq_grid_dunite[row, col] = seq_dunite
                    CO2_seq_grid_basalt[row, col] = seq_basalt
                    rate_grid_dunite[row, col] = rate_dunite
                    rate_grid_basalt[row, col] = rate_basalt

                    # Assign to CSV Arrays
                    idx = row * raster_col + col
                    CO2_seq_potential_dunite_csv[idx, s] = seq_dunite
                    CO2_seq_potential_basalt_csv[idx, s] = seq_basalt
                    weathering_rate_dunite_csv[idx, s] = rate_dunite
                    weathering_rate_basalt_csv[idx, s] = rate_basalt

        # Save Rasters (Only if not uncertainty analysis, per original logic)
        if not uncertainty:
            # Helper for directory creation
            out_dir = os.path.join(output_folder, str(start_year))
            if not os.path.exists(out_dir):
                os.makedirs(out_dir)

            suffix = "" if pathway == 1 else "_1"

            save_geotiff(CO2_seq_grid_dunite,
                         f"{out_dir}/CO2_seq_potential_dunite(tCO2·t rock-1)_{current_size_label} μm{suffix}.tif",
                         raster_row, raster_col)
            save_geotiff(CO2_seq_grid_basalt,
                         f"{out_dir}/CO2_seq_potential_basalt(tCO2·t rock-1)_{current_size_label} μm{suffix}.tif",
                         raster_row, raster_col)
            save_geotiff(rate_grid_dunite, f"{out_dir}/weathering_rate_dunite_{current_size_label} μm{suffix}.tif",
                         raster_row, raster_col)
            save_geotiff(rate_grid_basalt, f"{out_dir}/weathering_rate_basalt_{current_size_label} μm{suffix}.tif",
                         raster_row, raster_col)

    # 1. 准备返回数据
    results = {
        "weathering_rate_dunite_csv": weathering_rate_dunite_csv,
        "weathering_rate_basalt_csv": weathering_rate_basalt_csv,
        "CO2_seq_potential_dunite_csv": CO2_seq_potential_dunite_csv,
        "CO2_seq_potential_basalt_csv": CO2_seq_potential_basalt_csv
    }

    # 2. 仅当非不确定性分析时，保存 CSV 文件
    if not uncertainty:
        suffix = "" if pathway == 1 else "_1"
        out_dir = os.path.join(output_folder, str(start_year))
        # 再次检查目录是否存在 (虽然上面栅格保存时已经检查过)
        if not os.path.exists(out_dir):
            os.makedirs(out_dir)

        pd.DataFrame(weathering_rate_dunite_csv).to_csv(
            os.path.join(out_dir, f"weathering_rate_dunite{suffix}.csv"), index=False)
        pd.DataFrame(weathering_rate_basalt_csv).to_csv(
            os.path.join(out_dir, f"weathering_rate_basalt{suffix}.csv"), index=False)
        pd.DataFrame(CO2_seq_potential_dunite_csv).to_csv(
            os.path.join(out_dir, f"CO2_seq_potential_dunite{suffix}.csv"), index=False)
        pd.DataFrame(CO2_seq_potential_basalt_csv).to_csv(
            os.path.join(out_dir, f"CO2_seq_potential_basalt{suffix}.csv"), index=False)

    # 3. 始终返回数据
    return results


def save_geotiff(array, filename, rows, cols):
    driver = gdal.GetDriverByName("GTiff")
    raster = driver.Create(filename, cols, rows, 1, gdal.GDT_Float32)
    # GeoTransform: [top_left_x, w_e_pixel_resolution, rotation, top_left_y, rotation, n_s_pixel_resolution]
    raster.SetGeoTransform([-180, 0.5, 0, 90, 0, -0.5])
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(4326)
    raster.SetProjection(srs.ExportToWkt())
    raster.GetRasterBand(1).WriteArray(array)
    raster.FlushCache()
    raster = None


# =============================================================================
# 测试
# =============================================================================
if __name__ == "__main__":
    # -------------------------------------------------------------------------
    # 1. 准备数据和参数
    # -------------------------------------------------------------------------
    print("正在读取输入数据...")

    round_number = 2  # 统一保留2位小数

    EW_raw_data = pd.read_csv('E:/wzy/2-Grid-based-MONET/Raw Data/EW/EW.csv', encoding='gbk')
    grain_size = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Grain Size.csv', encoding='gbk')

    # 读取栅格数据
    PH = gdal.Open('E:/ArcGIS/Projects/GetData/T_PH_H20.tif')
    PH_array = np.round(PH.ReadAsArray(), round_number)
    soil_temperature = gdal.Open('E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif')
    soil_temperature_array = np.round(soil_temperature.ReadAsArray(), round_number)

    # -------------------------------------------------------------------------
    # 动态生成粒径分布字典
    # -------------------------------------------------------------------------
    print("\n[初始化] 正在生成粒径分布数据 (PSD Dictionary)...")

    # 导入粒径生成脚本
    grain_size_distribution_file_path = r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
    spec_psd = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
    grain_size_distribution_py = importlib.util.module_from_spec(spec_psd)
    spec_psd.loader.exec_module(grain_size_distribution_py)

    # 调用生成函数获取 psd_dict
    psd_dict = grain_size_distribution_py.generate_psd_for_multiple_p80(
        sigma=0.5,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
        plot=False,
        uncertainty=False  # 即使为 False，新修改的代码也会返回字典
    )
    print("粒径分布字典生成完成。")

    # 定义物理/动力学参数字典
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

    sim_year = 200

    # -------------------------------------------------------------------------
    # 2. 测试功能 A: 生成碳封存潜力地图
    # -------------------------------------------------------------------------
    print("\n[测试 1] 开始计算全球碳封存潜力地图...")
    results_map = carbon_sequestration_potential(
        EW_raw_data=EW_raw_data,
        grain_size=grain_size,
        PH_array=PH_array,
        soil_temperature_array=soil_temperature_array,
        start_year=2025,
        end_year=2200,
        simulated_year=sim_year,
        # 使用字典解包传入参数 (**params_dict)
        **params_dict,
        pathway=2,
        grain_size_psd_dict=psd_dict,
        output_folder="E:/wzy/1-CDR-Base/EW/Output/Raster Data/",
        uncertainty=False
    )
    print("地图计算完成！返回数据 keys:", results_map.keys())

    # -------------------------------------------------------------------------
    # 3. 测试功能 B: 计算单点风化速率曲线 (FAIR 接口测试)
    # -------------------------------------------------------------------------
    print("\n[测试 2] 开始计算单点风化速率曲线 (用于 FAIR)...")

    # 设定测试条件
    test_ph = 3.00
    test_temp = 0.00
    test_p80 = 20  # μm
    print(f"测试条件: pH={test_ph}, Temp={test_temp}°C, P80={test_p80}μm")

    # 调用函数 (注意这里输入的是 DataFrame: test_psd_df)
    annual_rates = get_annual_rate_curve(
        rock_type='Basalt',
        pH_scalar=test_ph,
        temp_scalar=test_temp,
        grain_size_psd_dict=psd_dict,  # 传入字典
        p80=test_p80,  # 传入粒径
        simulated_year=sim_year,
        params_dict=params_dict
    )

    # -------------------------------------------------------------------------
    # 4. 输出结果验证
    # -------------------------------------------------------------------------
    print("-" * 30)
    print("计算成功！前 100 年的年度风化速率 (Annual Weathering Rate):")
    for i in range(100):
        print(f"Year {i + 1}: {annual_rates[i]}")

    total_weathered = np.sum(annual_rates)
    print("-" * 30)
    print(f"模拟时长: {sim_year} 年")
    print(f"累积总风化比例: {total_weathered:.2%}")
