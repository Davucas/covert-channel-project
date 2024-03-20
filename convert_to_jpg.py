from PIL import Image
import os

# Convert image to JPG lossless
input_folder = './original_images/'
output_folder = './original_images_JPG/'
os.makedirs(output_folder, exist_ok=True)

for folder in os.listdir(input_folder):
    print("in: ", folder)
    if (folder == "flowers"):
        continue    # Skip the flowers folder

    os.makedirs(os.path.join(output_folder, folder), exist_ok=True)

    for filename in os.listdir(input_folder + "/" + folder):
        # If the file name is already jpeg, then just copy over to the folder
        jpg_filename = os.path.splitext(filename)[0] + ".jpg"

        if filename.endswith(".jpg") or filename.endswith(".jpeg"):
            os.system(f'cp {os.path.join(input_folder, folder, filename)} {os.path.join(output_folder, folder, jpg_filename)}')
        else:
            try:
                # Open the image
                with Image.open(os.path.join(input_folder, folder, filename), mode='r') as img:
                    img.save(os.path.join(output_folder, folder, jpg_filename), "JPEG", quality=100)
                    print(f'Converted {filename} to {jpg_filename} lossless')
            except Exception as e:
                print(f'Error converting {os.path.join(output_folder, folder, jpg_filename)} to JPG: {e}')
                continue