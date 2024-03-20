#!/bin/bash

# Copyright 2021 Joao Eriberto Mota Filho <eriberto@eriberto.pro.br>
#
# This file is under BSD-3-Clause license.

# Write message
echo -e "\nEmbedding a message..." 
outguess -k "secret-key-001" -d message.txt test.jpg test-with-message.jpg -p 100

# Retrieve message
echo -e "\nExtracting a message..." 
outguess -k "secret-key-001" -r test-with-message.jpg text-jpg.txt
cat text-jpg.txt | grep "inside of the image" || { echo ERROR; exit 1; }

# Remove files
rm -f test-with-message.jpg text-jpg.txt
