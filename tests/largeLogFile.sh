#!/bin/bash

# Create a large log file

# keep adding to the file regularly
for i in {1..10}; do
    echo "This is a log message index $i" >> ~/Desktop/keepUpdatingFile.txt
    sleep 2
done