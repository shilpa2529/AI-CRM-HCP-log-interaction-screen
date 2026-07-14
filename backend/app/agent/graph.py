"""
LangGraph agent that powers the "AI Assistant" chat panel on the Log
Interaction screen.

Role of the agent:
  The "Interaction Details" panel is read-only - the rep never types into
  it directly. The only input surface is this chat panel (typed or, for
  Topics Discussed, voice via the mic control). The rep can describe what
  happened in plain language ("Met Dr. Smith, discussed Product X
  efficacy, positive sentiment, shared brochure") or dictate a voice note.
  The LangGraph agent parses that message, decides which tool(s) to call
  (log a new interaction, edit an existing one, look up an HCP, pull
  follow-up suggestions, or summarize a voice note), executes them against
  the DB, and replies conversationally - the frontend then re-hydrates the
  read-only panel from whatever the agent just wrote.

Graph shape (ReAct loop):
    START -> agent -> (tool_calls?) -> tools -> agent -> ... -> END
"""
from typing import Annotated, TypedDict
from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langchain_core.messages import SystemMessage

from app.agent.llm import primary_llm
from app.agent.tools import build_tools

SYSTEM_PROMPT = """You are the AI Assistant embedded in a pharma CRM's "Log HCP \
Interaction" screen. The "Interaction Details" panel is READ-ONLY - the rep never \
types into it directly. You are the only way interaction data gets created or \
changed, via natural conversation (typed or voice-dictated).

Rules:
- If the rep describes a new interaction in plain language, call log_interaction \
  (resolve the HCP with search_hcp first only if the name is ambiguous).
- If the rep refers to something already logged and wants a change, call \
  edit_interaction.
- VOICE NOTES: if the message is a voice-note transcript (it will say things like \
  "voice note" or "I explicitly consent to processing this voice note"):
  1. Call summarize_voice_note with the transcript and consent_given=true (only \
     set true if the message explicitly states consent was given).
  2. If the message references an existing interaction_id, call edit_interaction \
     on that interaction_id with field="topics_discussed" and the summary as \
     new_value.
  3. If no interaction_id is referenced (this is a brand-new interaction), call \
     log_interaction using the transcript as raw_note - do not call \
     summarize_voice_note in that case, log_interaction already handles extraction.
  If consent was not clearly given, do not call summarize_voice_note - ask the \
  rep to confirm consent first.
- After logging a new interaction, proactively call suggest_followups and mention \
  the suggestions.
- Never fabricate an interaction_id - only use one that was given to you or \
  returned by a tool.
- Keep replies short, professional, and confirm exactly what was recorded.
"""


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]


def build_agent(db, session_id: str):
    tools = build_tools(db, session_id)
    llm_with_tools = primary_llm.bind_tools(tools)

    def agent_node(state: AgentState):
        messages = state["messages"]
        if not any(isinstance(m, SystemMessage) for m in messages):
            messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
        response = llm_with_tools.invoke(messages)
        return {"messages": [response]}

    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)
    graph.add_node("tools", ToolNode(tools))

    graph.set_entry_point("agent")
    graph.add_conditional_edges("agent", tools_condition, {"tools": "tools", END: END})
    graph.add_edge("tools", "agent")

    return graph.compile()
