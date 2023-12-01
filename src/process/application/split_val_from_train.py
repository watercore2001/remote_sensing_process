import os
import shutil
import random
import argparse
import dataclasses

from tqdm.contrib.concurrent import process_map


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("-i", "--input_folder", type=str, required=True, help="Input dataset folder.")
    parser.add_argument("-p", "--validation_percent", type=float, required=True)

    return parser.parse_args()


@dataclasses.dataclass
class RunArg:
    train_scene_folder: str
    valid_scene_folder: str
    validation_percent: float


def run(run_arg: RunArg):
    train_scene_folder = run_arg.train_scene_folder
    valid_scene_folder = run_arg.valid_scene_folder
    validation_percent = run_arg.validation_percent

    os.makedirs(valid_scene_folder, exist_ok=True)

    tif_filenames = []
    no_tif_filenames = []
    for filename in os.listdir(train_scene_folder):
        if filename.endswith("tif"):
            tif_filenames.append(filename)
        else:
            no_tif_filenames.append(filename)

    valid_num = int(len(tif_filenames) * validation_percent)
    valid_filenames = random.sample(tif_filenames, valid_num)
    for valid_filenames in valid_filenames:
        src_file = os.path.join(train_scene_folder, valid_filenames)
        dst_file = os.path.join(valid_scene_folder, valid_filenames)
        shutil.move(src_file, dst_file)

    for metadata_filename in no_tif_filenames:
        src_file = os.path.join(train_scene_folder, metadata_filename)
        dst_file = os.path.join(valid_scene_folder, metadata_filename)
        shutil.copy2(src_file, dst_file)


def main():
    args = parse_args()
    train_folder = os.path.join(args.input_folder, "train")
    val_folder = os.path.join(args.input_folder, "val")

    os.makedirs(val_folder, exist_ok=True)
    run_args = []
    for scene_name in os.listdir(train_folder):
        scene_train_folder = os.path.join(train_folder, scene_name)
        if not os.path.isdir(scene_train_folder):
            continue
        scene_val_folder = os.path.join(val_folder, scene_name)
        run_arg = RunArg(train_scene_folder=scene_train_folder,
                         valid_scene_folder=scene_val_folder,
                         validation_percent=args.validation_percent)
        run_args.append(run_arg)
    print(run_args)
    process_map(run, run_args)


if __name__ == "__main__":
    main()


