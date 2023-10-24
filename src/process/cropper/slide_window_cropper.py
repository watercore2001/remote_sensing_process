import os
import shutil

from process.util import WindowArg


class SlideWindowCropper:
    def __init__(self, image_height: int, image_width: int, window_size: int, overlap_size: int):
        self.image_height = image_height
        self.image_width = image_width
        self.window_size = window_size
        self.overlap_size = overlap_size

    def __iter__(self):
        real_window_size = self.window_size - self.overlap_size
        row_count = (self.image_height - self.window_size) // real_window_size + 1
        col_count = (self.image_width - self.window_size) // real_window_size + 1

        for row_id in range(row_count):
            row_start = row_id * real_window_size
            row_end = row_start + self.window_size
            for col_id in range(col_count):
                col_start = col_id * real_window_size
                col_end = col_start + self.window_size

                output_filename = f"{row_id+1:02}{col_id+1:02}.tif"
                yield WindowArg(row_start, row_end, col_start, col_end), output_filename



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












