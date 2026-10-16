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
trade = False  # 是否考虑贸易
maxcb = True  # 是否最大化气候净效益
start_year = 2025  # 起始年份

# --- 地图类型 ---
CURRENT_MAP_TYPE = 'MultiYearPotential'

# --- 路径配置 ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# SHP 路径
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-55, 90]

# --- 图例单位文本 (LaTeX 正体，每年的潜力) ---
LEGEND_UNIT = r"$\mathrm{tCO_2/ha/yr}$"

# ================= 2. 潜力专属配色方案 (蓝色系) =================

# 策略：沿用单年潜力的紫色系，代表“容量/数量”，全为正值。
# 顺序：极淡紫 -> 浅紫 -> 中紫 -> 深紫 -> 墨紫
POTENTIAL_COLORS = [
    '#d9ed92',  # 黄 (低潜力)
    '#b5e48c',
    '#99d98c',
    '#76c893',
    '#52b69a',
    '#34a0a4',
    '#168aad',
    '#1a759f',
    '#1e6091',
    '#184e77'  # 蓝 (高潜力)
]

# ================= 3. 自动构建文件路径 (基于你的Multi-year逻辑) =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

# 1. 确定子文件夹名称
if maxcb:
    if trade:
        sub_folder = "maxclimatebenefit_withtrade"
    else:
        sub_folder = "maxclimatebenefit_notrade"
else:
    if trade:
        sub_folder = "mincost_withtrade"
    else:
        sub_folder = "mincost_notrade"

# 2. 确定文件名 (文件名固定为 EW_multi_year_potential_raster.tif)
filename = "EW_multi_year_potential_raster_tCO2_ha.tif"

# 3. 拼接完整路径
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{filename}"
tif_path = os.path.abspath(tif_relative_path)

# 4. 构建输出路径
output_filename_base = f"Map_{start_year}_MultiYearPotential_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}"
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

    # 额外处理：如果数据中有极小的负数(误差)，设为 0
    if not np.ma.is_masked(data):
        data[data < 0] = 0
    else:
        # 如果是 masked array，只处理非 mask 区域的负数
        data[~data.mask & (data < 0)] = 0

# 读取 SHP
gdf = None
if os.path.exists(shp_path):
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    try:
        print(f"尝试读取 SHP: {shp_path}")
        gdf = gpd.read_file(shp_path, encoding='gbk')
    except Exception:
        try:
            gdf = gpd.read_file(shp_path, encoding='utf-8')
        except Exception as e:
            print(f"SHP 读取失败: {e}")
else:
    print(f"警告：找不到 SHP 文件: {shp_path}")

# ================= 5. 颜色映射逻辑 =================

vmin = np.nanmin(data)
vmax = np.nanmax(data)
# 确保 vmin 不小于 0
if vmin < 0: vmin = 0

print(f"数据范围: Min={vmin:.4f}, Max={vmax:.4f}")

print(">>> 模式：多年潜力全为正 (蓝色系)")
cmap = mcolors.LinearSegmentedColormap.from_list("PotentialSequential", POTENTIAL_COLORS)
norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

# 设置刻度：只显示 Min 和 Max，保留两位小数
ticks = [vmin, vmax]
tick_labels = [f"{vmin:.2f}", f"{vmax:.2f}"]

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

# PNG
plt.savefig(output_png_path, dpi=600, bbox_inches='tight', transparent=True)
print(f"PNG 保存成功: {output_png_path}")

plt.show()
