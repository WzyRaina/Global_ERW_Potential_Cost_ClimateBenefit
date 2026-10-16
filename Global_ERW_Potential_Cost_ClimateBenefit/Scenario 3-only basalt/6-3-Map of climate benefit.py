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
start_year = 2025

# --- 切换地图类型 (配色方案) ---
# 'CB' = Climate Benefit (气候效益): 黄色 -> 绿色
# 'NB' = Net Benefit (净效益): 黄色 -> 蓝色
CURRENT_MAP_TYPE = 'CB'

# --- 路径配置 (使用 r 前缀处理中文路径) ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# 注意：确保SHP文件及其同名的 .dbf, .shx 等文件都在这个路径下
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-57, 90]

# --- 图例单位文本 ---
LEGEND_UNIT = r"$\$/\mathrm{tCO_2\ removed}$"


# ================= 2. 高级配色方案 =================

def get_palette(map_type, has_negative):
    """
    返回颜色列表。
    策略：在全正模式下，大幅扩展黄色/暖色系的范围，
    防止低值区域过早变成绿色/蓝色，从而提高区分度。
    """

    # ====== 情况 A: 气候效益 (CB) ======
    if map_type == 'CB':
        # --- 模式 1: 有正有负 (红 - 白 - 绿) ---
        diverging_colors = [
            '#d73027',  # 负值：深红
            '#fc8d59',  # 负值过渡
            '#ffffff',  # 0值：纯白
            '#91cf60',  # 正值过渡(浅绿)
            '#1a9850'  # 正值：深绿
        ]

        # --- 模式 2: 全为正 ---
        sequential_colors = [
            '#ffff3f',
            '#eeef20',
            '#dddf00',
            '#d4d700',
            '#bfd200',
            '#aacc00',
            '#80b918',
            '#55a630',
            '#2b9348',
            '#007f5f'
        ]

    # ====== 情况 B: 净效益 (NB) ======
    else:
        # --- 模式 1: 有正有负 (红 - 白 - 蓝) ---
        diverging_colors = [
            '#b2182b',  # 负值：深酒红
            '#ef8a62',  # 负值过渡
            '#ffffff',  # 0值：纯白
            '#67a9cf',  # 正值过渡
            '#2166ac'  # 正值：深蓝
        ]

        # --- 模式 2: 全为正 (强化的黄色过渡) ---
        # 顺序：米黄 -> 浅黄 -> 金黄 -> 浅蓝 -> 深蓝
        sequential_colors = [
            '#ffffd4',  # 1. 米黄
            '#fed98e',  # 2. 浅黄
            '#fe9929',  # 3. 金黄/橙黄 - 同样增加黄色占比
            '#c7e9b4',  # 4. 蓝绿过渡
            '#41b6c4',  # 5. 浅蓝/青色
            '#225ea8',  # 6. 宝蓝
            '#081d58'  # 7. 深海军蓝
        ]

    if has_negative:
        return diverging_colors
    else:
        return sequential_colors


# ================= 3. 自动构建文件路径 =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

if maxcb:
    scenario_folder = "maxclimatebenefit"
    filename_tag = "maxnetbenefit"
else:
    scenario_folder = "mincost"
    filename_tag = "mincost"

suffix_folder = "_withtrade" if trade else "_notrade"
suffix_file = " (with trade)" if trade else ""
sub_folder = f"{scenario_folder}{suffix_folder}"

target_file_pattern = f"EW_climate_benefit_{filename_tag}_raster{suffix_file}.tif"
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{target_file_pattern}"
tif_path = os.path.abspath(tif_relative_path)

output_img_name = f"Map/Map_{start_year}_{CURRENT_MAP_TYPE}_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}.png"
output_img_path = os.path.join(os.path.dirname(tif_path), output_img_name)

print(f"当前模式: {CURRENT_MAP_TYPE}")
print(f"处理文件: {os.path.basename(tif_path)}")

# ================= 4. 读取数据 =================

if not os.path.exists(tif_path):
    print(f"错误：找不到 TIF 文件 {tif_path}")
    sys.exit(1)

with rasterio.open(tif_path) as src:
    data = src.read(1, masked=True)
    extent = [src.bounds.left, src.bounds.right, src.bounds.bottom, src.bounds.top]

# 读取 SHP (增强的中文路径支持)
gdf = None
if os.path.exists(shp_path):
    # 强制 GDAL 使用 UTF-8 处理路径，同时尝试 GBK 读取文件内容
    gdal.SetConfigOption("GDAL_FILENAME_IS_UTF8", "YES")
    gdal.SetConfigOption("SHAPE_ENCODING", "")
    try:
        print(f"尝试读取 SHP: {shp_path}")
        gdf = gpd.read_file(shp_path, encoding='gbk')  # 优先尝试 GBK
    except Exception as e1:
        print(f"GBK读取失败 ({e1})，尝试 UTF-8...")
        try:
            gdf = gpd.read_file(shp_path, encoding='utf-8')
        except Exception as e2:
            print(f"SHP 读取彻底失败: {e2}")
            print("将仅绘制栅格图。")
else:
    print(f"警告：找不到 SHP 文件: {shp_path}")

# ================= 5. 颜色映射逻辑 =================

vmin = np.nanmin(data)
vmax = np.nanmax(data)
print(f"数据范围: Min={vmin:.2f}, Max={vmax:.2f}")

has_negative = (vmin < 0 < vmax)
is_all_positive = (vmin >= 0)

# 获取颜色列表
colors = get_palette(CURRENT_MAP_TYPE, has_negative)

if has_negative:
    print(">>> 模式：有正有负 (0点对齐)")
    cmap = mcolors.LinearSegmentedColormap.from_list("CustomDiverging", colors)
    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    ticks = [vmin, 0, vmax]
    tick_labels = [f"{int(vmin)}", "0", f"{int(vmax)}"]

elif is_all_positive:
    print(">>> 模式：全为正 (多级黄色-绿色渐变)")
    # 使用 7 色渐变，Matplotlib 会在这些颜色间平滑插值
    cmap = mcolors.LinearSegmentedColormap.from_list("CustomSequential", colors)
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    ticks = [vmin, vmax]
    tick_labels = [f"{int(vmin)}", f"{int(vmax)}"]
else:
    print(">>> 模式：全为负")
    cmap = mcolors.LinearSegmentedColormap.from_list("CustomNeg", [colors[0], colors[1]])
    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    ticks = [vmin, vmax]
    tick_labels = [f"{int(vmin)}", f"{int(vmax)}"]

# ================= 6. 绘图 =================

fig, ax = plt.subplots(figsize=(10, 5.5))

# (1) 绘制栅格
im = ax.imshow(data, cmap=cmap, norm=norm, extent=extent, interpolation='nearest')

# (2) 绘制 SHP
if gdf is not None:
    # 边框颜色用深灰色，比纯黑柔和一点，线宽 0.25 比较精致
    gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5)

# (3) 裁剪范围 (使用修改后的 [-55, 90])
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

# 图例标题
cbar.set_label(LEGEND_UNIT, fontsize=16, labelpad=0)

plt.tight_layout()
plt.savefig(output_img_path, dpi=600, bbox_inches='tight', transparent=True)
print(f"保存成功: {output_img_path}")
plt.show()
