import os
import rasterio



class ShpReader:
    def __init__(self, label_shp_path_list: list[str], value_list: list[int],
                 false_shp_path: str = None, not_sure_shp_path: str = None):
        assert len(label_shp_path_list) == len(value_list), "shp num is not corresponding to value num."
        self.folder = os.path.dirname(label_shp_path_list[0])

    def rasterize(self):
