import rasterio
from rasterio.enums import Resampling
import numpy as np
import dataclasses
import os

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


def up_sample_and_save_as_tif(input_path: str, output_path: str, dst_resolution:int):
    data, profile = read_data_with_up_sample(input_path, dst_resolution)

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data)


def up_sample_and_sqrt_and_save_as_jpeg(input_path: str, output_path: str, dst_resolution:int):
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


def rasterize(
        shp_path_list: list[str], value_list: list[int], bounds: rasterio.coords.BoundingBox, output_path: str
):
    """
    rasterize each shapefile and then stack into one raster file
    Args:
        shp_path_list: shapefiles need to rasterize
        bounds: bounds to
        output_path: 输出文件路径
        value_list: 每个 shapefile 文件栅格化的值
    """

    dir_name = os.path.dirname(output_path)

    shapefile_num = len(shapefile_path_list)

    # 比较运算符优先级相同, 且可以串联使用
    if 1 < shapefile_num == len(value_list):
        raster_files = []
        nums = []
        shp_id = 0

        for shp, val in zip(shapefile_path_list, value_list):
            # shapefile 栅格化后的临时文件
            raster_file = os.path.splitext(shp)[0] + ".tif"
            # 在文件名前添加参数 -<i>, 用于 gdal_calc
            raster_files.append("-%s %s" % (chr(65 + shp_id), raster_file))
            nums.append(chr(65 + shp_id))
            shp_id = shp_id + 1

            # rasterize single shapefile
            os.system(
                rf"gdal_rasterize -burn {val} -ot Byte -te {bounds.left} {bounds.bottom} {bounds.right} {bounds.top} -tr 10 10 {shp} {raster_file}"
            )

        input_path = " ".join(raster_files)  # "-1 shape1.tif -2 shape2.tif"
        str_chs = ",".join(nums)  # "1,2"
        # 将栅格化后的图像整合为 output_file, 使用 max_value 的整合规则

        os.system(
            rf'gdal_calc.py --overwrite --outfile={output_path} {input_path} --calc="numpy.max(({str_chs}), axis=0)"'
        )

        # 删除中间文件
        [os.remove(file.split(" ")[1]) for file in raster_files]

    elif 1 == shapefile_num == len(value_list):
        os.system(
            rf"gdal_rasterize -burn {value_list[0]} -ot Byte -te {bounds.left} {bounds.bottom} {bounds.right} {bounds.top} -tr 10 10 {shapefile_path_list[0]} {output_path}"
        )

    else:
        raise Exception("shp 和 value 个数不匹配")