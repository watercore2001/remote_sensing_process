import os


class Downloader:
    def get_possible_item_ids(self, folder_name: str) -> list[str]:
        raise NotImplementedError

    def get_best_item(self, possible_product_ids: list[str]):
        raise NotImplementedError

    def download_one_item_hrefs(self, downloaded_item, bands: list[str], download_folder:str):
        raise NotImplementedError

    def download_all_files(self, input_folder:str, download_folder:str, bands:list[str]):
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

            self.download_one_item_hrefs(downloaded_item, bands, download_folder)
