import rasterio
import glob
import os
import numpy as np
from rasterio.windows import Window
import copy
import json
import shutil
from process.reader.util import read_data_with_up_sample
from process.util import WindowArg


class FolderReader:
    bands_filenames = ["B02.tif", "B03.tif", "B04.tif", "B05.tif", "B06.tif",
                       "B07.tif", "B08.tif", "B8A.tif", "B11.tif", "B12.tif"]

    def __init__(self, folder_path: str, dst_resolution: int):
        self.folder_path = folder_path
        self.dst_resolution = dst_resolution
        self.data, self.profile = self.read_data_and_profile()
        # use window_transform to update transform of sample
        self.window_transform = self.read_window_transform()

    def read_data_and_profile(self):
        data = None
        profile = None
        for input_path in glob.glob(os.path.join(self.folder_path, "*.tif")):
            temp_data, temp_profile = read_data_with_up_sample(input_path, self.dst_resolution)
            if data is None and profile is None:
                data = temp_data
                profile = temp_profile
            else:
                data = np.concatenate([data, temp_data], axis=0)
                profile["count"] += 1
        return data, profile

    def read_window_transform(self):
        input_path_for_src = glob.glob(os.path.join(self.folder_path, "*.tif"))[0]
        with rasterio.open(input_path_for_src) as src:
            window_transform = src.window_transform
        return window_transform

    def crop_data(self, window_arg: WindowArg, output_path: str):
        window = Window.from_slices(slice(window_arg.row_start, window_arg.row_end),
                                    slice(window_arg.col_start, window_arg.col_end))
        dst_transform = self.window_transform(window)
        profile = copy.copy(self.profile)
        height = window_arg.row_end - window_arg.row_start
        width = window_arg.col_end - window_arg.col_start
        profile.update(height=height,
                       width=width,
                       transform=dst_transform)
        dst_data = self.data[:, window_arg.row_start:window_arg.row_end, window_arg.col_start:window_arg.col_end]

        # remove nodata crop
        nodata_percentage = np.count_nonzero(dst_data == 0) / dst_data.size
        if nodata_percentage >= 0.5:
            return None

        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(dst_data)

    def read_metadata(self, output_folder: str):
        metadata = {"bands": []}
        for input_filename in self.bands_filenames:
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




