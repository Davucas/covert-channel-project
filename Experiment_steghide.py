import hashlib
import subprocess
import os
import numpy as np
import skimage.metrics as sm
from PIL import Image
import csv
import matplotlib.pyplot as plt
from skimage.io import imread
import zipfile
from pathlib import Path

current_working_dir = Path().absolute()

def calculate_psnr(original_image_path, modified_image_path):
    original = imread(original_image_path)
    stego = imread(modified_image_path)
    psnrValue = sm.peak_signal_noise_ratio(original.astype(np.int32), stego.astype(np.int32), data_range=255)
    return psnrValue

def calculate_ssi(original_image_path, modified_image_path):
    original = imread(original_image_path)
    stego = imread(modified_image_path)
    minDimension = min(original.shape[:2])
    windowSize = min(7, minDimension - (minDimension % 2 - 1))  # ensure odd window size
    ssiValue = sm.structural_similarity(original.astype(np.int32), stego.astype(np.int32), data_range=255, win_size=windowSize, channel_axis=-1)    # Due to bmp typically stored in 8-bit unsigned integer format
    return ssiValue

def calculate_file_hash(file_name):
    hash_obj = hashlib.sha256()
    with open(file_name, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_obj.update(chunk)
    return hash_obj.hexdigest()

def embed_data_with_steghide(image_path, data_file, password, output_image_path):
    subprocess.run(['steghide', 'embed', '-cf', image_path, '-ef', data_file, '-p', password, '-sf', output_image_path], check=True)

def get_embedded_message_steghide(image_path, password):
    message = subprocess.run(['steghide', 'extract', '-cf', image_path, '-p', password], check=True)
    return message


def zip_extract_image(modified_image_path, zipped_path, extract_path):
    with zipfile.ZipFile(zipped_path, 'w') as zip_ref:
            zip_ref.write(modified_image_path, arcname=modified_image_path)
    
    with zipfile.ZipFile(zipped_path, 'r') as zip_ref:
        file_data = zip_ref.read(modified_image_path[1:])
        with open(extract_path, 'wb') as new_extracted_file:
            new_extracted_file.write(file_data)
    
    # original_file_hash = calculate_file_hash(modified_image)
    # extracted_file_hash = calculate_file_hash(extract_path)
    # return original_file_hash == extracted_file_hash


def calculate_robustness_to_compression(modified_image, zipped_path, extract_path):
    # ZIP AND UNZIP IMAGE CALLING zip_extract_image
    zip_extract_image(modified_image, zipped_path, extract_path)

    # compare the hashes
    original_file_hash = calculate_file_hash(modified_image)
    extracted_file_hash = calculate_file_hash(extract_path)

    return original_file_hash == extracted_file_hash


def process_images_in_directory(data_sizes, directory, output_base_dir, output_csv, password, zipped_dir, extract_dir):
    # Iterate over all directories and files within the given directory
    # for root, dirs, files in os.walk(directory):
    for sub_dir in directory.iterdir():
        print(f"Working on the directory of: {sub_dir}")
        for name in sub_dir.iterdir():
            if name.suffix in ['.bmp', '.jpg', '.jpeg', '.png']:
                image_path = directory / sub_dir, name
                output_dir = output_base_dir / sub_dir
                zipped_path = zipped_dir / sub_dir
                extract_path = extract_dir / sub_dir
                output_dir.mkdir(parents=True, exist_ok=True)
                zipped_path.mkdir(parents=True, exist_ok=True)
                extract_path.mkdir(parents=True, exist_ok=True)
                
                # Process each data size for the current image
                for data_size in data_sizes:
                    data_file = f'/tmp/data_{data_size}.txt'
                    with open(data_file, 'w') as f:
                        original_data = '0'*data_size
                        f.write('0' * data_size)
                    
                    output_image_path = output_dir / Path(f"{name}_hidden_{data_size}.bmp")
                    embed_data_with_steghide(str(image_path), data_file, password, output_image_path) 

                    psnr_value = calculate_psnr(str(image_path), output_image_path)
                    ssim_value = calculate_ssi(str(image_path), output_image_path)

                    
                    image_match = calculate_robustness_to_compression(output_image_path, zipped_path, extract_path)
                    data_integrity = False

                    if original_data == get_embedded_message_steghide(zipped_path):
                        data_integrity = True    
                    

                    with open(output_csv, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([data_size, psnr_value, ssim_value, data_integrity, image_match])


def initialize_csv(output_csv):
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Data Size (bytes)", "PSNR", "SSIM", "Data Integrity", "Images Match"])


def plot_results(csv_filename):
    sizes, psnrs, ssims, integrities, matches = [], [], [], [], []
    
    with open(csv_filename, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            sizes.append(int(row[0]))
            psnrs.append(float(row[1]))
            ssims.append(float(row[2]))
            integrities.append(row[3] == 'True')
            matches.append(row[4] == 'True')
    
    # Plotting
    fig, ax1 = plt.subplots()

    color = 'tab:red'
    ax1.set_xlabel('Data Size (bytes)')
    ax1.set_ylabel('PSNR', color=color)
    ax1.plot(sizes, psnrs, color=color)
    ax1.tick_params(axis='y', labelcolor=color)

    ax2 = ax1.twinx()  # instantiate a second axes that shares the same x-axis
    color = 'tab:blue'
    ax2.set_ylabel('SSIM', color=color)  # we already handled the x-label with ax1
    ax2.plot(sizes, ssims, color=color)
    ax2.tick_params(axis='y', labelcolor=color)

    fig.tight_layout()  # otherwise the right y-label is slightly clipped
    plt.title('PSNR and SSIM vs Data Size')
    plt.show()



def main():
    data_sizes = [100, 500, 1000, 5000, 10000]
    source_dir = current_working_dir / Path("original_images_BMP")
    output_base_dir = current_working_dir / Path("steghide_images")
    output_csv = current_working_dir / Path("experiment_results.csv")
    password = ""
    zipped_dir = current_working_dir / Path("zipped_images_steghide")
    extract_dir = current_working_dir / Path("extracted_images_steghide")
    
    

    initialize_csv(output_csv)
    process_images_in_directory(data_sizes, source_dir, output_base_dir, output_csv, password, zipped_dir, extract_dir)
    plot_results(output_csv)



if __name__ == "__main__":
    main()