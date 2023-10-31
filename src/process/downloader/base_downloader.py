class BaseDownloader:
    def get_possible_item_ids(self, folder_name: str) -> list[str]:
        raise NotImplementedError

    def get_best_item(self, possible_product_ids: list[str]):
        raise NotImplementedError

    def download_one_item_hrefs(self, downloaded_item, bands: list[str], download_folder: str):
        raise NotImplementedError

    def download_all_files(self, input_folder: str, download_sub_folder: str, bands: list[str]):
        raise NotImplementedError
