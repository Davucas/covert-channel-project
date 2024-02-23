from PIL import Image
import os

# Replace 'input_folder' and 'output_folder' with your actual paths
input_folder = './original_images/'
output_folder = './original_images_BMP/'

os.makedirs(output_folder, exist_ok=True)

for folder in os.listdir(input_folder):
    print("hey: ", folder)
    for filename in os.listdir(input_folder + "/" + folder):
        #if filename.endswith(".jpg") or filename.endswith(".jpeg"):
        # Open the image
        img = Image.open(os.path.join(input_folder, folder, filename))
        
        # Convert and save as BMP
        bmp_filename = os.path.splitext(filename)[0] + ".bmp"
        img.save(os.path.join(output_folder, folder, bmp_filename), "BMP")
