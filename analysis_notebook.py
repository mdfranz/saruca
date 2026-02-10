import marimo

__generated_with = "0.19.9"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import saruca
    import os

    return mo, pl, saruca


@app.cell
def _(mo, saruca):
    log_files, session_files = saruca.discover_files(".")
    logs = saruca.load_log_entries(log_files)
    sessions = saruca.load_sessions(session_files)

    logs_df = saruca.to_polars_logs(logs)
    messages_df = saruca.to_polars_messages(sessions)

    mo.md(f"Loaded {len(logs)} log entries and {len(sessions)} sessions.")
    return (messages_df,)


@app.cell
def _(mo):
    mo.md("""
    ## Message Types Distribution
    """)
    return


@app.cell
def _(messages_df):
    type_counts = messages_df["type"].value_counts()
    import plotly.express as px
    fig = px.pie(type_counts.to_pandas(), values="count", names="type", title="Message Types")
    fig
    return


@app.cell
def _(mo):
    mo.md("""
    ## Messages over Time
    """)
    return


@app.cell
def _(pl):
    messages_df = messages_df.with_columns(
        pl.col("timestamp").str.to_datetime()
    )
    daily_activity = messages_df.group_by_day("timestamp").count()
    import plotly.express as px
    fig_time = px.line(daily_activity.to_pandas(), x="timestamp", y="count", title="Daily Activity")
    fig_time
    return (messages_df,)


@app.cell
def _(messages_df, mo):
    selected_type = mo.ui.dropdown(messages_df["type"].unique().to_list(), label="Filter by type")
    selected_type
    return (selected_type,)


@app.cell
def _(messages_df, pl, selected_type):
    filtered_df = messages_df.filter(pl.col("type") == selected_type.value)
    filtered_df.head(20)
    return


if __name__ == "__main__":
    app.run()
