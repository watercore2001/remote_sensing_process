from rasterio.transform import AffineTransformer
import dataclasses
from osgeo import ogr






def window2geom(affine_transformer: AffineTransformer, window: WindowArg):
    """
    根据 window 构建一个几何要素
    """
    # 根据 window 构造一个地理要素
    min_x, min_y = affine_transformer.xy(window.row_end, window.col_start)
    max_x, max_y = affine_transformer.xy(window.row_start, window.col_end)

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
