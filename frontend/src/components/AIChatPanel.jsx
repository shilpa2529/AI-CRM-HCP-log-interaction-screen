import { useEffect, useRef } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { setDraft } from '../store/chatSlice'
import { sendToAgent } from '../utils/agentSend'

export default function AIChatPanel() {
  const dispatch = useDispatch()
  const chat = useSelector((state) => state.chat)
  const scrollRef = useRef(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTo({
        top: scrollRef.current.scrollHeight,
        behavior: 'smooth',
      })
    }
  }, [chat.messages])

  const send = async () => {
    // Capture the message BEFORE anything clears the draft
    const message = chat.draft.trim()

    if (!message) return
    if (chat.status === 'loading') return

    try {
      await sendToAgent(dispatch, message)
    } catch (err) {
      console.error('Failed to send message:', err)
    }
  }

  return (
    <div className="panel">
      <div className="panel-header">
        <span className="status-dot" /> AI Assistant
      </div>

      <div
        className="panel-body"
        style={{ display: 'flex', flexDirection: 'column' }}
      >
        <div className="chat-messages" ref={scrollRef}>
          {chat.messages.length === 0 ? (
            <div className="chat-empty">
              Log interaction details here (e.g. "Met Dr. Smith, discussed
              Product X efficacy, positive sentiment, shared brochure") or use
              the voice-note mic under Topics Discussed.
            </div>
          ) : (
            chat.messages.map((message, index) => (
              <div
                key={index}
                className={`chat-bubble ${message.role}`}
              >
                {message.content}
              </div>
            ))
          )}

          {chat.status === 'loading' && (
            <div className="chat-bubble assistant">
              Thinking...
            </div>
          )}
        </div>
      </div>

      <div className="chat-input-row">
        <input
          type="text"
          placeholder="Describe interaction..."
          value={chat.draft}
          onChange={(e) => dispatch(setDraft(e.target.value))}
          onKeyDown={(e) => {
            if (e.key === 'Enter') {
              e.preventDefault()
              send()
            }
          }}
          disabled={chat.status === 'loading'}
        />

        <button
          className="btn btn-primary"
          onClick={send}
          disabled={chat.status === 'loading' || !chat.draft.trim()}
        >
          {chat.status === 'loading' ? 'Sending...' : 'Log'}
        </button>
      </div>
    </div>
  )
}