# AI-First CRM — HCP Module: Log Interaction Screen

Full-stack implementation per spec: **React + Redux** frontend, **FastAPI**
backend, **LangGraph** agent, **Groq** LLMs (`gemma2-9b-it` primary,
`llama-3.3-70b-versatile` for longer-context reasoning), **Postgres**
(swap-able to MySQL), **Google Inter** font.

```
hcp-crm/
├── backend/
│   ├── app/
│   │   ├── agent/
│   │   │   ├── llm.py        # Groq clients (gemma2-9b-it + llama-3.3-70b-versatile)
│   │   │   ├── tools.py      # 5 LangGraph tools
│   │   │   └── graph.py      # StateGraph: agent <-> tools ReAct loop
│   │   ├── routers/
│   │   │   ├── interactions.py  # structured-form REST CRUD
│   │   │   └── chat.py          # AI Assistant chat endpoint
│   │   ├── models.py, schemas.py, database.py, config.py, main.py
│   ├── requirements.txt
│   └── .env.example
└── frontend/
    ├── src/
    │   ├── store/  (Redux Toolkit: interactionSlice, chatSlice)
    │   ├── components/ (LogInteractionScreen, InteractionForm, AIChatPanel)
    │   └── api/client.js
    └── package.json
```

## Role of the LangGraph agent

The LangGraph agent is the engine behind the **AI Assistant** chat panel on
the right of the Log Interaction screen. **The "Interaction Details" panel
on the left is read-only** — reps never type directly into those fields.
The only way to log or change an interaction is to describe it (or dictate
it) to the AI Assistant, e.g. *"Met Dr. Smith, discussed Product X
efficacy, positive sentiment, shared brochure"*. The agent:

1. Parses the message and decides which tool(s) the request requires.
2. Resolves the HCP (creating the record if new).
3. Extracts structured entities from free text using the LLM (interaction
   type, topics, materials, samples, sentiment, outcomes, follow-ups).
4. Writes directly to the same Postgres tables the form uses, so the form
   and chat are always looking at one source of truth — the frontend
   re-hydrates the form fields from whatever the agent just logged.
5. Loops back through the LLM if a tool result implies another step is
   needed (e.g., after logging, it automatically calls `suggest_followups`),
   and stops once it has a plain-language confirmation to send back.

This is implemented as a small ReAct-style graph: `agent` node (LLM bound to
tools) → conditional edge → `tools` node (executes whichever tool(s) the LLM
requested) → back to `agent` → repeat until the LLM responds with plain text
instead of a tool call → `END`.

## The 5 tools

1. **`log_interaction`** (required) — Takes an HCP name and a free-text
   note. Sends the note to the Groq LLM with a strict JSON extraction
   prompt to pull out interaction type, attendees, topics, materials,
   samples, sentiment, outcomes, and follow-up actions, then creates the
   `Interaction` row (and the `HCP` row if it doesn't exist yet).
2. **`edit_interaction`** (required) — Takes an `interaction_id`, a field
   name, and a new value, and patches that single field on an
   already-logged interaction (e.g. "actually it was negative sentiment,
   not neutral").
3. **`search_hcp`** — Fuzzy-searches existing HCPs by name so the agent can
   disambiguate before logging (e.g. two "Dr. Sharma"s).
4. **`suggest_followups`** — Pulls the HCP's last 5 interactions and asks
   the larger-context model (`llama-3.3-70b-versatile`) to propose 2–4
   concrete next-best-actions, written back onto the interaction as
   `ai_suggested_followups` (these are what populate the "AI Suggested
   Follow-ups" list under the form).
5. **`summarize_voice_note`** — Powers the "Summarize from Voice Note
   (Requires Consent)" control: takes a transcript + an explicit
   `consent_given` flag, refuses if consent wasn't given, otherwise
   condenses the transcript into a "Topics Discussed" summary.

## Voice input for Topics Discussed

Since the "Interaction Details" panel is read-only, voice capture lives as
a mic control (`VoiceNoteButton.jsx`) directly under Topics Discussed:

1. Rep taps the mic → an explicit consent confirmation appears (per the
   "Requires Consent" requirement from the mock).
2. On consent, the browser's Web Speech API (`SpeechRecognition`) captures
   and transcribes the voice note client-side.
3. The transcript is sent to the AI Assistant as a chat message, tagged
   with the current `interaction_id` if one is already logged.
4. The agent calls `summarize_voice_note` (consent-gated) then either
   `edit_interaction` (field=`topics_discussed`) on the existing record, or
   `log_interaction` if this is a brand-new interaction.
5. The panel re-hydrates with the summarized text, same as any other
   agent turn.

Requires Chrome or Edge (or another `SpeechRecognition`-capable browser);
the button shows a graceful "not supported" message otherwise.

## Setup

### Backend
```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then set GROQ_API_KEY and DATABASE_URL
uvicorn app.main:app --reload --port 8000
```
Postgres: on startup the app automatically creates the target database
itself (via `sqlalchemy-utils`, using the credentials/host in
`DATABASE_URL`) if it doesn't already exist, then creates all tables — no
manual `createdb` step needed. You only need a running Postgres server and
a user with `CREATEDB` privileges (the default `postgres` superuser has
this). To use MySQL instead, change `DATABASE_URL` to a
`mysql+pymysql://...` URL and `pip install pymysql` — the same
auto-create logic works there too.

### Frontend
```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, proxies /api to :8000
```

## Notes / assumptions
- The "Interaction Details" panel is intentionally **read-only** — it has no
  editable inputs. `interactionSlice` only exposes `hydrateFromInteraction`
  (called after each AI Assistant turn) and `resetInteraction` (clears the
  panel to start a new record). All writes go through the LangGraph agent's
  `log_interaction` / `edit_interaction` tools.
- `hcp_name` is resolved to an `HCP` row on the fly (get-or-create) from
  both the form submit and the chat agent, since the mock only shows a
  name search field.
- Voice-note capture (mic → transcript) is stubbed as a text transcript
  input to `summarize_voice_note`; wiring an actual recorder/STT service is
  a drop-in swap behind that same tool.
- Redux Toolkit is used for both the form (`interactionSlice`) and chat
  (`chatSlice`) state, with async thunks calling the FastAPI endpoints.
