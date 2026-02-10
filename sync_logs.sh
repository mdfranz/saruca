#!/bin/bash

# Define source and destination
SOURCE_DIR="$HOME/.gemini/tmp/"
DEST_DIR=".gemini-tmp"

# Check if source exists
if [ ! -d "$SOURCE_DIR" ]; then
    echo "Error: Source directory $SOURCE_DIR does not exist."
    exit 1
fi

echo "Syncing logs from $SOURCE_DIR to $DEST_DIR..."

# rsync command:
# -a: archive mode (preserves permissions, symlinks, etc.)
# -v: verbose
# -z: compress during transfer
# --progress: show progress

rsync -avz --progress \
    --exclude '.venv' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude 'bin' \
    --exclude 'include' \
    --exclude 'lib' \
    --exclude 'share' \
    --exclude '__marimo__' \
    "$SOURCE_DIR" "$DEST_DIR"

echo "Sync complete."
