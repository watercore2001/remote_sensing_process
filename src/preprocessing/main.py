import os.path
from preprocessing.util import get_last_level_sub_folders, stack_bands_and_crop, copy_metadata
import argparse


def preprocess1(input_root_folder: str, output_root_folder: str):
    for rel_path in get_last_level_sub_folders(input_root_folder):
        input_folder = os.path.join(input_root_folder, rel_path)
        output_folder = os.path.join(output_root_folder, os.path.basename(rel_path))
        stack_bands_and_crop(input_folder, output_folder, dst_resolution=10, window_size=512, overlap_size=64)
        copy_metadata(input_folder, output_folder)


def test_preprocess1():
    input_root_folder = r"C:\Users\watercore\Desktop\1"
    output_root_folder = r"C:\Users\watercore\Desktop\2"
    preprocess1(input_root_folder, output_root_folder)


def preprocess1_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    parser.add_argument("-o", "--output_folder", type=str)
    args = parser.parse_args()
    preprocess1(args.input_folder, args.output_folder)
