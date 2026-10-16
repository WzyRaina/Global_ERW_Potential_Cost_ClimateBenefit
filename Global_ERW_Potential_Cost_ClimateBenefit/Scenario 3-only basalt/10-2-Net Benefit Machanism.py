# ==============================================================================
# 分别绘制两个图 (重要性排序柱状图 + 距离阈值箱线图)
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

# 字体大小配置
FONT_AXIS_LABEL = 20
FONT_TICK_LABEL = 18
FONT_TEXT_LABEL = 16

# === 2. 路径与配置 ===
base_dir = r"E:/wzy/2-Grid-based-MONET"
os.chdir(base_dir)

trade = False
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
# 模块 C: 分别绘制两个图
# ==============================================================================
print("\n>>> Plotting Separate Figures...")

# --- 1. 绘制并保存主图 (Feature Importance) ---
fig1, ax1 = plt.subplots(figsize=(10.5, 7))

bars = ax1.barh(feature_ranking["Feature"], feature_ranking["Importance"],
                color="#233d4d", height=0.6)

# 设置 X 轴范围
max_score = feature_ranking["Importance"].max()
ax1.set_xlim(0, max_score * 1.2)

# 标注 3 位小数
for i, v in enumerate(feature_ranking["Importance"]):
    ax1.text(v + 0.005, i, f"{v:.4f}", va='center', fontsize=FONT_TEXT_LABEL)

# 设置标签
ax1.set_xlabel("Relative Importance (0-1)", fontsize=FONT_AXIS_LABEL)
ax1.tick_params(axis='both', labelsize=FONT_TICK_LABEL)

plt.tight_layout()
save_path_importance = os.path.join(output_dir, "Fig_Feature_Importance.svg")
fig1.savefig(save_path_importance, format='svg', bbox_inches='tight')
plt.close(fig1)
print(f"Saved Importance Figure: {save_path_importance}")

# --- 2. 准备箱线图数据 (Boxplot Data) ---
pos_dist = df_clean[df_clean["Net Benefit"] > 0]["Rock Transport Distance"]
neg_dist = df_clean[df_clean["Net Benefit"] <= 0]["Rock Transport Distance"]
data_to_plot = [pos_dist, neg_dist]

# --- 3. 绘制并保存箱线图 ---
fig2, ax2 = plt.subplots(figsize=(10.5, 7))

# 绘制箱线图
bp = ax2.boxplot(data_to_plot, patch_artist=True,
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
ax2.text(1, med_pos * 1.05, f"{med_pos:.0f} km", ha='center', fontsize=FONT_TEXT_LABEL, fontweight='bold')
ax2.text(2, med_neg * 1.05, f"{med_neg:.0f} km", ha='center', fontsize=FONT_TEXT_LABEL, fontweight='bold')

# 设置轴标签和样式
ax2.set_ylabel("Rock Transport Distance (km)", fontsize=FONT_AXIS_LABEL)
ax2.tick_params(labelsize=FONT_TICK_LABEL)
ax2.grid(axis='y', linestyle='--', alpha=0.3)

plt.tight_layout()
save_path_distance = os.path.join(output_dir, "Fig_Transport_Distance_Boxplot.svg")
fig2.savefig(save_path_distance, format='svg', bbox_inches='tight')
plt.close(fig2)
print(f"Saved Distance Boxplot Figure: {save_path_distance}")
