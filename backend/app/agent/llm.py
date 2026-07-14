from langchain_groq import ChatGroq

from app.config import settings

# Primary conversational / tool-calling model - fast, cheap, used for the
# turn-by-turn chat + tool routing loop.
primary_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model_primary,  # gemma2-9b-it
    temperature=0.2,
)

# Larger-context model, used when a step needs to reason over a longer
# transcript/voice-note or produce richer follow-up suggestions.
context_llm = ChatGroq(
    api_key=settings.groq_api_key,
    model=settings.groq_model_context,  # llama-3.3-70b-versatile
    temperature=0.3,
)
