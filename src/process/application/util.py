from osgeo import ogr



def get_shapefile_geometrys(shapefile_path_list: list[str], sat_geometry: ogr.Geometry) -> list[ogr.Geometry]:
    driver = ogr.GetDriverByName("ESRI Shapefile")
    geometry_list = []
    for shp in shapefile_path_list:
        ds = driver.Open(shp, 0)
        layer = ds.GetLayer()
        for feature in layer:
            geometry = feature.GetGeometryRef()
            if geometry is not None and sat_geometry.Intersect(geometry):
                geometry_list.append(geometry.Clone())
    return geometry_list