import glob
import os

import rasterio
from osgeo import ogr

from process.cropper import ObjectOrientedCropper
from process.gt_reader import ShpReader
from process.util import window2geom, WindowArg

LabelShpFilename = "label*.shp"
FalseShpFilename = "false.shp"
UnsureShpFilename = "unsure.shp"


def init_shp_reader(shapefile_folder: str, sat_tif_path: str):
    if len(glob.glob(os.path.join(shapefile_folder, LabelShpFilename))) == 0:
        label_paths = None
        burn_values = None
    else:
        label_paths = glob.glob(os.path.join(shapefile_folder, LabelShpFilename))
        burn_values = [i + 1 for i in range(len(label_paths))]

    false_path = os.path.join(shapefile_folder, FalseShpFilename)
    if not os.path.exists(false_path):
        false_path = None

    unsure_path = os.path.join(shapefile_folder, UnsureShpFilename)
    if not os.path.exists(unsure_path):
        unsure_path = None

    rasterize_output_folder = os.path.join(shapefile_folder, "output")

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


def init_oo_cropper(shapefile_folder: str, sat_tif_path: str, window_size: int, shp_reader: ShpReader):
    with rasterio.open(sat_tif_path) as src:
        image_height = src.height
        image_width = src.width
        sat_transformer = rasterio.transform.AffineTransformer(src.transform)
        sat_geom = window2geom(sat_transformer, WindowArg(0, image_height, 0, image_width))

    sample_shapefiles = glob.glob(os.path.join(shapefile_folder, LabelShpFilename))
    if FalseShpFilename in os.listdir(shapefile_folder):
        sample_shapefiles.append(os.path.join(shapefile_folder, FalseShpFilename))

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
