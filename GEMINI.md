## Python Coding Style
- Use Python or `jq` to parse and analyze log files for initial exploration
- For large files preview with hq and head if they are larger than 20MB
- Review existing Python code in the current directory before writing new code to solve problems.
- Use `uv` to create virtual environments and install libraries. Maintain a `requirements.txt` file.
- Use `orjson` instead of the built-in `json` library for better performance.
- Use Python `polars` to convert JSON to parquet if needed.
- Use Python `pandas` for statistical analysis if beneficial.
