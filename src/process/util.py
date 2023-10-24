import dataclasses

from osgeo import ogr
from rasterio.transform import AffineTransformer


@dataclasses.dataclass
class WindowArg:
    row_start: int
    row_end: int
    col_start: int
    col_end: int

    def __post_init__(self):
        self.row_start = int(self.row_start)
        self.row_end = int(self.row_end)
        self.col_start = int(self.col_start)
        self.col_end = int(self.col_end)


def window2geom(affine_transformer: AffineTransformer, window_arg: WindowArg):
    min_x, min_y = affine_transformer.xy(window_arg.row_end, window_arg.col_start)
    max_x, max_y = affine_transformer.xy(window_arg.row_start, window_arg.col_end)

    if min_x > max_x:
        min_x, max_x = max_x, min_x
    if min_y > max_y:
        min_y, max_y = max_y, min_y

    ring = ogr.Geometry(ogr.wkbLinearRing)
    ring.AddPoint(min_x, min_y)
    ring.AddPoint(min_x, max_y)
    ring.AddPoint(max_x, max_y)
    ring.AddPoint(max_x, min_y)
    ring.AddPoint(min_x, min_y)

    mbr = ogr.Geometry(ogr.wkbPolygon)
    mbr.AddGeometry(ring)

    return mbr