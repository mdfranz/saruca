# Saruca: A Gemini CLI Log & Session Analyzer.

![saruca logo](saruca.png)

Mining log and session data from Gemini CLI using Polars for high-performance analysis.

## Features

- **Discovery:** Automatically find logs and session JSON files in project directories.
- **Analysis:** Detailed summaries including message types, project activity, and token usage.
- **AI Summarization:** Use Gemini models to automatically summarize conversation threads and project outcomes.
- **Export:** Convert nested session data into flat Parquet files for easy processing in other tools.
- **Data-centric:** Built on Polars, Orjson, and Pydantic.

## Requirements

- **Python:** 3.13 or higher.

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

#### Analyze and List Sessions

Get a detailed summary of activity in the current directory, including token usage, model breakdown, and top projects.

```bash
uv run saruca list --path .
```

**Options:**
- `--verbose`: Include full conversation history in the output.
- `--project <hash>`: Filter results by project hash (prefix matching).
- `--all`: List all projects, not just the top 5.

#### AI Summarization

Generate AI-powered summaries for all sessions within a specific project. This requires a Gemini API key (set via environment variable `GEMINI_API_KEY`).

```bash
uv run saruca summarize --path . --project <project_hash>
```

#### Export Data

Export sessions and logs to Parquet for external analysis in tools like Excel, PowerBI, or other Python scripts.

```bash
# Export sessions to Parquet
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

- **`analyze_tools.py`**: A utility specifically for analyzing tool usage and arguments across all sessions.

- **`dig_into_data.py`**: A utility for diving into the actual content of conversations within specific sessions.

