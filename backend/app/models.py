import uuid
import enum
from datetime import datetime

from sqlalchemy import (
    Column, String, DateTime, Text, ForeignKey, Enum, Date, Time
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.database import Base


def gen_uuid():
    return str(uuid.uuid4())


class SentimentEnum(str, enum.Enum):
    positive = "positive"
    neutral = "neutral"
    negative = "negative"


class InteractionTypeEnum(str, enum.Enum):
    meeting = "Meeting"
    call = "Call"
    email = "Email"
    conference = "Conference"
    sample_drop = "Sample Drop"


class HCP(Base):
    __tablename__ = "hcps"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name = Column(String(255), nullable=False)
    specialty = Column(String(255))
    institution = Column(String(255))
    email = Column(String(255))
    phone = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)

    interactions = relationship("Interaction", back_populates="hcp")


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    hcp_id = Column(UUID(as_uuid=False), ForeignKey("hcps.id"), nullable=False)
    interaction_type = Column(Enum(InteractionTypeEnum), default=InteractionTypeEnum.meeting)
    date = Column(Date, default=datetime.utcnow)
    time = Column(Time, default=datetime.utcnow)
    attendees = Column(JSONB, default=list)  # list[str]
    topics_discussed = Column(Text)
    materials_shared = Column(JSONB, default=list)   # list[{id, name}]
    samples_distributed = Column(JSONB, default=list)  # list[{id, name, qty}]
    sentiment = Column(Enum(SentimentEnum), default=SentimentEnum.neutral)
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    ai_suggested_followups = Column(JSONB, default=list)  # list[str]
    source = Column(String(20), default="form")  # "form" | "chat"
    raw_note = Column(Text)  # original free-text/voice-transcribed note, if any
    created_by = Column(String(255), default="rep")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    hcp = relationship("HCP", back_populates="interactions")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    session_id = Column(String(255), index=True, nullable=False)
    role = Column(String(20))  # user | assistant | tool
    content = Column(Text)
    tool_calls = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
