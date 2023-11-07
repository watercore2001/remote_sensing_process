import os
from urllib import request

from pystac_client import Client

from .base_downloader import BaseDownloader
from .util import sentinel2_l2a_asset


class AwsDownloader(BaseDownloader):
    aws_url = "https://earth-search.aws.element84.com/v1"

    def __init__(self):
        self.aws_client = Client.open(url=self.aws_url)


class AwsSentinel2L2aDownloader(AwsDownloader):
    sentinel2_l2a_asset = sentinel2_l2a_asset

    def __init__(self):
        super().__init__()

    def get_possible_item_ids(self, folder_name: str) -> list[str]:
        """Get possible item ids in aws downloader source

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
            band_index = self.sentinel2_l2a_asset[band]
            href = downloaded_item.assets[band_index].href
            download_path = os.path.join(download_folder, f"{band}.tif")
            if os.path.exists(download_path):
                continue
            request.urlretrieve(href, download_path)

    def download_all_files(self, input_folder: str, download_sub_folder: str, bands: list[str]):
        for folder_name in os.listdir(input_folder):
            if not os.path.isdir(os.path.join(input_folder, folder_name)):
                continue
            item_ids = self.get_possible_item_ids(folder_name)
            print(f"Possible downloaded item ids: {item_ids}.")
            downloaded_item = self.get_best_item(item_ids)
            if downloaded_item is None:
                print("There is not accessible item in possible items, skip this scene.")
                continue
            print(f"The item ID to be downloaded is: {downloaded_item.id}.")

            download_folder = os.path.join(input_folder, folder_name, download_sub_folder)
            self.download_one_item_hrefs(downloaded_item, bands, download_folder)
