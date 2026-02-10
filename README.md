# Saruca: A Gemini CLI Log & Session Analyzer.

![saruca logo](saruca.png)


Mining log and session data from Gemini CLI using Polars for high-performance analysis.

## Features

- **Discovery:** Automatically find logs and session JSON files in project directories.
- **Analysis:** Summarize message types, project activity, and token usage.
- **Export:** Convert nested session data into flat Parquet files for easy processing in other tools.
- **Data-centric:** Built on Polars, Orjson, and Pydantic.

## Quick Start

### Installation

```bash
uv venv
source .venv/bin/activate
uv sync
uv pip install -r requirements.txt
uv pip install -e .
```

### Usage


```bash

# Get a summary of activity in the current directory

uv run saruca summary --path .



# Export sessions to Parquet for external analysis

uv run saruca export --path . --output messages.parquet



# Export log entries to Parquet

uv run saruca export-logs --path . --output logs.parquet

```



### Utility Scripts



- **`./sync_logs.sh`**: Syncs logs from the default Gemini CLI temporary directory (`~/.gemini/tmp/`) to the local `.gemini-tmp/` directory, excluding unnecessary files.

- **`./export_unified.sh`**: Automatically exports all discovered sessions and logs from `.gemini-tmp/` into unified `sessions_unified.parquet` and `logs_unified.parquet` files.



## Exploration



The project includes several tools for data exploration:



- **`analysis_notebook.py`**: An interactive [marimo](https://marimo.io/) notebook for visualizing message types and activity over time.

- **`explore_data.py`**: A script to quickly preview data summaries, including detailed token usage analysis by model.

- **`dig_into_data.py`**: A utility for diving into the actual content of conversations within specific sessions.
