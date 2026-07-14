from datetime import date, time, datetime
from typing import List, Optional, Literal
from pydantic import BaseModel


class MaterialItem(BaseModel):
    id: Optional[str] = None
    name: str


class SampleItem(BaseModel):
    id: Optional[str] = None
    name: str
    quantity: int = 1


class InteractionBase(BaseModel):
    hcp_id: Optional[str] = None
    hcp_name: Optional[str] = None  # allows create-by-name if hcp_id unknown
    interaction_type: Literal["Meeting", "Call", "Email", "Conference", "Sample Drop"] = "Meeting"
    date: Optional[date] = None
    time: Optional[time] = None
    attendees: List[str] = []
    topics_discussed: Optional[str] = None
    materials_shared: List[MaterialItem] = []
    samples_distributed: List[SampleItem] = []
    sentiment: Literal["positive", "neutral", "negative"] = "neutral"
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionCreate(InteractionBase):
    pass


class InteractionUpdate(BaseModel):
    interaction_type: Optional[str] = None
    date: Optional[date] = None
    time: Optional[time] = None
    attendees: Optional[List[str]] = None
    topics_discussed: Optional[str] = None
    materials_shared: Optional[List[MaterialItem]] = None
    samples_distributed: Optional[List[SampleItem]] = None
    sentiment: Optional[str] = None
    outcomes: Optional[str] = None
    follow_up_actions: Optional[str] = None


class InteractionOut(BaseModel):
    id: str
    hcp_id: str
    hcp_name: Optional[str] = None
    interaction_type: str
    date: Optional[date]
    time: Optional[time]
    attendees: List[str]
    topics_discussed: Optional[str]
    materials_shared: list
    samples_distributed: list
    sentiment: str
    outcomes: Optional[str]
    follow_up_actions: Optional[str]
    ai_suggested_followups: list
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChatRequest(BaseModel):
    session_id: str
    message: str
    voice_consent: bool = False


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    tool_events: list = []
    interaction: Optional[InteractionOut] = None
