# 生成全球气候效益栅格地图

import os
import glob
import numpy as np
import pandas as pd
from osgeo import gdal, osr


# === 辅助函数：保存栅格 ===
def save_raster(output_path, array, geotransform, epsg=4326, dtype=gdal.GDT_Float32, nodata_value=np.nan):
    """保存 numpy 数组为 GeoTIFF"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    rows, cols = array.shape
    driver = gdal.GetDriverByName('GTiff')

    # 创建输出文件
    out_ds = driver.Create(output_path, cols, rows, 1, dtype)
    out_ds.SetGeoTransform(geotransform)

    # 设置投影
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(epsg)
    out_ds.SetProjection(srs.ExportToWkt())

    # 写入数据
    band = out_ds.GetRasterBand(1)
    band.WriteArray(array)
    if nodata_value is not None:
        band.SetNoDataValue(nodata_value)

    band.FlushCache()
    out_ds = None
    # print(f"[IO] Saved raster: {os.path.basename(output_path)}")


def build_EW_climate_benefit_rasters(
        EW_eff_basalt_2,
        EW_eff_basalt_10,
        EW_eff_basalt_20,
        EW_eff_basalt_50,
        EW_eff_dunite_2,
        EW_eff_dunite_10,
        EW_eff_dunite_20,
        EW_eff_dunite_50,
        grain_size,
        rock_type,
        PH_array,
        soil_temperature_array,
        EW_land_array,
        start_year,
        scenario="TimeVarying_CES",
        pathway=1,
        trade=False,
        uncertainty=False
):
    """
    计算气候效益的主函数（Workflow）。
    读取 FAIR+R 计算生成的 SCC 结果，并通过查表法映射回全球栅格。
    """
    print(f"[INFO] Starting Climate Benefit mapping for year {start_year}...")

    # ========= 1. 路径与环境设置 =========
    # 假设 FAIR 和 R 的结果都在 outputs/{start_year} 下
    base_dir = f"E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/outputs/{start_year}"
    log_path = os.path.join(base_dir, "FAIR_Output/Processed_Grid_Log.csv")  # 注意路径拼接
    howard_output_dir = os.path.join(base_dir, "Howard_Output")
    output_raster_dir = os.path.join(base_dir, "Climate_Benefit")

    if not uncertainty and not os.path.exists(output_raster_dir):
        os.makedirs(output_raster_dir)

    # 栅格参数
    rows, cols = PH_array.shape
    n_pixels = rows * cols
    geotransform = (-180, 0.5, 0, 90, 0, -0.5)

    # ========= 2. 数据预处理 (统一保留2位小数) =========
    print("[INFO] Pre-processing input arrays (rounding to 2 decimals)...")

    # 立即修约
    PH_array = np.round(PH_array, 2)
    soil_temperature_array = np.round(soil_temperature_array, 2)

    # 整理效率图到字典，同时修约
    eff_by_rock = {
        "Basalt": [
            np.round(EW_eff_basalt_2, 2),
            np.round(EW_eff_basalt_10, 2),
            np.round(EW_eff_basalt_20, 2),
            np.round(EW_eff_basalt_50, 2),
        ],
        "Dunite": [
            np.round(EW_eff_dunite_2, 2),
            np.round(EW_eff_dunite_10, 2),
            np.round(EW_eff_dunite_20, 2),
            np.round(EW_eff_dunite_50, 2),
        ]
    }

    # ========= 3. 加载模拟结果并计算平均值 (Memory Lookup) =========
    print("[INFO] Loading Metadata and calculating Average SCC...")

    # 3.1 读取 Log 文件 (获取 Key)
    if not os.path.exists(log_path):
        # 尝试去掉中间的 /FAIR_Output/ 再试一次，防止路径拼接错误
        log_path_alt = os.path.join(base_dir, "Processed_Grid_Log.csv")
        if os.path.exists(log_path_alt):
            log_path = log_path_alt
        else:
            raise FileNotFoundError(f"Log file not found: {log_path}")

    # 读取 Log，只取 Key 列
    df_log = pd.read_csv(log_path, usecols=['Key'])
    all_keys = df_log['Key'].values

    # 3.2 读取 SCC 结果文件
    scc_files = glob.glob(os.path.join(howard_output_dir, "SCC_Sample_*.csv"))
    if not scc_files:
        raise FileNotFoundError(f"No SCC result files found in {howard_output_dir}")

    print(f"[INFO] Found {len(scc_files)} simulation files. Calculating mean for '{scenario}'...")

    sum_benefits = None
    count = 0

    # 增量计算平均值
    for f in scc_files:
        try:
            # 只读取目标场景列
            df_chunk = pd.read_csv(f, usecols=[scenario])

            # 数据对齐：Log 行数可能多于未跑完的结果，取交集长度
            current_len = len(df_chunk)
            log_len = len(all_keys)
            min_len = min(current_len, log_len)

            vals = df_chunk[scenario].values[:min_len].astype(np.float64)

            if sum_benefits is None:
                sum_benefits = vals
            else:
                # 累加前需要确保长度一致 (以最短的为准)
                if len(vals) < len(sum_benefits):
                    sum_benefits = sum_benefits[:len(vals)]
                elif len(vals) > len(sum_benefits):
                    vals = vals[:len(sum_benefits)]

                sum_benefits += vals

            count += 1
        except Exception as e:
            print(f"[WARN] Failed to read {f}: {e}")

    if count == 0:
        raise ValueError("Could not read any SCC files correctly.")

    # 计算平均值
    avg_benefits = sum_benefits / count

    # 3.3 构建查找字典 {Key: Benefit}
    # 确保 Keys 和 Benefits 长度一致
    valid_keys = all_keys[:len(avg_benefits)]
    benefit_lookup = dict(zip(valid_keys, avg_benefits))

    print(f"[INFO] Lookup table built. Total unique combinations: {len(benefit_lookup)}")

    # ========= 4. 映射与绘图循环 (加速版) =========

    grain_list = [int(grain_size.iloc[i, 0]) for i in range(len(grain_size))]  # [2, 10, 20, 50]
    rock_names = [str(rock_type.iloc[i, 0]) for i in range(len(rock_type))]  # ['Basalt', 'Dunite']

    # 输出容器
    EW_benefit_csv = np.full((n_pixels, 8), np.nan, dtype=np.float32)

    # 基础 Mask
    valid_base = (EW_land_array > 0) & (PH_array > 0) & (soil_temperature_array > -256)

    mapped_count = 0

    for r_idx, rock_name in enumerate(rock_names):
        # 读取距离图
        trade_suffix = " (with trade)" if trade else ""
        dist_path = f"E:/wzy/2-Grid-based-MONET/Global Data/EW/Output/Global/EW_global_transport_distance_{rock_name}{trade_suffix}.tif"

        ds = gdal.Open(dist_path)
        if not ds:
            print(f"[WARN] Dist raster not found: {dist_path}")
            continue
        dist_array = ds.ReadAsArray()

        # CSV 列偏移
        col_offset = 0 if rock_name == "Basalt" else 4

        for s_idx, size in enumerate(grain_list):
            eff_array = eff_by_rock[rock_name][s_idx]

            # 初始化当前图层
            current_raster_layer = np.full((rows, cols), np.nan, dtype=np.float32)

            # Mask: 有效点
            valid_mask = valid_base & (~np.isnan(dist_array)) & (eff_array > 0)

            # 获取有效数据 (Flattened)
            ph_vec = PH_array[valid_mask]
            t_vec = soil_temperature_array[valid_mask]
            eff_vec = eff_array[valid_mask]

            if len(ph_vec) == 0:
                continue

            # [核心优化]：使用列表推导式批量生成 Key (比循环快得多)
            # Key 格式: "Basalt_10_5.50_15.20_0.85"
            # 注意：必须保留2位小数格式以匹配 Log 文件
            keys_vec = [
                f"{rock_name}_{size}_{p:.2f}_{t:.2f}_{e:.2f}"
                for p, t, e in zip(ph_vec, t_vec, eff_vec)
            ]

            # [核心优化]：批量查表 (List Comprehension)
            # 如果 Key 不存在，返回 NaN
            benefits_vec = [benefit_lookup.get(k, np.nan) for k in keys_vec]
            benefits_vec = np.array(benefits_vec, dtype=np.float32)

            # 将查到的值填回栅格
            current_raster_layer[valid_mask] = benefits_vec

            # 填入 CSV 容器
            flat_indices = np.where(valid_mask.flatten())[0]
            # 这里需要注意: benefits_vec 长度等于 flat_indices 长度
            # 但 benefits_vec 中可能含有 NaN (如果查表失败)
            # 我们直接赋值即可
            EW_benefit_csv[flat_indices, col_offset + s_idx] = benefits_vec

            mapped_count += np.sum(~np.isnan(benefits_vec))

            # === 保存单张 GeoTIFF (仅当 uncertainty=False) ===
            if not uncertainty:
                suffix_num = "_1" if pathway == 2 else ""
                out_filename = f"EW_climate_benefit_raster_{rock_name}_{size} μm{trade_suffix}{suffix_num}.tif"
                out_path = os.path.join(output_raster_dir, out_filename)
                save_raster(out_path, current_raster_layer, geotransform)

    print(f"[INFO] Mapping completed. Total mapped pixels: {mapped_count}")

    # ========= 5. 保存总 CSV (仅当 uncertainty=False) =========
    if not uncertainty:
        suffix_num = "_1" if pathway == 2 else ""
        csv_filename = f"Climate Benefit (Only Efficiency){trade_suffix}{suffix_num}.csv"
        csv_out_path = os.path.join(output_raster_dir, csv_filename)

        print(f"[INFO] Saving summary CSV to {csv_out_path}...")
        df_out = pd.DataFrame(EW_benefit_csv)
        # 添加列名
        cols_name = []
        for r_name in ["Basalt", "Dunite"]:  # 保持固定顺序
            for g_size in [2, 10, 20, 50]:
                cols_name.append(f"{r_name}_{g_size}um")
        df_out.columns = cols_name

        df_out.to_csv(csv_out_path, index=False)
        print("[INFO] CSV saved.")

    # 始终返回结果
    return {
        "EW_climate_benefit_csv": EW_benefit_csv
    }
