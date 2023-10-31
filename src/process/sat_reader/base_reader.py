from process.util import WindowArg


class SatReader:
    def read_data_and_profile(self, *args):
        raise NotImplementedError

    def read_window_transform(self, *args):
        raise NotImplementedError

    def crop_data(self, window_arg: WindowArg, output_path: str):
        raise NotImplementedError
