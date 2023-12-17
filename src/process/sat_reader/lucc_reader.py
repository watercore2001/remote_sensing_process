import copy
import json
import os
import shutil

import numpy as np
import rasterio
from rasterio.windows import Window

from process.util import WindowArg
from .base_reader import SatBaseReader
from .util import read_data_with_up_sample


class LuccReader(SatBaseReader):
    lucc_filename = "lulc.tif"
    lucc_values = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 95, 100]
    def __init__(self, folder_path: str, dst_resolution: int):

        self.folder_path = folder_path
        self.dst_resolution = dst_resolution
        # read data and profile
        self.data, self.profile = self.read_data_and_profile()
        # use window_transform to update transform of sample
        self.window_transform = self.read_window_transform()

    def read_data_and_profile(self):
        input_path = os.path.join(self.folder_path, self.lucc_filename)
        data, profile = read_data_with_up_sample(input_path, self.dst_resolution)

        for new_value, old_value in enumerate(self.lucc_values):
            data[data == old_value] = new_value

        return data, profile

    def read_window_transform(self):
        input_path = os.path.join(self.folder_path, self.lucc_filename)
        with rasterio.open(input_path) as src:
            if max(src.res) == self.dst_resolution:
                return src.window_transform
        return 1

    def crop_data(self, window_arg: WindowArg, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        profile = copy.copy(self.profile)
        height = window_arg.row_end - window_arg.row_start
        width = window_arg.col_end - window_arg.col_start
        window = Window.from_slices(slice(window_arg.row_start, window_arg.row_end),
                                    slice(window_arg.col_start, window_arg.col_end))
        dst_transform = self.window_transform(window)

        profile.update(count=1,
                       height=height,
                       width=width,
                       transform=dst_transform)
        dst_data = self.data[:, window_arg.row_start:window_arg.row_end, window_arg.col_start:window_arg.col_end]

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(dst_data)

