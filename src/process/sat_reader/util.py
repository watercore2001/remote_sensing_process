import os

import numpy as np
import rasterio
from osgeo import gdal, ogr
from rasterio.enums import Resampling

gdal.UseExceptions()


def read_data_with_up_sample(input_path: str, dst_resolution: int):
    with rasterio.open(input_path) as src:
        src_resolution = max(src.res)
        if src_resolution == dst_resolution:
            return src.read(), src.profile
        else:
            upscale_factor = int(src_resolution / dst_resolution)
            dst_data = src.read(
                out_shape=(
                    src.count,
                    src.height * upscale_factor,
                    src.width * upscale_factor
                ),
                resampling=Resampling.bilinear)
            dst_transform = src.transform * src.transform.scale((1 / upscale_factor), (1 / upscale_factor))
            profile = src.profile
            profile.update(transform=dst_transform,
                           width=dst_data.shape[1],
                           height=dst_data.shape[2],
                           blockxsize=profile["blockxsize"] * upscale_factor,
                           blockysize=profile["blockysize"] * upscale_factor)
            return dst_data, profile


def up_sample_and_save_as_tif(input_path: str, output_path: str, dst_resolution: int):
    data, profile = read_data_with_up_sample(input_path, dst_resolution)

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data)


def up_sample_and_sqrt_and_save_as_jpeg(input_path: str, output_path: str, dst_resolution: int):
    data, profile = read_data_with_up_sample(input_path, dst_resolution)

    # Apply square root operation
    sqrt_data = np.sqrt(data).astype(np.uint8)

    profile.update(driver="JPEG", dtype=sqrt_data.dtype)

    # Save as an 8-bit JPEG
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(sqrt_data)


def get_last_level_sub_folders(root_folder: str):
    rel_paths = []
    for dir_path, dirs, files in os.walk(root_folder):
        if len(dirs) == 0:
            rel_paths.append(dir_path)
    return rel_paths


def rasterize_geojson(json_paths: list[str], burn_values: list[int], tif_path: str, output_path: str):
    assert len(json_paths) == len(burn_values), "shp num should be corresponding to value num"
    json_num = len(json_paths)

    # read tif data
    tif_dst = gdal.Open(tif_path)

    # create output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tif_driver = gdal.GetDriverByName("GTiff")
    out_dst = tif_driver.Create(utf8_path=output_path, xsize=tif_dst.RasterXSize,
                                ysize=tif_dst.RasterYSize, bands=json_num, eType=gdal.GDT_Byte,
                                options=["COMPRESS=LZW"])

    # copy CRS and Transform
    out_dst.SetProjection(tif_dst.GetProjection())
    out_dst.SetGeoTransform(tif_dst.GetGeoTransform())
    tif_dst = None

    for i, (shp_path, burn_value) in enumerate(zip(json_paths, burn_values), start=1):
        json_dst = ogr.Open(shp_path, 0)
        json_layer = json_dst.GetLayer()
        gdal.RasterizeLayer(dataset=out_dst, bands=[i], layer=json_layer, burn_values=[burn_value])
        json_dst = None

    out_dst = None
