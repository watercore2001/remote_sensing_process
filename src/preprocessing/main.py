import os.path
from preprocessing.crop import get_last_level_sub_folders, stack_bands_and_crop, write_metadata
from preprocessing.norm import read_folder_and_hist
import argparse
import shutil
from tqdm.contrib.concurrent import process_map


def preprocess1(input_root_folder: str, output_root_folder: str):
    def task(_rel_path: str):
        _input_folder = os.path.join(input_root_folder, _rel_path)
        _output_folder = os.path.join(output_root_folder, os.path.basename(_rel_path))
        if os.path.exists(_output_folder):
            return
        try:
            os.makedirs(_output_folder, exist_ok=True)
            stack_bands_and_crop(_input_folder, _output_folder, dst_resolution=10, window_size=512, overlap_size=64)
            write_metadata(_input_folder, _output_folder)
        except:
            shutil.rmtree(_output_folder)

    rel_paths = get_last_level_sub_folders(input_root_folder)
    process_map(task, rel_paths)


def preprocess2(input_folder: str):
    folders = [os.path.join(input_folder, folder) for folder in os.listdir(input_folder)]
    process_map(read_folder_and_hist, folders)


def preprocess1_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    parser.add_argument("-o", "--output_folder", type=str)
    args = parser.parse_args()
    preprocess1(args.input_folder, args.output_folder)


def preprocess2_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    args = parser.parse_args()
    preprocess2(args.input_folder)
