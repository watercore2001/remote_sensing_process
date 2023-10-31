from process.gt_reader.shp_reader import ShpReader
from .base_cropper import BaseCropper
from .util import read_geometry_list


class FileCropper(BaseCropper):
    def __init__(self, shp_file_path: str, shp_reader: ShpReader):
        super().__init__(shp_reader)
        self.window_geometry_list = read_geometry_list(shp_file_path)

    def __iter__(self):
        window_id = 0
        for window_geometry in self.window_geometry_list:
            window_id += 1
            window_arg = self.get_geom_window(window_geometry)
            yield window_arg, str(window_id)
