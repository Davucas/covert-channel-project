import hashlib
import subprocess
import os
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim
from PIL import Image
import csv
import matplotlib.pyplot as plt
from skimage.io import imread
import zipfile

def calculate_psnr(original_image_path, modified_image_path):
    original = imread(original_image_path)
    stego = imread(modified_image_path)
    psnrValue = sm.peak_signal_noise_ratio(original.astype(np.int32), stego.astype(np.int32), data_range=255)
    return psnrValue

def calculate_ssi(original_image_path, modified_image_path):
    original = imread(original_image_path)
    stego = imread(modified_image_path)
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

def get_embedded_message_steghide():
    pass


def zip_extract_image(original_image_path, zipped_path, extract_path):
    with zipfile.ZipFile(zipped_path, 'w') as zip_ref:
            zip_ref.write(original_image_path, arcname=original_image_path)
    
    with zipfile.ZipFile(zipped_path, 'r') as zip_ref:
        file_data = zip_ref.read(original_image_path[1:])
        with open(extract_path, 'wb') as new_extracted_file:
            new_extracted_file.write(file_data)
    
    # original_file_hash = calculate_file_hash(original_image_path)
    # extracted_file_hash = calculate_file_hash(extract_path)
    # return original_file_hash == extracted_file_hash


def calculate_robustness_to_compression(modified_image):
    # ZIP AND UNZIP IMAGE CALLING zip_extract_image

    # compare the hashes
    
    # return the message embedded. Calling get_embedded_message_steghide()
    pass



def process_images_in_directory(data_sizes, directory, output_base_dir, output_csv, password):
    # Iterate over all directories and files within the given directory
    for root, dirs, files in os.walk(directory):
        for name in files:
            if name.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png')):
                image_path = os.path.join(root, name)
                relative_path = os.path.relpath(root, directory)  # Get the relative path to create equivalent structure in output
                output_dir = os.path.join(output_base_dir, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                
                # Process each data size for the current image
                for data_size in data_sizes:
                    data_file = f'/tmp/data_{data_size}.txt'
                    with open(data_file, 'w') as f:
                        original_data = '0'*data_size
                        f.write('0' * data_size)
                    
                    output_image_path = os.path.join(output_dir, f"{name}_hidden_{data_size}.bmp")
                    embed_data_with_steghide(image_path, data_file, password, output_image_path) 


                    psnr_value = calculate_psnr(image_path, output_image_path)
                    ssim_value = calculate_ssi(image_path, output_image_path)


                    data_integrity = calculate_robustness_to_compression(output_image_path)

                    
                    



                    with open(output_csv, 'a', newline='') as file:
                        writer = csv.writer(file)
                        writer.writerow([data_size, psnr_value, ssim_value, data_integrity])


def initialize_csv(output_csv):
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Data Size (bytes)", "PSNR", "SSIM", "Data Integrity"])


def plot_results(csv_filename):
    sizes, psnrs, ssims, integrities = [], [], [], []
    
    with open(csv_filename, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            sizes.append(int(row[0]))
            psnrs.append(float(row[1]))
            ssims.append(float(row[2]))
            integrities.append(row[3] == 'True')
    
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
    source_dir = "original_images_BMP"
    output_base_dir = "steghide_images"
    output_csv = "experiment_results.csv"
    password = ""
    # zipped_dir = "zipped_images_steghide"
    # extract_dir = "extracted_images_steghide"

    initialize_csv(output_csv)
    process_images_in_directory(data_sizes, source_dir, output_base_dir, output_csv, password)
    plot_results(output_csv)



if __name__ == "__main__":
    main()