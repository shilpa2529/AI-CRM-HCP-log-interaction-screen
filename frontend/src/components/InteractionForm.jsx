import { useDispatch, useSelector } from 'react-redux'
import { resetInteraction } from '../store/interactionSlice'
import VoiceNoteButton from './VoiceNoteButton'

const SENTIMENT_META = {
  positive: { label: 'Positive', emoji: '🙂', cls: 'positive' },
  neutral: { label: 'Neutral', emoji: '😐', cls: 'neutral' },
  negative: { label: 'Negative', emoji: '🙁', cls: 'negative' },
}

// READ-ONLY panel: every value here comes from Redux state that is only ever
// written by hydrateFromInteraction, which fires after the AI Assistant
// (LangGraph agent) logs or edits a record. There is no direct text entry
// here on purpose — the chat panel is the single way to create or change data.
function ReadOnlyField({ label, value, placeholder = '—' }) {
  return (
    <div className="field">
      <label>{label}</label>
      <div className="readonly-value">{value || <span className="placeholder">{placeholder}</span>}</div>
    </div>
  )
}

export default function InteractionForm() {
  const dispatch = useDispatch()
  const s = useSelector((state) => state.interaction)
  const hasData = Boolean(s.interactionId)

  return (
    <div className="panel">
      <div className="panel-header">
        Interaction Details
        <span className="readonly-badge">Auto-filled by AI Assistant</span>
      </div>
      <div className="panel-body">
        {!hasData && (
          <div className="chat-empty" style={{ marginBottom: 16 }}>
            Nothing logged yet. Describe the interaction to the AI Assistant on the
            right — this panel fills in automatically as it's logged.
          </div>
        )}

        <div className="field-row">
          <ReadOnlyField label="HCP Name" value={s.hcpName} placeholder="Not set" />
          <ReadOnlyField label="Interaction Type" value={s.interactionType} placeholder="Not set" />
        </div>

        <div className="field-row">
          <ReadOnlyField label="Date" value={s.date} placeholder="Not set" />
          <ReadOnlyField label="Time" value={s.time} placeholder="Not set" />
        </div>

        <div className="field" style={{ marginBottom: 14 }}>
          <label>Attendees</label>
          {s.attendees.length > 0 ? (
            <div className="chip-list">
              {s.attendees.map((a) => (
                <span className="chip readonly" key={a}>{a}</span>
              ))}
            </div>
          ) : (
            <div className="readonly-value"><span className="placeholder">Not set</span></div>
          )}
        </div>

        <ReadOnlyField label="Topics Discussed" value={s.topicsDiscussed} placeholder="Not set" />
        <VoiceNoteButton />

        <div className="section-title">Materials Shared / Samples Distributed</div>

        <div className="field" style={{ marginBottom: 10 }}>
          <label>Materials Shared</label>
          {s.materialsShared.length > 0 ? (
            <div className="chip-list">
              {s.materialsShared.map((m) => (
                <span className="chip readonly" key={m}>{m}</span>
              ))}
            </div>
          ) : (
            <div className="readonly-value"><span className="placeholder">No materials logged</span></div>
          )}
        </div>

        <div className="field" style={{ marginBottom: 14 }}>
          <label>Samples Distributed</label>
          {s.samplesDistributed.length > 0 ? (
            <div className="chip-list">
              {s.samplesDistributed.map((m) => (
                <span className="chip readonly" key={m}>{m}</span>
              ))}
            </div>
          ) : (
            <div className="readonly-value"><span className="placeholder">No samples logged</span></div>
          )}
        </div>

        <div className="section-title">Observed/Inferred HCP Sentiment</div>
        <div className="sentiment-row" style={{ marginBottom: 16 }}>
          {Object.entries(SENTIMENT_META).map(([key, meta]) => (
            <span
              key={key}
              className={`sentiment-option ${meta.cls} ${s.sentiment === key ? 'selected' : ''}`}
            >
              {meta.emoji} {meta.label}
            </span>
          ))}
        </div>

        <ReadOnlyField label="Outcomes" value={s.outcomes} placeholder="Not set" />
        <ReadOnlyField label="Follow-up Actions" value={s.followUpActions} placeholder="Not set" />

        {s.aiSuggestedFollowups?.length > 0 && (
          <>
            <div className="section-title">AI Suggested Follow-ups</div>
            <ul className="suggestion-list">
              {s.aiSuggestedFollowups.map((f, i) => (
                <li key={i}>• {f}</li>
              ))}
            </ul>
          </>
        )}
      </div>

      <div className="form-footer">
        <button className="btn" onClick={() => dispatch(resetInteraction())}>
          Start New Interaction
        </button>
      </div>
    </div>
  )
}
