import asyncio
import xml.dom.minidom
import logging

import click
import orjson
import polars as pl

from saruca import (
    discover_files,
    extract_thoughts,
    extract_tool_calls,
    load_log_entries,
    load_sessions,
    load_tool_outputs,
    to_polars_logs,
    to_polars_messages,
)
from saruca.log_config import setup_logging

from .summarizer import summarize_session

logger = logging.getLogger(__name__)


@click.group()
def main():
    """Saruca: Gemini CLI Log Analyzer"""
    setup_logging()
    pass


@main.command(name="summarize")
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--project", required=True, help="Filter by project hash")
def summarize_cmd(path, project):
    """Use AI to summarize sessions for a specific project."""
    logger.info(f"Command: summarize, Path: {path}, Project: {project}")
    log_files, session_files = discover_files(path)
    if not session_files:
        logger.warning("No sessions found.")
        click.echo("No sessions found.")
        return

    sessions = [
        s for s in load_sessions(session_files) if s.projectHash.startswith(project)
    ]
    if not sessions:
        logger.warning(f"No sessions found for project: {project}")
        click.echo(f"No sessions found for project: {project}")
        return

    async def run_summaries():
        for s in sessions:
            click.echo(f"\nSummarizing Session: {s.sessionId}")
            logger.info(f"Summarizing Session: {s.sessionId}")
            duration = s.lastUpdated - s.startTime
            click.echo(f"Start Time: {s.startTime.strftime('%Y-%m-%d %H:%M:%S')}")
            click.echo(f"End Time: {s.lastUpdated.strftime('%Y-%m-%d %H:%M:%S')}\nDuration: {duration}")
            
            try:
                summary = await summarize_session(s)
                click.echo(f"Title: {summary.title}")
                click.echo("Key Points:")
                for pt in summary.key_points:
                    click.echo(f"  - {pt}")
                click.echo(f"Outcome: {summary.outcome}")
                click.echo("-" * 40)
            except Exception as e:
                logger.error(f"Failed to summarize session {s.sessionId}: {e}")
                click.echo(f"Failed to summarize session: {e}")

    asyncio.run(run_summaries())


@main.command(name="list")
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--verbose", is_flag=True, help="Include full conversation history")
@click.option("--project", help="Filter by project hash (prefix matches)")
@click.option(
    "--all", "all_projects", is_flag=True, help="List all projects, not just top 5"
)
@click.option("--thought", "show_thoughts", is_flag=True, help="Show model thoughts")
def list_sessions(path, verbose, project, all_projects, show_thoughts):
    """List sessions and show a detailed summary."""
    logger.info(f"Command: list, Path: {path}, Verbose: {verbose}, Project: {project}, All: {all_projects}")
    _list_sessions_impl(path, verbose, project, all_projects, show_thoughts)


def _recursive_parse_json(obj):
    """Recursively parse strings that look like JSON or XML."""
    if isinstance(obj, dict):
        return {k: _recursive_parse_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_recursive_parse_json(i) for i in obj]
    elif isinstance(obj, str):
        trimmed = obj.strip()
        if trimmed.startswith(("{", "[")):
            try:
                parsed = orjson.loads(obj)
                return _recursive_parse_json(parsed)
            except Exception:
                return obj
        # Check for XML-like strings
        elif trimmed.startswith("<") and trimmed.endswith(">"):
            try:
                # Basic check to avoid parsing simple text as XML
                if "<" in trimmed and ">" in trimmed:
                    dom = xml.dom.minidom.parseString(obj)
                    pretty_xml = dom.toprettyxml()
                    # Remove the xml declaration if it was added and wasn't there (optional, but cleaner)
                    if pretty_xml.startswith("<?xml"):
                        pretty_xml = pretty_xml.split("\n", 1)[1]
                    return f"XML_CONTENT:\n{pretty_xml.strip()}"
            except Exception:
                pass
            return obj
        return obj
    else:
        return obj


def _list_sessions_impl(
    path, verbose, project, all_projects=False, show_thoughts=False
):
    """Internal implementation for listing and summarizing sessions."""
    log_files, session_files = discover_files(path)

    click.echo(
        f"\nFound {len(log_files)} log files and {len(session_files)} session files."
    )

    if not session_files:
        click.echo("No sessions found.")
        return

    sessions = load_sessions(session_files)

    if project:
        sessions = [s for s in sessions if s.projectHash.startswith(project)]
        if not sessions:
            click.echo(f"No sessions found for project: {project}")
            return

    # Sort sessions by start time
    sessions.sort(key=lambda s: s.startTime)

    messages_df = to_polars_messages(sessions)

    if messages_df.is_empty():
        click.echo("Sessions found but no messages parsed.")
        return

    # --- Time Range ---
    if "timestamp" in messages_df.columns:
        # Convert string timestamp to datetime if needed, though models say it's datetime
        # Polars from_dicts usually handles datetime objects well.
        min_time = messages_df["timestamp"].min()
        max_time = messages_df["timestamp"].max()
        duration = max_time - min_time if min_time and max_time else "N/A"
        click.echo(f"\nActivity Range: {min_time} to {max_time} ({duration})")

    # --- Token Usage ---
    click.echo("\n--- Token Usage ---")
    token_cols = [c for c in messages_df.columns if c.startswith("tokens_")]
    if token_cols:
        token_stats = messages_df.select([pl.col(c).sum() for c in token_cols])
        for col in token_cols:
            val = token_stats[col][0]
            if val is not None and val > 0:
                click.echo(f"  {col.replace('tokens_', '').capitalize()}: {val:,}")
    else:
        click.echo("  No token usage data found.")

    # --- Model Breakdown ---
    if "model" in messages_df.columns:
        click.echo("\n--- Models Used ---")
        # Filter out rows where model is null (e.g. user messages, info, error)
        model_counts = (
            messages_df.filter(pl.col("model").is_not_null())
            .group_by("model")
            .len()
            .sort("len", descending=True)
        )
        for row in model_counts.iter_rows():
            model_name = row[0]
            count = row[1]
            click.echo(f"  {model_name}: {count:,} messages")

    # --- Tool Usage ---
    tool_calls_df = extract_tool_calls(sessions)
    if not tool_calls_df.is_empty():
        if all_projects:
            click.echo("\n--- All Tools ---")
            top_tools = (
                tool_calls_df["name"].value_counts().sort("count", descending=True)
            )
        else:
            click.echo("\n--- Top Tools ---")
            top_tools = (
                tool_calls_df["name"]
                .value_counts()
                .sort("count", descending=True)
                .head(5)
            )

        for row in top_tools.iter_rows():
            click.echo(f"  {row[0]}: {row[1]:,} calls")

    # --- Top Projects ---
    if all_projects:
        click.echo(click.style("\n--- All Projects (Sorted by Date) ---", bold=True))
    else:
        click.echo(click.style("\n--- Recent Projects ---", bold=True))

    # Calculate stats
    project_stats = messages_df.group_by("projectHash").agg(
        [pl.len().alias("count"), pl.col("timestamp").max().alias("last_activity")]
    )

    # Extract descriptions (first user message)
    descriptions = (
        messages_df.filter(pl.col("type") == "user")
        .sort("timestamp")
        .group_by("projectHash")
        .agg(pl.col("content_raw").first().alias("description"))
    )

    # Join and sort
    top_projects_df = project_stats.join(
        descriptions, on="projectHash", how="left"
    ).sort("last_activity", descending=True)

    if not all_projects:
        top_projects_df = top_projects_df.head(5)

    for row in top_projects_df.iter_rows(named=True):
        p_hash = row["projectHash"]
        count = row["count"]
        last_act = row["last_activity"]
        desc = row["description"]

        # Clean up description
        if desc:
            # Remove newlines and truncate
            clean_desc = desc.replace("\n", " ").replace("\r", "")[:80]
            if len(desc) > 80:
                clean_desc += "..."
        else:
            clean_desc = "No user prompts found"

        date_str = last_act.strftime("%Y-%m-%d %H:%M") if last_act else "N/A"
        click.echo(f"  {date_str} | {p_hash[:12]}... : {count:4d} msgs | {clean_desc}")

    if verbose or show_thoughts:
        click.echo("\n--- Full Conversation History ---")
        for s in sessions:
            click.echo(f"\nSession: {s.sessionId}")
            click.echo(f"Project: {s.projectHash}")
            click.echo(f"Start Time: {s.startTime}")
            click.echo("-" * 60)

            # Sort messages by timestamp
            sorted_messages = sorted(s.messages, key=lambda m: m.timestamp)

            for m in sorted_messages:
                role = "USER" if m.type == "user" else "MODEL"

                if verbose:
                    click.echo(f"[{m.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {role}:")

                    if isinstance(m.content, str):
                        click.echo(m.content)
                    else:
                        click.echo(
                            orjson.dumps(m.content, option=orjson.OPT_INDENT_2).decode()
                        )

                if show_thoughts and m.thoughts:
                    for t in m.thoughts:
                        thought_text = t.thought or t.description
                        if thought_text:
                            if t.subject:
                                thought_text = f"[{t.subject}] {thought_text}"

                            click.echo(f"\nTHOUGHT: {thought_text}")

                if verbose and m.toolCalls:
                    for tc in m.toolCalls:
                        click.echo(f"\nTOOL CALL: {tc.name}")
                        if tc.args:
                            cleaned_args = _recursive_parse_json(tc.args)
                            args_json = orjson.dumps(
                                cleaned_args, option=orjson.OPT_INDENT_2
                            ).decode()
                            click.echo(f"Args: {args_json}")
                        if tc.result:
                            out_val = tc.result

                            # Try to parse string output as JSON for better display
                            if isinstance(out_val, str):
                                trimmed_val = out_val.strip()
                                if trimmed_val.startswith("<") and trimmed_val.endswith(
                                    ">"
                                ):
                                    click.echo(f"XML Output:\n{out_val}")
                                    continue

                                try:
                                    parsed = orjson.loads(out_val)
                                    out_val = parsed
                                except Exception:
                                    pass

                            # Recursively parse any nested JSON in the structure
                            out_val = _recursive_parse_json(out_val)

                            if not isinstance(out_val, str):
                                out_val = orjson.dumps(
                                    out_val, option=orjson.OPT_INDENT_2
                                ).decode()
                            click.echo(f"Output: {out_val}")

                if verbose:
                    click.echo("")
            click.echo("=" * 60)


@main.command(name="export")
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--prefix", default="", help="Prefix for output parquet files")
def export_all(path, prefix):
    """Export all metadata tables to parquet (messages, logs, tool_calls, thoughts, outputs)."""
    # Import lazily to avoid hard dependency errors on startup.
    try:
        from .extract_data import collect_chat_logs, collect_security_events
    except ModuleNotFoundError:
        collect_chat_logs = None
        collect_security_events = None

    log_files, session_files = discover_files(path)

    # 1. Logs
    logs = load_log_entries(log_files)
    if logs:
        df_logs = to_polars_logs(logs)
        df_logs.write_parquet(f"{prefix}logs.parquet")
        click.echo(f"Saved {prefix}logs.parquet ({len(df_logs)} rows)")

    # 2. Sessions
    sessions = load_sessions(session_files)
    if sessions:
        df_messages = to_polars_messages(sessions)
        df_messages.write_parquet(f"{prefix}messages.parquet")
        click.echo(f"Saved {prefix}messages.parquet ({len(df_messages)} rows)")

        df_tool_calls = extract_tool_calls(sessions)
        if not df_tool_calls.is_empty():
            df_tool_calls.write_parquet(f"{prefix}tool_calls.parquet")
            click.echo(f"Saved {prefix}tool_calls.parquet ({len(df_tool_calls)} rows)")

        df_thoughts = extract_thoughts(sessions)
        if not df_thoughts.is_empty():
            df_thoughts.write_parquet(f"{prefix}thoughts.parquet")
            click.echo(f"Saved {prefix}thoughts.parquet ({len(df_thoughts)} rows)")

    # 3. Tool Outputs
    df_outputs = load_tool_outputs(path)
    if not df_outputs.is_empty():
        df_outputs.write_parquet(f"{prefix}tool_outputs.parquet")
        click.echo(f"Saved {prefix}tool_outputs.parquet ({len(df_outputs)} rows)")

    # 4. Security Events (from tool outputs / event files)
    if collect_security_events:
        df_events = collect_security_events(root_dir=path)
        if not df_events.is_empty():
            df_events.write_parquet(f"{prefix}security_events.parquet")
            click.echo(f"Saved {prefix}security_events.parquet ({len(df_events)} rows)")
    else:
        click.echo("Skipping security events: extract_data module not available.")

    # 5. Chat Logs (redundant with logs, but includes _project_hash metadata)
    if collect_chat_logs:
        df_chat_logs = collect_chat_logs(root_dir=path)
        if not df_chat_logs.is_empty():
            df_chat_logs.write_parquet(f"{prefix}chat_logs.parquet")
            click.echo(f"Saved {prefix}chat_logs.parquet ({len(df_chat_logs)} rows)")
    else:
        click.echo("Skipping chat logs: extract_data module not available.")


if __name__ == "__main__":
    main()
