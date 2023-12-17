import argparse
import json
import os
import shutil

import rasterio
from tqdm.contrib.concurrent import process_map
import random
from process.application.util import get_last_level_sub_folders
from process.application.util import init_oo_cropper, init_shp_reader
from process.cropper import SlideWindowCropper, FileCropper
from process.downloader import AwsSentinel2L2aDownloader, sentinel2_l2a_bands
from process.sat_reader import StackReader, UnstackReader, LuccReader
from process.util import window2geom
import dataclasses

def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument("-i1", "--sat_folder", type=str, required=True, help="Input sat folder.")
    parser.add_argument("-i2", "--lucc_folder", type=str, required=True, help="Input lucc folder.")
    parser.add_argument("-o", "--output_folder", type=str, required=True)
    parser.add_argument("-p", "--train_val_test_percent", type=int, required=True, nargs="+",
                        help="The percentage value attributed to train/val/test dataset, "
                             "which should collectively amount to 100.")
    parser.add_argument("-b", "--bands", choices=sentinel2_l2a_bands, type=str, required=True, nargs="+",
                        help="These bands will be downloaded and subsequently stacked in the order of your input "
                             "if the -s flag is chosen.")
    parser.add_argument("-s", "--use_stack", action=argparse.BooleanOptionalAction,
                        help="If stack or not.")
    parser.add_argument("-d", "--delete_input", action=argparse.BooleanOptionalAction,
                        help="If delete input sat image.")
    parser.add_argument("--window_size", type=int, required=True,
                        help="This will be used if you choose object cropper and slide cropper.")
    parser.add_argument("--window_overlap_size", type=int, required=True,
                        help="This will be used if you choose slide cropper.")

    args = parser.parse_args()

    assert sum(args.train_val_test_percent) == 100

    return args


@dataclasses.dataclass
class RunArg:
    scene_folder: str
    lucc_folder: str
    output_folder: str
    window_size: int
    window_overlap_size: int
    bands: list[str]
    use_stack: bool
    train_val_test_percent: list[int]
    delete_input: bool


def run(args: RunArg):
    try:
        scene_id = os.path.basename(args.scene_folder)

        sat_tif_path = os.path.join(args.scene_folder, "B02.tif")
        with rasterio.open(sat_tif_path) as src:
            image_height = src.height
            image_width = src.width

        cropper = SlideWindowCropper(image_height, image_width, args.window_size, args.window_overlap_size, shp_reader=None)

        band_filenames = [f"{band}.tif" for band in args.bands]
        if args.use_stack:
            sat_reader = StackReader(args.scene_folder, band_filenames, dst_resolution=10)
        else:
            sat_reader = UnstackReader(args.scene_folder, band_filenames)
        lucc_reader = LuccReader(args.lucc_folder, dst_resolution=10)

        os.makedirs(args.output_folder, exist_ok=True)
        sub_folder_names = ["train", "val", "test"]
        metadata_output_path = os.path.join(args.output_folder, "metadata.json")
        with open(metadata_output_path, "w") as file:
            json.dump(obj={"bands": args.bands}, fp=file)

        for window, window_id in iter(cropper):
            sub_folder_name = random.choices(sub_folder_names, weights=args.train_val_test_percent)[0]
            sat_output_path = os.path.join(args.output_folder, sub_folder_name, "sat", scene_id, f"{window_id}.tif")
            gt_output_path = os.path.join(args.output_folder, sub_folder_name, "gt", scene_id, f"{window_id}.tif")

            sat_reader.crop_data(window, sat_output_path)
            lucc_reader.crop_data(window, gt_output_path)

        metadata_filenames = ["granule_metadata.xml", "tileinfo_metadata.json"]
        for sub_folder_name in sub_folder_names:
            for filename in metadata_filenames:
                src_path = os.path.join(args.scene_folder, filename)
                dst_path = os.path.join(args.output_folder, sub_folder_name, "sat", scene_id, filename)
                shutil.copy(src_path, dst_path)

    except:
        return 1

    finally:
        if args.delete_input:
            shutil.rmtree(args.scene_folder)
            shutil.rmtree(args.lucc_folder)

def main():
    args = parse_args()

    scene_folders = get_last_level_sub_folders(args.sat_folder)
    run_args = []

    for scene_folder in scene_folders:
        lucc_folder = scene_folder.replace(args.sat_folder, args.lucc_folder)
        run_arg = RunArg(scene_folder=scene_folder, lucc_folder=lucc_folder, output_folder=args.output_folder,
                         window_size=args.window_size, window_overlap_size=args.window_overlap_size,
                         bands=args.bands, use_stack=args.use_stack, delete_input=args.delete_input,
                         train_val_test_percent=args.train_val_test_percent)
        if run(run_arg)==1:
            print(f"{os.path.basename(scene_folder)} fail")

    #process_map(run, run_args)


if __name__ == "__main__":
    main()
