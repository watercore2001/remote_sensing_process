from pystac_client import Client
import os
from urllib import request
from .downloader import Downloader


class AwsDownloader(Downloader):
    aws_url = "https://earth-search.aws.element84.com/v1"

    def __init__(self):
        self.aws_client = Client.open(url=self.aws_url)


class AwsSentinel2L2aDownloader(AwsDownloader):
    sentinel2_l2a_asset = {"B01": "coastal", "B02": "blue", "B03": "green", "B04": "red", "B05": "rededge1",
                           "B06": "rededge2", "B07": "rededge3", "B08": "nir", "B8A": "nir08", "B09": "nir09",
                           "B11": "swir16", "B12": "swir22"}

    def __init__(self):
        super().__init__()

    def get_possible_item_ids(self, folder_name: str) -> list[str]:
        """Get possible item ids in aws download source

        :param folder_name: such as T47RPL_20211001T034549
        :return: such as [S2A_47RPL_20211001_0_L2A, S2A_47RPL_20211001_1_L2A, S2B_47RPL_20211001_0_L2A, S2B_47RPL_20211001_1_L2A]
        """
        parts = folder_name.split("_")

        area_id = parts[0][1:]
        time_id = parts[1][:8]

        product_ids = [f"{sat}_{area_id}_{time_id}_{v}_L2A" for v in range(2) for sat in ["S2A", "S2B"]]

        return product_ids

    def get_best_item(self, possible_product_ids: list[str]):
        item_search = self.aws_client.search(collections="sentinel-2-l2a", ids=possible_product_ids)
        prefer_item = None
        for item in item_search.item_collection():
            if prefer_item is None or item.id.endswith("0_L2A"):
                prefer_item = item
        return prefer_item

    def download_one_item_hrefs(self, downloaded_item, bands: list[str], download_folder: str):
        os.makedirs(download_folder, exist_ok=True)
        accessible_bands = set(self.sentinel2_l2a_asset.keys())
        assert set(bands).issubset(accessible_bands), \
            f"Accessible bands: {accessible_bands}, input bands {bands} are not all accessible"
        for band in bands:
            href = downloaded_item.assets[band].href
            download_path = os.path.join(download_folder, f"{band}.tif")
            if os.path.exists(download_path):
                continue
            request.urlretrieve(href, download_path)

