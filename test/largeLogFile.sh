#!/bin/bash

# Create a large log file

# keep adding to the file regularly
while true; do
    echo "Adding to the file" >> dropbox/FUSE-TEST/largeLogFile.log
    sleep 2
done