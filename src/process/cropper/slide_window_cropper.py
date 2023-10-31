from process.gt_reader.shp_reader import ShpReader
from process.util import WindowArg
from .cropper import Cropper


class SlideWindowCropper(Cropper):
    def __init__(self, image_height: int, image_width: int, window_size: int, overlap_size: int, shp_reader: ShpReader):
        self.image_height = image_height
        self.image_width = image_width
        self.window_size = window_size
        self.overlap_size = overlap_size

        self.shp_reader = shp_reader

    def get_window_and_check_bound(self, row_start: int, col_start: int):
        if (row_start + self.window_size) > self.image_height:
            row_start = self.image_height - self.window_size
        if (col_start + self.window_size) > self.image_width:
            col_start = self.image_width - self.window_size
        if row_start < 0:
            row_start = 0
        if col_start < 0:
            col_start = 0

        return WindowArg(row_start=row_start, row_end=row_start+self.window_size,
                         col_start=col_start, col_end=col_start+self.window_size)

    def __iter__(self):
        real_window_size = self.window_size - self.overlap_size
        row_count = (self.image_height - self.window_size) // real_window_size + 2
        col_count = (self.image_width - self.window_size) // real_window_size + 2

        for row_id in range(row_count):
            row_start = row_id * real_window_size
            for col_id in range(col_count):
                col_start = col_id * real_window_size
                window_args = self.get_window_and_check_bound(row_start, col_start)
                score = self.shp_reader.get_window_score(window_args)
                if score is None:
                    continue
                window_id = f"{row_id+1:02}{col_id+1:02}"
                yield window_args, window_id












