import argparse
import os

import rasterio
import random
from process.application.util import init_oo_cropper, init_shp_reader, img_folder_name
from process.cropper import SlideWindowCropper, FileCropper
from process.downloader import AwsSentinel2L2aDownloader, sentinel2_l2a_bands
from process.sat_reader import StackReader, UnstackReader

def parse_args():
    cropper_choices = ["object", "slide", "file"]

    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Input folder.")
    parser.add_argument("-o", "--output_folder", type=str, required=True)
    parser.add_argument("-p", "--train_val_test_percent", type=int, required=True, nargs="+",
                        help="The percentage value attributed to train val test dataset, sum to 100.")
    parser.add_argument("-b", "--bands", choices=sentinel2_l2a_bands, type=str, required=True, nargs="+",
                        help="These bands will be downloaded and subsequently stacked in the order of your input "
                             "if the -s flag is chosen.")
    parser.add_argument("-a", "--align_band", choices=sentinel2_l2a_bands, type=str, required=True)
    parser.add_argument("-s", "--use_stack", action=argparse.BooleanOptionalAction,
                        help="If stack or not.")
    parser.add_argument("-c", "--cropper", choices=cropper_choices, type=str, required=True,
                        help="There are three cropper to choose.")
    parser.add_argument("--window_size", type=int,
                        help="This will be used if you choose object cropper and slide cropper.")
    parser.add_argument("--window_overlap_size", type=int,
                        help="This will be used if you choose slide cropper.")

    args = parser.parse_args()

    # check args
    if args.cropper == "slide" and args.window_overlap_size is None:
        parser.error("Argument --window_overlap_size requires when --cropper is slide.")

    if args.cropper in ["object", "slide"] and args.window_size is None:
        parser.error("Argument --window_size requires.")

    if sum(args.train_val_test_percent) != 100:
        parser.error("Argument -p percentage should sum to 100.")

    return args


def main():
    args = parse_args()

    # 1. download aws sentinel-2 sat images
    download_bands = list(set(args.bands+[args.align_band]))
    band_filenames = [f"{band}.tif" for band in args.bands]
    aws_downloader = AwsSentinel2L2aDownloader()
    aws_downloader.download_all_files(input_folder=args.input_folder,
                                      download_sub_folder=img_folder_name,
                                      bands=download_bands)

    band_composition = "".join(args.bands)

    # 2. iter scene folder
    for scene_id in os.listdir(args.input_folder):
        scene_folder = os.path.join(args.input_folder, scene_id)
        if not os.path.isdir(scene_folder):
            continue

        sat_tif_path = os.path.join(scene_folder, img_folder_name, f"{args.align_band}.tif")
        with rasterio.open(sat_tif_path) as src:
            image_height = src.height
            image_width = src.width

        # 3. init shp reader
        shp_reader = init_shp_reader(scene_folder, sat_tif_path)

        # 4. init cropper
        match args.cropper:
            case "object":
                cropper = init_oo_cropper(scene_folder, sat_tif_path, args.window_size, shp_reader)
            case "slide":
                cropper = SlideWindowCropper(image_height, image_width, args.window_size, args.window_overlap_size,
                                             shp_reader)
            case "file":
                shp_file_path = os.path.join(scene_folder, "window", "window.shp")
                cropper = FileCropper(shp_file_path, shp_reader)
            case _:
                raise ValueError

        # 5. init sat reader
        sat_folder = os.path.join(scene_folder, img_folder_name)
        if args.use_stack:
            sat_reader = StackReader(sat_folder, band_filenames, dst_resolution=10)
        else:
            sat_reader = UnstackReader(sat_folder, band_filenames)

        # 6. start generate dataset
        os.makedirs(args.output_folder, exist_ok=True)
        sub_folder_names = ["train", "val", "test"]

        for window, window_id in iter(cropper):

            sub_folder_name = random.choices(sub_folder_names, weights=args.train_val_test_percent)[0]

            filename = f"{scene_id}_{window}_{band_composition}.tif"

            shp_output_path = os.path.join(args.output_folder, sub_folder_name, "gt", scene_id, filename)
            sat_output_path = os.path.join(args.output_folder, sub_folder_name, "image", scene_id, filename)

            shp_reader.crop_data(window, shp_output_path, window_id)
            sat_reader.crop_data(window, str(sat_output_path))



if __name__ == "__main__":
    main()
