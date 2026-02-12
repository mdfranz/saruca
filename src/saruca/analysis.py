import polars as pl
import asyncio
import orjson
import logging
from datetime import datetime
from saruca.models import Session, Message, TokenUsage
from saruca import summarizer

logger = logging.getLogger(__name__)

def load_parquet_safe(file_path):
    try:
        return pl.read_parquet(file_path)
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return None

def print_header(title):
    print(f"\n{'='*len(title)}")
    print(title)
    print(f"{'='*len(title)}")

def reconstruct_session(df, session_id):
    """Reconstructs a Session object from the messages DataFrame for a specific session_id."""
    session_rows = df.filter(pl.col("sessionId") == session_id).sort("timestamp")
    if session_rows.is_empty():
        return None

    rows = session_rows.to_dicts()
    messages = []
    
    for r in rows:
        # Handle content
        content = r.get("content_raw")
        if content:
            try:
                content = orjson.loads(content)
            except:
                pass # keep as string
        else:
            content = r.get("content", "")

        # Handle timestamp
        ts = r.get("timestamp")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except:
                ts = datetime.now() # Fallback

        # Handle tokens
        tokens = None
        if "tokens_total" in r and r["tokens_total"] is not None:
            # Construct minimal TokenUsage if columns exist
            tokens = TokenUsage(total=r["tokens_total"])

        msg = Message(
            id=str(r.get("id", "")),
            timestamp=ts,
            type=r.get("type", "unknown"),
            content=content,
            tokens=tokens
        )
        messages.append(msg)

    if not messages:
        return None

    first_ts = messages[0].timestamp
    last_ts = messages[-1].timestamp
    project_hash = rows[0].get("projectHash", "unknown")

    return Session(
        sessionId=session_id,
        projectHash=project_hash,
        startTime=first_ts,
        lastUpdated=last_ts,
        messages=messages
    )

async def get_session_title(df, session_id):
    session = reconstruct_session(df, session_id)
    if not session:
        return "N/A (Not found)"
    
    try:
        summary = await summarizer.summarize_session(session)
        return summary.title
    except Exception as e:
        logger.error(f"Error summarizing session {session_id}: {e}")
        return f"Error: {e}"

def analyze_general_stats(files):
    print_header("General Statistics")
    for name, df in files.items():
        if df is not None:
            print(f"{name}: {len(df)} rows")
            if "timestamp" in df.columns:
                try:
                    if df["timestamp"].dtype == pl.Utf8:
                        ts = df["timestamp"].str.to_datetime(strict=False)
                        min_ts = ts.min()
                        max_ts = ts.max()
                        print(f"  Range: {min_ts} to {max_ts}")
                    else:
                        min_ts = df["timestamp"].min()
                        max_ts = df["timestamp"].max()
                        print(f"  Range: {min_ts} to {max_ts}")
                except Exception as e:
                    print(f"  Could not determine time range: {e}")

async def analyze_sessions(messages_df):
    if messages_df is None: 
        return

    print_header("Session Analysis")
    
    # Ensure timestamp is datetime if needed
    if messages_df["timestamp"].dtype == pl.Utf8:
         messages_df = messages_df.with_columns(pl.col("timestamp").str.to_datetime(strict=False))

    group_cols = ["sessionId"]
    if "projectHash" in messages_df.columns:
        group_cols.append("projectHash")

    session_stats = messages_df.group_by(group_cols).agg([
        pl.count("id").alias("message_count"),
        pl.col("timestamp").min().alias("start_time"),
        pl.col("timestamp").max().alias("end_time"),
        pl.col("tokens_total").sum().alias("total_tokens")
    ]).with_columns(
        (pl.col("end_time") - pl.col("start_time")).alias("duration")
    )

    print(f"Total Sessions: {len(session_stats)}")
    print(f"Avg Messages per Session: {session_stats['message_count'].mean():.2f}")
    
    if "total_tokens" in session_stats.columns and session_stats["total_tokens"].sum() is not None:
        print(f"Avg Tokens per Session: {session_stats['total_tokens'].mean():.2f}")
        print(f"Total Tokens Consumed: {session_stats['total_tokens'].sum()}")

    print("\nTop 5 Longest Sessions (by message count) with AI Summaries:")
    top_sessions = session_stats.sort("message_count", descending=True).head(5)
    
    print(f"{'Session ID':<36} | {'Msgs':<5} | {'Duration':<15} | {'Project':<10} | {'Title'}")
    print("-" * 120)

    for row in top_sessions.iter_rows(named=True):
        sid = row['sessionId']
        msgs = row['message_count']
        dur = str(row['duration'])
        proj = row.get('projectHash', 'N/A')[:8] + ".." if row.get('projectHash') else "N/A"
        
        title = await get_session_title(messages_df, sid)
        
        print(f"{sid:<36} | {msgs:<5} | {dur:<15} | {proj:<10} | {title}")


async def analyze_projects(messages_df):
    if messages_df is None:
        return

    print_header("Project Analysis")

    if "projectHash" not in messages_df.columns:
        print("No projectHash column found in messages.")
        return

    # Ensure timestamp is datetime
    if messages_df["timestamp"].dtype == pl.Utf8:
         messages_df = messages_df.with_columns(pl.col("timestamp").str.to_datetime(strict=False))

    project_stats = messages_df.group_by("projectHash").agg([
        pl.col("sessionId").n_unique().alias("session_count"),
        pl.count("id").alias("message_count"),
        pl.col("timestamp").min().alias("first_seen"),
        pl.col("timestamp").max().alias("last_seen"),
        pl.col("tokens_total").sum().alias("total_tokens")
    ])

    print(f"Total Projects: {len(project_stats)}")
    
    print("\nTop 5 Projects by Session Count (Identifying by latest session):")
    top_projects = project_stats.sort("session_count", descending=True).head(5)
    
    print(f"{'Project Hash':<20} | {'Sess':<4} | {'Msgs':<5} | {'Latest Session Title'}")
    print("-" * 100)

    for row in top_projects.iter_rows(named=True):
        phash = row['projectHash']
        sess_count = row['session_count']
        msg_count = row['message_count']
        
        proj_messages = messages_df.filter(pl.col("projectHash") == phash)
        latest_session_id = proj_messages.sort("timestamp", descending=True).select("sessionId").head(1).item()
        
        title = await get_session_title(messages_df, latest_session_id)
        
        print(f"{phash[:18]}.. | {sess_count:<4} | {msg_count:<5} | {title}")

    if "total_tokens" in project_stats.columns and project_stats["total_tokens"].sum() is not None:
         print("\nTop 5 Projects by Token Usage:")
         print(project_stats.sort("total_tokens", descending=True).head(5).select(
            ["projectHash", "session_count", "total_tokens"]
         ))

def analyze_tools(tool_calls_df):
    if tool_calls_df is None:
        return

    print_header("Tool Usage Analysis")
    
    print("Top 10 Used Tools:")
    print(tool_calls_df["name"].value_counts().sort("count", descending=True).head(10))

    if "status" in tool_calls_df.columns:
        print("\nTool Status Breakdown:")
        print(tool_calls_df["status"].value_counts())

def analyze_thoughts(thoughts_df):
    if thoughts_df is None:
        return

    print_header("Thought Patterns")
    
    if "subject" in thoughts_df.columns:
        print("Top 10 Thought Subjects:")
        print(thoughts_df["subject"].value_counts().sort("count", descending=True).head(10))

async def run_analysis(path=".", prefix=""):
    import os
    
    file_map = {
        "chat_logs": f"{prefix}chat_logs.parquet",
        "logs": f"{prefix}logs.parquet",
        "messages": f"{prefix}messages.parquet",
        "thoughts": f"{prefix}thoughts.parquet",
        "tool_calls": f"{prefix}tool_calls.parquet",
    }
    
    files = {}
    any_found = False
    for name, filename in file_map.items():
        file_path = os.path.join(path, filename)
        if os.path.exists(file_path):
            files[name] = load_parquet_safe(file_path)
            any_found = True
        else:
            files[name] = None
            
    if not any_found:
        raise FileNotFoundError(f"No parquet files found in {path} with prefix '{prefix}'")

    analyze_general_stats(files)
    await analyze_sessions(files["messages"])
    await analyze_projects(files["messages"])
    analyze_tools(files["tool_calls"])
    analyze_thoughts(files["thoughts"])
