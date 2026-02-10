#!/bin/bash

# Export all discovered sessions into a single unified Parquet file
echo "Exporting sessions from .gemini-tmp to sessions_unified.parquet..."

./.venv/bin/python -m saruca.cli export --path .gemini-tmp --output sessions_unified.parquet

echo "Exporting logs from .gemini-tmp to logs_unified.parquet..."
./.venv/bin/python -m saruca.cli export-logs --path .gemini-tmp --output logs_unified.parquet

echo "Export complete."
