import { useRef, useState } from 'react'
import { useDispatch, useSelector } from 'react-redux'
import { sendToAgent } from '../utils/agentSend'

function getSpeechRecognition() {
  return window.SpeechRecognition || window.webkitSpeechRecognition || null
}

export default function VoiceNoteButton() {
  const dispatch = useDispatch()
  const interactionId = useSelector((state) => state.interaction.interactionId)
  const chatStatus = useSelector((state) => state.chat.status)

  const [recording, setRecording] = useState(false)
  const [unsupported, setUnsupported] = useState(false)
  const recognitionRef = useRef(null)

  const startRecording = () => {
    const SpeechRecognition = getSpeechRecognition()
    if (!SpeechRecognition) {
      setUnsupported(true)
      return
    }

    const consented = window.confirm(
      'Summarize from Voice Note requires consent.\n\n' +
      'This will record your voice, transcribe it in your browser, and send ' +
      'the transcript to the AI Assistant to summarize into "Topics Discussed". ' +
      'Continue?'
    )
    if (!consented) return

    const recognition = new SpeechRecognition()
    recognition.lang = 'en-US'
    recognition.interimResults = false
    recognition.maxAlternatives = 1

    recognition.onstart = () => setRecording(true)
    recognition.onerror = () => setRecording(false)
    recognition.onend = () => setRecording(false)

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript
      const message = interactionId
        ? `Summarize this voice note for Topics Discussed on interaction ${interactionId}: ` +
          `"${transcript}". I explicitly consent to processing this voice note.`
        : `Log a new interaction from this voice note: "${transcript}". ` +
          `I explicitly consent to processing this voice note.`
      sendToAgent(dispatch, message)
    }

    recognitionRef.current = recognition
    recognition.start()
  }

  const stopRecording = () => {
    recognitionRef.current?.stop()
    setRecording(false)
  }

  if (unsupported) {
    return (
      <div className="voice-note-row">
        <span className="voice-unsupported">
          Voice input isn't supported in this browser. Try Chrome or Edge.
        </span>
      </div>
    )
  }

  return (
    <div className="voice-note-row">
      <button
        type="button"
        className={`btn-ghost voice-btn ${recording ? 'recording' : ''}`}
        onClick={recording ? stopRecording : startRecording}
        disabled={chatStatus === 'loading'}
      >
        {recording ? (
          <>
            <span className="rec-dot" /> Listening… tap to stop
          </>
        ) : (
          <>🎙 Summarize from Voice Note (Requires Consent)</>
        )}
      </button>
    </div>
  )
}
