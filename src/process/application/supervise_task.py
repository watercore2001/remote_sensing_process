import argparse
import json
import os

import rasterio
from osgeo import ogr, osr

from process.application.util import init_oo_cropper, init_shp_reader
from process.cropper import SlideWindowCropper, FileCropper
from process.downloader import AwsSentinel2L2aDownloader, sentinel2_l2a_bands
from process.sat_reader import StackReader, UnstackReader
from process.util import window2geom


def parse_args():
    cropper_choices = ["object", "slide", "file"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Input label folder.")
    parser.add_argument("-o", "--output_folder", type=str, required=True)
    parser.add_argument("-b", "--bands", choices=sentinel2_l2a_bands, type=str, required=True, nargs="+",
                        help="These bands will be downloaded and subsequently stacked in the order of your input "
                             "if the -s flag is chosen.")
    parser.add_argument("-s", "--use_stack", action=argparse.BooleanOptionalAction, help="If stack or not.")
    parser.add_argument("-c", "--cropper", choices=cropper_choices, type=str, required=True,
                        help="There are three cropper.")
    parser.add_argument("--window_size", type=int,
                        help="This will be used if you choose object cropper and slide cropper.")
    parser.add_argument("--window_overlap_size", type=int,
                        help="This will be used if you choose slide cropper.")

    args = parser.parse_args()

    # check args
    if args.cropper == "slide" and args.window_overlap_size is None:
        parser.error("Argument --window_overlap_size requires when --cropper is slide.")

    os.makedirs(args.output_folder, exist_ok=True)
    os.makedirs(os.path.join(args.output_folder, "sat"), exist_ok=True)
    os.makedirs(os.path.join(args.output_folder, "sat"), exist_ok=True)
    return args


def main():
    args = parse_args()

    # 1. download aws sentinel-2 sat images
    band_filenames = [f"{band}.tif" for band in args.bands]
    aws_downloader = AwsSentinel2L2aDownloader()
    aws_downloader.download_all_files(input_folder=args.input_folder,
                                                       download_sub_folder="image",
                                                       bands=args.bands)

    # 2. iter scene folder
    for folder in os.listdir(args.input_folder):
        shapefile_folder = os.path.join(args.input_folder, folder)
        if not os.path.isdir(shapefile_folder):
            continue

        # todo
        os.makedirs(os.path.join(shapefile_folder, "output"), exist_ok=True)
        output_window_shp_path = os.path.join(shapefile_folder, "output", "window.shp")
        driver = ogr.GetDriverByName("ESRI Shapefile")
        if os.path.exists(output_window_shp_path):
            driver.DeleteDataSource(output_window_shp_path)

        ds = driver.CreateDataSource(output_window_shp_path)
        srs = osr.SpatialReference()
        sat_tif_path = os.path.join(shapefile_folder, "image/B02.tif")
        with rasterio.open(sat_tif_path) as src:
            epsg = src.crs.to_epsg()
            image_height = src.height
            image_width = src.width
        srs.ImportFromEPSG(epsg)
        window_layer = ds.CreateLayer("windows", srs, ogr.wkbPolygon)
        window_layer.CreateField(ogr.FieldDefn("id", ogr.OFTString))
        # todo

        # 3. init shp reader
        shp_reader = init_shp_reader(shapefile_folder, sat_tif_path)

        # 4. init cropper
        match args.cropper:
            case "object":
                cropper = init_oo_cropper(shapefile_folder, sat_tif_path, args.window_size, shp_reader)
            case "slide":
                cropper = SlideWindowCropper(image_height, image_width, args.window_size, args.window_overlap_size,
                                             shp_reader)
            case "file":
                shp_file_path = os.path.join(shapefile_folder, "window.shp")
                cropper = FileCropper(shp_file_path, shp_reader)
            case _:
                raise ValueError

        # 5. init sat reader
        sat_folder = os.path.join(shapefile_folder, "image")
        if args.use_stack:
            sat_reader = StackReader(sat_folder, band_filenames, dst_resolution=10)
        else:
            sat_reader = UnstackReader(sat_folder, band_filenames)

        # 6. start generate dataset
        os.makedirs(os.path.join(args.output_folder, "sat", folder), exist_ok=True)
        metadata_output_path = os.path.join(args.output_folder, "sat", folder, "metadata.json")
        with open(metadata_output_path, "w") as file:
            json.dump(obj={"bands": args.bands}, fp=file)

        sample_id = 0
        for window, window_id in iter(cropper):
            sample_id += 1
            shp_output_path = os.path.join(args.output_folder, "gt", folder, f"{sample_id}.tif")
            sat_output_path = os.path.join(args.output_folder, "sat", folder, f"{sample_id}.tif")

            shp_reader.crop_data(window, shp_output_path, window_id)
            sat_reader.crop_data(window, sat_output_path)

            # todo
            feature = ogr.Feature(window_layer.GetLayerDefn())
            feature.SetField("id", window_id)
            window_geometry = window2geom(shp_reader.affine_transform, window)
            feature.SetGeometry(window_geometry)
            window_layer.CreateFeature(feature)
            # todo


if __name__ == "__main__":
    main()
