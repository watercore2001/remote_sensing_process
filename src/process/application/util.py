import glob
import os

import rasterio
from osgeo import ogr

from process.cropper import ObjectOrientedCropper
from process.gt_reader import ShpReader
from process.util import window2geom, WindowArg

gt_folder_name = "gt"
img_folder_name = "img"


def init_shp_reader(scene_folder: str, sat_tif_path: str):

    gt_folder = os.path.join(scene_folder, "gt")

    label_paths = []
    burn_values = []

    for label_value in os.listdir(gt_folder):
        label_folder = os.path.join(gt_folder, label_value)
        if label_value.isdigit() and os.path.isdir(label_folder):
            value = int(label_value)
            for shp_path in glob.glob(os.path.join(label_folder, "*.shp")):
                label_paths.append(shp_path)
                burn_values.append(value)

    if len(label_paths) == 0:
        label_paths = None
        burn_values = None

    false_path = None
    unsure_path = None

    rasterize_output_folder = os.path.join(scene_folder, "rasterize")

    shp_reader = ShpReader(sat_tif_path, rasterize_output_folder, label_paths, burn_values, false_path, unsure_path)
    return shp_reader


def get_shapefile_geometry_list(shapefile_path_list: list[str], sat_geometry: ogr.Geometry) -> list[ogr.Geometry]:
    driver = ogr.GetDriverByName("ESRI Shapefile")
    geometry_list = []
    for shp in shapefile_path_list:
        ds = driver.Open(shp, 0)
        layer = ds.GetLayer()
        for feature in layer:
            geometry = feature.GetGeometryRef()
            if geometry is not None and sat_geometry.Intersect(geometry):
                geometry_list.append(geometry.Clone())
    return geometry_list


def init_oo_cropper(scene_folder: str, sat_tif_path: str, window_size: int, shp_reader: ShpReader):
    with rasterio.open(sat_tif_path) as src:
        image_height = src.height
        image_width = src.width
        sat_transformer = rasterio.transform.AffineTransformer(src.transform)
        sat_geom = window2geom(sat_transformer, WindowArg(0, image_height, 0, image_width))

    sample_shapefiles = []
    for label_value in os.listdir(scene_folder):
        label_folder = os.path.join(scene_folder, label_value)
        if label_value.isdigit() and os.path.isdir(label_folder):
            for shp_path in glob.glob(os.path.join(label_folder, "*.shp")):
                sample_shapefiles.append(shp_path)

    geometry_list = get_shapefile_geometry_list(sample_shapefiles, sat_geom)
    geometry_list.sort(key=lambda x: x.Area(), reverse=True)
    cropper = ObjectOrientedCropper(image_height, image_width, window_size, geometry_list, shp_reader)

    return cropper


def get_last_level_sub_folders(root_folder: str):
    rel_paths = []
    for dir_path, dirs, files in os.walk(root_folder):
        if len(dirs) == 0:
            rel_paths.append(dir_path)
    return rel_paths
