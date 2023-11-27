import argparse
from process.downloader import AwsSentinel2L2aDownloader, sentinel2_l2a_bands
import os
import rasterio
from process.cropper import SlideWindowCropper
from process.sat_reader import StackReader, UnstackReader
import json

def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Input label folder.")
    parser.add_argument("-o", "--output_folder", type=str, required=True)
    parser.add_argument("-b", "--bands", choices=sentinel2_l2a_bands, type=str, required=True, nargs="+",
                        help="These bands will be downloaded and subsequently stacked in the order of your input "
                             "if the -s flag is chosen.")
    parser.add_argument("-s", "--use_stack", action=argparse.BooleanOptionalAction, help="If stack or not.")
    parser.add_argument("--window_size", type=int,
                        help="This will be used if you choose object cropper and slide cropper.")
    parser.add_argument("--window_overlap_size", type=int,
                        help="This will be used if you choose slide cropper.")

    args = parser.parse_args()
    return args


def main():
    args = parse_args()

    # 1. download aws sentinel-2 sat images
    band_filenames = [f"{band}.tif" for band in args.bands]
    aws_downloader = AwsSentinel2L2aDownloader()
    aws_downloader.download_all_files(input_folder=args.input_folder,
                                      download_sub_folder=None,
                                      bands=args.bands)

    # 2. iter scene folder
    for folder in os.listdir(args.input_folder):
        scene_folder = os.path.join(args.input_folder, folder)
        if not os.path.isdir(scene_folder):
            continue
        sat_tif_path = os.path.join(scene_folder, "B04.tif")
        with rasterio.open(sat_tif_path) as src:
            image_height = src.height
            image_width = src.width

        cropper = SlideWindowCropper(image_height, image_width, args.window_size, args.window_overlap_size,
                                     shp_reader=None)

        if args.use_stack:
            sat_reader = StackReader(scene_folder, band_filenames, dst_resolution=10)
        else:
            sat_reader = UnstackReader(scene_folder, band_filenames)

        os.makedirs(os.path.join(args.output_folder, "sat", folder), exist_ok=True)
        metadata_output_path = os.path.join(args.output_folder, "sat", folder, "metadata.json")
        with open(metadata_output_path, "w") as file:
            json.dump(obj={"bands": args.bands}, fp=file)

        for window, window_id in iter(cropper):
            sat_output_path = os.path.join(args.output_folder, "sat", folder, f"{window_id}.tif")
            sat_reader.crop_data(window, sat_output_path)


if __name__ == "__main__":
    main()