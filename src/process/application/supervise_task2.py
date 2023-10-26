from pystac_client import Client
import os
from process.util import window2geom, WindowArg
from process.application.util import get_shapefile_geometrys
from process.cropper import SlideWindowCropper
from process.reader import ShpReader, AwsSentinelUnstackReader
from urllib import request
import rasterio
from osgeo import ogr, osr



class AwsLabelFilesManager:
    aws_url = "https://earth-search.aws.element84.com/v1"
    aws_asset = {"B01": "coastal", "B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1", "B06": "rededge2",
                 "B07": "rededge3", "B08": "nir", "B8A": "nir08", "B09": "nir09", "B11": "swir16", "B12": "swir22"}
    label_shp_filename = "building.shp"
    false_shp_filename = "false.shp"
    unsure_shp_file = "notsure.shp"

    def __init__(self, input_folder: str, window_size:int, output_folder: str, ):
        # tif image should cover label file and false file
        self.input_folder = input_folder
        self.window_size = window_size
        self.output_folder = output_folder

        self.aws_client = Client.open(url=self.aws_url)
        self.shp_reader = None
        self.image_reader = None
        self.cropper = None

    def run(self):
        self.download_all_aws_files()
        self.generate_dataset()

    def get_prefer_item(self, aws_ids: tuple[str]):
        item_search = self.aws_client.search(collections="sentinel-2-l2a", ids=aws_ids)
        prefer_item = None
        for item in item_search.item_collection():
            if prefer_item is None or item.id.endswith("0_L2A"):
                prefer_item = item
        return prefer_item

    def download_one_item_hrefs(self, item, download_folder: str):
        os.makedirs(download_folder, exist_ok=True)
        for band, name in self.aws_asset.items():
            href = item.assets[name].href
            download_path = os.path.join(download_folder, f"{band}.tif")
            if os.path.exists(download_path):
                continue
            request.urlretrieve(href, download_path)

    def download_all_aws_files(self):
        for folder in os.listdir(self.input_folder):
            shapefile_folder = os.path.join(self.input_folder, folder)
            if not os.path.isdir(shapefile_folder):
                continue
            aws_ids = get_aws_sentinel_ids(folder)
            print(aws_ids)
            prefer_item = self.get_prefer_item(aws_ids)
            if prefer_item is None:
                continue
            print(prefer_item.id)
            download_folder = os.path.join(shapefile_folder, "image")
            self.download_one_item_hrefs(prefer_item, download_folder)

    def init_shp_reader(self, shapefile_folder: str):
        # todo optimize here
        label_paths = [os.path.join(shapefile_folder, self.label_shp_filename)]
        burn_values = [1]
        if not os.path.exists(label_paths[0]):
            label_paths = None
            burn_values = None

        false_path = os.path.join(shapefile_folder, self.false_shp_filename)
        if not os.path.exists(false_path):
            false_path = None

        unsure_path = os.path.join(shapefile_folder, self.unsure_shp_file)
        if not os.path.exists(unsure_path):
            unsure_path = None

        sat_tif_path = os.path.join(shapefile_folder, "image/B02.tif")
        if not os.path.exists(sat_tif_path):
            raise Exception(f"{shapefile_folder} do not have B02 file")

        rasterize_output_folder = os.path.join(shapefile_folder, "rasterize_output")

        shp_reader = ShpReader(sat_tif_path, rasterize_output_folder, label_paths, burn_values, false_path, unsure_path)
        return shp_reader

    def init_slide_cropper(self, shapefile_folder: str):
        sat_tif_path = os.path.join(shapefile_folder, "image/B02.tif")
        with rasterio.open(sat_tif_path) as src:
            image_height = src.height
            image_width = src.width
        cropper = SlideWindowCropper(image_height, image_width, self.window_size, 64, self.shp_reader)
        return cropper

    def generate_dataset(self):
        sample_id = 0
        for folder in os.listdir(self.input_folder):
            shapefile_folder = os.path.join(self.input_folder, folder)

            #todo
            os.makedirs(os.path.join(shapefile_folder, "rasterize_output"), exist_ok=True)
            output_window_shp_path = os.path.join(shapefile_folder, "rasterize_output", "window.shp")
            driver = ogr.GetDriverByName("ESRI Shapefile")
            if os.path.exists(output_window_shp_path):
                driver.DeleteDataSource(output_window_shp_path)

            ds = driver.CreateDataSource(output_window_shp_path)
            srs = osr.SpatialReference()
            sat_tif_path = os.path.join(shapefile_folder, "image/B02.tif")
            with rasterio.open(sat_tif_path) as src:
                epsg = src.crs.to_epsg()
            srs.ImportFromEPSG(epsg)
            window_layer = ds.CreateLayer("windows", srs, ogr.wkbPolygon)
            window_layer.CreateField(ogr.FieldDefn("id", ogr.OFTString))
            #todo

            if not os.path.isdir(shapefile_folder):
                continue
            self.shp_reader = self.init_shp_reader(shapefile_folder)
            self.image_reader = AwsSentinelUnstackReader(os.path.join(shapefile_folder, "image"))
            self.cropper = self.init_slide_cropper(shapefile_folder)
            for window, window_id in iter(self.cropper):
                sample_id += 1
                shp_output_path = os.path.join(self.output_folder, "gt", f"{sample_id}.tif")
                image_output_folder = os.path.join(self.output_folder, "image", f"{sample_id}")
                self.shp_reader.crop_data(window, shp_output_path, window_id)
                self.image_reader.crop_data(window, output_folder=image_output_folder)

                #todo
                feature = ogr.Feature(window_layer.GetLayerDefn())
                feature.SetField("id", window_id)
                window_geometry = window2geom(self.shp_reader.affine_transform, window)
                feature.SetGeometry(window_geometry)
                window_layer.CreateFeature(feature)
                #todo



