import marimo

__generated_with = "0.19.9"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import polars as pl
    import saruca
    import os
    import altair as alt
    from datetime import datetime
    import asyncio

    return alt, mo, pl, saruca


@app.cell
def _(mo, saruca):
    log_files, session_files = saruca.discover_files(".")
    logs = saruca.load_log_entries(log_files)
    sessions = saruca.load_sessions(session_files)

    logs_df = saruca.to_polars_logs(logs)
    messages_df = saruca.to_polars_messages(sessions)
    thoughts_df = saruca.extract_thoughts(sessions)
    tool_calls_df = saruca.extract_tool_calls(sessions)

    mo.md(f"Loaded {len(logs)} log entries and {len(sessions)} sessions.")
    return logs_df, messages_df, sessions, thoughts_df, tool_calls_df


@app.cell
def _(logs_df, messages_df, mo, sessions, thoughts_df, tool_calls_df):
    mo.hstack(
        [
            mo.stat(label="Sessions", value=len(sessions)),
            mo.stat(label="Messages", value=len(messages_df)),
            mo.stat(label="Log Entries", value=len(logs_df)),
            mo.stat(label="Tool Calls", value=len(tool_calls_df)),
            mo.stat(label="Thoughts", value=len(thoughts_df)),
        ],
        justify="start"
    )
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Message Distribution
    """)
    return


@app.cell
def _(alt, messages_df):
    _type_counts = messages_df["type"].value_counts()

    chart_types = (
        alt.Chart(_type_counts)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta(field="count", type="quantitative"),
            color=alt.Color(field="type", type="nominal"),
            tooltip=["type", "count"]
        )
        .properties(title="Message Types Distribution")
    )
    chart_types
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Session & Project Analysis
    """)
    return


@app.cell
def _(messages_df, mo, pl):
    _project_stats = messages_df.group_by("projectHash").agg([
        pl.col("sessionId").n_unique().alias("session_count"),
        pl.count("id").alias("message_count"),
        pl.col("tokens_total").sum().alias("total_tokens")
    ]).sort("session_count", descending=True)

    mo.vstack([
        mo.md("### Project Activity"),
        mo.ui.table(_project_stats.head(10))
    ])
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Tool Usage & Thoughts
    """)
    return


@app.cell
def _(alt, mo, tool_calls_df):
    if tool_calls_df.is_empty():
        _tool_viz = mo.md("No tool calls found.")
    else:
        _tool_counts = tool_calls_df["name"].value_counts().sort("count", descending=True).head(15)
        _tool_viz = (
            alt.Chart(_tool_counts)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="Usage Count"),
                y=alt.Y("name:N", sort="-x", title="Tool Name"),
                color=alt.Color("name:N", legend=None),
                tooltip=["name", "count"]
            )
            .properties(title="Top Tools Used")
        )

    _tool_viz
    return


@app.cell
def _(alt, mo, thoughts_df):
    if thoughts_df.is_empty():
        _thought_viz = mo.md("No thoughts found.")
    else:
        _thought_counts = thoughts_df["subject"].value_counts().sort("count", descending=True).head(15)
        _thought_viz = (
            alt.Chart(_thought_counts)
            .mark_bar()
            .encode(
                x=alt.X("count:Q", title="Frequency"),
                y=alt.Y("subject:N", sort="-x", title="Thought Subject"),
                color=alt.Color("subject:N", legend=None),
                tooltip=["subject", "count"]
            )
            .properties(title="Common Thought Subjects")
        )

    _thought_viz
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Interactive Session Summarizer
    """)
    return


@app.cell
def _(mo, sessions):
    _session_options = [s.sessionId for s in sessions if getattr(s, "sessionId", None) is not None]
    session_dropdown = mo.ui.dropdown(
        options=_session_options,
        value=_session_options[0] if _session_options else None,
        label="Select a Session to Summarize"
    )
    run_summarize = mo.ui.run_button(label="Summarize Session")
    mo.hstack([session_dropdown, run_summarize])
    return run_summarize, session_dropdown


@app.cell
async def _(mo, run_summarize, session_dropdown, sessions):
    mo.stop(not run_summarize.value, mo.md("Click 'Summarize Session' to generate AI summary."))

    # Find the session object
    selected_session = next((s for s in sessions if s.sessionId == session_dropdown.value), None)

    summary = None
    if not selected_session:
        result = mo.md("Session not found.")
    else:
        try:
            from saruca import summarizer
            with mo.status.loading("Summarizing with AI..."):
                summary = await summarizer.summarize_session(selected_session)

            result = mo.vstack([
                mo.md(f"### {summary.title}"),
                mo.md(f"**Outcome:** {summary.outcome}"),
                mo.md("**Key Points:**"),
                mo.md("\n".join([f"- {kp}" for kp in summary.key_points]))
            ])
        except Exception as e:
            result = mo.md(f"Error during summarization: {e}")
    return (result,)


@app.cell
def _(result):
    result
    return


@app.cell
def _(mo):
    mo.md(r"""
    ## Data Explorer
    """)
    return


@app.cell
def _(messages_df, mo):
    selected_type = mo.ui.dropdown(
        ["All"] + messages_df["type"].unique().to_list(), 
        value="All",
        label="Filter messages by type"
    )
    selected_type
    return (selected_type,)


@app.cell
def _(messages_df, pl, selected_type):
    filtered_df = messages_df
    if selected_type.value != "All":
        filtered_df = messages_df.filter(pl.col("type") == selected_type.value)

    filtered_df.select([
        "timestamp", "type", "content_summary", "sessionId", "projectHash"
    ]).head(50)
    return


if __name__ == "__main__":
    app.run()
