from typing import List, Optional, Any, Dict, Union
from pydantic import BaseModel, Field
from datetime import datetime

class TokenUsage(BaseModel):
    input: Optional[int] = None
    output: Optional[int] = None
    cache_creation: Optional[int] = Field(None, alias="cacheCreation")
    cache_read: Optional[int] = Field(None, alias="cacheRead")

class Thought(BaseModel):
    subject: Optional[str] = None
    thought: Optional[str] = None

class ToolCall(BaseModel):
    id: str
    name: Optional[str] = None
    args: Optional[Dict[str, Any]] = None
    output: Optional[Any] = None

class Message(BaseModel):
    id: str
    timestamp: datetime
    type: str
    content: Union[str, Dict[str, Any]]
    thoughts: Optional[List[Thought]] = None
    tokens: Optional[TokenUsage] = None
    model: Optional[str] = None
    toolCalls: Optional[List[ToolCall]] = None

class Session(BaseModel):
    sessionId: str
    projectHash: str
    startTime: datetime
    lastUpdated: datetime
    messages: List[Message]

class LogEntry(BaseModel):
    sessionId: str
    messageId: int
    type: str
    message: str
    timestamp: datetime
    source_file: Optional[str] = None
