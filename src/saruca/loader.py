import polars as pl
import orjson
import glob
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
            
            content = d.get("content")
            if isinstance(content, dict):
                d["content_raw"] = orjson.dumps(content).decode()
                d["content_summary"] = str(content.get("output", d["content_raw"]))[:200]
            else:
                d["content_raw"] = str(content)
                d["content_summary"] = str(content)[:200]

            if d.get("tokens"):
                for k, v in d["tokens"].items():
                    if v is not None:
                        d[f"tokens_{k}"] = v
            
            if d.get("thoughts"):
                d["thoughts_text"] = " ".join([t["thought"] for t in d["thoughts"] if t.get("thought")])
            
            all_msgs.append(d)
            
    for msg in all_msgs:
        for k, v in list(msg.items()):
            if isinstance(v, (dict, list)):
                msg[k] = orjson.dumps(v).decode()
                
    return pl.from_dicts(all_msgs)

def extract_tool_calls(sessions: List[Session]) -> pl.DataFrame:
    calls = []
    for s in sessions:
        for m in s.messages:
            if m.toolCalls:
                for tc in m.toolCalls:
                    d = tc.model_dump()
                    d["sessionId"] = s.sessionId
                    d["messageId"] = m.id
                    d["timestamp"] = m.timestamp
                    
                    # Flatten args
                    if d.get("args"):
                        for k, v in d["args"].items():
                            if not isinstance(v, (dict, list)):
                                d[f"arg_{k}"] = v
                            else:
                                d[f"arg_{k}"] = orjson.dumps(v).decode()
                    
                    # Handle output
                    if d.get("output"):
                        if isinstance(d["output"], (dict, list)):
                            d["output_raw"] = orjson.dumps(d["output"]).decode()
                        else:
                            d["output_raw"] = str(d["output"])
                    
                    calls.append(d)
                    
    # Normalize for Polars
    for call in calls:
        for k, v in list(call.items()):
            if isinstance(v, (dict, list)):
                call[k] = orjson.dumps(v).decode()

    if not calls:
        return pl.DataFrame()

    return pl.from_dicts(calls)
