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
from typing import List
import argparse

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
    subprocess.run(['steghide', 'embed', '-cf', image_path, '-ef', data_file, '-p', password, '-sf', output_image_path, '-f', '-q'], check=True)

def get_embedded_message_steghide(image_path, data_path, password):
    message = subprocess.run(['steghide', 'extract', '-sf', image_path, '-xf', data_path, '-p', password, '-f', '-q'], check=True)

def zip_extract_image(modified_image_path, zipped_path, extract_path):
    with zipfile.ZipFile(zipped_path, 'w') as zip_ref:
            zip_ref.write(modified_image_path, arcname=modified_image_path)
    
    with zipfile.ZipFile(zipped_path, 'r') as zip_ref:
        file_data = zip_ref.read(modified_image_path)
        with open(extract_path, 'wb') as new_extracted_file:
            new_extracted_file.write(file_data)

def calculate_robustness_to_compression(modified_image, zipped_path, extract_path):
    '''
    Calculate the robustness of the given image to compression by zipping and unzipping it and comparing the hashes
    '''
    # ZIP AND UNZIP IMAGE CALLING zip_extract_image
    zip_extract_image(modified_image, zipped_path, extract_path)

    # compare the hashes
    original_file_hash = calculate_file_hash(modified_image)
    extracted_file_hash = calculate_file_hash(extract_path)

    return original_file_hash == extracted_file_hash

def calculate_hidden_data_to_img_size_ratio(hidden_path, image_path):
    '''
    Calculate the ratio of hidden data to image size
    '''
    hidden_data_size = os.path.getsize(hidden_path)
    image_size = os.path.getsize(image_path)
    return hidden_data_size / image_size

def process_images_in_directory(
        embedFunctionCallback: callable, extractFunctionCallback: callable,
        hidden_files: List[str], directory: str, output_base_dir: str, output_csv: str, password: str, zipped_dir: str, extract_dir: str):
    '''
    Process all images in the given directory and its subdirectories, embedding data of different sizes and calculating PSNR and SSIM
    '''
    # Iterate over all directories and files within the given directory
    for root, dirs, files in os.walk(directory):
        
        ###### THIS IS ONLY TEMPORAL UNTIL WE DECIDE IF WE REMOVE THE FLOWER IMAGES OR NOT
        if root=="original_images_BMP/flowers":
            continue
        ######
        
        for name in files:
            if name.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png')):
                og_image_path = os.path.join(root, name)
                relative_path = os.path.relpath(root, directory)  # Get the relative path to create equivalent structure in output
                output_dir = os.path.join(output_base_dir, relative_path)
                zipped_path = os.path.join(zipped_dir, relative_path)
                extract_path = os.path.join(extract_dir, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                os.makedirs(zipped_path, exist_ok=True)
                os.makedirs(extract_path, exist_ok=True)
                
                # Process each data size for the current image
                for ratio in data_sizes:
                    data_size = os.stat(image_path).st_size * ratio
                    data_file = f'/tmp/data_{data_size}.txt'
                    with open(data_file, 'w') as f:
                        original_data = '0'*data_size
                        f.write('0' * data_size)
                    
                    data_integrity = False
                    output_image_path = os.path.join(output_dir, f"{name}")
                    embed_data_with_steghide(image_path, data_file, password, output_image_path) 

                    psnr_value = calculate_psnr(image_path, output_image_path)
                    ssim_value = calculate_ssi(image_path, output_image_path)
                    zipped_file_path = os.path.join(zipped_path, name)
                    extract_file_path = os.path.join(extract_path, name)
                    image_match = calculate_robustness_to_compression(output_image_path, zipped_file_path, extract_file_path)
                    
                    data_extracted = f'/tmp/data_extracted_{data_size}.txt'
                    get_embedded_message_steghide(extract_file_path, data_extracted, password)
                    with open(data_extracted, 'r') as file:
                        if original_data == file.read(data_size):
                            data_integrity = True    
                    
                    with open(output_csv, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([data_size, psnr_value, ssim_value, data_integrity, image_match])


def initialize_csv(output_csv):
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Image Path", "Data Size (bytes)", "PSNR", "SSIM", "Data Integrity", "Images Match", "Hidden data to Cover Image Ratio"])


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
    data_sizes = [10, 20, 30, 40]    # This is the % of the image_size we want to hide

    source_dir = "original_images_BMP"

    steghide_output_base_dir = "steghide_images"
    steghideoutput_csv = "experiment_results_steghide.csv"
    steghidezipped_dir = "./zipped_images_steghide"
    steghideextract_dir = "./extracted_images_steghide"
    
    funcType = 'steghide'
    password = ""

    openstego_output_base_dir = "openstego_images"
    openstego_outputcsv = "experiment_results_openstego.csv"
    openstego_zipped_dir = "./zipped_images_openstego"
    openstego_extract_dir = "./extracted_images_openstego"
    
    if (funcType == 'steghide'):
        initialize_csv(steghideoutput_csv)
        process_images_in_directory(
            embed_data_with_steghide, get_embedded_message_steghide,
        [hidden_file], source_dir, steghide_output_base_dir, steghideoutput_csv, password, steghidezipped_dir, steghideextract_dir)
        plot_results(steghideoutput_csv)
    elif (funcType == 'openstego'):
        initialize_csv(openstego_outputcsv)
        process_images_in_directory(
            embed_data_with_openstego, get_embedded_message_openstego,
        [hidden_file], source_dir, openstego_output_base_dir, openstego_outputcsv, password, openstego_zipped_dir, openstego_extract_dir)
        plot_results(openstego_outputcsv)


if __name__ == "__main__":
    main()