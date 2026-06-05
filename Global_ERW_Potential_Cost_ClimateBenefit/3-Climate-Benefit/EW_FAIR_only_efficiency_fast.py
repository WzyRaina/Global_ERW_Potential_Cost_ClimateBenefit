# 输入移除效率地图，调用FAIR
# 分层抽样 + Base只算一次 + 增量计算 + 防中断断点续传

import os
import sys
import hashlib

# ====== 1. 环境设置 ======
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")

model_path = 'E:/wzy/1-CDR-Base/EW'
if model_path not in sys.path:
    sys.path.append(model_path)
import ERW_Core_Model

import fair
import numpy as np
import pandas as pd
from scipy.stats import truncnorm
from osgeo import gdal
from joblib import Parallel, delayed
import gc
import importlib.util

# ====== 2. 参数定义 ======
PARAMS_DICT = {
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

# ====== 3. 辅助函数 ======

def get_stratified_sample_indices(values, n_samples=50):
    """(1) 分层抽样函数：返回50个代表性样本的索引"""
    df = pd.DataFrame({'value': values, 'original_index': range(len(values))})
    df = df.sort_values('value')
    splits = np.array_split(df, n_samples)
    selected_indices = []
    for split in splits:
        # 取区间中位数对应的样本
        median_idx = len(split) // 2
        selected_indices.append(split.iloc[median_idx]['original_index'])
    return np.array(selected_indices, dtype=int)

def generate_unique_key(rock, size, ph, temp, eff):
    """生成唯一组合的 Key (用于去重)"""
    # 统一保留两位小数，确保 Key 的一致性
    return f"{rock}_{size}_{ph:.2f}_{temp:.2f}_{eff:.2f}"

# ====== 核心 Worker 函数 (并行单元) ======
def process_single_grid_task(
        task_info,
        selected_indices,
        scenario_sample,
        rffsp_co2_emissions,
        tcr,
        ecs,
        start_year,
        compute_year,
        emissions_template,
        psd_dict,
        slice_limit
):
    """
    处理单个网格组合任务。
    在函数内部串行运行 50 个 Sample，同时计算 Base 和 Extra。
    """
    # 解包任务信息
    rock_type, grain_size, ph_val, t_val, eff_val, grid_id_start = task_info

    # 1. 计算物理风化曲线 (只算一次)
    CO2_seq_potential_annual = ERW_Core_Model.get_annual_rate_curve(
        rock_type=rock_type,
        pH_scalar=ph_val,
        temp_scalar=t_val,
        grain_size_psd_dict=psd_dict,  # 传入字典
        p80=int(grain_size),  # 传入 p80
        simulated_year=compute_year + 50,
        params_dict=PARAMS_DICT
    )

    # 2. 结果容器
    t_base_results = []
    c_base_results = []
    t_extra_results = []
    c_extra_results = []

    # 预计算常量
    idx0 = 2020 - 1765
    idx1 = 2300 - 1765 + 1
    len_seq = len(CO2_seq_potential_annual)
    limit = min(compute_year, len_seq)
    pulse = np.float32(0.1 * 12 / 44)
    eff_loss = pulse * np.float32(1 - eff_val)
    seq_arr = pulse * np.float32(CO2_seq_potential_annual[:limit])

    # 3. 循环 50 个 Sample
    for i in selected_indices:
        scenario_target = scenario_sample[i]

        # --- A. 构建 Base Emissions ---
        emissions_rffsps_base = emissions_template.copy()

        co2_series = rffsp_co2_emissions.loc[
            (rffsp_co2_emissions['sample'] == scenario_target), "value"
        ].to_numpy(dtype=np.float32)

        # 填充 Base Emission 数据 (注意不越界)
        current_max_len = emissions_rffsps_base.shape[0]
        real_idx1 = min(idx1, current_max_len)
        needed_len = real_idx1 - idx0

        if needed_len > 0:
            emissions_rffsps_base[idx0:real_idx1, 1] = (
                    co2_series[:needed_len] - emissions_rffsps_base[idx0:real_idx1, 2]
            )

        tcrecs_val = np.array([max(1, min(float(tcr[i]), 2.5)), float(ecs[i])], dtype=np.float32)

        # === Run FAIR for Base ===
        C_base, _, T_base = fair.forward.fair_scm(
            emissions=emissions_rffsps_base,
            tcrecs=tcrecs_val
        )

        # 保存 Base 结果 (裁剪到 slice_limit)
        t_base_results.append(T_base[:slice_limit].astype(np.float32))
        c_base_results.append(C_base[:slice_limit, 0].astype(np.float32))

        # --- B. 构建 Extra Emissions ---
        emissions_extra = emissions_rffsps_base.copy()

        idx_start = start_year - 1765
        if idx_start < current_max_len:
            # 第一年：移除 + 效率损失
            emissions_extra[idx_start, 1] = (
                    emissions_rffsps_base[idx_start, 1]
                    - pulse * np.float32(CO2_seq_potential_annual[0])
                    + eff_loss
            )

        # 后续年份扣减
        end_idx = min(idx_start + limit, current_max_len)
        actual_steps = end_idx - (idx_start + 1)

        if actual_steps > 0:
            emissions_extra[idx_start + 1: end_idx, 1] -= seq_arr[1: 1 + actual_steps]

        # === Run FAIR for Extra ===
        C_extra, _, T_extra = fair.forward.fair_scm(
            emissions=emissions_extra,
            tcrecs=tcrecs_val
        )

        # 保存 Extra 结果
        t_extra_results.append(T_extra[:slice_limit].astype(np.float32))
        c_extra_results.append(C_extra[:slice_limit, 0].astype(np.float32))

    # 返回增加了 Base 的结果
    return grid_id_start, rock_type, grain_size, ph_val, t_val, eff_val, t_base_results, c_base_results, t_extra_results, c_extra_results

# ====== 4. 主流程函数 ======

def run_fair_for_EW_only_efficiency(
        EW_eff_basalt_2,
        EW_eff_basalt_10,
        EW_eff_basalt_20,
        EW_eff_basalt_50,
        EW_eff_dunite_2,
        EW_eff_dunite_10,
        EW_eff_dunite_20,
        EW_eff_dunite_50,
        scenario_sample,
        rffsp_co2_emissions,
        tcr,
        ecs,
        PH_array,
        soil_temperature_array,
        EW_land_array,
        start_year,
        end_year,
        selected_indices,  # 传入选中的50个索引
        psd_dict,  # 新增参数：粒径分布字典
        trade=False
):
    # 性能配置
    n_jobs = 50  # 并行进程数
    BATCH_SIZE = 500  # 批量大小 (一次处理500个Unique组合)

    compute_year = end_year - start_year + 1
    slice_limit = end_year - 1765 + 1

    # 1. 路径准备
    output_base_dir = f'E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/EW/only_efficiency/outputs/{start_year}/FAIR_Output'
    # 创建专门存放 50 个 Sample 的 Base 和 Extra 文件的目录
    base_results_dir = f'{output_base_dir}/Base_Results'  # 存放 T_base.csv, C_base.csv
    sample_dir = f'{output_base_dir}/Samples_50'  # 存放 T_extra_Sample_X.csv, C_extra_Sample_X.csv
    meta_log_path = f'{output_base_dir}/Processed_Grid_Log.csv'

    if not os.path.exists(base_results_dir): os.makedirs(base_results_dir)
    if not os.path.exists(sample_dir): os.makedirs(sample_dir)

    # 2. 加载日志 (断点续传)
    processed_keys = set()
    current_grid_id = 0
    if os.path.exists(meta_log_path):
        print("[INFO] Resuming from existing log...")
        try:
            # 优化：只读取 Key 列，极大加快启动速度
            df_log = pd.read_csv(meta_log_path, usecols=['Key', 'Grid_ID'])
            processed_keys = set(df_log['Key'].values)
            if not df_log.empty:
                current_grid_id = df_log['Grid_ID'].max() + 1
        except Exception:
            print("[WARN] Log file read error, starting fresh.")
            pass
    else:
        with open(meta_log_path, 'w') as f:
            f.write("Grid_ID,Key,Rock,Size,pH,T,Eff\n")

    print(f"[INFO] Already processed {len(processed_keys)} unique combinations. Starting Grid_ID: {current_grid_id}")

    # 3. 预处理 FAIR 模板
    emissions_template = pd.read_csv(
        "E:/wzy/3-Climate-Benefit/Climate_Benefit/Compute_Code/FAIR_Howard/rffsps/FAIR_rffsps_template.csv"
    ).to_numpy()

    emissions_template = emissions_template[3:, :]
    emissions_template = emissions_template.astype(np.float32, copy=False)
    emissions_template = np.delete(emissions_template, 6, 1)

    # 4. 初始化 Extra CSV 文件
    # Base 文件由后续逻辑生成，这里只确保 Extra 文件存在
    for idx in selected_indices:
        t_path = f'{sample_dir}/T_extra_Sample_{idx}.csv'
        c_path = f'{sample_dir}/C_extra_Sample_{idx}.csv'
        if not os.path.exists(t_path): open(t_path, 'w').close()
        if not os.path.exists(c_path): open(c_path, 'w').close()

    # Base 文件路径
    t_base_file = f'{base_results_dir}/T_base_samples.csv'
    c_base_file = f'{base_results_dir}/C_base_samples.csv'

    # 标记 Base 是否已经保存 (根据文件是否存在)
    base_saved = False
    if os.path.exists(t_base_file) and os.path.exists(c_base_file):
        base_saved = True
        print("[INFO] Base files detected. Will not overwrite.")
    else:
        print("[INFO] Base files missing. Will save from the first processed batch.")

    # ====== 5. 向量化任务生成 ======
    print("[INFO] Generating task list (Vectorized)...")

    eff_maps = {
        ('Basalt', 2): EW_eff_basalt_2,
        ('Basalt', 10): EW_eff_basalt_10,
        ('Basalt', 20): EW_eff_basalt_20,
        ('Basalt', 50): EW_eff_basalt_50,
        ('Dunite', 2): EW_eff_dunite_2,
        ('Dunite', 10): EW_eff_dunite_10,
        ('Dunite', 20): EW_eff_dunite_20,
        ('Dunite', 50): EW_eff_dunite_50,
    }

    base_mask = (EW_land_array > 0) & (PH_array > 0) & (soil_temperature_array > -256)
    all_tasks = []

    for (rock, size), eff_map in eff_maps.items():
        t_path = f'E:/wzy/2-Grid-based-MONET/Global Data/EW/Output/Global/EW_global_transport_distance_{rock}'
        t_path += ' (with trade).tif' if trade else '.tif'
        dist_array = gdal.Open(t_path).ReadAsArray()

        valid_mask = base_mask & (~np.isnan(dist_array)) & (eff_map > 0) & (~np.isnan(eff_map))

        ph_vals = PH_array[valid_mask]
        t_vals = soil_temperature_array[valid_mask]
        eff_vals = eff_map[valid_mask]

        if len(ph_vals) == 0: continue

        # 向量化构建 DataFrame
        df_tmp = pd.DataFrame({
            'rock': rock,
            'size': size,
            'ph': np.round(ph_vals, 2),  # 匹配 Key 精度
            't': np.round(t_vals, 2),
            'eff': np.round(eff_vals, 2)
        })

        df_tmp['key'] = df_tmp.apply(
            lambda row: f"{row['rock']}_{int(row['size'])}_{row['ph']:.2f}_{row['t']:.2f}_{row['eff']:.2f}", axis=1)

        # 去重
        df_unique = df_tmp.drop_duplicates(subset=['key'])

        # 过滤已做过的
        df_todo = df_unique[~df_unique['key'].isin(processed_keys)]

        if not df_todo.empty:
            print(f"  -> {rock} {size}um: Found {len(df_todo)} new unique combinations.")
            all_tasks.append(df_todo)

    if not all_tasks:
        print("[INFO] No new tasks found. Everything is processed.")
        finalize_metadata(meta_log_path, f'{output_base_dir}/EW_result_number.csv')
        return

    df_all_tasks = pd.concat(all_tasks, ignore_index=True)
    df_all_tasks = df_all_tasks.drop_duplicates(subset=['key'])
    print(f"[INFO] Total unique tasks to process: {len(df_all_tasks)}")

    # ====== 6. 批量并行处理 ======
    total_tasks = len(df_all_tasks)
    batch_data_t = {idx: [] for idx in selected_indices}
    batch_data_c = {idx: [] for idx in selected_indices}

    batch_meta_lines = []

    with Parallel(n_jobs=n_jobs) as parallel:
        for start_idx in range(0, total_tasks, BATCH_SIZE):
            end_idx = min(start_idx + BATCH_SIZE, total_tasks)
            chunk = df_all_tasks.iloc[start_idx:end_idx]

            print(f"[Compute] Processing batch {start_idx} to {end_idx} ({len(chunk)} tasks)...")

            chunk_indices = range(current_grid_id, current_grid_id + len(chunk))
            tasks_args = []
            for (i, row), g_id in zip(chunk.iterrows(), chunk_indices):
                tasks_args.append((
                    row['rock'], row['size'], row['ph'], row['t'], row['eff'], g_id
                ))

            results = parallel(
                delayed(process_single_grid_task)(
                    args,
                    selected_indices, scenario_sample, rffsp_co2_emissions, tcr, ecs,
                    start_year, compute_year, emissions_template,
                    psd_dict,  # 传入完整的字典
                    slice_limit
                ) for args in tasks_args
            )

            # === [核心逻辑]：如果 Base 没存，用第一个结果存一次 ===
            if not base_saved and len(results) > 0:
                print("[IO] Saving Base T & C from the first processed task...")
                # 提取第一条结果的 base
                # res[0]: g_id, res[1]: rock..., res[6]: t_base_list, res[7]: c_base_list
                first_res = results[0]
                t_base_list_sample = first_res[6]  # 这是一个 list (50个Sample)
                c_base_list_sample = first_res[7]

                # 堆叠成 (Time, 50) 数组
                T_base_all = np.stack(t_base_list_sample, axis=1)  # axis=1 -> col is sample
                C_base_all = np.stack(c_base_list_sample, axis=1)

                # 保存
                pd.DataFrame(T_base_all, columns=selected_indices).to_csv(t_base_file, index=False)
                pd.DataFrame(C_base_all, columns=selected_indices).to_csv(c_base_file, index=False)

                base_saved = True
                print("[IO] Base files saved successfully.")

            # 结果处理 (只收集 Extra 写入 Log)
            for res in results:
                g_id, r_type, g_size, ph, t, eff, t_base, c_base, t_extra_list, c_extra_list = res

                key = f"{r_type}_{int(g_size)}_{ph:.2f}_{t:.2f}_{eff:.2f}"
                batch_meta_lines.append(f"{g_id},{key},{r_type},{int(g_size)},{ph:.2f},{t:.2f},{eff:.2f}")

                for k, idx in enumerate(selected_indices):
                    batch_data_t[idx].append(t_extra_list[k])
                    batch_data_c[idx].append(c_extra_list[k])

            current_grid_id += len(chunk)

            # 刷写磁盘
            flush_buffers(batch_data_t, batch_data_c, batch_meta_lines, sample_dir, meta_log_path)

            # 清理
            batch_meta_lines = []
            batch_data_t = {idx: [] for idx in selected_indices}
            batch_data_c = {idx: [] for idx in selected_indices}
            gc.collect()

    print("[INFO] Processing complete.")
    finalize_metadata(meta_log_path, f'{output_base_dir}/EW_result_number.csv')

def flush_buffers(data_t, data_c, meta_list, sample_dir, meta_log_path):
    """同时刷写 T 和 C 数据"""
    with open(meta_log_path, 'a') as f:
        for line in meta_list: f.write(line + "\n")

    for idx, rows in data_t.items():
        if not rows: continue
        # Write T
        f_path_t = f'{sample_dir}/T_extra_Sample_{idx}.csv'
        pd.DataFrame(rows).to_csv(f_path_t, mode='a', header=False, index=False)
        # Write C
        rows_c = data_c[idx]
        f_path_c = f'{sample_dir}/C_extra_Sample_{idx}.csv'
        pd.DataFrame(rows_c).to_csv(f_path_c, mode='a', header=False, index=False)

def finalize_metadata(log_path, output_path):
    """转置 Log 为 EW_result_number.csv"""
    if not os.path.exists(os.path.dirname(output_path)): os.makedirs(os.path.dirname(output_path))
    try:
        df = pd.read_csv(log_path)
        df_clean = df[['Rock', 'Size', 'pH', 'T', 'Eff']].copy()
        df_clean.T.to_csv(output_path, header=False)
        print(f"[INFO] Final metadata saved to {output_path}")
    except Exception:
        print("[WARN] Could not finalize metadata (Log empty?).")


# ====== 5. 运行入口 ======
if __name__ == '__main__':

    trade = False
    start_year = 2025
    end_year = 2200
    round_number = 2  # 统一保留2位小数

    # 读入两类岩石四种颗粒大小的移除效率栅格地图
    # dunite
    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_dunite_2 μm.tif')
    EW_efficiency_raster_dunite_2_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_dunite_10 μm.tif')
    EW_efficiency_raster_dunite_10_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_dunite_20 μm.tif')
    EW_efficiency_raster_dunite_20_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_dunite_50 μm.tif')
    EW_efficiency_raster_dunite_50_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    # basalt
    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_basalt_2 μm.tif')
    EW_efficiency_raster_basalt_2_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_basalt_10 μm.tif')
    EW_efficiency_raster_basalt_10_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_basalt_20 μm.tif')
    EW_efficiency_raster_basalt_20_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    ds = gdal.Open(f'E:/wzy/2-Grid-based-MONET/Output/EW/Global/Removal Efficiency/{start_year}/EW_removal_efficiency_raster_basalt_50 μm.tif')
    EW_efficiency_raster_basalt_50_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    # 读入电力排放因子栅格地图
    ds = gdal.Open('E:/ArcGIS/Projects/Country/UNFCCC_Electricity_Factor.tif')
    EEF_array = ds.ReadAsArray()
    ds = None

    # 读入其他需要的数据
    grain_size = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Grain Size.csv', encoding='gbk')
    rock_type = pd.read_csv('E:/wzy/2-Grid-based-MONET/Input Data/EW/Rock Type.csv', encoding='gbk')

    # PH data
    ds = gdal.Open('E:/ArcGIS/Projects/GetData/T_PH_H20.tif')
    PH_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    # Soil temperature
    ds = gdal.Open('E:/ArcGIS/Projects/Biomass Yield/Soil_Temperature.tif')
    soil_temperature_array = np.round(ds.ReadAsArray(), round_number)
    ds = None

    # land available for EW
    ds = gdal.Open('E:/wzy/2-Grid-based-MONET/Global Data/EW/Input/Global/Global cropland map.tif')
    EW_land_array = ds.ReadAsArray()
    ds = None

    # 抽样
    total_samples = 10000
    ecs_ar5_sample = pd.read_csv('E:/wzy/3-Climate-Benefit/Climate_Benefit/Sample/ecs_sample.csv')["x"].values
    scenario_sample = pd.read_csv('E:/wzy/3-Climate-Benefit/Climate_Benefit/Sample/climate_scenario_sample.csv')["x"]
    rwf = truncnorm.rvs(-3, 3, loc=0.6, scale=0.1, size=total_samples, random_state=301)
    tcr = rwf * ecs_ar5_sample
    rffsp_co2_emissions = pd.read_csv(
        "E:/wzy/3-Climate-Benefit/Climate_Benefit/rffsps_v5/emissions/rffsp_co2_emissions.csv")

    print("Selecting 50 stratified samples...")
    selected_indices = get_stratified_sample_indices(ecs_ar5_sample, 50)
    print(f"Selected Sample Indices: {selected_indices}")

    # 动态加载粒径生成函数
    print("[INFO] Generating PSD Dictionary...")
    grain_size_distribution_file_path = r"E:/wzy/1-CDR-Base/EW/Grain_Size_Distribution.py"
    spec_psd = importlib.util.spec_from_file_location("grain_size_distribution", grain_size_distribution_file_path)
    grain_size_distribution_py = importlib.util.module_from_spec(spec_psd)
    spec_psd.loader.exec_module(grain_size_distribution_py)

    # 生成 psd_dict
    psd_dict = grain_size_distribution_py.generate_psd_for_multiple_p80(
        sigma=0.5,
        save_folder='E:/wzy/1-CDR-Base/EW/Output/Grain Size Distribution/',
        plot=False,
        uncertainty=False
    )

    # === 调用封装好的 FAIR 计算函数 ===
    run_fair_for_EW_only_efficiency(
        EW_eff_basalt_2=EW_efficiency_raster_basalt_2_array,
        EW_eff_basalt_10=EW_efficiency_raster_basalt_10_array,
        EW_eff_basalt_20=EW_efficiency_raster_basalt_20_array,
        EW_eff_basalt_50=EW_efficiency_raster_basalt_50_array,
        EW_eff_dunite_2=EW_efficiency_raster_dunite_2_array,
        EW_eff_dunite_10=EW_efficiency_raster_dunite_10_array,
        EW_eff_dunite_20=EW_efficiency_raster_dunite_20_array,
        EW_eff_dunite_50=EW_efficiency_raster_dunite_50_array,
        scenario_sample=scenario_sample,
        rffsp_co2_emissions=rffsp_co2_emissions,
        tcr=tcr,
        ecs=ecs_ar5_sample,
        PH_array=PH_array,
        soil_temperature_array=soil_temperature_array,
        EW_land_array=EW_land_array,
        start_year=start_year,
        end_year=end_year,
        selected_indices=selected_indices,
        psd_dict=psd_dict,
        trade=trade
    )
