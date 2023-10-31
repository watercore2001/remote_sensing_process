from osgeo import ogr

from process.gt_reader.shp_reader import ShpReader
from process.util import WindowArg


class BaseCropper:
    def __init__(self, shp_reader: ShpReader):
        self.shp_reader = shp_reader

    def __iter__(self):
        raise NotImplementedError

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
