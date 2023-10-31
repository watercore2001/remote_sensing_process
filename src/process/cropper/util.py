from osgeo import ogr


def read_geometry_list(shp_file_path):
    driver = ogr.GetDriverByName("ESRI Shapefile")
    geometry_list = []
    ds = driver.Open(shp_file_path, 0)
    layer = ds.GetLayer()
    for feature in layer:
        geometry = feature.GetGeometryRef()
        if geometry is None:
            continue
        geometry_list.append(geometry.Clone())
    return geometry_list
