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
CURRENT_MAP_TYPE = 'Potential'

# --- 路径配置 ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# SHP 路径
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-57, 90]

# --- 图例单位文本 (LaTeX 正体) ---
LEGEND_UNIT = r"$\mathrm{tCO_2/ha}$"

# ================= 2. 潜力专属配色方案 =================

# 策略：潜力代表“容量”或“数量”，全为正值。
# 为了区别于气候效益(绿)、净效益(蓝)和成本(红黄)，
# 这里推荐使用 **紫色系 (Purples)**。
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

# ================= 3. 自动构建文件路径 (基于你的统计代码) =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

# 1. 确定文件夹和文件名
if maxcb:
    if trade:
        sub_folder = "maxclimatebenefit_withtrade"
        # 注意：这里文件名有空格 (with trade)
        filename = "EW_potential_maxnetbenefit_raster_tCO2_ha (with trade).tif"
    else:
        sub_folder = "maxclimatebenefit_notrade"
        filename = "EW_potential_maxnetbenefit_raster_tCO2_ha.tif"
else:
    if trade:
        sub_folder = "mincost_withtrade"
        filename = "EW_potential_mincost_raster_tCO2_ha (with trade).tif"
    else:
        sub_folder = "mincost_notrade"
        filename = "EW_potential_mincost_raster_tCO2_ha.tif"

# 2. 拼接完整路径
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{filename}"
tif_path = os.path.abspath(tif_relative_path)

# 3. 构建输出路径
output_filename_base = f"Map_{start_year}_Potential_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}"
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

    # 额外处理：如果数据中有极小的负数(误差)或者 NoData，确保它们被处理
    # 你的统计代码里做了 data[data < 0] = 0 的处理，这里仅做可视化，masked=True 通常已足够
    # 但为了保险，可以将 < 0 的值设为 0 (仅在 data 不是 masked array 时)
    if not np.ma.is_masked(data):
        data[data < 0] = 0

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

print(">>> 模式：直方图均衡化 (分位数映射)")

# 提取一维纯净有效数据进行统计
valid_data = data[~np.isnan(data)]
valid_data = valid_data[valid_data > 0]

vmin_val = np.nanmin(valid_data)
vmax_val = np.nanmax(valid_data)
print(f"数据绝对范围: Min={vmin_val:.4f}, Max={vmax_val:.4f}")

# 生成基础颜色渐变尺
cmap = mcolors.LinearSegmentedColormap.from_list("PotentialSequential", POTENTIAL_COLORS)

# BoundaryNorm 计算256个分位数点作为颜色断层边界，强制拉伸拥挤的高值区
quantiles = np.unique(np.percentile(valid_data, np.linspace(0, 100, 256)))
norm = None
if len(quantiles) > 1:
    norm = mcolors.BoundaryNorm(quantiles, cmap.N)

# 为了视觉清爽，Colorbar 上的刻度仅显示两端极值点
ticks = [vmin_val, vmax_val]
tick_labels = [f"{vmin_val:.2f}", f"{vmax_val:.2f}"]

# ================= 6. 绘图 (集成体积优化) =================

fig, ax = plt.subplots(figsize=(10, 5.5))

# (1) 绘制栅格
im = ax.imshow(data, cmap=cmap, norm=norm, extent=extent, interpolation='nearest')

# (2) 绘制 SHP (体积优化 + 样式)
if gdf is not None:
    # 绘制边界线
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

if norm is not None:
    cbar.set_ticks([quantiles[0], quantiles[-1]])
else:
    cbar.set_ticks(ticks)

cbar.set_ticklabels(tick_labels)
cbar.ax.tick_params(axis='x', which='both', size=0, labelsize=15)
cbar.set_label(LEGEND_UNIT, fontsize=16, labelpad=0)

plt.tight_layout()

# ================= 7. 保存 =================

# PNG
plt.savefig(output_png_path, dpi=600, bbox_inches='tight', transparent=True)
print(f"PNG 保存成功: {output_png_path}")

plt.show()
