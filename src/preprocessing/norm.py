import rasterio
import numpy as np
import os
import json
import glob

def read_file_and_hist(input_path:str):
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


def test_read_file_and_hist():
    input_path = r"C:\Users\watercore\Desktop\2\S2A_43SCC_20221219_0_L2A\0101.tif"
    result = read_file_and_hist(input_path)


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

