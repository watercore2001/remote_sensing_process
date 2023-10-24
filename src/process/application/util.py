from osgeo import ogr

def get_aws_sentinel_ids(sentinel2_id: str):
    # T47RPL_20211001T034549 -> S2B_47RPL_20211001_0_L2A
    parts = sentinel2_id.split("_")

    area_id = parts[0][1:]
    time_id = parts[1][:8]

    product_ids = [f"{sat}_{area_id}_{time_id}_{v}_L2A" for v in range(2) for sat in ["S2A", "S2B"]]

    return product_ids

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