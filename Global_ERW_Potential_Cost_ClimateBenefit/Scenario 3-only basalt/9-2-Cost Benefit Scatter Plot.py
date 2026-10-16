# 绘制成本和气候效益的气泡图

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from osgeo import gdal
from matplotlib.lines import Line2D
from mpl_toolkits.axes_grid1.inset_locator import mark_inset

# 专门处理文本自动避让防重叠的库
from adjustText import adjust_text

trade = False
maxcb = True
start_year = 2025  # 2025, 2030, 2035, 2040, 2050
show_inset = False  # 开关：True 表示插入画中画小图，False 表示不插入

# ===================== 0) Paths =====================
os.chdir(r"E:/wzy/2-Grid-based-MONET")

mapping_path = r"E:/ArcGIS/Projects/Country/global_all_count_ExportTable.csv"

if maxcb:
    if trade:
        cost_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Cost Rank (with trade).csv"
        cb_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Climate Benefit Rank (with trade).csv"
        pot_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Potential Rank (with trade).csv"
        cep_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Country Cost-effective Potential Rank (with trade).csv"
    else:
        cost_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Cost Rank.csv"
        cb_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Climate Benefit Rank.csv"
        pot_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Potential Rank.csv"
        cep_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Country Cost-effective Potential Rank.csv"
else:
    if trade:
        cost_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Cost Rank (with trade).csv"
        cb_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Climate Benefit Rank (with trade).csv"
        pot_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Potential Rank (with trade).csv"
        cep_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Country Cost-effective Potential Rank (with trade).csv"
    else:
        cost_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Cost Rank.csv"
        cb_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Climate Benefit Rank.csv"
        pot_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Potential Rank.csv"
        cep_csv_path = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Country Cost-effective Potential Rank.csv"

country_code_tif = r"E:/ArcGIS/Projects/Country/Country_code.tif"  # pixel = OID_
region_tif       = r"E:/ArcGIS/Projects/Country/Region.tif"

if maxcb:
    if trade:
        output_check_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Map/BubblePlot_CheckTable.csv"
        map_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_withtrade/Map"
    else:
        output_check_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Map/BubblePlot_CheckTable.csv"
        map_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/maxclimatebenefit_notrade/Map"
else:
    if trade:
        output_check_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Map/BubblePlot_CheckTable.csv"
        map_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_withtrade/Map"
    else:
        output_check_csv = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Map/BubblePlot_CheckTable.csv"
        map_dir = rf"./Output/EW/Global/Scenario 3/{start_year}/mincost_notrade/Map"

os.makedirs(map_dir, exist_ok=True)

# === 因为合并为一张图，只输出一个最终文件 ===
out_svg_fig = os.path.join(map_dir, "BubblePlot_Combined_Inset.svg")

# ===================== 1) Plot params =====================
# 全球平均成本与气候效益在读取国家统计结果后按潜力动态加权计算，
# 不再硬编码各年份数值。

REGION5 = [1, 4, 3, 2, 5]
region_labels = {1: "Asia", 2: "Americas", 3: "Africa", 4: "Europe", 5: "Oceania"}
REGION_COLORS = {
    1: "#1f77b4",  # Asia
    4: "#d62728",  # Europe
    3: "#2ca02c",  # Africa
    2: "#ff7f0e",  # Americas
    5: "#9467bd",  # Oceania
}

# === 【可以调整的地方】 ===
# 气泡的基准大小，如果由于画布放大显得气泡太小，可以把 900 调成 1200 或 1500
SIZE_SCALE = 1800.0

# === 【可以调整的地方】：全局气泡显示阈值 ===
# 画两个图：（1）所有国家；（2）只画出潜力大于全球最大国家潜力 0.05 的国家
PLOT_THRESH_FRAC = 0.05

TICK_FONTSIZE = 28

# 线型
LS_AVG_CB   = (0, (6, 2, 1, 2))
LS_AVG_COST = (0, (4, 2))
LS_EQUAL    = "-"

# ===================== 2) Helpers =====================
def to_num_clean(s):
    return pd.to_numeric(s.astype(str).str.replace(",", "", regex=False).str.strip(), errors="coerce")

def read_raster(path):
    ds = gdal.Open(path)
    if ds is None: raise FileNotFoundError(f"Cannot open: {path}")
    return ds.ReadAsArray()

def build_oid_to_region(country_arr, region_arr):
    valid = (country_arr >= 0) & (region_arr > 0) & (country_arr != 255)
    oid_to_region = {}
    for oid in np.unique(country_arr[valid]):
        m = valid & (country_arr == oid)
        regs = region_arr[m]
        if regs.size > 0:
            vals, cnts = np.unique(regs, return_counts=True)
            oid_to_region[int(oid)] = int(vals[np.argmax(cnts)])
    return oid_to_region

# ===================== 3) Read & merge country stats =====================
df_cost = pd.read_csv(cost_csv_path)
df_cb   = pd.read_csv(cb_csv_path)
df_pot  = pd.read_csv(pot_csv_path)
df_cep  = pd.read_csv(cep_csv_path)

for d in [df_cost, df_cb, df_pot, df_cep]:
    d["Country Code"] = to_num_clean(d["Country Code"])
df_cost["Cost"] = to_num_clean(df_cost["Cost"])
df_cb["Climate Benefit"] = to_num_clean(df_cb["Climate Benefit"])
df_pot["Potential"] = to_num_clean(df_pot["Potential"])
df_cep["Cost-effective Potential"] = to_num_clean(df_cep["Cost-effective Potential"])

df = (df_cost.merge(df_cb, on="Country Code", how="inner")
             .merge(df_pot, on="Country Code", how="inner")
             .merge(df_cep[["Country Code", "Cost-effective Potential"]], on="Country Code", how="left"))
df["Cost-effective Potential"] = df["Cost-effective Potential"].fillna(0)
df = df.dropna(subset=["Country Code", "Cost", "Climate Benefit", "Potential"]).copy()
df = df[df["Country Code"] >= 0].copy()
df["OID_INT"] = df["Country Code"].round().astype(int)

# ===================== 4) Merge SOC_CODE =====================
m = pd.read_csv(mapping_path)
m["OID_"] = to_num_clean(m["OID_"])
m = m.dropna(subset=["OID_"]).copy()
m["OID_INT"] = m["OID_"].round().astype(int)
m["SOC_LABEL"] = m["SOC_CODE"].astype(str).str.strip()
m.loc[m["SOC_LABEL"].isin(["nan", "None", ""]), "SOC_LABEL"] = np.nan

df = df.merge(m[["OID_INT", "SOC_LABEL"]], on="OID_INT", how="left")

# ===================== 5) Assign Region_ID from rasters =====================
country_arr = read_raster(country_code_tif).astype(int)
region_arr  = read_raster(region_tif).astype(int)

oid_to_region = build_oid_to_region(country_arr, region_arr)
df["Region_ID"] = df["OID_INT"].map(oid_to_region)

df = df[(df["Potential"] > 0) & (df["Region_ID"].isin(REGION5))].copy()

# 国家成本和气候效益本身已经是国内潜力加权平均；再次用国家总潜力
# 加权得到与气泡图全部国家数据完全一致的国家统计口径全球平均值。
global_potential = df["Potential"].sum()
if not np.isfinite(global_potential) or global_potential <= 0:
    raise ValueError("No positive country potential available for global weighted averages.")
global_avg_cost = float(np.sum(df["Cost"] * df["Potential"]) / global_potential)
global_avg_benefit = float(np.sum(df["Climate Benefit"] * df["Potential"]) / global_potential)

# ===================== 6) Plot metadata & Filtering =====================
pot_max = df["Potential"].max()
df["BubbleSize"] = SIZE_SCALE * np.sqrt(df["Potential"] / pot_max)
df["ColorHex"] = df["Region_ID"].map(REGION_COLORS)

# 保存完整对照表
os.makedirs(os.path.dirname(output_check_csv), exist_ok=True)
df_out = df[["OID_INT", "SOC_LABEL", "Region_ID", "Cost", "Climate Benefit", "Potential", "Cost-effective Potential", "BubbleSize", "ColorHex"]].sort_values("Potential", ascending=False).reset_index(drop=True)
df_out.to_csv(output_check_csv, index=False, float_format="%.6f")

# 划定阈值
plot_thresh_val = PLOT_THRESH_FRAC * pot_max

# 过滤图 1 的数据：全景气泡 (只显示大于阈值的)
df_plot1 = df[df["Potential"] >= plot_thresh_val].copy()

# 过滤图 2 的数据：仅 Climate Benefit > Cost 且 大于阈值
df2_all = df[(df["SOC_LABEL"].notna()) & (df["Climate Benefit"] > df["Cost"])].copy()
df_plot2 = df2_all[df2_all["Potential"] >= plot_thresh_val].copy()

# ===================== 7) 画布极限放大与主图绘制 =====================

# === 【可以调整的地方】：超级大的画布尺寸 ===
# 22 和 14 很大了，如果觉得纵轴被拉得太开，可以改为 (24, 12) 或者你喜欢的比例
fig, ax = plt.subplots(figsize=(34, 16))

# 主图散点
ax.scatter(
    df_plot1["Cost"], df_plot1["Climate Benefit"],
    s=df_plot1["BubbleSize"], c=df_plot1["ColorHex"],
    alpha=0.75, edgecolors="black", linewidths=0.3, zorder=2
)

# 主图均值线
ax.axhline(y=global_avg_benefit, color="black", linestyle=LS_AVG_CB,   linewidth=1.3, zorder=1)
ax.axvline(x=global_avg_cost,    color="black", linestyle=LS_AVG_COST, linewidth=1.3, zorder=1)

xmin, xmax = ax.get_xlim()
ymin, ymax = ax.get_ylim()
if ymin < xmin: ax.set_xlim(ymin, xmax)

x_start, x_end = max(xmin, ymin), min(xmax, ymax)
if x_end > x_start:
    ax.plot([x_start, x_end], [x_start, x_end], color="black", linestyle=LS_EQUAL, linewidth=1.6, zorder=1)

# 主图标注国家代码
texts = []
for _, r in df_plot1.iterrows():
    if pd.notna(r["SOC_LABEL"]):
        x, y = float(r["Cost"]), float(r["Climate Benefit"])
        code = str(r["SOC_LABEL"])
        texts.append(ax.text(x, y, code, fontsize=22, color="black", zorder=4))

# 由于画布很大，可以让连接线稍微拉远一点 (expand_points)
adjust_text(texts, ax=ax,
            arrowprops=dict(arrowstyle='-', color='gray', lw=0.8, alpha=0.7),
            expand_points=(2, 2))

ax.set_xlabel("Net Removal Cost ($/tCO₂ removed)", fontsize=32)
ax.set_ylabel("Climate Benefit ($/tCO₂ removed)", fontsize=32)
ax.tick_params(axis="both", which="major", labelsize=TICK_FONTSIZE)

# ===================== 8) 2列图例 =====================

# 第 1 列：颜色分类 (共 5 项，补齐至 6 项)
handles_col1 = []
for rid in REGION5:
    handles_col1.append(Line2D([0], [0], marker="o", color="none",
                          markerfacecolor=REGION_COLORS[rid], markeredgecolor="black",
                          markersize=22, label=region_labels[rid]))
# 第1列补 1 个空行，凑足 6 个
handles_col1.append(Line2D([0], [0], color="none", label=" "))

# 第 2 列：大小(3个) + 参考线(3个) = 共 6 项
handles_col2_combined = []
ref_pots = [pot_max, pot_max * 0.5, pot_max * 0.1]
for pot_val in ref_pots:
    s_val = SIZE_SCALE * np.sqrt(pot_val / pot_max)
    handles_col2_combined.append(Line2D([0], [0], marker="o", color="none",
                          markerfacecolor="white", markeredgecolor="black",
                          markersize=np.sqrt(s_val),
                          label=f"Potential: {pot_val:.1f} GtCO₂"))

handles_col2_combined.append(Line2D([0], [0], color="black", linestyle=LS_AVG_CB,   linewidth=1.6, label="Global avg climate benefit"))
handles_col2_combined.append(Line2D([0], [0], color="black", linestyle=LS_AVG_COST, linewidth=1.6, label="Global avg cost"))
handles_col2_combined.append(Line2D([0], [0], color="black", linestyle=LS_EQUAL,    linewidth=1.8, label="Cost = Climate benefit"))

# 直接把列表相加！Matplotlib 会自动把前 6 个放第一列，后 6 个放第二列。
handles_2col = handles_col1 + handles_col2_combined

# 设定 ncol=2 即可完美左右排开
ax.legend(handles=handles_2col, frameon=False, fontsize=24,
          ncol=2, columnspacing=2.5, handletextpad=0.5,
          loc="upper right", bbox_to_anchor=(0.65, 0.30))

# ===================== 9) 画中画 (Inset Plot) 绘制 CB > Cost 小图 =====================

if show_inset:
    # === 【可以调整的地方】：画中画的位置和大小 ===
    # 数组 [X起点, Y起点, 宽度, 高度]，这里使用的是相对于整个大图的坐标（0~1之间）
    # [0.60, 0.10, 0.35, 0.40] 表示：从X轴 60%、Y轴 10% 的位置开始，宽度占35%，高度占40% (即右下角)
    ax_inset = fig.add_axes([0.52, 0.42, 0.33, 0.42])

    ax_inset.scatter(
        df_plot2["Cost"], df_plot2["Climate Benefit"],
        s=df_plot2["BubbleSize"], c=df_plot2["ColorHex"],
        alpha=0.75, edgecolors="black", linewidths=0.3, zorder=2
    )

    ax_inset.axhline(y=global_avg_benefit, color="black", linestyle=LS_AVG_CB,   linewidth=1.3, zorder=1)
    ax_inset.axvline(x=global_avg_cost,    color="black", linestyle=LS_AVG_COST, linewidth=1.3, zorder=1)

    xmin2, xmax2 = ax_inset.get_xlim()
    ymin2, ymax2 = ax_inset.get_ylim()
    if ymin2 < xmin2: ax_inset.set_xlim(ymin2, xmax2)

    x_start2, x_end2 = max(xmin2, ymin2), min(xmax2, ymax2)
    if x_end2 > x_start2:
        ax_inset.plot([x_start2, x_end2], [x_start2, x_end2], color="black", linestyle=LS_EQUAL, linewidth=1.6, zorder=1)

    # 给小图加上标题，标明这是局部放大
    ax_inset.set_title("Climate Benefit > Cost", fontsize=26, pad=10)

    # 小图国家标签
    texts2 = []
    for _, r in df_plot2.iterrows():
        x, y = float(r["Cost"]), float(r["Climate Benefit"])
        code = str(r["SOC_LABEL"])
        texts2.append(ax_inset.text(x, y, code, fontsize=22, color="black", zorder=4))

    adjust_text(texts2, ax=ax_inset,
                arrowprops=dict(arrowstyle='-', color='gray', lw=0.6, alpha=0.7),
                expand_points=(1.2, 1.2))

    ax_inset.tick_params(axis="both", which="major", labelsize=20)

    # 移除画中画多余的坐标轴标题（因为大图已经有了，留刻度即可，看起来更清爽）
    ax_inset.set_xlabel("")
    ax_inset.set_ylabel("")

    # loc1 和 loc2 指定连接大图和画中画的哪个角落。
    # 这里 loc1=2 (左上), loc2=4 (右下) 或者你可以尝试 1(右上), 3(左下) 等组合，找到不挡住气泡的最佳连线
    # ec 是边缘颜色，fc 是填充色
    mark_inset(ax, ax_inset, loc1=2, loc2=3, fc="none", ec="black", linestyle="--", lw=1.5, zorder=5)


# ===================== 10) 导出与打印统计 =====================

# 注意，由于使用了 add_axes 进行画中画，不能直接用 tight_layout，这会挤压自定义轴
# plt.tight_layout() # <-- 注释掉，否则可能会引起警告或坐标移位

fig.savefig(out_svg_fig, format="svg", bbox_inches="tight")
plt.close(fig)
print(f"[Saved] Combined Figure to: {out_svg_fig}")
print(f"[Plot Info] Main view: {len(df_plot1)} countries plotted. Inset view: {len(df_plot2)} countries plotted.")

# === 这里的计算仍然使用全体未过滤的 df 进行，保证总和完全准确！ ===
df_cbgtcost_all = df[(df["SOC_LABEL"].notna()) & (df["Climate Benefit"] > df["Cost"])].copy()

pot_sum_all = df_cbgtcost_all["Potential"].sum()
cep_sum_all = df_cbgtcost_all["Cost-effective Potential"].sum()
n_countries_all = len(df_cbgtcost_all)
pot_total_all = df[df["SOC_LABEL"].notna()]["Potential"].sum()

print("\n===================== Summary: CB > Cost (All Data) =====================")
print(f"** Note: This calculation includes ALL countries, not just the >1% plotted ones **")
print(f"global_avg_cost: {global_avg_cost}; global_avg_benefit: {global_avg_benefit}")
print(f"Countries with Climate Benefit > Cost: {n_countries_all}")
print(f"Total potential (CB > Cost): {pot_sum_all:.6f} GtCO₂")
print(f"Total cost-effective potential (CB > Cost countries): {cep_sum_all:.6f} GtCO₂")
print(f"Total potential (all countries): {pot_total_all:.6f} GtCO₂")
if pot_total_all > 0:
    print(f"Share of total potential: {pot_sum_all / pot_total_all * 100:.2f}%")
    print(f"Share of cost-effective potential: {cep_sum_all / pot_total_all * 100:.2f}%")
print("==========================================================================\n")
