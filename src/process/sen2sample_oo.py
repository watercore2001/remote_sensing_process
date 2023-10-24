import argparse
import os

import numpy as np
import rasterio
from osgeo import ogr, osr
from rasterio import features

NEGATIVE_VALUE = 99
CROPPED_VALUE = 254
NOT_SURE_VALUE = 255


def next_window(
        geom_envelop: tuple[int, int, int, int],
        window_shape: tuple[int, int],
        satellite_shape: tuple[int, int],
        gt_path: str,
        transformer,
        geometry_list,
        geometry_index,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    给定要素的范围, 不断地产生窗口
    Args:
        gt_path: 备用 gt 图层
        window_shape: 窗口大小 (224, 224)
        satellite_shape: 卫星图大小, 窗口不能超过这个范围 (10980, 10980)
        geom_envelop: 要素 mbr (start_row, stop_row, start_col, stop_col)

    Returns:
        切割窗口 ((start_row, stop_row), (start_col, stop_col))
    """

    row_length = geom_envelop[1] - geom_envelop[0]
    col_length = geom_envelop[3] - geom_envelop[2]

    with rasterio.open(gt_path, "r+") as gt:
        if row_length <= window_shape[0] and col_length < window_shape[1]:

            row_buffer = (window_shape[0] - row_length) // 2.5
            col_buffer = (window_shape[1] - col_length) // 2.5

            start_row_1 = (geom_envelop[1] + geom_envelop[0] - window_shape[0]) // 2
            start_col_1 = (geom_envelop[3] + geom_envelop[2] - window_shape[1]) // 2
            start_row_2 = start_row_1 - row_buffer
            start_col_2 = start_col_1 - col_buffer
            start_row_3 = start_row_1 + row_buffer
            start_col_3 = start_col_1 + col_buffer

            # 循环遍历
            starts = (
                (start_row_1, start_col_1),
                (start_row_2, start_col_2),
                (start_row_2, start_col_3),
                (start_row_3, start_col_2),
                (start_row_3, start_col_3),
            )

            best_window = ((0, 0), (0, 0))
            best_sum = -100
            flag = False

            for start_row, start_col in starts:
                window = get_window_and_check_bound(satellite_shape, window_shape, start_row, start_col)
                image = gt.read(1, window=window)
                # 如果包含不确定的像元就跳过
                if np.sum(image == NOT_SURE_VALUE) > 0:
                    continue
                # 计算当前窗口评分
                current_sum = np.sum((0 < image) & (image < 100)) - np.sum(image == CROPPED_VALUE) * 0.00001
                if current_sum > best_sum:
                    flag = True
                    best_sum = current_sum
                    best_window = window
            if flag:
                # 将当前窗口设置为已采样
                update_image = np.ones(window_shape, dtype=rasterio.ubyte) * CROPPED_VALUE
                gt.write(update_image, window=best_window, indexes=1)
                yield best_window
        else:
            row_buffer = window_shape[0] // 8
            col_buffer = window_shape[1] // 8
            for start_row in next_line(geom_envelop[0] - row_buffer, geom_envelop[1] + row_buffer, window_shape[0]):
                for start_col in next_line(geom_envelop[2] - col_buffer, geom_envelop[3] + col_buffer, window_shape[1]):
                    window = get_window_and_check_bound(satellite_shape, window_shape, start_row, start_col)
                    image = gt.read(1, window=window)
                    window_geometry = window2geom(transformer, window)
                    # 如果包含不确定的像元或者不包含当前要素或者不包含未采样的像元 就跳过
                    if (
                            np.sum(image == NOT_SURE_VALUE) > 0
                            or not window_geometry.Intersect(geometry_list[geometry_index])
                            or np.sum((0 < image) & (image < 100)) == 0
                    ):
                        continue
                    # 将当前窗口设置为已采样
                    update_image = np.ones(window_shape, dtype=rasterio.ubyte) * CROPPED_VALUE
                    gt.write(update_image, window=window, indexes=1)
                    yield window


def window_contains_geometry(window_geometry, geometry_list, skip_list):
    for j in range(len(geometry_list)):
        if skip_list[j] is False and is_skip_feature(window_geometry, geometry_list[j]):
            skip_list[j] = True


def is_skip_feature(window_geometry: ogr.Geometry, geom: ogr.Geometry):
    intersection = window_geometry.Intersection(geom)
    if intersection.Area() >= geom.Area() * 0.6:
        return True
    return False


def next_line(geo_start_line: int, geo_end_line: int, window_length: int):
    """
    在要素的一条边上, 返回窗口的起始位置
    Args:
        geo_start_line: 地理要素的起始位置
        geo_end_line: 地理要素的结束位置
        window_length: 窗口的边长

    Returns:
        窗口的起始位置
    """

    geo_length = geo_end_line - geo_start_line
    if geo_length <= window_length:
        yield (geo_end_line + geo_start_line - window_length) // 2
    else:
        window_num = round(geo_length / window_length)
        for i in range(window_num):
            start_line = geo_start_line + i * window_length
            yield start_line
            # yield min(start_line, geo_end_line - window_length)


def get_window_and_check_bound(
        satellite_shape: tuple[int, int], window_shape: tuple[int, int], row_start: int, col_start: int
):
    """
    检查窗口是否超过卫星图的边界
    Args:
        satellite_shape: 卫星图像的像素数
        window_shape: 窗口大小
        row_start: 起始行
        col_start: 起始列

    Returns:
        窗口
    """
    win_h, win_w = window_shape
    sat_h, sat_w = satellite_shape
    if (row_start + win_h) > sat_h:
        row_start = sat_h - win_h
    if (col_start + win_w) > sat_w:
        col_start = sat_w - win_w
    if row_start < 0:
        row_start = 0
    if col_start < 0:
        col_start = 0

    return (row_start, row_start + win_h), (col_start, col_start + win_w)


def window2geom(transformer: rasterio.transform.AffineTransformer, window: tuple[tuple[int, int]]):
    """
    根据 window 构建一个几何要素
    """
    # 根据 window 构造一个地理要素
    min_x, min_y = transformer.xy(window[0][0], window[1][0])
    max_x, max_y = transformer.xy(window[0][1], window[1][1])

    if min_x > max_x:
        min_x, max_x = max_x, min_x
    if min_y > max_y:
        min_y, max_y = max_y, min_y

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(min_x, min_y)
    ring.AddPoint(min_x, max_y)
    ring.AddPoint(max_x, max_y)
    ring.AddPoint(max_x, min_y)
    ring.AddPoint(min_x, min_y)

    mbr = ogr.Geometry(ogr.wkbPolygon)
    mbr.AddGeometry(ring)

    return mbr


def crop_image(raster_filepath, output_dir, filename, window, cmp=None):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    with rasterio.open(raster_filepath) as src:

        profile = src.profile
        output_filepath = os.path.join(output_dir, filename)

        image = src.read(window=window)

        h, w = image.shape[-2], image.shape[-1]

        win_transform = src.window_transform(window)

        profile.update(
            {
                "width": w,
                "height": h,
                "transform": win_transform,
                "compress": "DEFLATE",
                "dtype": image.dtype,
            }
        )

        with rasterio.open(output_filepath, "w", **profile) as dst:
            dst.write(image)
            if cmp is not None:
                dst.write_colormap(1, cmp)


def add_mask(gt_path, mask):
    with rasterio.open(gt_path, "r+") as dst:
        image = dst.read(indexes=1)
        image[mask == 0] = NOT_SURE_VALUE
        dst.write(image, indexes=1)


def rasterize(
        shapefile_path_list: list[str], value_list: list[int], bounds: rasterio.coords.BoundingBox, output_path: str
):
    """
    栅格化每个 shapefile, 并合并为一个栅格文件
    Args:
        shapefile_path_list: 需要栅格化的 shapefile 文件
        bounds: 栅格化的范围
        output_path: 输出文件路径
        value_list: 每个 shapefile 文件栅格化的值
    """

    dir_name = os.path.dirname(output_path)
    if not os.path.isdir(dir_name):
        os.makedirs(dir_name)

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


def add_feature_to_layer(layer: ogr.Layer, geometry: ogr.Geometry, id_value: str):
    """
    根据几何数据和属性数据将要素添加到图层中
    Args:
        layer: 图层
        geometry: 几何数据
        id_value: id 值
    """
    feature = ogr.Feature(layer.GetLayerDefn())
    feature.SetField("id", id_value)
    feature.SetGeometry(geometry)
    layer.CreateFeature(feature)


def geo2pixel(
        geo_envelope: tuple[float], transformer: rasterio.transform.AffineTransformer
) -> tuple[int, int, int, int]:
    """
    将地理坐标系表示的矩形, 转换为卫星行列坐标系下的矩形
    Args:
        geo_envelope: 地理坐标系表示的矩形: (minX, maxX, minY, maxY)
        transformer: 卫星的坐标转换对象

    Returns:
        行列坐标系表示的矩形: (start_row, stop_row, start_col, stop_col)
    """
    start_row, start_col = transformer.rowcol(geo_envelope[0], geo_envelope[2])
    stop_row, stop_col = transformer.rowcol(geo_envelope[1], geo_envelope[3])

    if start_row > stop_row:
        start_row, stop_row = stop_row, start_row

    if start_col > stop_col:
        start_col, stop_col = stop_col, start_col

    return start_row, stop_row, start_col, stop_col


def get_colormap(value: list[int]) -> dict[int, tuple[int, int, int]]:
    """
    返回 值 到 RGB 的字典映射
    """
    all_colormap = {
        0: (0, 0, 0),
        1: (255, 0, 0),  # red
        2: (0, 255, 0),  # green
        3: (0, 0, 255),  # blue
    }
    return {v: all_colormap[v] for v in value}


def is_shp_crs_correct(shapefile_path_list: list[str], correct_epsg: int) -> bool:
    driver = ogr.GetDriverByName("ESRI Shapefile")
    for shp in shapefile_path_list:
        ds = driver.Open(shp, 0)  # 0 代表只读
        layer = ds.GetLayer()
        shp_epsg = int(layer.GetSpatialRef().GetAttrValue("AUTHORITY", 1))
        if shp_epsg != correct_epsg:
            return False
    return True


def get_shapefile_geometrys(shapefile_path_list: list[str], sat_geometry) -> list[ogr.Geometry]:
    """
    将多个 shapefile 文件中的要素对象中的几何数据合并为一个列表
    Args:
        shapefile_path_list: shapefile 文件

    Returns:
        几何数据列表
    """
    geometrys = []
    driver = ogr.GetDriverByName("ESRI Shapefile")

    for shp in shapefile_path_list:
        ds = driver.Open(shp, 0)  # 0 代表只读
        layer = ds.GetLayer()
        for feature in layer:
            geometry = feature.GetGeometryRef()
            # 忽略无效几何要素
            if geometry is not None and sat_geometry.Intersect(geometry):
                geometrys.append(geometry.Clone())
    return geometrys


if __name__ == "__main__":
    r"""
    sen2sample_oo.py
        -s C:\Users\watercore\Desktop\generate_dataset\T45SXS_20200726T044659\T45SXS_20200726T044659_SNR.tif
        -t C:\Users\watercore\Desktop\generate_dataset\T45SXS_20200726T044659\T45SXS_20200726T044659_Lake\T45SXS_20200726T044659_Lake.shp
        -v 1 2
        -n not_sure.shp (可选)
        -f false.shp (可选)
        -o C:\Users\watercore\Desktop\generate_dataset\data
        -w 272 272
    """

    parser = argparse.ArgumentParser()

    parser.add_argument("-s", "--sat_file", help="the satellite image", required=True)
    parser.add_argument("-t", "--gt_shapefile", nargs="+", help="the ground-truth shapefile", required=True)
    parser.add_argument("-v", "--value", type=int, nargs="+",
                        help="the value for shapefile, less than 255", required=True)
    parser.add_argument("-n", "--not_sure_shapefile", help="the not sure shapefile")
    parser.add_argument("-f", "--negative_shapefile")
    parser.add_argument("-o", "--output_dir", help="the output root directory", required=True)
    parser.add_argument("-w", "--window_shape", type=int, nargs="+", help="the shape of window for cropping images",
                        default=272)

    args = parser.parse_args()

    colormap = get_colormap(args.value)
    output_sat_dir = os.path.join(args.output_dir, "sat")
    output_gt_dir = os.path.join(args.output_dir, "gt")
    root_name = os.path.splitext(os.path.basename(args.sat_file))[0]
    gt_raster_path = os.path.join(args.output_dir, root_name + "_gt.tif")
    gt_backup_path = os.path.join(args.output_dir, root_name + "_gt_backup.tif")
    window_shapefile_path = os.path.join(args.output_dir, root_name + "_window.shp")

    # 获取栅格数据元数据
    with rasterio.open(args.sat_file) as sat:

        sat_epsg = sat.crs.to_epsg()
        # 处理 Nodata 掩膜
        sat_shape = sat.shape
        sat_mask = np.ones(sat_shape, np.int8) * 255
        sat_mask[sat.read(1) == 0] = 0
        sat_mask = features.sieve(sat_mask, size=500)
        # 投影坐标系下的范围
        sat_bounds = sat.bounds
        # 行列坐标和投影坐标的转换器
        sat_transformer = rasterio.transform.AffineTransformer(sat.transform)
        # 栅格范围
        sat_geom = window2geom(sat_transformer, ((0, sat_shape[0]), (0, sat_shape[1])))

    # 栅格化 shapefile 文件
    rasterize(args.gt_shapefile, args.value, sat_bounds, gt_raster_path)

    if args.negative_shapefile is not None:
        args.gt_shapefile.append(args.negative_shapefile)
        args.value.append(NEGATIVE_VALUE)

    # 获取 shapefile 几何数据, 注意不包括 not_sure 图层
    gt_geometrys = get_shapefile_geometrys(args.gt_shapefile, sat_geom)

    if args.not_sure_shapefile is not None:
        args.gt_shapefile.append(args.not_sure_shapefile)
        args.value.append(NOT_SURE_VALUE)

    # 检查 gt 坐标系是否和 sat 一致
    if not is_shp_crs_correct(args.gt_shapefile, sat_epsg):
        raise Exception("坐标系不一致")

    # 评分文件
    rasterize(args.gt_shapefile, args.value, sat_bounds, gt_backup_path)
    # 添加掩膜
    add_mask(gt_backup_path, sat_mask)

    # 按照面积从大到小进行排序
    gt_geometrys.sort(key=lambda x: x.Area(), reverse=True)
    # bool 列表对应几何数据列表, true 代表被跳过了
    is_geom_skip = [False] * len(gt_geometrys)

    # 创建 window 文件
    driver = ogr.GetDriverByName("ESRI Shapefile")
    if os.path.exists(window_shapefile_path):
        driver.DeleteDataSource(window_shapefile_path)

    ds = driver.CreateDataSource(window_shapefile_path)
    srs = osr.SpatialReference()
    srs.ImportFromEPSG(sat_epsg)
    # 创建图层
    window_layer = ds.CreateLayer("windows", srs, ogr.wkbPolygon)
    # 添加字段
    window_layer.CreateField(ogr.FieldDefn("id", ogr.OFTString))

    # 当前处理的要素编号
    feature_id = 1
    # 遍历列表中的每一个要素
    for i in range(len(gt_geometrys)):
        if is_geom_skip[i] is True:
            continue
        # 投影坐标系下的 mbr: (minX, maxX, minY, maxY)
        geom_geo_envelope = gt_geometrys[i].GetEnvelope()
        # 卫星像元行列坐标系下的 mbr: (start_row, stop_row, start_col, stop_col)
        geom_pixel_envelop = geo2pixel(geom_geo_envelope, sat_transformer)

        # 第 i 个要素输出的第 j 个窗口
        window_id = 0
        for crop_window in next_window(
                geom_pixel_envelop,
                args.window_shape,
                sat_shape,
                gt_backup_path,
                sat_transformer,
                gt_geometrys,
                i,
        ):
            window_geom = window2geom(sat_transformer, crop_window)
            window_contains_geometry(window_geom, gt_geometrys, is_geom_skip)
            window_id += 1
            add_feature_to_layer(window_layer, window_geom, rf"{feature_id}_{window_id}")
            # 裁剪窗口
            output_filename = rf"{root_name}_{feature_id}_{window_id}.tif"
            crop_image(args.sat_file, output_sat_dir, output_filename, crop_window)
            crop_image(gt_raster_path, output_gt_dir, output_filename, crop_window, colormap)
        feature_id += 1
        # 删除掉已经遍历完的要素, 减少 skip_feature 的耗时
        is_geom_skip[i] = True

    os.remove(gt_raster_path)
