from osgeo import ogr

from process.reader.shp_reader import ShpReader
from process.util import WindowArg, window2geom


class ObjectOrientedCropper:
    def __init__(self, image_height: int, image_width: int, window_size: int,
                 geometry_list: list[ogr.Geometry], shp_reader: ShpReader):

        self.image_height = image_height
        self.image_width = image_width
        self.window_size = window_size
        self.geometry_list = geometry_list
        self.shp_reader = shp_reader

        self.is_geom_skip = [False] * len(geometry_list)

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

    def iter_small_geom(self, current_geometry: ogr.Geometry):
        def iter_possible_windows(geom_window_: WindowArg):
            row_length_ = geom_window.row_end - geom_window.row_start
            col_length_ = geom_window.col_end - geom_window.col_start
            row_buffer_ = (self.window_size - row_length_) // 2.5
            col_buffer_ = (self.window_size - col_length_) // 2.5

            # possible position
            row_start_1_ = (geom_window_.row_start + geom_window_.row_end - self.window_size) // 2
            row_start_2_ = row_start_1_ - row_buffer_
            row_start_3_ = row_start_1_ + row_buffer_

            col_start_1_ = (geom_window_.col_start + geom_window_.col_end - self.window_size) // 2
            col_start_2_ = col_start_1_ - col_buffer_
            col_start_3_ = col_start_1_ + col_buffer_

            # five possible window
            return (
                (row_start_1_, col_start_1_),
                (row_start_2_, col_start_2_),
                (row_start_2_, col_start_3_),
                (row_start_3_, col_start_2_),
                (row_start_3_, col_start_3_),
            )

        best_score = None
        best_window = None
        geom_window = self.get_geom_window(current_geometry)
        for row_start, col_start in iter_possible_windows(geom_window):
            window = self.get_window_and_check_bound(row_start, col_start)
            score = self.shp_reader.get_window_score(window, current_geometry)
            if score is None:
                continue
            if best_score is None or score > best_score:
                best_score = score
                best_window = window
        if best_window is not None:
            yield best_window

    def iter_big_geom(self, current_geometry: ogr.Geometry):
        def next_line(start_line_: int, end_line_: int, window_size_: int):
            length_ = end_line_ - start_line_
            if length_ <= window_size_:
                yield (end_line_ + start_line_ - window_size_) // 2
            else:
                window_num = round(length_ / window_size_)
                for i in range(window_num):
                    yield start_line_ + i * window_size_

        row_buffer = self.window_size // 8
        col_buffer = self.window_size // 8
        geom_window = self.get_geom_window(current_geometry)
        for row_start in next_line(geom_window.row_start - row_buffer, geom_window.row_end + row_buffer, self.window_size):
            for col_start in next_line(geom_window.col_start - col_buffer, geom_window.col_end + col_buffer, self.window_size):
                window = self.get_window_and_check_bound(row_start, col_start)
                score = self.shp_reader.get_window_score(window, current_geometry)
                if score is None:
                    continue
                yield window

    def iter_one_geom(self, current_geometry: ogr.Geometry):
        geom_window = self.get_geom_window(current_geometry)
        row_length = geom_window.row_end - geom_window.row_start
        col_length = geom_window.col_end - geom_window.col_start
        if row_length <= self.window_size and col_length <= self.window_size:
            yield from self.iter_small_geom(current_geometry)
        else:
            yield from self.iter_big_geom(current_geometry)

    def get_geom_window(self, geometry: ogr.Geometry):
        # mbr in crs: (minX, maxX, minY, maxY)
        geom_geo_envelope = geometry.GetEnvelope()
        row_start, col_start = self.shp_reader.affine_transform.rowcol(geom_geo_envelope[0], geom_geo_envelope[2])
        row_end, col_end = self.shp_reader.affine_transform.rowcol(geom_geo_envelope[1], geom_geo_envelope[3])

        if row_start > row_end:
            row_start, row_end = row_end, row_start

        if col_start > col_end:
            col_start, col_end = col_end, col_start

        return WindowArg(row_start, row_end, col_start, col_end)

    def check_which_geometry_is_contained(self, window: WindowArg):
        window_geom = window2geom(self.shp_reader.affine_transform, window)
        for i, current_geometry in enumerate(self.geometry_list):
            if self.is_geom_skip[i] is True:
                continue
            intersection = window_geom.Intersection(current_geometry)
            if intersection.Area() >= current_geometry.Area() * 0.6:
                self.is_geom_skip[i] = True

    def __iter__(self):
        geometry_id = 0
        for i, current_geometry in enumerate(self.geometry_list):
            geometry_id += 1
            if self.is_geom_skip[i]:
                continue
            window_id = 0
            for window in self.iter_one_geom(current_geometry):
                self.check_which_geometry_is_contained(window)
                window_id += 1
                yield window, f"{geometry_id:02d}{window_id:02d}"

            self.is_geom_skip[i] = True


