import os.path
from preprocessing.crop import get_last_level_sub_folders, preprocess1_wrapper
from preprocessing.norm import read_folder_and_hist, read_root_folder_and_hist, cal_min_and_max
import argparse
from tqdm.contrib.concurrent import process_map


def preprocess1(input_root_folder: str, output_root_folder: str):
    rel_paths = get_last_level_sub_folders(input_root_folder)
    args = [(os.path.join(input_root_folder, rel_path), os.path.join(output_root_folder, os.path.basename(rel_path)))
            for rel_path in rel_paths]

    process_map(preprocess1_wrapper, args)


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

def preprocess3_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    args = parser.parse_args()
    save_path = read_root_folder_and_hist(args.input_folder)
    cal_min_and_max(save_path)
