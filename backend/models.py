from pydantic import BaseModel
from typing import Any

class Message(BaseModel):
    role: str        # "user" | "assistant" | "tool"
    content: str

class ChatRequest(BaseModel):
    messages: list[Message]
    plan: dict | None = None   # current plan state sent from frontend

class ChatResponse(BaseModel):
    reply: str
    plan: dict | None = None   # populated when generate_plan fires
    patch: dict | None = None  # populated when patch_exercise fires
    phase: str = "intake"      # "intake" | "plan" | "adjustment"