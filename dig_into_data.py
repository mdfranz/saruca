import polars as pl
import saruca
import os
import sys

def dig():
    sys.path.append(os.getcwd())
    
    log_files, session_files = saruca.discover_files(".")
    sessions = saruca.load_sessions(session_files)
    df = saruca.to_polars_messages(sessions)
    
    # Sort by session and timestamp
    df = df.sort(["sessionId", "timestamp"])
    
    print(f"Total messages: {len(df)}")
    
    # Let's look at a few full conversations
    sessions_ids = df["sessionId"].unique().to_list()
    
    for sid in sessions_ids[:3]: # Look at first 3 sessions
        session_msgs = df.filter(pl.col("sessionId") == sid)
        project = session_msgs["projectHash"][0]
        print("\n" + "="*80)
        print(f"SESSION: {sid} | PROJECT: {project}")
        print("="*80)
        
        for i in range(len(session_msgs)):
            m_type = session_msgs["type"][i]
            content = session_msgs["content_raw"][i]
            
            if m_type not in ["user", "gemini"] and len(content) > 500:
                content = content[:500] + "... [TRUNCATED]"
                
            print(f"\n[{m_type.upper()}]")
            print(content)

if __name__ == "__main__":
    dig()