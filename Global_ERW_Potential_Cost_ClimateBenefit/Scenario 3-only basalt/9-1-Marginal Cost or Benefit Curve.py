# 绘制边际成本和气候效益曲线

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from osgeo import gdal

trade = True
maxcb = True
start_year = 2025  # 2025, 2030, 2035, 2040, 2050

# ===================== 0. 工作目录 =====================
os.chdir(r"E:/wzy/2-Grid-based-MONET")

# ===================== 1. 输入路径 =====================
if maxcb:
    if trade:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_cost_maxnetbenefit_raster (with trade).tif"
        climate_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_climate_benefit_maxnetbenefit_raster (with trade).tif"
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_max_net_benefit_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/EW_potential_maxnetbenefit_raster (with trade).tif"
    else:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_cost_maxnetbenefit_raster.tif"
        climate_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_climate_benefit_maxnetbenefit_raster.tif"
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_max_net_benefit_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/EW_potential_maxnetbenefit_raster.tif"
else:
    if trade:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_min_cost_raster (with trade).tif"
        climate_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_climate_benefit_mincost_raster (with trade).tif"
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_net_benefit_mincost_raster (with trade).tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/EW_potential_mincost_raster (with trade).tif"
    else:
        cost_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_min_cost_raster.tif"
        climate_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_climate_benefit_mincost_raster.tif"
        net_benefit_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_net_benefit_mincost_raster.tif"
        potential_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/EW_potential_mincost_raster.tif"

region_path = r"E:/ArcGIS/Projects/Country/Region.tif"
subregion_path = r"E:/ArcGIS/Projects/Country/Subregion.tif"

# 输出目录
if maxcb:
    if trade:
        output_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Marginal_Curves"
    else:
        output_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Marginal_Curves"
else:
    if trade:
        output_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Marginal_Curves"
    else:
        output_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Marginal_Curves"

os.makedirs(output_dir, exist_ok=True)

# NoData
NODATA = -9999.0

# Raw step 曲线最大点数
MAX_POINTS_PER_CURVE = 5000

# 分箱宽度（MtCO2）
BIN_WIDTH_MTCO2 = 10.0

# 横坐标单位：把 MtCO2 -> GtCO2
X_SCALE = 1000.0

# ===================== 2. 样式参数 =====================

# 颜色
GLOBAL_COLOR = "#000000"
REGION_COLORS = {
    1: "#1f77b4",  # Asia
    4: "#d62728",  # Europe
    3: "#2ca02c",  # Africa
    2: "#ff7f0e",  # Americas
    5: "#9467bd",  # Oceania
}

# 线宽与透明度
RAW_ALPHA_MAIN = 0.22
RAW_LW_MAIN = 1.2
BIN_LW_MAIN = 2.6

# Inset (现在是区域)
RAW_ALPHA_SUB = 0.25
RAW_LW_SUB = 1.0
BIN_LW_SUB = 2.0

# 字体
BASE_FONTSIZE = 16

# ===================== 3. Inset 位置与图例位置配置 =====================
# 现在的逻辑：Global 是主图，Regions 是 Inset
# Inset 里面会有 5 条线，需要大一点的空间
# 位置 [left, bottom, width, height]

if maxcb:
    if trade:
        # Inset 的坐标轴位置
        INSET_POS_CONFIG = {
            "MC": [0.1, 0.45, 0.6, 0.5],  # Cost: 左中/左上
            "MB": [0.10, 0.1, 0.6, 0.5],  # Benefit: 左下 (因为 Benefit 曲线也是左高右低)
            "MN": [0.12, 0.1, 0.6, 0.5],  # Net Benefit: 左下 (空出右上角画 0 线标注)
        }
        # Inset 内部图例的位置 (新增参数)
        INSET_LEGEND_LOC_CONFIG = {
            "MC": "upper left", # Cost 曲线通常左低右高，图例放右下
            "MB": "upper right", # Benefit 曲线通常左高右低，图例放右上
            "MN": "lower right", # Net Benefit 曲线通常左高右低，图例放右上
        }
    else:
        INSET_POS_CONFIG = {
            "MC": [0.15, 0.25, 0.65, 0.60],
            "MB": [0.12, 0.12, 0.65, 0.60],
            "MN": [0.12, 0.12, 0.65, 0.60],  # 左下角
        }
        INSET_LEGEND_LOC_CONFIG = {
            "MC": "upper right",
            "MB": "lower right",
            "MN": "lower right",
        }
else:
    # Mincost 模式
    if trade:
        INSET_POS_CONFIG = {
            "MC": [0.15, 0.25, 0.55, 0.50],
            "MB": [0.10, 0.10, 0.55, 0.50],
            "MN": [0.12, 0.12, 0.65, 0.60],
        }
        INSET_LEGEND_LOC_CONFIG = {
            "MC": "lower right",
            "MB": "upper right",
            "MN": "lower right",
        }
    else:
        INSET_POS_CONFIG = {
            "MC": [0.15, 0.25, 0.65, 0.60],
            "MB": [0.12, 0.12, 0.58, 0.53],
            "MN": [0.12, 0.12, 0.65, 0.60],
        }
        INSET_LEGEND_LOC_CONFIG = {
            "MC": "upper right",
            "MB": "lower right",
            "MN": "lower right",
        }

# 默认位置配置
DEFAULT_INSET_AXES = [0.15, 0.15, 0.50, 0.45]
DEFAULT_INSET_LEGEND_LOC = "best" # Matplotlib 自动寻找最佳位置

# ===================== 4. 标签 =====================
region_labels = {1: "Asia", 2: "Americas", 3: "Africa", 4: "Europe", 5: "Oceania", 6: "Antarctica"}
REGION5 = [1, 4, 3, 2, 5]


# ===================== 5. 读栅格 =====================
def read_raster(path):
    ds = gdal.Open(path)
    if ds is None:
        raise FileNotFoundError(f"Cannot open: {path}")
    return ds.ReadAsArray()


cost_arr = read_raster(cost_path).astype(float)
cb_arr = read_raster(climate_benefit_path).astype(float)
pot_arr = read_raster(potential_path).astype(float)
nb_arr = read_raster(net_benefit_path).astype(float)
reg_arr = read_raster(region_path).astype(int)
sub_arr = read_raster(subregion_path).astype(int)

if not (cost_arr.shape == cb_arr.shape == pot_arr.shape == nb_arr.shape == reg_arr.shape == sub_arr.shape):
    raise ValueError("Raster shapes are not aligned. Please align before analysis.")

cost = cost_arr.flatten()
cb = cb_arr.flatten()
nb = nb_arr.flatten()
pot = pot_arr.flatten()
reg = reg_arr.flatten()
sub = sub_arr.flatten()

base_valid = (
        np.isfinite(pot) & (pot != NODATA) & (pot > 0) &
        (reg > 0) & (sub > 0)
)
valid_cost = base_valid & np.isfinite(cost) & (cost != NODATA)
valid_cb = base_valid & np.isfinite(cb) & (cb != NODATA)
valid_nb = base_valid & np.isfinite(nb) & (nb != NODATA)

print("Valid pixels (cost):", int(np.sum(valid_cost)))
print("Valid pixels (climate benefit):", int(np.sum(valid_cb)))
print("Valid pixels (net benefit):", int(np.sum(valid_nb)))


# ===================== 6. 边际曲线计算逻辑 =====================
def compute_sorted_curve(x, w, reverse=False):
    idx = np.argsort(-x) if reverse else np.argsort(x)
    x_sorted = x[idx]
    w_sorted = w[idx]
    cum_w = np.cumsum(w_sorted)
    return cum_w, x_sorted, w_sorted


def downsample_by_index(cum, x_sorted, w_sorted, max_points=None):
    if max_points is None:
        return cum, x_sorted, w_sorted
    n = len(cum)
    if n <= max_points:
        return cum, x_sorted, w_sorted
    idx = np.linspace(0, n - 1, max_points).astype(int)
    idx = np.unique(idx)
    return cum[idx], x_sorted[idx], w_sorted[idx]


def bin_smooth_weighted(cum, x_sorted, w_sorted, bin_width=10.0):
    if len(cum) == 0:
        return np.array([]), np.array([])
    edges = np.arange(0, cum[-1] + bin_width, bin_width)
    xs, ys = [], []
    start = 0
    for edge in edges[1:]:
        end = np.searchsorted(cum, edge, side="right")
        if end <= start:
            continue
        ww = w_sorted[start:end]
        xx = x_sorted[start:end]
        wsum = np.sum(ww)
        if wsum <= 0:
            start = end
            continue
        x_pos = np.sum(cum[start:end] * ww) / wsum
        y_val = np.sum(xx * ww) / wsum
        xs.append(x_pos);
        ys.append(y_val)
        start = end
    return np.array(xs), np.array(ys)


# ===================== 7. 生成曲线数据 =====================
def build_global(x_flat, mask, reverse):
    cum, xs, ws = compute_sorted_curve(x_flat[mask], pot[mask], reverse=reverse)
    cum_ds, xs_ds, ws_ds = downsample_by_index(cum, xs, ws, MAX_POINTS_PER_CURVE)
    xb, yb = bin_smooth_weighted(cum, xs, ws, bin_width=BIN_WIDTH_MTCO2)
    return (cum, xs), (cum_ds, xs_ds), (xb, yb)


def build_regions(x_flat, mask, reverse):
    raw, ds, binned = {}, {}, {}
    for rid in REGION5:
        m = mask & (reg == rid)
        if np.sum(m) == 0:
            continue
        cum, xs, ws = compute_sorted_curve(x_flat[m], pot[m], reverse=reverse)
        cum_ds, xs_ds, ws_ds = downsample_by_index(cum, xs, ws, MAX_POINTS_PER_CURVE)
        xb, yb = bin_smooth_weighted(cum, xs, ws, bin_width=BIN_WIDTH_MTCO2)
        raw[rid] = (cum, xs)
        ds[rid] = (cum_ds, xs_ds)
        binned[rid] = (xb, yb)
    return raw, ds, binned


# ===================== 8. CSV 写入 =====================
def append_rows(rows, curve_type, series_type, group_level, region_id, group_name, x, y):
    for i in range(len(x)):
        rows.append({
            "CurveType": curve_type,
            "Series": series_type,
            "GroupLevel": group_level,
            "Region_ID": region_id if region_id is not None else "",
            "GroupName": group_name,
            "Cumulative_Potential_GtCO2": float(x[i] / X_SCALE),
            "Marginal_Value_USD_per_tCO2": float(y[i]),
            "BinWidth_MtCO2": BIN_WIDTH_MTCO2 if series_type == "Binned" else ""
        })


# ===================== 9. 绘图核心函数（Global主，Region嵌） =====================

def find_zero_crossing_potential(cum_arr, y_arr):
    """
    找到曲线穿过 y=0 的点的 X 值（累积潜力）。
    假设曲线是单调下降的（净效益）。
    """
    positive_indices = np.where(y_arr > 0)[0]
    if len(positive_indices) == 0:
        return 0.0
    if len(positive_indices) == len(y_arr):
        return cum_arr[-1] / X_SCALE

    last_pos_idx = positive_indices[-1]
    potential_gt = cum_arr[last_pos_idx] / X_SCALE
    return potential_gt


def plot_global_with_region_inset(fig_key, global_data, region_data, out_svg, y_label):
    # 解包数据
    # global_data: (raw_full, ds, binned)
    g_raw_full, g_ds, g_binned = global_data
    # region_data: (raw_full_dict, ds_dict, binned_dict)
    r_raw_full, r_ds, r_binned = region_data

    fig, ax = plt.subplots(figsize=(10.5, 7))

    # --- 主图：全球 (Global) ---
    ax.set_xlabel("Net Removal Potential (GtCO₂)", fontsize=BASE_FONTSIZE + 4)
    ax.set_ylabel(y_label, fontsize=BASE_FONTSIZE + 4)
    ax.tick_params(labelsize=BASE_FONTSIZE)
    ax.grid(False)
    ax.set_title("Global", fontsize=BASE_FONTSIZE + 4, pad=12)

    # 绘制全球曲线
    cum_g_ds, y_g_ds = g_ds
    xb_g, yb_g = g_binned
    ax.step(cum_g_ds / X_SCALE, y_g_ds, where="post", color=GLOBAL_COLOR, alpha=RAW_ALPHA_MAIN, linewidth=RAW_LW_MAIN)
    ax.plot(xb_g / X_SCALE, yb_g, color=GLOBAL_COLOR, linewidth=BIN_LW_MAIN, label="Global")

    is_net_benefit = "Net Benefit" in y_label

    # --- 净效益图的特殊处理：零点线与标注（画在主图上） ---
    if is_net_benefit:
        # 1. 画 0 线
        ax.axhline(0, color='black', linestyle='--', linewidth=1.2, alpha=0.8)

        # 2. 计算交点
        g_cum_full, g_y_full = g_raw_full
        pot_at_zero = find_zero_crossing_potential(g_cum_full, g_y_full)

        # 3. 标注
        # 在主图上标注
        ax.annotate(f"Potential: {pot_at_zero:.2f} Gt",
                    xy=(pot_at_zero, 0),
                    xytext=(pot_at_zero + 1, 33),  # 偏移一点
                    arrowprops=dict(arrowstyle="->", color='red', lw=1.2),
                    color='red', fontsize=BASE_FONTSIZE, fontweight='bold')

    # --- 嵌入小图：区域 (Regions) ---
    # 确定 Inset 位置
    prefix = fig_key[:2]
    inset_rect = INSET_POS_CONFIG.get(prefix, DEFAULT_INSET_AXES)

    inset = ax.inset_axes(inset_rect)
    inset.grid(False)
    inset.tick_params(labelsize=BASE_FONTSIZE - 4)  # 字体调小

    # 绘制区域曲线
    for rid in REGION5:
        if rid not in r_ds:
            continue
        c = REGION_COLORS.get(rid, "#666666")

        cum_r, y_r = r_ds[rid]
        xb_r, yb_r = r_binned[rid]

        inset.step(cum_r / X_SCALE, y_r, where="post", color=c, alpha=RAW_ALPHA_SUB, linewidth=RAW_LW_SUB)
        inset.plot(xb_r / X_SCALE, yb_r, color=c, linewidth=BIN_LW_SUB, label=region_labels[rid])

    # 如果是净效益图，Insets 里也可以画个细虚线 0 线，方便看各区域的盈亏点
    if is_net_benefit:
        inset.axhline(0, color='black', linestyle='--', linewidth=0.8, alpha=0.6)

    # Inset 图例：获取配置位置
    legend_loc = INSET_LEGEND_LOC_CONFIG.get(prefix, DEFAULT_INSET_LEGEND_LOC)
    inset.legend(frameon=False, fontsize=BASE_FONTSIZE - 4, loc=legend_loc)

    plt.savefig(out_svg, format="svg", bbox_inches="tight")
    plt.close(fig)


# ===================== 10. 主流程：输出 3 张图 + 2 CSV =====================
def run_all(curve_type, x_flat, mask, reverse, y_label, file_prefix):
    rows = []

    # Global data
    global_data = build_global(x_flat, mask, reverse)

    # Region data
    region_data = build_regions(x_flat, mask, reverse)

    # 绘图：Global 主图 + Region Inset
    fig_key = f"{file_prefix}_Global_with_Region_Inset"
    out_svg = os.path.join(output_dir, f"{fig_key}.svg")
    plot_global_with_region_inset(fig_key, global_data, region_data, out_svg, y_label)

    # CSV 数据记录
    # Global
    g_ds, g_binned = global_data[1], global_data[2]
    append_rows(rows, curve_type, "RawStep", "Global", None, "Global", g_ds[0], g_ds[1])
    append_rows(rows, curve_type, "Binned", "Global", None, "Global", g_binned[0], g_binned[1])

    # Regions
    r_ds, r_binned = region_data[1], region_data[2]
    for rid in REGION5:
        if rid not in r_ds:
            continue
        label = region_labels[rid]
        append_rows(rows, curve_type, "RawStep", "Region", rid, label, r_ds[rid][0], r_ds[rid][1])
        append_rows(rows, curve_type, "Binned", "Region", rid, label, r_binned[rid][0], r_binned[rid][1])

    return rows


# ===================== 11. 执行 =====================
y_cost = "Net Removal Cost ($/tCO₂ removed)"
y_cb = "Climate Benefit ($/tCO₂ removed)"
y_nb = "Net Benefit ($/tCO₂ removed)"

print("Generating Cost Curves...")
rows_cost = run_all("Cost", cost, valid_cost, reverse=False, y_label=y_cost, file_prefix="MC")

print("Generating Climate Benefit Curves...")
rows_cb = run_all("ClimateBenefit", cb, valid_cb, reverse=True, y_label=y_cb, file_prefix="MB")

print("Generating Net Benefit Curves...")
rows_nb = run_all("NetBenefit", nb, valid_nb, reverse=True, y_label=y_nb, file_prefix="MN")

# 保存 CSV
df_cost = pd.DataFrame(rows_cost)
df_cb = pd.DataFrame(rows_cb)
df_nb = pd.DataFrame(rows_nb)

cost_csv_path = os.path.join(output_dir, "Marginal_Cost_Curves.csv")
cb_csv_path = os.path.join(output_dir, "Marginal_ClimateBenefit_Curves.csv")
nb_csv_path = os.path.join(output_dir, "Marginal_NetBenefit_Curves.csv")

df_cost.to_csv(cost_csv_path, index=False, float_format="%.6f")
df_cb.to_csv(cb_csv_path, index=False, float_format="%.6f")
df_nb.to_csv(nb_csv_path, index=False, float_format="%.6f")

print("Saved figures into:", output_dir)
print("Saved CSVs.")
