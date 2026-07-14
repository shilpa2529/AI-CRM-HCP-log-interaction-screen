import json
import logging
import traceback

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage

from app import models, schemas
from app.database import get_db
from app.agent.graph import build_agent
from app.config import settings

router = APIRouter(prefix="/api/chat", tags=["chat"])
logger = logging.getLogger("hcp_crm.chat")


@router.post("", response_model=schemas.ChatResponse)
def chat(payload: schemas.ChatRequest, db: Session = Depends(get_db)):
    """Entry point for the 'AI Assistant' panel. Rebuilds the LangGraph
    agent per-request (bound to this DB session), replays prior turns for
    this session_id from chat_messages, runs the graph, persists the new
    turns, and returns the assistant's reply plus any tool activity.

    Any exception here is caught, logged with a full traceback (check the
    uvicorn console), and re-raised as an HTTPException whose `detail`
    contains the real error message - so the frontend can surface the
    actual cause instead of a generic 'server unreachable' message.
    """
    if not payload.message or not payload.message.strip():
        raise HTTPException(400, "Message cannot be empty.")

    if not settings.groq_api_key or settings.groq_api_key == "your_groq_api_key_here":
        raise HTTPException(
            500,
            "GROQ_API_KEY is not configured on the backend. Set it in backend/.env "
            "(copy from .env.example) and restart the server.",
        )

    try:
        history_rows = (
            db.query(models.ChatMessage)
            .filter_by(session_id=payload.session_id)
            .order_by(models.ChatMessage.created_at.asc())
            .all()
        )
        messages = []
        for row in history_rows:
            if row.role == "user":
                messages.append(HumanMessage(content=row.content))
            elif row.role == "assistant":
                messages.append(AIMessage(content=row.content))
        messages.append(HumanMessage(content=payload.message))

        agent = build_agent(db, payload.session_id)
        result = agent.invoke({"messages": messages})
        result_messages = result["messages"]

        tool_events = []
        last_interaction_id = None
        for m in result_messages:
            if isinstance(m, ToolMessage):
                tool_events.append({"tool": m.name, "output": m.content})
                if m.name in ("log_interaction", "edit_interaction") and '"interaction_id"' in m.content:
                    try:
                        last_interaction_id = json.loads(m.content).get("interaction_id")
                    except Exception:
                        pass

        final_ai = next((m for m in reversed(result_messages) if isinstance(m, AIMessage) and m.content), None)
        reply_text = final_ai.content if final_ai else "Done."

        db.add(models.ChatMessage(session_id=payload.session_id, role="user", content=payload.message))
        db.add(models.ChatMessage(session_id=payload.session_id, role="assistant", content=reply_text))
        db.commit()

        interaction_out = None
        if last_interaction_id:
            interaction = db.query(models.Interaction).filter_by(id=last_interaction_id).first()
            if interaction:
                interaction.hcp_name = interaction.hcp.name
                interaction_out = schemas.InteractionOut.model_validate(interaction)

        return schemas.ChatResponse(
            session_id=payload.session_id,
            reply=reply_text,
            tool_events=tool_events,
            interaction=interaction_out,
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        tb = traceback.format_exc()
        logger.error("Chat agent failed:\n%s", tb)
        # Print too, in case logging isn't configured to show on console.
        print(tb)
        raise HTTPException(
            500,
            f"Chat agent error ({type(e).__name__}): {e}",
        )
