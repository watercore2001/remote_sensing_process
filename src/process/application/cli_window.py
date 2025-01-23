import argparse
import os
import datetime

import rasterio
from osgeo import ogr, osr
from process.application.util import init_oo_cropper, init_shp_reader, img_folder_name
from process.cropper import SlideWindowCropper
from process.downloader import AwsSentinel2L2aDownloader, sentinel2_l2a_bands
from process.util import window2geom


def parse_args():
    cropper_choices = ["object", "slide"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Input folder.")
    parser.add_argument("-a", "--align_band", choices=sentinel2_l2a_bands, type=str, required=True, default="B04")
    parser.add_argument("-c", "--cropper", choices=cropper_choices, type=str, required=True, default="slide",
                        help="There are three cropper to choose.")
    parser.add_argument("--window_size", type=int)
    parser.add_argument("--window_overlap_size", type=int, default=0,
                        help="This will be used if you choose slide cropper.")

    args = parser.parse_args()

    # check args
    if args.cropper == "slide" and args.window_overlap_size is None:
        parser.error("Argument --window_overlap_size requires when --cropper is slide.")

    return args


def main():
    args = parse_args()

    # 1. download aws sentinel-2 sat images, will skip exist band
    aws_downloader = AwsSentinel2L2aDownloader()
    aws_downloader.download_all_files(input_folder=args.input_folder,
                                      download_sub_folder=img_folder_name,
                                      bands=[args.align_band])

    # 2. iter scene folder
    for folder in os.listdir(args.input_folder):
        scene_folder = os.path.join(args.input_folder, folder)
        if not os.path.isdir(scene_folder):
            continue

        now_str = datetime.datetime.now().strftime("%Y%m%d_%H%M")
        output_window_folder_name = f"window_{now_str}"

        output_window_shp_path = os.path.join(scene_folder, output_window_folder_name, "window.shp")
        os.makedirs(os.path.dirname(output_window_shp_path), exist_ok=True)
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(output_window_shp_path):
            driver.DeleteDataSource(output_window_shp_path)

        ds = driver.CreateDataSource(output_window_shp_path)
        srs = osr.SpatialReference()
        sat_tif_path = os.path.join(scene_folder, img_folder_name, f"{args.align_band}.tif")
        with rasterio.open(sat_tif_path) as src:
            epsg = src.crs.to_epsg()
            image_height = src.height
            image_width = src.width
        srs.ImportFromEPSG(epsg)
        window_layer = ds.CreateLayer("windows", srs, ogr.wkbPolygon)
        window_layer.CreateField(ogr.FieldDefn("id", ogr.OFTString))

        # 3. init shp reader
        shp_reader = init_shp_reader(scene_folder, sat_tif_path)

        # 4. init cropper
        match args.cropper:
            case "object":
                cropper = init_oo_cropper(scene_folder, sat_tif_path, args.window_size, shp_reader)
            case "slide":
                cropper = SlideWindowCropper(image_height, image_width, args.window_size, args.window_overlap_size,
                                             shp_reader)
            case _:
                raise ValueError

        # 6. start generate dataset
        for window, window_id in iter(cropper):

            feature = ogr.Feature(window_layer.GetLayerDefn())
            feature.SetField("id", window_id)
            window_geometry = window2geom(shp_reader.affine_transform, window)
            feature.SetGeometry(window_geometry)
            window_layer.CreateFeature(feature)


if __name__ == "__main__":
    main()
