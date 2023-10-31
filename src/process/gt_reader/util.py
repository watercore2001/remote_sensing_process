import os

from osgeo import gdal, ogr

gdal.UseExceptions()


def rasterize_shapefiles(shp_paths: list[str], burn_values: list[int], tif_path: str, output_path: str):
    assert len(shp_paths) == len(burn_values), "shp num should be corresponding to value num"
    shp_num = len(shp_paths)

    # read shapefile data
    shp_driver = ogr.GetDriverByName("ESRI Shapefile")

    # read tif data
    tif_dst = gdal.Open(tif_path)

    # create output file
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    tif_driver = gdal.GetDriverByName("GTiff")
    out_dst = tif_driver.Create(utf8_path=output_path, xsize=tif_dst.RasterXSize,
                                ysize=tif_dst.RasterYSize, bands=shp_num, eType=gdal.GDT_Byte, options=["COMPRESS=LZW"])

    # copy CRS and Transform
    out_dst.SetProjection(tif_dst.GetProjection())
    out_dst.SetGeoTransform(tif_dst.GetGeoTransform())
    tif_dst = None

    for i, (shp_path, burn_value) in enumerate(zip(shp_paths, burn_values), start=1):
        shp_dst = shp_driver.Open(shp_path, 0)
        shp_layer = shp_dst.GetLayer()
        gdal.RasterizeLayer(dataset=out_dst, bands=[i], layer=shp_layer, burn_values=[burn_value])
        shp_dst = None

    out_dst = None
