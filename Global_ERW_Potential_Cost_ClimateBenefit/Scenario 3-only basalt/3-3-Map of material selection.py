# 代替arcgis绘制地图

import os
import sys
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
CURRENT_MAP_TYPE = 'TechSelect'

# --- 路径配置 ---
base_work_dir = r"E:/wzy/2-Grid-based-MONET"
# SHP 路径
shp_path = r"C:\博三上\CDR成本\MONET\Parameter\电力排放因子\Global Map\global_all_country.shp"

# --- 地图裁剪范围 (南纬 55 度以北) ---
MAP_Y_LIMIT = [-57, 90]

# ================= 2. 离散配色方案 =================

# 对应你之前饼图代码中的技术颜色：
# "1" = "Basalt, 2μm"  = "#f8dda4"
# "2" = "Basalt, 10μm" = "#f9a03f"
# "3" = "Basalt, 20μm" = "#d45113"
# "4" = "Basalt, 50μm" = "#813405"

TECH_COLORS = [
    "#f8dda4",  # Tech 1
    "#f9a03f",  # Tech 2
    "#d45113",  # Tech 3
    "#813405"   # Tech 4
]

# ================= 3. 自动构建文件路径 =================

if os.path.exists(base_work_dir):
    os.chdir(base_work_dir)

# 1. 确定文件夹和文件名
if maxcb:
    if trade:
        sub_folder = "maxclimatebenefit_withtrade"
        filename = "EW_max_net_benefit_scenario_raster (with trade).tif"
    else:
        sub_folder = "maxclimatebenefit_notrade"
        filename = "EW_max_net_benefit_scenario_raster.tif"
else:
    if trade:
        sub_folder = "mincost_withtrade"
        filename = "EW_min_cost_scenario_raster (with trade).tif"
    else:
        sub_folder = "mincost_notrade"
        filename = "EW_min_cost_scenario_raster.tif"

# 2. 拼接完整路径
tif_relative_path = f"./Output/EW/Global/Scenario 3/{start_year}/{sub_folder}/{filename}"
tif_path = os.path.abspath(tif_relative_path)

# 3. 构建输出路径
output_filename_base = f"Map_{start_year}_Tech_{'MaxCB' if maxcb else 'MinCost'}_{'Trade' if trade else 'NoTrade'}"
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
    # 读取数据，Masked=True 会自动处理 NoData
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
    except Exception:
        try:
            gdf = gpd.read_file(shp_path, encoding='utf-8')
        except Exception as e:
            print(f"SHP 读取失败: {e}")
else:
    print(f"警告：找不到 SHP 文件: {shp_path}")


# ================= 5. 离散颜色映射逻辑 (核心修改) =================

print(">>> 模式：技术选择 (离散 1-4)")

# 1. 创建离散色表
cmap = mcolors.ListedColormap(TECH_COLORS)

# 2. 创建边界归一化 (BoundaryNorm)
# 这里的边界定义为 [0.5, 1.5, 2.5, 3.5, 4.5]
# 意思就是：
#   数值 1 (在 0.5-1.5 之间) -> 映射到 第1个颜色
#   数值 2 (在 1.5-2.5 之间) -> 映射到 第2个颜色
#   ...以此类推
bounds = [0.5, 1.5, 2.5, 3.5, 4.5]
norm = mcolors.BoundaryNorm(bounds, cmap.N)


# ================= 6. 绘图 =================

fig, ax = plt.subplots(figsize=(10, 5.5))

# (1) 绘制栅格
# interpolation='nearest' 非常重要！
# 对于分类数据，绝对不能用 linear 或 bicubic 插值，否则边界会出现不存在的小数值
im = ax.imshow(data, cmap=cmap, norm=norm, extent=extent, interpolation='nearest')

# (2) 绘制 SHP
if gdf is not None:
    gdf.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=0.5)

# (3) 裁剪范围
ax.set_ylim(MAP_Y_LIMIT)
ax.set_xlim([-180, 180])
ax.set_axis_off()

# (4) 不绘制图例 (根据要求)
# 如果以后需要图例，可以用 plt.legend 或自定义 patch
print("提示：已根据要求隐藏图例。")

plt.tight_layout()

# ================= 7. 保存 =================

# PNG
plt.savefig(output_png_path, dpi=600, bbox_inches='tight', transparent=True)
print(f"PNG 保存成功: {output_png_path}")

plt.show()
