# 计算（1）全球网格面积；（2）各国农田总面积（需要考虑所在网格耕地占比）；（3）全球农田总面积（需要考虑所在网格耕地占比）

import rasterio
import numpy as np
import pandas as pd
import math

os.chdir(r'C:/wzy/2-Grid-based-MONET')

# === 1. 读取全球耕地栅格、全球国家代码栅格 ===
ew_tif_path = "./Global Data/EW/Input/Global/Global cropland map.tif"  # 像素值表示该网格cropland的比例（0-1）
country_tif_path = "C:/Users/WangZeyu/Documents/ArcGIS/Projects/Country/Country_code.tif"

# 全球耕地数据
with rasterio.open(ew_tif_path) as ew_src:
    ew_data = ew_src.read(1).astype(np.float32)  # 已为比例
    transform = ew_src.transform
    bounds = ew_src.bounds
    profile = ew_src.profile

# 国家代码数据（已将海洋和NoData标记为-1）
with rasterio.open(country_tif_path) as country_src:
    country_data = country_src.read(1).astype(np.int32)

print(ew_data.shape, country_data.shape)
print(f"农田比例范围: {np.min(ew_data):.2f}~{np.max(ew_data):.2f}")  # 应为0~1

# === 2. 计算全球网格面积 ===
height, width = ew_data.shape
lon_min, lat_max = bounds.left, bounds.top
lon_max, lat_min = bounds.right, bounds.bottom

latitudes = np.linspace(lat_max - 0.25, lat_min + 0.25, height)
longitudes = np.linspace(lon_min + 0.25, lon_max - 0.25, width)
lat_grid, lon_grid = np.meshgrid(latitudes, longitudes, indexing='ij')

R = 6371  # 地球半径 km
dlon_rad = math.radians(0.5)
lat1 = np.radians(lat_grid - 0.25)
lat2 = np.radians(lat_grid + 0.25)
grid_area = R**2 * dlon_rad * (np.sin(lat2) - np.sin(lat1))  # 每格面积（km²）

# 保存全球网格面积
global_area_tif_path = "./Global Data/EW/Input/Global/Global_grid_area_km2.tif"
profile.update(dtype=rasterio.float32, count=1)
with rasterio.open(global_area_tif_path, 'w', **profile) as dst:
    dst.write(grid_area.astype(np.float32), 1)

# === 3. 计算实际耕地面积 ===
# 全球实际耕地面积 = 网格面积 × 农田比例
global_cropland_area = grid_area * ew_data  # 单位: km²

# 保存耕地面积栅格
output_tif = "./Global Data/EW/Input/Global/Global_cropland_area_km2.tif"
profile.update(dtype=rasterio.float32, nodata=0)
with rasterio.open(output_tif, 'w', **profile) as dst:
    dst.write(global_cropland_area.astype(np.float32), 1)

# === 4. 按国家统计耕地面积 ===
country_stats = []
for code in np.unique(country_data):
    if code < 0:     # ✅ 跳过 -1（海洋或无国区）
        continue
    mask = (country_data == code)
    total_area = np.sum(global_cropland_area[mask])
    area_country = grid_area[mask]
    cropland_area_country = global_cropland_area[mask]
    total_area_country = np.sum(area_country)
    if total_area_country > 0:
        mean_coverage = np.sum(cropland_area_country) / total_area_country * 100  # %
    else:
        mean_coverage = 0.0
    country_stats.append({
        'country_code': int(code),
        'total_cropland_area_km2': float(total_area),
        'mean_coverage_percent': float(mean_coverage)
    })

# 保存统计结果
df = pd.DataFrame(country_stats)
df.to_csv("./Global Data/EW/Input/Global/Global_country_cropland_area.csv", index=False)

# === 5. 汇总结果：全球每个网格的面积、农田比例、农田面积 ===
# 创建DataFrame
mask_land = country_data.flatten() >= 0
df_all = pd.DataFrame({
    'Country Code': country_data.flatten()[mask_land],
    'Grid Area': grid_area.flatten()[mask_land],
    'Cropland Ratio': ew_data.flatten()[mask_land],
    'Cropland Area': global_cropland_area.flatten()[mask_land]
})

# 保存为CSV
df_all.to_csv("./Global Data/EW/Input/Global/Global_Cropland_Stats.csv", index=False)

total_global_cropland_area_km2 = np.sum(global_cropland_area)
print(f"全球适宜EW的土地总面积为：{total_global_cropland_area_km2:.2f} 平方公里")
