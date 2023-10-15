import os.path
import multiprocessing
from preprocessing.crop import get_last_level_sub_folders, stack_bands_and_crop, write_metadata
from preprocessing.norm import read_folder_and_hist
import argparse


def preprocess1(input_root_folder: str, output_root_folder: str):
    for rel_path in get_last_level_sub_folders(input_root_folder):
        input_folder = os.path.join(input_root_folder, rel_path)
        output_folder = os.path.join(output_root_folder, os.path.basename(rel_path))
        stack_bands_and_crop(input_folder, output_folder, dst_resolution=10, window_size=512, overlap_size=64)
        write_metadata(input_folder, output_folder)

def test_preprocess1():
    input_root_folder = r"C:\Users\watercore\Desktop\1"
    output_root_folder = r"C:\Users\watercore\Desktop\2"
    preprocess1(input_root_folder, output_root_folder)

def preprocess2(input_folder: str, num_processes: int):
    folders = [os.path.join(input_folder, folder) for folder in os.listdir(input_folder)]

    pool = multiprocessing.Pool(processes=num_processes)
    pool.map(read_folder_and_hist, folders)
    pool.close()
    pool.join()

def test_preprocess2():
    input_folder = r"C:\Users\watercore\Desktop\2\S2A_43SCC_20221219_0_L2A"
    num_processes = 2
    preprocess2(input_folder, num_processes)

def preprocess1_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    parser.add_argument("-o", "--output_folder", type=str)
    args = parser.parse_args()
    preprocess1(args.input_folder, args.output_folder)

def preprocess2_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str)
    parser.add_argument("-p", "--num_processes", type=int)
    args = parser.parse_args()
    preprocess2(args.input_folder, args.num_processes)
