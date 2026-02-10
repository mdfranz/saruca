import polars as pl
import orjson
import glob
import os
from pathlib import Path
from typing import List, Iterable, Any, Dict
from .models import Session, LogEntry, Message

def discover_files(root_dir: str = "."):
    logs = glob.glob(f"{root_dir}/**/logs.json", recursive=True)
    sessions = glob.glob(f"{root_dir}/**/chats/*.json", recursive=True)
    
    # Also search specifically in .gemini-tmp if it exists, as glob doesn't always follow hidden dirs
    gemini_tmp = Path(root_dir) / ".gemini-tmp"
    if gemini_tmp.exists():
        logs.extend(glob.glob(f"{gemini_tmp}/**/logs.json", recursive=True))
        sessions.extend(glob.glob(f"{gemini_tmp}/**/chats/*.json", recursive=True))
        
    return list(set(logs)), list(set(sessions))

def load_log_entries(files: Iterable[str]) -> List[LogEntry]:
    entries = []
    for f in files:
        with open(f, "rb") as f_in:
            data = orjson.loads(f_in.read())
            for item in data:
                item["source_file"] = f
                entries.append(LogEntry(**item))
    return entries

def load_sessions(files: Iterable[str]) -> List[Session]:
    sessions = []
    for f in files:
        try:
            with open(f, "rb") as f_in:
                data = orjson.loads(f_in.read())
                sessions.append(Session(**data))
        except Exception as e:
            print(f"Error loading session {f}: {e}")
    return sessions

def to_polars_logs(entries: List[LogEntry]) -> pl.DataFrame:
    return pl.from_dicts([e.model_dump() for e in entries])

def to_polars_messages(sessions: List[Session]) -> pl.DataFrame:
    all_msgs = []
    for s in sessions:
        for m in s.messages:
            d = m.model_dump()
            d["sessionId"] = s.sessionId
            d["projectHash"] = s.projectHash
            d["startTime"] = s.startTime
            
            content = d.get("content")
            if isinstance(content, dict):
                d["content_raw"] = orjson.dumps(content).decode()
                # Try to extract a meaningful summary from different dict structures
                if "output" in content:
                    d["content_summary"] = str(content["output"])[:200]
                elif "message" in content:
                    d["content_summary"] = str(content["message"])[:200]
                else:
                    d["content_summary"] = d["content_raw"][:200]
            else:
                d["content_raw"] = str(content)
                d["content_summary"] = str(content)[:200]

            if d.get("tokens"):
                for k, v in d["tokens"].items():
                    if v is not None:
                        d[f"tokens_{k}"] = v
            
            if d.get("thoughts"):
                # Actual sessions use 'description' instead of 'thought' often
                d["thoughts_text"] = " ".join([
                    t.get("description") or t.get("thought") or "" 
                    for t in d["thoughts"]
                ])
                d["thought_count"] = len(d["thoughts"])
            
            if d.get("toolCalls"):
                d["tool_call_count"] = len(d["toolCalls"])
            
            all_msgs.append(d)
            
    for msg in all_msgs:
        for k, v in list(msg.items()):
            if isinstance(v, (dict, list)):
                msg[k] = orjson.dumps(v).decode()
                
    return pl.from_dicts(all_msgs)

def extract_thoughts(sessions: List[Session]) -> pl.DataFrame:
    thoughts = []
    for s in sessions:
        for m in s.messages:
            if m.thoughts:
                for t in m.thoughts:
                    d = t.model_dump()
                    d["sessionId"] = s.sessionId
                    d["messageId"] = m.id
                    d["messageTimestamp"] = m.timestamp
                    d["projectHash"] = s.projectHash
                    thoughts.append(d)
                    
    if not thoughts:
        return pl.DataFrame()
        
    return pl.from_dicts(thoughts)

def extract_tool_calls(sessions: List[Session]) -> pl.DataFrame:
    calls = []
    for s in sessions:
        for m in s.messages:
            if m.toolCalls:
                for tc in m.toolCalls:
                    d = tc.model_dump()
                    d["sessionId"] = s.sessionId
                    d["messageId"] = m.id
                    d["messageTimestamp"] = m.timestamp
                    d["projectHash"] = s.projectHash
                    
                    # Flatten args
                    if d.get("args"):
                        for k, v in d["args"].items():
                            if not isinstance(v, (dict, list)):
                                d[f"arg_{k}"] = v
                            else:
                                d[f"arg_{k}"] = orjson.dumps(v).decode()
                    
                    # Handle result
                    if d.get("result"):
                        # Usually a list of dicts with functionResponse
                        d["result_raw"] = orjson.dumps(d["result"]).decode()
                    
                    calls.append(d)
                    
    # Normalize for Polars
    for call in calls:
        for k, v in list(call.items()):
            if isinstance(v, (dict, list)):
                call[k] = orjson.dumps(v).decode()

    if not calls:
        return pl.DataFrame()

    return pl.from_dicts(calls)

def load_tool_outputs(root_dir: str = ".") -> pl.DataFrame:

    """Discovers and loads tool output .txt files that contain JSON."""

    txt_files = glob.glob(f"{root_dir}/**/*.txt", recursive=True)

    

    gemini_tmp = Path(root_dir) / ".gemini-tmp"

    if gemini_tmp.exists():

        txt_files.extend(glob.glob(f"{gemini_tmp}/**/*.txt", recursive=True))



    all_outputs = []

    for f in set(txt_files):

        # Skip very large files to avoid OOM or slow processing

        if os.path.getsize(f) > 10 * 1024 * 1024: # 10MB limit

            continue

            

        try:

            with open(f, "rb") as f_in:

                content = f_in.read().strip()

                if content.startswith(b"{") and content.endswith(b"}"):

                    data = orjson.loads(content)

                    if not isinstance(data, dict):

                        continue

                        

                    data["source_file"] = f

                    data["tool_name"] = Path(f).name.rsplit("_", 1)[0]

                    

                    # Extract project hash from path if possible

                    path_parts = Path(f).parts

                    for part in path_parts:

                        if len(part) == 64: # Likely a hash

                            data["projectHash"] = part

                            break

                    all_outputs.append(data)

        except Exception:

            pass

            

    if not all_outputs:

        return pl.DataFrame()

        

    # Flatten outputs for Polars

    # Since different tools have different schemas, we might have many nulls

    # or need to be careful with column types.

    flattened = []

    for out in all_outputs:

        d = out.copy()

        for k, v in list(d.items()):

            if isinstance(v, (dict, list)):

                d[k] = orjson.dumps(v).decode()

        flattened.append(d)

        

    return pl.from_dicts(flattened)
