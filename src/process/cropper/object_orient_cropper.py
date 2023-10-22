from process.cropper.util import window2geom, WindowArg, AffineTransformer
import numpy as np
import rasterio

def next_window(
        geom_envelop: tuple[int, int, int, int],
        window_shape: tuple[int, int],
        satellite_shape: tuple[int, int],
        gt_path: str,
        transformer,
        geometry_list,
        geometry_index,
) -> tuple[tuple[int, int], tuple[int, int]]:
    """
    给定要素的范围, 不断地产生窗口
    Args:
        gt_path: 备用 gt 图层
        window_shape: 窗口大小 (224, 224)
        satellite_shape: 卫星图大小, 窗口不能超过这个范围 (10980, 10980)
        geom_envelop: 要素 mbr (row_start, stop_row, col_start, stop_col)

    Returns:
        切割窗口 ((row_start, stop_row), (col_start, stop_col))
    """

    row_length = geom_envelop[1] - geom_envelop[0]
    col_length = geom_envelop[3] - geom_envelop[2]

    with rasterio.open(gt_path, "r+") as gt:
        if row_length <= window_shape[0] and col_length < window_shape[1]:

            best_window = ((0, 0), (0, 0))
            best_sum = -100
            flag = False

            for row_start, col_start in starts:
                window = get_window_and_check_bound(satellite_shape, window_shape, row_start, col_start)
                image = gt.read(1, window=window)
                # 如果包含不确定的像元就跳过
                if np.sum(image == NOT_SURE_VALUE) > 0:
                    continue
                # 计算当前窗口评分
                current_sum = np.sum((0 < image) & (image < 100)) - np.sum(image == CROPPED_VALUE) * 0.00001
                if current_sum > best_sum:
                    flag = True
                    best_sum = current_sum
                    best_window = window
            if flag:
                # 将当前窗口设置为已采样
                update_image = np.ones(window_shape, dtype=rasterio.ubyte) * CROPPED_VALUE
                gt.write(update_image, window=best_window, indexes=1)
                yield best_window
            else:
                return
        else:
            row_buffer = window_shape[0] // 8
            col_buffer = window_shape[1] // 8
            for row_start in next_line(geom_envelop[0] - row_buffer, geom_envelop[1] + row_buffer, window_shape[0]):
                for col_start in next_line(geom_envelop[2] - col_buffer, geom_envelop[3] + col_buffer, window_shape[1]):
                    window = get_window_and_check_bound(satellite_shape, window_shape, row_start, col_start)
                    image = gt.read(1, window=window)
                    window_geometry = window2geom(transformer, window)
                    # 如果包含不确定的像元或者不包含当前要素或者不包含未采样的像元 就跳过
                    if (
                            np.sum(image == NOT_SURE_VALUE) > 0
                            or not window_geometry.Intersect(geometry_list[geometry_index])
                            or np.sum((0 < image) & (image < 100)) == 0
                    ):
                        continue
                    # 将当前窗口设置为已采样
                    update_image = np.ones(window_shape, dtype=rasterio.ubyte) * CROPPED_VALUE
                    gt.write(update_image, window=window, indexes=1)
                    yield window

class ObjectOrientedCropper:
    def __init__(self, image_height: int, image_width: int, window_size: int,
                 geometry_list: list, affine_transformer: AffineTransformer):

        self.image_height = image_height
        self.image_width = image_width
        self.window_size = window_size

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


    def iter_small_geom(self, geom_window: WindowArg, gt_data: np.ndarray):
        def iter_possible_windows(geom_window_: WindowArg):
            row_length_ = geom_window.row_end - geom_window.row_start
            col_length_ = geom_window.col_end - geom_window.col_start
            row_buffer_ = (self.window_size - row_length_) // 2.5
            col_buffer_ = (self.window_size - col_length_) // 2.5

            # possible position
            row_start_1_ = (geom_window_.row_start + geom_window_.row_end - self.window_size) // 2
            col_start_1_ = (geom_window_.col_start + geom_window_.col_end - self.window_size) // 2
            row_start_2_ = row_start_1_ - row_buffer_
            col_start_2_ = col_start_1_ - col_buffer_
            row_start_3_ = row_start_1_ + row_buffer_
            col_start_3_ = col_start_1_ + col_buffer_

            # five possible window
            return (
                (row_start_1_, col_start_1_),
                (row_start_2_, col_start_2_),
                (row_start_2_, col_start_3_),
                (row_start_3_, col_start_2_),
                (row_start_3_, col_start_3_),
            )

        def assess_window_score(row_start_:int, col_start_: int):
            window = self.get_window_and_check_bound(row_start_, col_start_)
            window_data = gt_data[:, window:row_start_:window.row_end, window.col_start:window.col_end]
            # todo: wait for shapefile reader
            not_sure_sum = np.sum()
            current_sum = np.sum((0 < image) & (image < 100)) - np.sum(image == CROPPED_VALUE) * 0.00001


        best_window = None
        best_score = -100

        for row_start, col_start in iter_possible_windows(geom_window):



    def iter_big_geom(self):

    def iter_one_geom(self, geom_window: WindowArg, gt_raster_path: str):
        with rasterio.open(gt_raster_path, "r") as src:
            gt_data = src.read()

        row_length = geom_window.row_end - geom_window.row_start
        col_length = geom_window.col_end - geom_window.col_start
        if row_length <= self.window_size and col_length <= self.window_size:
            yield from self.iter_small_geom(, gt_data)
        else:
            yield from self.iter_big_geom()

    def __iter__(self):

