import click
import polars as pl
from saruca import discover_files, load_log_entries, load_sessions, to_polars_logs, to_polars_messages

@click.group()
def main():
    """Saruca: Gemini CLI Log Analyzer"""
    pass

@main.command()
@click.option("--path", default=".", help="Path to search for logs")
def summary(path):
    """Show a summary of logs and sessions."""
    log_files, session_files = discover_files(path)
    click.echo(f"Found {len(log_files)} log files and {len(session_files)} session files.")
    
    logs = load_log_entries(log_files)
    sessions = load_sessions(session_files)
    
    logs_df = to_polars_logs(logs)
    messages_df = to_polars_messages(sessions)
    
    click.echo("")
    click.echo("--- Message Types ---")
    click.echo(messages_df["type"].value_counts())
    
    click.echo("")
    click.echo("--- Top Projects by Activity ---")
    click.echo(messages_df["projectHash"].value_counts().head(5))

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

if __name__ == "__main__":
    main()