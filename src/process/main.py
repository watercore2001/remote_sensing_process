from process.application.supervise_task2 import AwsLabelFilesManager


def main():
    input_folder = "/mnt/data/building/"
    output_folder = "/mnt/data/dataset/build/"
    aws_manager = AwsLabelFilesManager(input_folder=input_folder, window_size=512, output_folder=output_folder)
    aws_manager.run()


if __name__ == "__main__":
    main()