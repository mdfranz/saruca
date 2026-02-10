import polars as pl
import saruca
import os
import sys

def analyze():
    sys.path.append(os.getcwd())
    
    _, session_files = saruca.discover_files(".")
    sessions = saruca.load_sessions(session_files)
    tools_df = saruca.extract_tool_calls(sessions)
    
    if len(tools_df) == 0:
        print("No tool calls found in the data.")
        return

    print(f"Total tool calls: {len(tools_df)}")
    
    print("\n--- Most Used Tools ---")
    print(tools_df["name"].value_counts())
    
    print("\n--- Sample Tool Calls ---")
    sample_cols = ["name", "timestamp"]
    arg_cols = [c for c in tools_df.columns if c.startswith("arg_")]
    # Limit number of columns to prevent display mess
    display_cols = sample_cols + arg_cols[:min(3, len(arg_cols))]
    
    print(tools_df.select(display_cols).head(10))

if __name__ == "__main__":
    analyze()