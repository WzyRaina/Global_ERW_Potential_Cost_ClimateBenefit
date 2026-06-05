# 由高分辨率的全球农田地图重采样为0.5°分辨率，用网格平均值

import os
import numpy as np
from osgeo import gdal

# ===== 0. 基本路径设置 =====
os.chdir(r'C:/wzy/2-Grid-based-MONET')

# 高分辨率全球农田栅格（像元值 0–100，无 NoData）
GLOBAL_CROPLAND_HIGH = r'C:/博三上/CDR成本/MONET/Parameter/土地覆盖类型/Global_cropland_3km_2019.tif'

# 0.5° 模板栅格
TEMPLATE_0P5 = r'C:/Users/WangZeyu/Documents/ArcGIS/Projects/GetData/T_PH_H20.tif'

# 输出路径（0–1 比例的全球 cropland）
OUTPUT_CROPLAND_0P5 = r'./Global Data/EW/Input/Global/Global cropland map.tif'


def main():
    # ===== 1. 读取模板栅格，获取空间信息 =====
    tmpl_ds = gdal.Open(TEMPLATE_0P5)
    if tmpl_ds is None:
        raise RuntimeError("无法打开模板栅格，请检查 TEMPLATE_0P5 路径。")

    tmpl_gt = tmpl_ds.GetGeoTransform()
    tmpl_proj = tmpl_ds.GetProjection()
    tmpl_cols = tmpl_ds.RasterXSize
    tmpl_rows = tmpl_ds.RasterYSize

    # 模板空间范围
    minx = tmpl_gt[0]
    maxy = tmpl_gt[3]
    maxx = minx + tmpl_cols * tmpl_gt[1]
    miny = maxy + tmpl_rows * tmpl_gt[5]  # 注意 gt[5] < 0

    # ===== 2. 读取高分辨率全球农田栅格 =====
    high_ds = gdal.Open(GLOBAL_CROPLAND_HIGH)
    if high_ds is None:
        raise RuntimeError("无法打开高分辨率全球农田栅格，请检查 GLOBAL_CROPLAND_HIGH 路径。")

    # ===== 3. 重采样到 0.5°，并与模板对齐 =====
    # 高分辨率像元值为 0–100 百分比，对其做平均即得到 0.5° 网格的平均农田比例（仍为 0–100）
    cropland_0p5_ds = gdal.Warp(
        '',
        high_ds,
        format='MEM',
        dstSRS=tmpl_proj,                      # 投影与模板一致
        outputBounds=(minx, miny, maxx, maxy), # 范围与模板一致
        width=tmpl_cols,
        height=tmpl_rows,
        resampleAlg=gdal.GRA_Average           # 对 0–100 百分比求平均
    )

    cropland_0p5_arr = cropland_0p5_ds.ReadAsArray().astype(np.float32)

    # 理论上没有 NaN，但保险起见：
    cropland_0p5_arr = np.where(np.isnan(cropland_0p5_arr), 0.0, cropland_0p5_arr)

    # 从 0–100 转为 0–1 比例
    cropland_0p5_arr = cropland_0p5_arr / 100.0

    # ===== 4. 写出结果栅格 =====
    driver = gdal.GetDriverByName('GTiff')
    os.makedirs(os.path.dirname(OUTPUT_CROPLAND_0P5), exist_ok=True)

    out_ds = driver.Create(
        OUTPUT_CROPLAND_0P5,
        xsize=tmpl_cols,
        ysize=tmpl_rows,
        bands=1,
        eType=gdal.GDT_Float32
    )
    out_ds.SetGeoTransform(tmpl_gt)
    out_ds.SetProjection(tmpl_proj)

    band = out_ds.GetRasterBand(1)
    band.WriteArray(cropland_0p5_arr)
    # 真实的 0 表示“农田比例为 0”，NoData 单独设一个值
    band.SetNoDataValue(-9999)
    band.FlushCache()
    out_ds = None

    print("Done! Global 0.5° cropland fraction (0–1) saved to:", OUTPUT_CROPLAND_0P5)


if __name__ == "__main__":
    main()
