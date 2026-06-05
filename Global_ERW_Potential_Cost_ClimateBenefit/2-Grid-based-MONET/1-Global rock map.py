# GLiM的数据排除保护区（非保护区比例大于0的网格被保留），中国网格用中国岩石数据

import os
import numpy as np
from osgeo import gdal

os.chdir('C:/wzy/2-Grid-based-MONET')

# ========= 1. 读取全球 GLiM 岩石分布（0.5°） =========
global_rock_path = r'C:/Users/WangZeyu/Documents/ArcGIS/Projects/Biomass Yield/glim_rock_distribution.tif'
rock_ds = gdal.Open(global_rock_path)
rock_glim = rock_ds.ReadAsArray().astype(np.int16)   # 2=basalt, 4=olivine

rows = rock_ds.RasterYSize
cols = rock_ds.RasterXSize
gt   = rock_ds.GetGeoTransform()
proj = rock_ds.GetProjection()

minx = gt[0]
maxy = gt[3]
maxx = minx + cols * gt[1]
miny = maxy + rows * gt[5]

# ========= 2. 读取 WDPA 高分辨率，计算非保护区比例 =========
wdpa_high_path = r'C:/Users/WangZeyu/Documents/ArcGIS/Projects/GetData/WDPA_Raster.tif'
wdpa_ds = gdal.Open(wdpa_high_path)
wdpa_band = wdpa_ds.GetRasterBand(1)

wdpa_arr = wdpa_band.ReadAsArray().astype(np.float32)
wdpa_nodata = wdpa_band.GetNoDataValue()

# 把 NoData 当作 0（非保护区），否则平均时会被忽略
if wdpa_nodata is not None:
    wdpa_arr[wdpa_arr == wdpa_nodata] = 0.0

mem_drv = gdal.GetDriverByName('MEM')
wdpa_clean_ds = mem_drv.Create(
    '', wdpa_ds.RasterXSize, wdpa_ds.RasterYSize, 1, gdal.GDT_Float32
)
wdpa_clean_ds.SetGeoTransform(wdpa_ds.GetGeoTransform())
wdpa_clean_ds.SetProjection(wdpa_ds.GetProjection())
wdpa_clean_ds.GetRasterBand(1).WriteArray(wdpa_arr)

# 重采样到 0.5°，用 Average 得到保护区比例 [0,1]
wdpa_frac_ds = gdal.Warp(
    '',
    wdpa_clean_ds,
    format='MEM',
    dstSRS=proj,
    outputBounds=(minx, miny, maxx, maxy),
    width=cols,
    height=rows,
    resampleAlg=gdal.GRA_Average
)

wdpa_frac = wdpa_frac_ds.ReadAsArray().astype(np.float32)
wdpa_frac = np.where(np.isnan(wdpa_frac), 0.0, wdpa_frac)
wdpa_frac = np.clip(wdpa_frac, 0.0, 1.0)

# 非保护区比例
non_pa_frac = 1.0 - wdpa_frac
non_pa_frac = np.clip(non_pa_frac, 0.0, 1.0)

# ========= 3. 基于 GLiM + WDPA 剔除完全保护的岩石网格 =========
rock_available = np.zeros((rows, cols), dtype=np.int16)  # 先全设为 0（不可用）

mask_glim_rock = np.isin(rock_glim, [2, 4])
mask_keep_glim = mask_glim_rock & (non_pa_frac > 0)

rock_available[mask_keep_glim] = rock_glim[mask_keep_glim]

# ========= 4. 读取中国 0.5° 岩石分布（全球 360×720，含 NaN/NoData） =========
china_rock_path = r'./Global Data/EW/Input/China/China Rock Available Map.tif'
china_ds = gdal.Open(china_rock_path)
china_band = china_ds.GetRasterBand(1)

china_rock = china_band.ReadAsArray().astype(np.float32)  # 保留 NaN
china_nodata = china_band.GetNoDataValue()

# 把显式 NoData 统一成 NaN，便于判断
if china_nodata is not None:
    china_rock = np.where(china_rock == china_nodata, np.nan, china_rock)

if (china_ds.RasterXSize != cols) or (china_ds.RasterYSize != rows):
    raise ValueError("中国岩石栅格尺寸与 GLiM 不一致，请检查！")

# 有效的中国岩石网格：2 或 4
china_valid = np.isin(china_rock, [2.0, 4.0])

# ========= 5. 在“全局范围”直接用中国岩石值覆盖 =========
# 不再依赖国家代码，只要中国图上有 2/4 的地方，认为是中国 ERW 结果
rock_available[china_valid] = china_rock[china_valid].astype(np.int16)

# ========= 6. 输出最终可用岩石分布 =========
out_path = r'./Global Data/EW/Input/Global/Global Rock Available Map.tif'
driver = gdal.GetDriverByName('GTiff')
out_ds = driver.Create(out_path, xsize=cols, ysize=rows, bands=1, eType=gdal.GDT_Int16)
out_ds.SetGeoTransform(gt)
out_ds.SetProjection(proj)

band = out_ds.GetRasterBand(1)
band.WriteArray(rock_available)
band.SetNoDataValue(0)  # 0 = 无 basalt/olivine 或不可用
band.FlushCache()
out_ds = None

print("Done! Final available rock map saved to:", out_path)
