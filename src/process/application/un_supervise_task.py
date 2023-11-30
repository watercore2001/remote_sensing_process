import argparse
from process.downloader import sentinel2_l2a_bands
import os
import rasterio
import dataclasses
from process.cropper import SlideWindowCropper
from process.sat_reader import StackReader, UnstackReader
from process.application.util import get_last_level_sub_folders
import json
import shutil
from tqdm.contrib.concurrent import process_map

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


@dataclasses.dataclass
class RunArg:
    scene_folder: str
    output_folder: str
    window_size: int
    window_overlap_size: int
    bands: list[str]
    use_stack: bool


def run(args: RunArg):
    try:
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

        os.makedirs(args.output_folder, exist_ok=True)
        metadata_output_path = os.path.join(args.output_folder, "metadata.json")
        with open(metadata_output_path, "w") as file:
            json.dump(obj={"bands": args.bands}, fp=file)

        for window, window_id in iter(cropper):
            sat_output_path = os.path.join(args.output_folder, f"{window_id}.tif")
            sat_reader.crop_data(window, sat_output_path)

        metadata_filename = ["granule_metadata.xml", "tileinfo_metadata.json"]
        for filename in metadata_filename:
            src_path = os.path.join(args.scene_folder, filename)
            dst_path = os.path.join(args.output_folder, filename)
            shutil.copy(src_path, dst_path)

    except:
        return 1

    finally:
        shutil.rmtree(args.scene_folder)



def main():
    args = parse_args()

    scene_folders = get_last_level_sub_folders(args.input_folder)
    run_args = []

    for scene_folder in scene_folders:
        output_folder = os.path.join(args.output_folder, os.path.basename(scene_folder))
        run_arg = RunArg(scene_folder=scene_folder, output_folder=output_folder,
                         window_size=args.window_size, window_overlap_size=args.window_overlap_size,
                         bands=args.bands, use_stack=args.use_stack)
        run_args.append(run_arg)

    process_map(run, run_args)


if __name__ == "__main__":
    main()