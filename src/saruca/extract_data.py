import glob
import os
from pathlib import Path

import orjson
import polars as pl


def collect_security_events(root_dir: str = "."):
    """
    Discovers and loads security event files.
    Looks for:
    - search_security_events_*.txt
    - search_udm_*.txt
    - *_events.json
    """
    patterns = [
        "**/search_security_events_*.txt",
        "**/search_udm_*.txt",
        "**/*_events.json",
    ]

    all_files = []
    for p in patterns:
        all_files.extend(glob.glob(os.path.join(root_dir, p), recursive=True))

    # Also check .gemini-tmp specifically
    gemini_tmp = os.path.join(root_dir, ".gemini-tmp")
    if os.path.exists(gemini_tmp):
        for p in patterns:
            all_files.extend(glob.glob(os.path.join(gemini_tmp, p), recursive=True))

    events = []
    for f in set(all_files):
        # Skip directories if glob picked them up
        if not os.path.isfile(f):
            continue
            
        try:
            with open(f, "rb") as f_in:
                content = f_in.read().strip()
                if not content:
                    continue

                # Try to parse as JSON
                data = orjson.loads(content)
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item["source_file"] = f
                            events.append(item)
                elif isinstance(data, dict):
                    data["source_file"] = f
                    events.append(data)
        except Exception:
            # Not a valid JSON or other error, skip
            pass

    if not events:
        return pl.DataFrame()

    # Flatten nested dicts/lists for Polars compatibility
    flattened = []
    for e in events:
        d = e.copy()
        for k, v in list(d.items()):
            if isinstance(v, (dict, list)):
                d[k] = orjson.dumps(v).decode()
        flattened.append(d)

    return pl.from_dicts(flattened)


def collect_chat_logs(root_dir: str = "."):
    """
    Collects logs from all logs.json files and attempts to associate them with a project hash.
    """
    log_files = glob.glob(os.path.join(root_dir, "**/logs.json"), recursive=True)

    gemini_tmp = os.path.join(root_dir, ".gemini-tmp")
    if os.path.exists(gemini_tmp):
        log_files.extend(
            glob.glob(os.path.join(gemini_tmp, "**/logs.json"), recursive=True)
        )

    all_logs = []
    for f in set(log_files):
        if not os.path.isfile(f):
            continue
            
        try:
            # Try to extract project hash from path (64-character hex string)
            project_hash = None
            path_parts = Path(f).parts
            for part in path_parts:
                if len(part) == 64:
                    project_hash = part
                    break

            with open(f, "rb") as f_in:
                data = orjson.loads(f_in.read())
                if isinstance(data, list):
                    for item in data:
                        if isinstance(item, dict):
                            item["source_file"] = f
                            item["_project_hash"] = project_hash
                            all_logs.append(item)
        except Exception:
            pass

    if not all_logs:
        return pl.DataFrame()

    # Flatten nested dicts/lists
    flattened = []
    for log in all_logs:
        d = log.copy()
        for k, v in list(d.items()):
            if isinstance(v, (dict, list)):
                d[k] = orjson.dumps(v).decode()
        flattened.append(d)

    return pl.from_dicts(flattened)
