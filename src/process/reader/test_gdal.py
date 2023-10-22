import os
from osgeo import gdal, ogr





def main():
    tif_path = "/mnt/data/AWS sample/test/T45SXS_20200726T044659_B04_10m.tif"
    shp_path = "/mnt/data/AWS sample/test/T45SXS_water.shp"
    output_path = "/mnt/data/AWS sample/test/output.tif"
    shp_paths = [shp_path, shp_path]
    burn_values = [5, 6]
    rasterize_shapefiles(shp_paths, burn_values, tif_path, output_path)


if __name__ == "__main__":
    main()
