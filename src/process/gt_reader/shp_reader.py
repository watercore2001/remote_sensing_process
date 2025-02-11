import copy
import os

import numpy as np
import rasterio
from einops import reduce
from osgeo import ogr
from rasterio import features
from rasterio.windows import Window

from process.util import WindowArg, window2geom
from .util import rasterize_shapefiles


class ShpReader:
    negative_value = 99
    cropped_value = 254
    unsure_value = 255

    def __init__(self, sat_tif_path: str, rasterize_output_folder: str,
                 label_path_list_in_one_scene: list[str] = None, burn_values: list[int] = None,
                 false_path_in_one_scene: str = None, unsure_file_path_in_one_scene: str = None):

        # rasterize shapefiles for output
        if label_path_list_in_one_scene is None:
            label_path_list_in_one_scene = []
            burn_values = []
            self.data, self.profile = self.read_zero_data_and_profile(sat_tif_path)
        else:
            rasterize_output_path = os.path.join(rasterize_output_folder, "rasterize.tif")
            rasterize_shapefiles(label_path_list_in_one_scene, burn_values, sat_tif_path, rasterize_output_path)
            self.data, self.profile = self.read_data_and_profile(rasterize_output_path)

        # rasterize shapefiles for score window
        if false_path_in_one_scene is not None:
            label_path_list_in_one_scene.append(false_path_in_one_scene)
            burn_values.append(self.negative_value)
        if unsure_file_path_in_one_scene is not None:
            label_path_list_in_one_scene.append(unsure_file_path_in_one_scene)
            burn_values.append(self.unsure_value)
        rasterize_output_path_for_score = os.path.join(rasterize_output_folder, "rasterize_backup.tif")
        rasterize_shapefiles(label_path_list_in_one_scene, burn_values, sat_tif_path, rasterize_output_path_for_score)
        self.data_for_score = self.read_data_for_score(rasterize_output_path_for_score, sat_tif_path)

        # read window transform and affine transform
        with rasterio.open(sat_tif_path) as src:
            self.epsg = src.crs.to_epsg()
            self.window_transform = src.window_transform
            self.affine_transform = rasterio.transform.AffineTransformer(src.transform)

    def read_zero_data_and_profile(self, sat_tif_path: str):
        with rasterio.open(sat_tif_path) as src:
            data = np.zeros(shape=(1, src.height, src.width), dtype=np.uint8)
            profile = src.profile
        return data, profile

    def read_data_and_profile(self, rasterize_path: str):
        with rasterio.open(rasterize_path) as src:
            data = src.read()
            profile = src.profile

        data = reduce(data, "c h w -> 1 h w", "max")
        return data, profile

    def read_data_for_score(self, rasterize_path: str, sat_tif_path: str):
        with rasterio.open(rasterize_path) as src:
            data = src.read()
            data = reduce(data, "c h w -> 1 h w", "max")
        # update mask area
        with rasterio.open(sat_tif_path) as src:
            sat_shape = src.shape
            sat_mask = np.ones(sat_shape, np.uint8) * 255
            # nodata area
            sat_mask[src.read(1) == 0] = 0
            sat_mask = features.sieve(sat_mask, size=500)
        # nodata area is unsure
        data[:, sat_mask == 0] = self.unsure_value
        return data

    def get_window_score(self, window_arg: WindowArg, current_geometry: ogr.Geometry = None):
        data = self.data_for_score[:, window_arg.row_start:window_arg.row_end, window_arg.col_start:window_arg.col_end]
        # 1.if contains unsure value, drop window
        if np.isin(self.unsure_value, data):
            return None
        window_geom = window2geom(self.affine_transform, window_arg)
        # 2.if not contain the current geometry, drop window
        if current_geometry is not None and not current_geometry.Intersect(window_geom):
            return None
        # 3.if not contain any un cropped pixel, drop window
        score = np.sum(np.logical_and(0 < data, data < 100))
        if score == 0:
            return None
        else:
            return score

    def update_cropped_area(self, window_arg: WindowArg):
        # update
        self.data_for_score[:, window_arg.row_start:window_arg.row_end,
        window_arg.col_start:window_arg.col_end] = self.cropped_value

    def crop_data(self, window_arg: WindowArg, output_path: str, window_id: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        window = Window.from_slices(slice(window_arg.row_start, window_arg.row_end),
                                    slice(window_arg.col_start, window_arg.col_end))
        dst_transform = self.window_transform(window)
        profile = copy.copy(self.profile)
        height = window_arg.row_end - window_arg.row_start
        width = window_arg.col_end - window_arg.col_start
        profile.update(count=1,
                       height=height,
                       width=width,
                       dtype=rasterio.uint8,
                       transform=dst_transform,
                       )
        dst_data = self.data[:, window_arg.row_start:window_arg.row_end, window_arg.col_start:window_arg.col_end]
        with rasterio.open(output_path, "w", **profile) as dst:
            dst.write(dst_data)

        self.update_cropped_area(window_arg)
