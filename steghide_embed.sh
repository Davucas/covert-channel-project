#!/bin/bash

# Input directory
input_directory="original_images_BMP"

# Verify if 'steghide_images' exists, if not it creates it
if [ ! -d "steghide_images" ]; then
    mkdir steghide_images
fi

# Iterate through the subdirectories of the input directory
for category in "$input_directory"/*; do
    # Verify that is a directory
    if [ -d "$category" ]; then
        category_name=$(basename "$category")

        # Verify that the subdirectory exists, if not create it
        output_category_directory="steghide_images/$category_name"
        if [ ! -d "$output_category_directory" ]; then
            mkdir "$output_category_directory"
        fi

        # Iterate through all the images of the subdirectory
        for image in "$category"/*.bmp; do
            if [ -e "$image" ]; then
                # Name for the output file
                output_file="steghide_images/${category_name}/${image##*/}"

                passphrase="tu_contraseña_secreta"

                steghide embed -cf "$image" -ef data.txt -sf "$output_file" -p "$passphrase"

                if [[ ! $? -eq 0 ]]; then
                    # echo "Se ocultó data.txt en $output_file"
                    echo "Error hiding data.txt in $image"
                fi
            fi
        done
    fi
done
