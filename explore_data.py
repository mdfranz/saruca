import polars as pl
import orjson
import glob
import os
from pathlib import Path
import saruca

def load_logs():
    log_files, _ = saruca.discover_files(".")
    logs = saruca.load_log_entries(log_files)
    if not logs:
        return pl.DataFrame()
    return saruca.to_polars_logs(logs)

def load_sessions():
    _, session_files = saruca.discover_files(".")
    sessions = saruca.load_sessions(session_files)
    if not sessions:
        return pl.DataFrame()
    return saruca.to_polars_messages(sessions)

if __name__ == "__main__":
    logs_df = load_logs()
    print("Logs DataFrame Summary:")
    if not logs_df.is_empty():
        print(logs_df.head())
        print(logs_df.schema)
    else:
        print("No logs found.")
    
    sessions_df = load_sessions()
    print("\nSessions DataFrame Summary:")
    if not sessions_df.is_empty():
        print(sessions_df.head())
        print(sessions_df.schema)
    else:
        print("No sessions found.")

    # Basic Analysis
    if not sessions_df.is_empty():
        print("\nMessage types count in sessions:")
        if "type" in sessions_df.columns:
            print(sessions_df["type"].value_counts())
        
        print("\nSessions per project:")
        if "projectHash" in sessions_df.columns:
            print(sessions_df["projectHash"].value_counts())
