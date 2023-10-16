import json
import rasterio
from rasterio.windows import Window
from rasterio.enums import Resampling
import numpy as np
import shutil
import os

def read_data_with_up_sample(input_path: str, dst_resolution: int):
    with rasterio.open(input_path) as src:
        src_resolution = max(src.res)
        if src_resolution == dst_resolution:
            return src.read(), src.profile
        else:
            upscale_factor = int(src_resolution / dst_resolution)
            dst_data = src.read(
                out_shape=(
                    src.count,
                    src.height * upscale_factor,
                    src.width * upscale_factor
                ),
                resampling=Resampling.bilinear)
            dst_transform = src.transform * src.transform.scale((1 / upscale_factor), (1 / upscale_factor))
            profile = src.profile
            profile.update(transform=dst_transform,
                           width=dst_data.shape[1],
                           height=dst_data.shape[2],
                           blockxsize=profile["blockxsize"]*upscale_factor,
                           blockysize=profile["blockysize"]*upscale_factor)
            return dst_data, profile


def up_sample_and_save_as_tif(input_path: str, output_path: str, dst_resolution:int):
    data, profile = read_data_with_up_sample(input_path, dst_resolution)

    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(data)


def up_sample_and_sqrt_and_save_as_jpeg(input_path: str, output_path: str, dst_resolution:int):
    data, profile = read_data_with_up_sample(input_path, dst_resolution)

    # Apply square root operation
    sqrt_data = np.sqrt(data).astype(np.uint8)

    profile.update(driver="JPEG", dtype=sqrt_data.dtype)

    # Save as an 8-bit JPEG
    with rasterio.open(output_path, 'w', **profile) as dst:
        dst.write(sqrt_data)


def stack_bands_and_crop(input_folder: str, output_folder: str,  dst_resolution: int, window_size: int, overlap_size: int):
    input_filenames = ["B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif",
                       "B07.tif", "B08.tif", "B8A.tif", "B11.tif", "B12.tif"]

    # read data and profile
    data = None
    profile = None
    for input_filename in input_filenames:
        input_path = os.path.join(input_folder, input_filename)
        if not os.path.exists(input_path):
            continue
        temp_data, temp_profile = read_data_with_up_sample(input_path, dst_resolution=dst_resolution)
        if data is None and profile is None:
            data = temp_data
            profile = temp_profile
        else:
            data = np.concatenate([data, temp_data], axis=0)
            profile["count"] += 1

    input_path_for_src = os.path.join(input_folder, input_filenames[0])
    with rasterio.open(input_path_for_src) as src:
        window_transform = src.window_transform

    real_window_size = window_size - overlap_size
    row_count = (profile["height"] - window_size) // real_window_size + 1
    col_count = (profile["width"] - window_size) // real_window_size + 1
    for row_id in range(row_count):
        row_start = row_id * real_window_size
        row_end = row_start + window_size
        for col_id in range(col_count):
            col_start = col_id * real_window_size
            col_end = col_start + window_size

            window = Window.from_slices(slice(row_start, row_end), slice(col_start, col_end))
            dst_transform = window_transform(window)
            profile.update(width=window_size,
                           height=window_size,
                           transform=dst_transform)
            dst_data = data[:, row_start:row_end, col_start:col_end]

            # remove nodata crop
            nodata_percentage = np.count_nonzero(dst_data == 0) / dst_data.size
            if nodata_percentage >= 0.5:
                continue

            output_filename = f"{row_id+1:02}{col_id+1:02}.tif"
            output_path = os.path.join(output_folder, output_filename)

            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(dst_data)


def write_metadata(input_folder: str, output_folder: str):
    bands_filenames = ["B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif",
                       "B07.tif", "B08.tif", "B8A.tif", "B11.tif", "B12.tif"]
    metadata = {"bands": []}
    for input_filename in bands_filenames:
        input_path = os.path.join(input_folder, input_filename)
        if not os.path.exists(input_path):
            continue
        metadata["bands"].append(os.path.splitext(input_filename)[0])

    metadata_path = os.path.join(output_folder, "metadata.json")
    with open(metadata_path, "w") as file:
        json.dump(metadata, file)

    copy_filenames = ["tileinfo_metadata.json", "granule_metadata.xml"]
    for filename in copy_filenames:
        input_path = os.path.join(input_folder, filename)
        output_path = os.path.join(output_folder, filename)
        shutil.copy2(input_path, output_path)


def preprocess1_wrapper(args: tuple):
    input_folder, output_folder = args
    if os.path.exists(output_folder):
        return
    try:
        os.makedirs(output_folder, exist_ok=True)
        stack_bands_and_crop(input_folder, output_folder, dst_resolution=10, window_size=512, overlap_size=64)
        write_metadata(input_folder, output_folder)
    except:
        shutil.rmtree(output_folder)


def get_last_level_sub_folders(root_folder: str):
    rel_paths = []
    for dir_path, dirs, files in os.walk(root_folder):
        if len(dirs) == 0:
            rel_paths.append(dir_path)
    return rel_paths









