#!/bin/bash

SRC_DIR="./src"
DEST_DIR="~/Desktop/.config"
DEST_SRC_DIR="~/Desktop/.config/src"
EXTENSION_SRC="./ui/CloudStatusExtension.py"
EXTENSION_DEST="~/.local/share/nemo-python/CloudStatusExtension.py"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" &> /dev/null && pwd)"
cd "$SCRIPT_DIR"

case "$1" in
    start)
        echo "Starting application..."
        if [ ! -d "$EXTENSION_DEST" ]; then
            mkdir -p $EXTENSION_DEST
        fi
        cp $EXTENSION_SRC $EXTENSION_DEST
        nemo -q && nemo &
        if [ ! -d "$DEST_SRC_DIR" ]; then
            if [ ! -d "$DEST_DIR" ]; then
                mkdir -p $DEST_DIR
            fi
            cp -r $SRC_DIR $DEST_DIR
        fi
        cd $DEST_DIR
        python3 -m src start
        ;;
    stop)
        echo "Stopping application..."
        cd $DEST_DIR
        python3 -m src stop
        rm $EXTENSION_DEST
        nemo -q && nemo &
        ;;
    *)
        echo "Unknown command: $1"
        echo "Usage: $0 {start|stop}"
        exit 1
esac
