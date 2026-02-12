from typing import List
import logging

from pydantic import BaseModel
from pydantic_ai import Agent

from .models import Session

logger = logging.getLogger(__name__)

class SessionSummary(BaseModel):
    title: str
    key_points: List[str]
    outcome: str


def get_agent():
    return Agent(
        "google-gla:gemini-2.5-flash",
        output_type=SessionSummary,
        system_prompt="""You are an expert technical assistant who understands data and code and systems.
            Summarize the following conversation between a user and an AI model.
            Identify any failures to communicate or errors.
        """,
    )


async def summarize_session(session: Session) -> SessionSummary:
    logger.info(f"Starting summarization for session {session.sessionId}")
    history = []
    duration = session.lastUpdated - session.startTime
    history.append(f"SESSION START: {session.startTime.strftime('%Y-%m-%d %H:%M:%S')}")
    history.append(f"SESSION END:   {session.lastUpdated.strftime('%Y-%m-%d %H:%M:%S')}\n(DURATION: {duration})")
    history.append("-" * 20)
    
    for m in session.messages:
        role = "user" if m.type == "user" else "model"
        content = m.content if isinstance(m.content, str) else str(m.content)
        history.append(f"{role.upper()}: {content}")

    conversation_text = "\n".join(history)
    agent = get_agent()
    
    try:
        result = await agent.run(conversation_text)
        logger.info(f"Summarization complete for session {session.sessionId}. Title: {result.output.title}")
        return result.output
    except Exception as e:
        logger.error(f"Error summarizing session {session.sessionId}: {e}")
        # Return a dummy summary or re-raise
        raise e
