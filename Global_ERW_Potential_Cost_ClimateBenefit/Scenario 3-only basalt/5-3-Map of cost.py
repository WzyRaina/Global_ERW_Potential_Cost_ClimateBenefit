# 代替arcgis绘制地图

import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import rasterio
import geopandas as gpd
from osgeo import gdal

# ================= 1. 用户配置区域 =================

# --- 核心开关 ---
trade = False
maxcb = True
start_year = 2050

# --- 地图类型 ---
CURRENT_MAP_TYPE = 'Cost'

# --- 路径配置 ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# SHP 路径
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-57, 90]

# --- 图例单位文本 ---
LEGEND_UNIT = r"$\$/\mathrm{tCO_2\ removed}$"

# ================= 2. 成本专属配色方案 =================

# 策略：成本全为正。
# 通常低成本(好)用浅色/冷色/黄色，高成本(坏/贵)用深色/暖色/红色。
# 这里推荐：米黄 -> 橙色 -> 红色 -> 深胭脂红 -> 深紫
# 这种“热力图”风格能很好地突显高成本区域。

COST_COLORS = [
    '#0077b6',  # 深蓝 (低成本)
    '#00b4d8',
    '#90e0ef',
    '#caf0f8',  # 浅蓝
    '#fcf300',  # 浅黄
    '#fedd00',
    '#ffc600',
    '#f6bf00',  # 深黄
    '#f7b538',  # 浅红
    '#d8572a'   # 深红 (高成本)
]

# ================= 3. 自动构建文件路径 =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

# 1. 确定文件夹和文件名
if maxcb:
    if trade:
        sub_folder = "maxclimatebenefit_withtrade"
        filename = "EW_cost_maxnetbenefit_raster (with trade).tif"
    else:
        sub_folder = "maxclimatebenefit_notrade"
        filename = "EW_cost_maxnetbenefit_raster.tif"
else:
    if trade:
        sub_folder = "mincost_withtrade"
        filename = "EW_min_cost_raster (with trade).tif"
    else:
        sub_folder = "mincost_notrade"
        filename = "EW_min_cost_raster.tif"

# 2. 拼接完整路径
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{filename}"
tif_path = os.path.abspath(tif_relative_path)

# 3. 构建输出路径
# 建立 Map 文件夹
output_filename_base = f"Map_{start_year}_Cost_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}"
output_dir = os.path.join(os.path.dirname(tif_path), "Map")
os.makedirs(output_dir, exist_ok=True)

output_png_path = os.path.join(output_dir, output_filename_base + ".png")
output_svg_path = os.path.join(output_dir, output_filename_base + ".svg")

print(f"当前模式: {CURRENT_MAP_TYPE}")
print(f"处理文件: {os.path.basename(tif_path)}")
print(f"完整路径: {tif_path}")

# ================= 4. 读取数据 =================

if not os.path.exists(tif_path):
    print(f"错误：找不到 TIF 文件 {tif_path}")
    sys.exit(1)

with rasterio.open(tif_path) as src:
    data = src.read(1, masked=True)
    extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]

# 读取 SHP
gdf = None
if os.path.exists(shp_path):
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    try:
        print(f"尝试读取 SHP: {shp_path}")
        gdf = gpd.read_file(shp_path, encoding='gbk')
    except Exception as e1:
        print(f"GBK读取失败，尝试 UTF-8...")
        try:
            gdf = gpd.read_file(shp_path, encoding='utf-8')
        except Exception as e2:
            print(f"SHP 读取失败: {e2}")
else:
    print(f"警告：找不到 SHP 文件: {shp_path}")

# ================= 5. 颜色映射逻辑 =================

vmin = np.nanmin(data)
vmax = np.nanmax(data)
print(f"数据范围: Min={vmin:.2f}, Max={vmax:.2f}")

# 成本全为正，直接使用线性渐变
print(">>> 模式：成本全为正 (红->黄->蓝)")
cmap = mcolors.LinearSegmentedColormap.from_list("CostSequential", COST_COLORS)
norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
ticks = [vmin, vmax]
tick_labels = [f"{int(vmin)}", f"{int(vmax)}"]

# ================= 6. 绘图 (集成体积优化) =================

fig, ax = plt.subplots(figsize=(10, 5.5))

# (1) 绘制栅格
im = ax.imshow(data, cmap=cmap, norm=norm, extent=extent, interpolation='nearest')

# (2) 绘制 SHP (体积优化 + 样式)
if gdf is not None:
    gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5)

# (3) 裁剪范围
ax.set_ylim(MAP_Y_LIMIT)
ax.set_xlim([-180, 180])
ax.set_axis_off()

# (4) 绘制图例
cbar = plt.colorbar(im, ax=ax,
                    orientation='horizontal',
                    fraction=0.045,
                    pad=0.05,
                    aspect=40)

cbar.set_ticks(ticks)
cbar.set_ticklabels(tick_labels)
cbar.ax.tick_params(labelsize=15)
cbar.set_label(LEGEND_UNIT, fontsize=16, labelpad=0)

plt.tight_layout()

# ================= 7. 保存 =================

# PNG (高分辨率预览)
plt.savefig(output_png_path, dpi=600, bbox_inches='tight', transparent=True)
print(f"PNG 保存成功: {output_png_path}")

plt.show()
