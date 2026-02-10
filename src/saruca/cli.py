import click
import polars as pl
import orjson
import asyncio
from saruca import discover_files, load_log_entries, load_sessions, to_polars_logs, to_polars_messages, extract_tool_calls
from .summarizer import summarize_session

@click.group()
def main():
    """Saruca: Gemini CLI Log Analyzer"""
    pass

@main.command(name="summarize")
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--project", required=True, help="Filter by project hash")
def summarize_cmd(path, project):
    """Use AI to summarize sessions for a specific project."""
    log_files, session_files = discover_files(path)
    if not session_files:
        click.echo("No sessions found.")
        return

    sessions = [s for s in load_sessions(session_files) if s.projectHash.startswith(project)]
    if not sessions:
        click.echo(f"No sessions found for project: {project}")
        return

    async def run_summaries():
        for s in sessions:
            click.echo(click.style(f"\nSummarizing Session: {s.sessionId}", bold=True, fg="cyan"))
            summary = await summarize_session(s)
            click.echo(click.style(f"Title: {summary.title}", bold=True))
            click.echo("Key Points:")
            for pt in summary.key_points:
                click.echo(f"  - {pt}")
            click.echo(f"Outcome: {summary.outcome}")
            click.echo("-" * 40)

    asyncio.run(run_summaries())

@main.command(name="list")
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--verbose", is_flag=True, help="Include full conversation history")
@click.option("--project", help="Filter by project hash (prefix matches)")
@click.option("--all", "all_projects", is_flag=True, help="List all projects, not just top 5")
def list_sessions(path, verbose, project, all_projects):
    """List sessions and show a detailed summary."""
    _list_sessions_impl(path, verbose, project, all_projects)

def _list_sessions_impl(path, verbose, project, all_projects=False):
    """Internal implementation for listing and summarizing sessions."""
    log_files, session_files = discover_files(path)
    
    click.echo(click.style(f"\nFound {len(log_files)} log files and {len(session_files)} session files.", fg="green"))
    
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
    click.echo(click.style("\n--- Token Usage ---", bold=True))
    token_cols = [c for c in messages_df.columns if c.startswith("tokens_")]
    if token_cols:
        token_stats = messages_df.select([pl.col(c).sum() for c in token_cols])
        for col in token_cols:
            val = token_stats[col][0]
            if val is not None:
                click.echo(f"  {col.replace('tokens_', '').capitalize()}: {val:,}")
    else:
        click.echo("  No token usage data found.")

    # --- Model Breakdown ---
    if "model" in messages_df.columns:
        click.echo(click.style("\n--- Models Used ---", bold=True))
        model_counts = messages_df.group_by("model").len().sort("len", descending=True)
        for row in model_counts.iter_rows():
            model_name = row[0] if row[0] else "Unknown"
            count = row[1]
            click.echo(f"  {model_name}: {count:,} messages")

    # --- Tool Usage ---
    tool_calls_df = extract_tool_calls(sessions)
    if not tool_calls_df.is_empty():
        click.echo(click.style("\n--- Top Tools ---", bold=True))
        top_tools = tool_calls_df["name"].value_counts().sort("count", descending=True).head(5)
        for row in top_tools.iter_rows():
            click.echo(f"  {row[0]}: {row[1]:,} calls")
    
    # --- Top Projects ---
    if all_projects:
        click.echo(click.style("\n--- All Projects ---", bold=True))
    else:
        click.echo(click.style("\n--- Top Projects ---", bold=True))
    
    # Calculate counts
    project_counts = messages_df["projectHash"].value_counts().sort("count", descending=True)
    if not all_projects:
        project_counts = project_counts.head(5)
    
    # Extract descriptions (first user message)
    descriptions = (
        messages_df.filter(pl.col("type") == "user")
        .sort("timestamp")
        .group_by("projectHash")
        .agg(pl.col("content_raw").first().alias("description"))
    )
    
    # Join
    top_projects_df = project_counts.join(descriptions, on="projectHash", how="left")
    
    for row in top_projects_df.iter_rows(named=True):
        p_hash = row["projectHash"]
        count = row["count"]
        desc = row["description"]
        
        # Clean up description
        if desc:
            # Remove newlines and truncate
            clean_desc = desc.replace("\n", " ").replace("\r", "")[:80]
            if len(desc) > 80:
                clean_desc += "..."
        else:
            clean_desc = "No user prompts found"
            
        click.echo(f"  {p_hash[:12]}... : {count:4d} msgs | {clean_desc}")

    if verbose:
        click.echo(click.style("\n--- Full Conversation History ---", bold=True))
        for s in sessions:
            click.echo(click.style(f"\nSession: {s.sessionId}", fg="cyan", bold=True))
            click.echo(click.style(f"Project: {s.projectHash}", fg="cyan"))
            click.echo(click.style(f"Start Time: {s.startTime}", fg="cyan", dim=True))
            click.echo(click.style("-" * 60, fg="cyan"))
            
            # Sort messages by timestamp
            sorted_messages = sorted(s.messages, key=lambda m: m.timestamp)
            
            for m in sorted_messages:
                color = "blue" if m.type == "user" else "magenta"
                role = "USER" if m.type == "user" else "MODEL"
                
                click.echo(click.style(f"[{m.timestamp.strftime('%Y-%m-%d %H:%M:%S')}] {role}:", fg=color, bold=True))
                
                if isinstance(m.content, str):
                    click.echo(m.content)
                else:
                    click.echo(orjson.dumps(m.content, option=orjson.OPT_INDENT_2).decode())

                if m.thoughts:
                    for t in m.thoughts:
                        if t.thought:
                            click.echo(click.style(f"\nTHOUGHT: {t.thought}", fg="yellow", dim=True))

                if m.toolCalls:
                    for tc in m.toolCalls:
                        click.echo(click.style(f"\nTOOL CALL: {tc.name}", fg="green", bold=True))
                        if tc.args:
                            args_json = orjson.dumps(tc.args, option=orjson.OPT_INDENT_2).decode()
                            click.echo(click.style(f"Args: {args_json}", fg="green"))
                        if tc.output:
                            out_val = tc.output
                            if not isinstance(out_val, str):
                                out_val = orjson.dumps(out_val, option=orjson.OPT_INDENT_2).decode()
                            click.echo(click.style(f"Output: {out_val}", fg="green", dim=True))
                
                click.echo("")
            click.echo(click.style("=" * 60, fg="cyan"))

@main.command()
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--output", default="messages.parquet", help="Output file")
def export(path, output):
    """Export messages to a parquet file."""
    _, session_files = discover_files(path)
    sessions = load_sessions(session_files)
    df = to_polars_messages(sessions)
    df.write_parquet(output)
    click.echo(f"Exported {len(df)} messages to {output}")

@main.command()
@click.option("--path", default=".", help="Path to search for logs")
@click.option("--output", default="logs.parquet", help="Output file")
def export_logs(path, output):
    """Export log entries to a parquet file."""
    log_files, _ = discover_files(path)
    logs = load_log_entries(log_files)
    df = to_polars_logs(logs)
    df.write_parquet(output)
    click.echo(f"Exported {len(df)} log entries to {output}")

if __name__ == "__main__":
    main()