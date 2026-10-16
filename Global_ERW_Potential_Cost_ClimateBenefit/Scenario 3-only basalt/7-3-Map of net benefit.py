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
CURRENT_MAP_TYPE = 'NB'

# --- 路径配置 ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# SHP 路径
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-57, 90]

# --- 图例单位文本 ---
LEGEND_UNIT = r"$\$/\mathrm{tCO_2\ removed}$"


# ================= 2. 高级配色方案 =================

def get_palette(map_type, has_negative):
    """
    返回颜色列表。
    """

    # ====== 情况 A: 气候效益 (CB) - 黄绿系 ======
    if map_type == 'CB':
        # 模式 1: 有正有负 (红 - 白 - 绿)
        diverging_colors = ['#d73027', '#fc8d59', '#ffffff', '#91cf60', '#1a9850']
        # 模式 2: 全为正 (金黄 -> 柠檬绿 -> 深绿)
        sequential_colors = [
            '#ffff3f', '#eeef20', '#dddf00', '#d4d700', '#bfd200',
            '#aacc00', '#80b918', '#55a630', '#2b9348', '#007f5f'
        ]

    # ====== 情况 B: 净效益 (NB) - 黄蓝系 ======
    else:
        # 模式 1: 有正有负 (红 - 白 - 绿)
        diverging_colors = [
            '#691e06',  # 负值：深酒红
            '#8f250c',  # 负值过渡
            '#bb4d00',
            '#fbba72',
            '#ffffff',  # 0值：纯白
            '#ecf39e',
            '#90a955',
            '#4f772d',  # 正值过渡
            '#31572c'   # 正值：深绿
        ]

        # 模式 2: 全为正 (金黄 -> 浅蓝 -> 深蓝)
        sequential_colors = [
            '#ffffd4',  # 1. 米黄
            '#fed98e',  # 2. 浅黄
            '#fe9929',  # 3. 金黄/橙黄 (低值高亮)
            '#c7e9b4',  # 4. 蓝绿过渡
            '#41b6c4',  # 5. 浅蓝/青色
            '#225ea8',  # 6. 宝蓝
            '#081d58'   # 7. 深海军蓝
        ]

    if has_negative:
        return diverging_colors
    else:
        return sequential_colors


# ================= 3. 自动构建文件路径 =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

# 1. 确定文件夹前缀
if maxcb:
    scenario_folder = "maxclimatebenefit"
else:
    scenario_folder = "mincost"

# 2. 确定后缀
suffix_folder = "_withtrade" if trade else "_notrade"
suffix_file = " (with trade)" if trade else ""
sub_folder = f"{scenario_folder}{suffix_folder}"

# 3. 确定文件名 (核心修改：区分 CB 和 NB 的命名规则)
if CURRENT_MAP_TYPE == 'CB':
    # 气候效益的文件名逻辑
    tag = "maxnetbenefit" if maxcb else "mincost"
    filename = f"EW_climate_benefit_{tag}_raster{suffix_file}.tif"

elif CURRENT_MAP_TYPE == 'NB':
    # 净效益的文件名逻辑
    if maxcb:
        # maxcb=True 时，文件名是 EW_max_net_benefit_raster
        filename = f"EW_max_net_benefit_raster{suffix_file}.tif"
    else:
        # maxcb=False (mincost) 时，文件名是 EW_net_benefit_mincost_raster
        filename = f"EW_net_benefit_mincost_raster{suffix_file}.tif"

# 4. 拼接完整路径
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{filename}"
tif_path = os.path.abspath(tif_relative_path)

# 5. 构建输出路径
output_filename_base = f"Map_{start_year}_{CURRENT_MAP_TYPE}_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}"
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

has_negative = (vmin < 0 < vmax)
is_all_positive = (vmin >= 0)

colors = get_palette(CURRENT_MAP_TYPE, has_negative)

if has_negative:
    print(">>> 模式：有正有负 (0点对齐)")
    cmap = mcolors.LinearSegmentedColormap.from_list("CustomDiverging", colors)
    norm = mcolors.TwoSlopeNorm(vmin=vmin, vcenter=0, vmax=vmax)
    ticks = [vmin, 0, vmax]
    tick_labels = [f"{int(vmin)}", "0", f"{int(vmax)}"]

elif is_all_positive:
    print(">>> 模式：全为正 (多级渐变)")
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

# (2) 绘制 SHP (黑色，清晰线宽)
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
