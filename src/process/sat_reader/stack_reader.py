import copy
import json
import os
import shutil

import numpy as np
import rasterio
from einops import rearrange
from rasterio.windows import Window

from process.util import WindowArg
from .base_reader import SatBaseReader
from .util import read_data_with_up_sample


class StackReader(SatBaseReader):
    def __init__(self, folder_path: str, band_filenames: list[str], dst_resolution: int):
        self.folder_path = folder_path
        self.band_filenames = band_filenames
        self.dst_resolution = dst_resolution
        # read data and profile
        self.data, self.profile = self.read_data_and_profile()
        # use window_transform to update transform of sample
        self.window_transform = self.read_window_transform()

    def read_data_and_profile(self):
        data = None
        profile = None
        for band_filename in self.band_filenames:
            input_path = os.path.join(self.folder_path, band_filename)
            temp_data, temp_profile = read_data_with_up_sample(input_path, self.dst_resolution)
            if data is None and profile is None:
                data = [temp_data]
                profile = temp_profile
            else:
                data.append(temp_data)
        data = rearrange(data, "c 1 h w -> c h w")
        return data, profile

    def save(self, output_path: str):
        _, h, w = self.data.shape()
        window_arg = WindowArg(row_start=0, row_end=h, col_start=0, col_end=w)
        self.crop_data(window_arg, output_path)

    def read_window_transform(self):
        for band_filename in self.band_filenames:
            input_path = os.path.join(self.folder_path, band_filename)
            with rasterio.open(input_path) as src:
                if max(src.res) == self.dst_resolution:
                    return src.window_transform
        return 1

    def crop_data(self, window_arg: WindowArg, output_path: str, drop_nodata_percentage: float = None):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        profile = copy.copy(self.profile)
        height = window_arg.row_end - window_arg.row_start
        width = window_arg.col_end - window_arg.col_start
        window = Window.from_slices(slice(window_arg.row_start, window_arg.row_end),
                                    slice(window_arg.col_start, window_arg.col_end))
        dst_transform = self.window_transform(window)

        profile.update(count=len(self.band_filenames),
                       height=height,
                       width=width,
                       transform=dst_transform)
        dst_data = self.data[:, window_arg.row_start:window_arg.row_end, window_arg.col_start:window_arg.col_end]

        # remove nodata crop
        if drop_nodata_percentage is not None:
            nodata_percentage = np.count_nonzero(dst_data == 0) / dst_data.size
            if nodata_percentage >= drop_nodata_percentage:
                return

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(dst_data)

    def read_metadata(self, output_folder: str):
        metadata = {"bands": []}
        for input_filename in self.band_filenames:
            input_path = os.path.join(self.folder_path, input_filename)
            if not os.path.exists(input_path):
                continue
            metadata["bands"].append(os.path.splitext(input_filename)[0])

        metadata_path = os.path.join(output_folder, "metadata.json")
        with open(metadata_path, "w") as file:
            json.dump(metadata, file)

        copy_filenames = ["tileinfo_metadata.json", "granule_metadata.xml"]
        for filename in copy_filenames:
            input_path = os.path.join(self.folder_path, filename)
            output_path = os.path.join(output_folder, filename)
            shutil.copy2(input_path, output_path)
