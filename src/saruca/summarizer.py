from typing import List

from pydantic import BaseModel
from pydantic_ai import Agent

from .models import Session


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
    history = []
    for m in session.messages:
        role = "user" if m.type == "user" else "model"
        content = m.content if isinstance(m.content, str) else str(m.content)
        history.append(f"{role.upper()}: {content}")

    conversation_text = "\n".join(history)
    agent = get_agent()
    result = await agent.run(conversation_text)
    return result.output
