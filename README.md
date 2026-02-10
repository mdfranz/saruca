# saruca

Gemini CLI Log & Session Analyzer.

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
pip install -r requirements.txt
```

### Usage

```bash
# Get a summary of activity in the current directory
python -m saruca.cli summary --path .

# Export sessions to Parquet for external analysis
python -m saruca.cli export --path . --output messages.parquet
```

## Exploration

The project includes `analysis_notebook.py` which can be run with [marimo](https://marimo.io/) for interactive data exploration.