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
# --include='*/' --include='logs.json' --include='chats/*.json' --exclude='*' 
# (Optional: specific filters if you only want the data files)

rsync -avz --progress "$SOURCE_DIR" "$DEST_DIR"

echo "Sync complete."
