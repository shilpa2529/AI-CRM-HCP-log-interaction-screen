"""
Tools available to the HCP-interaction LangGraph agent.

Each tool is built with a live DB session bound in via closure
(`build_tools(db)`), so the agent can read/write real rows during a chat
turn instead of just producing text.
"""
import json
from datetime import datetime, date as date_cls
from typing import List, Optional

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app import models
from app.agent.llm import primary_llm, context_llm


def build_tools(db: Session, session_id: str):

    # ---------- 1. Log Interaction --------------------------------------
    class LogInteractionArgs(BaseModel):
        hcp_name: str = Field(..., description="Name of the HCP the rep met/called/emailed.")
        raw_note: str = Field(
            ..., description="Free-text note from the rep describing the interaction, "
                              "e.g. 'Met Dr. Smith, discussed Product X efficacy, positive "
                              "sentiment, shared brochure'."
        )

    @tool("log_interaction", args_schema=LogInteractionArgs)
    def log_interaction(hcp_name: str, raw_note: str) -> str:
        """Create a new HCP interaction record. Uses the LLM to extract
        structured entities (interaction type, topics, materials, samples,
        sentiment, outcomes, follow-ups) out of a free-text/chat note, then
        persists them to the database. Use this whenever the rep describes
        a NEW interaction that hasn't been logged yet."""

        extraction_prompt = f"""Extract structured CRM fields from this field-rep note
about a healthcare professional (HCP) interaction. Respond ONLY with strict JSON,
no markdown, no commentary, matching this schema exactly:

{{
  "interaction_type": "Meeting" | "Call" | "Email" | "Conference" | "Sample Drop",
  "attendees": string[],
  "topics_discussed": string,
  "materials_shared": string[],
  "samples_distributed": [{{"name": string, "quantity": number}}],
  "sentiment": "positive" | "neutral" | "negative",
  "outcomes": string,
  "follow_up_actions": string
}}

Note: "{raw_note}"
"""
        raw = primary_llm.invoke(extraction_prompt).content
        data = _safe_json(raw)

        hcp = _get_or_create_hcp(db, hcp_name)

        interaction = models.Interaction(
            hcp_id=hcp.id,
            interaction_type=data.get("interaction_type", "Meeting"),
            date=date_cls.today(),
            time=datetime.now().time(),
            attendees=data.get("attendees", []),
            topics_discussed=data.get("topics_discussed", ""),
            materials_shared=[{"name": m} for m in data.get("materials_shared", [])],
            samples_distributed=data.get("samples_distributed", []),
            sentiment=data.get("sentiment", "neutral"),
            outcomes=data.get("outcomes", ""),
            follow_up_actions=data.get("follow_up_actions", ""),
            source="chat",
            raw_note=raw_note,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)

        return json.dumps({
            "status": "logged",
            "interaction_id": interaction.id,
            "hcp_name": hcp.name,
            "summary": data,
        })

    # ---------- 2. Edit Interaction --------------------------------------
    class EditInteractionArgs(BaseModel):
        interaction_id: str = Field(..., description="ID of the interaction to modify.")
        field: str = Field(
            ..., description="Which field to change: interaction_type, topics_discussed, "
                              "materials_shared, samples_distributed, sentiment, outcomes, "
                              "or follow_up_actions."
        )
        new_value: str = Field(..., description="The new value, as plain text.")

    @tool("edit_interaction", args_schema=EditInteractionArgs)
    def edit_interaction(interaction_id: str, field: str, new_value: str) -> str:
        """Modify a single field on an already-logged interaction, e.g.
        correcting the sentiment or appending a missed outcome. Use this
        when the rep references an EXISTING logged interaction and wants
        to change or append to it."""
        interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": "Interaction not found."})

        list_fields = {"materials_shared", "samples_distributed"}
        if field in list_fields:
            try:
                parsed = json.loads(new_value)
            except json.JSONDecodeError:
                parsed = [{"name": new_value}]
            setattr(interaction, field, parsed)
        elif hasattr(interaction, field):
            setattr(interaction, field, new_value)
        else:
            return json.dumps({"status": "error", "message": f"Unknown field '{field}'."})

        interaction.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(interaction)
        return json.dumps({"status": "updated", "interaction_id": interaction.id, "field": field})

    # ---------- 3. Search / Resolve HCP -----------------------------------
    class SearchHcpArgs(BaseModel):
        query: str = Field(..., description="HCP name or partial name to search for.")

    @tool("search_hcp", args_schema=SearchHcpArgs)
    def search_hcp(query: str) -> str:
        """Search existing HCPs by name so the agent can confirm identity
        before logging an interaction, or disambiguate similarly-named
        doctors."""
        matches = (
            db.query(models.HCP)
            .filter(models.HCP.name.ilike(f"%{query}%"))
            .limit(5)
            .all()
        )
        return json.dumps([
            {"id": h.id, "name": h.name, "specialty": h.specialty, "institution": h.institution}
            for h in matches
        ])

    # ---------- 4. Suggest Follow-ups -------------------------------------
    class SuggestFollowupsArgs(BaseModel):
        interaction_id: str = Field(..., description="ID of the interaction to generate follow-ups for.")

    @tool("suggest_followups", args_schema=SuggestFollowupsArgs)
    def suggest_followups(interaction_id: str) -> str:
        """Generate 2-4 AI-suggested next-best-actions for a logged
        interaction (e.g. schedule a follow-up meeting, send a specific
        clinical PDF, add the HCP to an advisory board list), using the
        larger context model for higher-quality reasoning over the full
        interaction history for that HCP."""
        interaction = db.query(models.Interaction).filter_by(id=interaction_id).first()
        if not interaction:
            return json.dumps({"status": "error", "message": "Interaction not found."})

        history = (
            db.query(models.Interaction)
            .filter_by(hcp_id=interaction.hcp_id)
            .order_by(models.Interaction.date.desc())
            .limit(5)
            .all()
        )
        history_text = "\n".join(
            f"- {h.date}: {h.topics_discussed} (sentiment: {h.sentiment}, outcomes: {h.outcomes})"
            for h in history
        )
        prompt = f"""You are a pharma field-sales strategist. Given this HCP's recent
interaction history, suggest 2-4 short, concrete next-best-actions
(each under 12 words). Respond ONLY as a JSON array of strings.

History:
{history_text}
"""
        raw = context_llm.invoke(prompt).content
        suggestions = _safe_json(raw, default=[])
        if not isinstance(suggestions, list):
            suggestions = []

        interaction.ai_suggested_followups = suggestions
        db.commit()
        return json.dumps({"interaction_id": interaction_id, "suggestions": suggestions})

    # ---------- 5. Summarize Voice Note -----------------------------------
    class SummarizeVoiceNoteArgs(BaseModel):
        transcript: str = Field(..., description="Raw transcript of the rep's voice note.")
        consent_given: bool = Field(
            ..., description="Whether the rep has explicitly confirmed consent to process "
                              "the voice note (must be true to proceed)."
        )

    @tool("summarize_voice_note", args_schema=SummarizeVoiceNoteArgs)
    def summarize_voice_note(transcript: str, consent_given: bool) -> str:
        """Summarize a voice-note transcript into the 'Topics Discussed'
        field. Requires explicit consent per the 'Summarize from Voice
        Note (Requires Consent)' control on the form - refuses if consent
        was not given."""
        if not consent_given:
            return json.dumps({
                "status": "blocked",
                "message": "Consent required before summarizing a voice note.",
            })
        prompt = (
            "Summarize the key discussion points from this field-rep voice-note "
            "transcript into 2-3 concise sentences suitable for a CRM 'Topics "
            f"Discussed' field:\n\n{transcript}"
        )
        summary = primary_llm.invoke(prompt).content.strip()
        return json.dumps({"status": "ok", "topics_discussed": summary})

    return [
        log_interaction,
        edit_interaction,
        search_hcp,
        suggest_followups,
        summarize_voice_note,
    ]


def _get_or_create_hcp(db: Session, name: str) -> models.HCP:
    hcp = db.query(models.HCP).filter(models.HCP.name.ilike(name)).first()
    if hcp:
        return hcp
    hcp = models.HCP(name=name)
    db.add(hcp)
    db.commit()
    db.refresh(hcp)
    return hcp


def _safe_json(raw: str, default=None):
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.replace("json\n", "", 1) if raw.startswith("json\n") else raw
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default if default is not None else {}
