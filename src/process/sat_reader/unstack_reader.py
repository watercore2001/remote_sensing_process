import copy
import os

import numpy as np
import rasterio
from rasterio.windows import Window

from process.util import WindowArg
from .base_reader import SatReader


class UnstackReader(SatReader):

    def __init__(self, folder_path: str, band_filenames: list[str]):
        self.folder_path = folder_path
        self.band_filenames = band_filenames
        self.datas, self.profiles, self.window_transforms, self.resolutions \
            = self.read_data_and_profile_and_window_transform()
        self.min_resolution = min(self.resolutions)

    def read_data_and_profile_and_window_transform(self):
        datas = []
        profiles = []
        window_transforms = []
        resolutions = []
        for filename in self.band_filenames:
            input_path = os.path.join(self.folder_path, filename)
            with rasterio.open(input_path) as src:
                datas.append(src.read())
                profiles.append(src.profile)
                window_transforms.append(src.window_transform)
                resolutions.append(min(src.res))
        return datas, profiles, window_transforms, resolutions

    @staticmethod
    def get_window_arg_in_factor(window_arg: WindowArg, factor: int):
        row_start = window_arg.row_start // factor
        row_end = row_start + (window_arg.row_end - window_arg.row_start) // factor

        col_start = window_arg.col_start // factor
        col_end = col_start + (window_arg.col_end - window_arg.col_start) // factor

        return WindowArg(row_start, row_end, col_start, col_end)

    def crop_data(self, window_arg_in_min_resolution: WindowArg, output_path: str):
        output_folder = os.path.splitext(output_path)[0]
        os.makedirs(output_folder, exist_ok=True)

        for i, filename in enumerate(self.band_filenames):
            band_output_path = os.path.join(output_folder, filename)
            factor = self.resolutions[i] / self.min_resolution
            window_arg = self.get_window_arg_in_factor(window_arg_in_min_resolution, factor)
            window = Window.from_slices(slice(window_arg.row_start, window_arg.row_end),
                                        slice(window_arg.col_start, window_arg.col_end))
            dst_transform = self.window_transforms[i](window)
            profile = copy.copy(self.profiles[i])
            height = window_arg.row_end - window_arg.row_start
            width = window_arg.col_end - window_arg.col_start
            profile.update(height=height,
                           width=width,
                           transform=dst_transform)
            dst_data = self.datas[i][:, window_arg.row_start:window_arg.row_end,
                       window_arg.col_start:window_arg.col_end]

            # remove nodata crop
            nodata_percentage = np.count_nonzero(dst_data == 0) / dst_data.size
            if nodata_percentage >= 0.5:
                return

            with rasterio.open(band_output_path, "w", **profile) as dst:
                dst.write(dst_data)
