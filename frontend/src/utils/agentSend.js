import { sendChatMessage, setDraft } from '../store/chatSlice'
import { hydrateFromInteraction } from '../store/interactionSlice'

/**
 * Sends a message to the LangGraph agent (via /api/chat) and, if the agent
 * logged or edited an interaction, hydrates the Interaction Details panel.
 */
export async function sendToAgent(dispatch, text) {
  const trimmed = (text || '').trim()

  if (!trimmed) return null

  // Optional: clear the input immediately
  dispatch(setDraft(''))

  // Pass the message directly to the thunk
  const action = await dispatch(sendChatMessage(trimmed))

  if (
    sendChatMessage.fulfilled.match(action) &&
    action.payload?.interaction
  ) {
    dispatch(hydrateFromInteraction(action.payload.interaction))
  }

  return action
}