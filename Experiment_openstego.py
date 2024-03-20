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
    subprocess.run(['java', '-jar', '/home/carlos/openstego.jar', 'embed', '-cf', image_path, '-mf', data_file, '-p', password, '-sf', output_image_path, '-C'], check=True)

def get_embedded_message_steghide(image_path, data_path, password):
    message = subprocess.run(['java', '-jar', '/home/carlos/openstego.jar', 'extract', '-sf', image_path, '-xf', data_path, '-p', password, '-C'], check=True)

def zip_extract_image(modified_image_path, zipped_path, extract_path):
    with zipfile.ZipFile(zipped_path, 'w') as zip_ref:
            zip_ref.write(modified_image_path, arcname=modified_image_path)
    
    with zipfile.ZipFile(zipped_path, 'r') as zip_ref:
        file_data = zip_ref.read(modified_image_path)
        with open(extract_path, 'wb') as new_extracted_file:
            new_extracted_file.write(file_data)

def calculate_robustness_to_compression(modified_image, zipped_path, extract_path):
    # ZIP AND UNZIP IMAGE CALLING zip_extract_image
    zip_extract_image(modified_image, zipped_path, extract_path)

    # compare the hashes
    original_file_hash = calculate_file_hash(modified_image)
    extracted_file_hash = calculate_file_hash(extract_path)

    return original_file_hash == extracted_file_hash


def process_images_in_directory(data_sizes, directory, output_base_dir, output_csv, password, zipped_dir, extract_dir):
    # Iterate over all directories and files within the given directory
    for root, dirs, files in os.walk(directory):
        
        ###### THIS IS ONLY TEMPORAL UNTIL WE DECIDE IF WE REMOVE THE FLOWER IMAGES OR NOT
        if root=="original_images_BMP/flowers":
            continue
        ######

        for name in files:
            if name.lower().endswith(('.bmp', '.jpg', '.jpeg', '.png')):
                image_path = os.path.join(root, name)
                relative_path = os.path.relpath(root, directory)  # Get the relative path to create equivalent structure in output
                output_dir = os.path.join(output_base_dir, relative_path)
                zipped_path = os.path.join(zipped_dir, relative_path)
                extract_path = os.path.join(extract_dir, relative_path)
                os.makedirs(output_dir, exist_ok=True)
                os.makedirs(zipped_path, exist_ok=True)
                os.makedirs(extract_path, exist_ok=True)
                
                # Process each data size for the current image
                for ratio in data_sizes:
                    image_size = os.stat(image_path).st_size
                    data_size = int(ratio * image_size / 100)
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
                        writer.writerow([output_image_path, image_size, data_size, ratio, psnr_value, ssim_value, data_integrity, image_match])


def initialize_csv(output_csv):
    with open(output_csv, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Image", "Image_size", "Data Size (bytes)", "Ratio", "PSNR", "SSIM", "Data Integrity", "Images Match"])


def plot_results(csv_filename):
    image, image_size, sizes, ratios, psnrs, ssims, integrities, matches = [], [], [], [], [], [], [], []
    
    with open(csv_filename, mode='r') as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            image.append(str(row[0]))
            image_size.append(str(row[1]))
            sizes.append(int(row[2]))
            ratios.append(int(row[3]))
            psnrs.append(float(row[4]))
            ssims.append(float(row[5]))
            integrities.append(row[6] == 'True')
            matches.append(row[7] == 'True')
    
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
    #data_sizes = [100, 500, 1000, 5000, 10000]
    data_sizes = [1, 2, 3, 4]

    source_dir = "original_images_BMP"
    output_base_dir = "openstego_images"
    output_csv = "./experiment_results_openstego.csv"
    password = ""
    zipped_dir = "./zipped_images_openstego"
    extract_dir = "./extracted_images_openstego"
    
    # initialize_csv(output_csv)
    # process_images_in_directory(data_sizes, source_dir, output_base_dir, output_csv, password, zipped_dir, extract_dir)
    plot_results(output_csv)



if __name__ == "__main__":
    main()