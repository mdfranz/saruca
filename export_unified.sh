#!/bin/bash

# Export all discovered sessions into a single unified Parquet file
echo "Exporting sessions from .gemini-tmp to sessions_unified.parquet..."

uv run saruca export --path .gemini-tmp --output sessions_unified.parquet

echo "Exporting logs from .gemini-tmp to logs_unified.parquet..."
uv run saruca export-logs --path .gemini-tmp --output logs_unified.parquet

echo "Export complete."
