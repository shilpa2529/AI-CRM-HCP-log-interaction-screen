import { createSlice, createAsyncThunk } from '@reduxjs/toolkit'
import { api } from '../api/client'

function makeSessionId() {
  return 'sess_' + Math.random().toString(36).slice(2) + Date.now().toString(36)
}

const initialState = {
  sessionId: makeSessionId(),
  draft: '',
  messages: [], // { role: 'user'|'assistant'|'tool', content }
  status: 'idle',
}

export const sendChatMessage = createAsyncThunk(
  'chat/send',
  async (message, { getState, rejectWithValue }) => {
    try {
      const { chat } = getState()

      const trimmedMessage = message.trim()

      const res = await api.post('/api/chat', {
        session_id: chat.sessionId,
        message: trimmedMessage,
      })

      return {
        userMessage: trimmedMessage,
        ...res,
      }
    } catch (err) {
      return rejectWithValue(
        err?.response?.data?.detail ||
          err?.message ||
          'Unknown error contacting the backend.'
      )
    }
  }
)

const chatSlice = createSlice({
  name: 'chat',
  initialState,
  reducers: {
    setDraft(state, action) {
      state.draft = action.payload
    },
  },
  extraReducers: (builder) => {
    builder

      .addCase(sendChatMessage.pending, (state, action) => {
        const message = action.meta.arg.trim()

        if (message) {
          state.messages.push({
            role: 'user',
            content: message,
          })
        }

        state.draft = ''
        state.status = 'loading'
      })

      .addCase(sendChatMessage.fulfilled, (state, action) => {
        state.status = 'succeeded'

        for (const evt of action.payload.tool_events || []) {
          state.messages.push({
            role: 'tool',
            content: `${evt.tool} → ${evt.output}`,
          })
        }

        state.messages.push({
          role: 'assistant',
          content: action.payload.reply,
        })
      })

      .addCase(sendChatMessage.rejected, (state, action) => {
        state.status = 'failed'

        state.messages.push({
          role: 'assistant',
          content: `⚠️ ${
            action.payload ||
            action.error?.message ||
            'Unknown error contacting the backend.'
          }`,
        })
      })
  },
})

export const { setDraft } = chatSlice.actions

export default chatSlice.reducer