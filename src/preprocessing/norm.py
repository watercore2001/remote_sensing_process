import rasterio
import numpy as np
import os
import json
import glob


def read_file_and_hist(input_path: str):
    uint16_num = np.iinfo(np.uint16).max + 1
    result = []

    with rasterio.open(input_path) as src:
        for band in src.read():
            band_hist = [0] * uint16_num
            unique, counts = np.unique(band, return_counts=True)
            for idx, value in zip(unique, counts):
                band_hist[idx] += value
            result.append(band_hist)

    return np.array(result)


def read_folder_and_hist(input_folder: str):
    metadata_path = os.path.join(input_folder, "metadata.json")
    with open(metadata_path, 'r') as file:
        metadata = json.load(file)
        bands = metadata["bands"]

    uint16_num = np.iinfo(np.uint16).max + 1
    result = np.zeros(shape=(len(bands), uint16_num), dtype=int)

    for tif_file in glob.iglob(os.path.join(input_folder, "*.tif")):
        result = result + read_file_and_hist(tif_file)

    save_path = os.path.join(input_folder, "hist.npy")
    np.save(save_path, result)

def get_subdirectories(directory):
    sub_directories = []
    for item in os.listdir(directory):
        item_path = os.path.join(directory, item)
        if os.path.isdir(item_path):
            sub_directories.append(item_path)
    return sub_directories


def read_root_folder_and_hist(root_folder: str):
    all_bands = ["B02", "B03", "B04", "B05", "B06", "B07", "B08", "B8A", "B11", "B12"]
    uint16_num = np.iinfo(np.uint16).max + 1
    result = np.zeros(shape=(len(all_bands), uint16_num), dtype=int)
    for input_folder in get_subdirectories(root_folder):
        metadata_path = os.path.join(input_folder, "metadata.json")
        hist_path = os.path.join(input_folder, "hist.npy")
        with open(metadata_path, 'r') as file:
            metadata = json.load(file)
            bands = metadata["bands"]
        hist_data = np.load(hist_path)

        for i, band in enumerate(bands):
            result[all_bands.index(band)] += hist_data[i]

    save_path = os.path.join(root_folder, "hist.npy")
    np.save(save_path, result)























