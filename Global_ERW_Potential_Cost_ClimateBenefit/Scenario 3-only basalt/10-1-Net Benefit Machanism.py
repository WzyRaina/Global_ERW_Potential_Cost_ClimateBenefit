# ==============================================================================
# 绘制组合图 (重要性排序 + 镶嵌箱线图)
# 包含: 随机森林归因 -> 条形图 (主) + 距离阈值箱线图 (嵌)
# ==============================================================================

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from osgeo import gdal
from sklearn.ensemble import RandomForestRegressor

# === 1. 全局绘图参数设置 ===
plt.rcParams['font.family'] = 'Arial'
plt.rcParams['axes.linewidth'] = 1.5
plt.rcParams['xtick.major.width'] = 1.5
plt.rcParams['ytick.major.width'] = 1.5
plt.rcParams['xtick.direction'] = 'out'
plt.rcParams['ytick.direction'] = 'out'

# 字体大小配置 (根据组合图调整)
FONT_AXIS_LABEL = 20
FONT_TICK_LABEL = 18
FONT_TEXT_LABEL = 16

# === 2. 路径与配置 ===
base_dir = r"E:/wzy/2-Grid-based-MONET"
os.chdir(base_dir)

trade = True
maxcb = True
start_year = 2025

# 自动构建路径
if maxcb:
    folder_name = "maxclimatebenefit_withtrade" if trade else "maxclimatebenefit_notrade"
    nb_name = "EW_max_net_benefit_raster"
    pot_name = "EW_potential_maxnetbenefit_raster"
else:
    folder_name = "mincost_withtrade" if trade else "mincost_notrade"
    nb_name = "EW_net_benefit_mincost_raster"
    pot_name = "EW_potential_mincost_raster"

suffix = " (with trade)" if trade else ""
input_dir = f"./Output/EW/Global/Scenario 3/{start_year}/{folder_name}"
output_dir = f"{input_dir}/Marginal_Curves"
os.makedirs(output_dir, exist_ok=True)

nb_path = f"{input_dir}/{nb_name}{suffix}.tif"
pot_path = f"{input_dir}/{pot_name}{suffix}.tif"

# 驱动因子路径
base_arcgis = r"E:/ArcGIS/Projects"
feature_paths = {
    "Soil Temperature":    f"{base_arcgis}/Biomass Yield/Soil_Temperature.tif",
    "Soil pH":             f"{base_arcgis}/GetData/T_PH_H20.tif",
    "Electricity Emission Factor":  f"{base_arcgis}/Country/UNFCCC_Electricity_Factor.tif",
    "Diesel Price":   f"{base_arcgis}/Country/Diesel_Cost_Raster.tif",
    "GNI":      f"{base_arcgis}/Country/GNI_Raster.tif",
    "Electricity Price":     f"{base_arcgis}/Country/Electricity_Price_Raster.tif",
    "Rock Price":     f"{base_arcgis}/Country/Rock_Price.tif",
}

if trade:
    dist_path = "./Global Data/EW/Output/Global/EW_global_transport_distance_basalt (with trade).tif"
else:
    dist_path = "./Global Data/EW/Output/Global/EW_global_transport_distance_basalt.tif"
feature_paths["Rock Transport Distance"] = dist_path

# ==============================================================================
# 模块 A: 数据加载与清洗 (保持严谨逻辑)
# ==============================================================================
def read_raster(path):
    if not os.path.exists(path):
        print(f"[Error] File not found: {path}")
        return None
    ds = gdal.Open(path)
    if ds is None: return None
    array = ds.ReadAsArray()
    return array.flatten()

print(">>> Loading and Cleaning Data...")
nb_flat = read_raster(nb_path)
pot_flat = read_raster(pot_path)

if nb_flat is None or pot_flat is None: raise ValueError("Core data missing!")

data_dict = {"Net Benefit": nb_flat, "Potential": pot_flat}
valid_features = []
for name, path in feature_paths.items():
    arr = read_raster(path)
    if arr is not None and len(arr) == len(nb_flat):
        data_dict[name] = arr
        valid_features.append(name)

df = pd.DataFrame(data_dict)
# 清洗 NoData 和 无潜力区域
df = df.replace(-9999, np.nan).replace(-9999.0, np.nan)
df_clean = df.dropna()
df_clean = df_clean[df_clean["Potential"] > 0]

print(f"Data ready. Valid pixels: {len(df_clean)}")

# ==============================================================================
# 模块 B: 随机森林归因计算
# ==============================================================================
print("\n>>> Running Random Forest...")

X = df_clean[valid_features]
y = df_clean["Net Benefit"]

# 训练随机森林
rf = RandomForestRegressor(n_estimators=200, max_depth=20, n_jobs=-1, random_state=42)
rf.fit(X, y)

importances = rf.feature_importances_
feature_ranking = pd.DataFrame({
    "Feature": valid_features,
    "Importance": importances
}).sort_values("Importance", ascending=True)  # 从小到大排，方便 barh

# ==============================================================================
# 模块 C: 绘制组合图 (主图: Bar, 插图: Boxplot)
# ==============================================================================
print("\n>>> Plotting Combined Figure...")

fig, ax_main = plt.subplots(figsize=(10.5, 6))

# --- 1. 绘制主图 (Feature Importance) ---
bars = ax_main.barh(feature_ranking["Feature"], feature_ranking["Importance"],
                    color="#233d4d", height=0.6)

# 设置 X 轴范围 (多留空白给数字和插图)
max_score = feature_ranking["Importance"].max()
ax_main.set_xlim(0, max_score * 1.2)  # 留出 30% 空白

# 标注 5 位小数
for i, v in enumerate(feature_ranking["Importance"]):
    ax_main.text(v + 0.005, i, f"{v:.3f}", va='center', fontsize=FONT_TEXT_LABEL)

# 设置标签
ax_main.set_xlabel("Relative Importance (0-1)", fontsize=FONT_AXIS_LABEL)
ax_main.tick_params(axis='both', labelsize=FONT_TICK_LABEL)

# 去除边框
# ax_main.spines['right'].set_visible(False)
# ax_main.spines['top'].set_visible(False)

# --- 2. 准备插图数据 (Boxplot Data) ---
pos_dist = df_clean[df_clean["Net Benefit"] > 0]["Rock Transport Distance"]
neg_dist = df_clean[df_clean["Net Benefit"] <= 0]["Rock Transport Distance"]
data_to_plot = [pos_dist, neg_dist]

# --- 3. 创建插图 (Inset Axes) ---
# [left, bottom, width, height] 这里的坐标是相对于 ax_main 的比例 (0-1)
# 因为 Distance 在最上面，下面是空的，所以把图放在右下角
inset_ax = ax_main.inset_axes([0.35, 0.1, 0.6, 0.6])

# 绘制箱线图
bp = inset_ax.boxplot(data_to_plot, patch_artist=True,
                      labels=['Profit\n(net benefit > 0)', 'Loss\n(net benefit ≤ 0)'],
                      widths=0.5, showfliers=False)

# 美化箱线图
colors = ['#fe7f2d', '#fcca46']
for patch, color in zip(bp['boxes'], colors):
    patch.set_facecolor(color)
    patch.set_alpha(0.8)
    patch.set_linewidth(1.2)
for median in bp['medians']:
    median.set(color='black', linewidth=1.5)

# 标注中位数
med_pos = np.median(pos_dist)
med_neg = np.median(neg_dist)
# 在箱体上方标注数字
inset_ax.text(1, med_pos * 1.3, f"{med_pos:.0f} km", ha='center', fontsize=FONT_TEXT_LABEL-2, fontweight='bold')
inset_ax.text(2, med_neg * 1.1, f"{med_neg:.0f} km", ha='center', fontsize=FONT_TEXT_LABEL-2, fontweight='bold')

# 设置插图样式
inset_ax.set_ylabel("Rock Transport Distance (km)", fontsize=FONT_TEXT_LABEL)
inset_ax.tick_params(labelsize=FONT_TEXT_LABEL-2)
inset_ax.grid(axis='y', linestyle='--', alpha=0.3)
inset_ax.set_title("Transport distance: profit vs loss", fontsize=FONT_TEXT_LABEL, pad=5)

# --- 4. 保存 ---
plt.tight_layout()
save_path = os.path.join(output_dir, "Fig_Combined_Importance_Distance.svg")
plt.savefig(save_path, format='svg', bbox_inches='tight')
plt.close()

print(f"Saved Combined Figure: {save_path}")
