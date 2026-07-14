import { createSlice } from '@reduxjs/toolkit'

// NOTE: This form is READ-ONLY by design. Reps do not type into it directly —
// every field here is populated exclusively by the LangGraph agent behind the
// AI Assistant chat panel (see chatSlice.js -> hydrateFromInteraction below).
// This keeps the structured record and the conversational log as a single
// source of truth instead of two places that can drift out of sync.

const emptyInteraction = {
  interactionId: null,
  hcpName: '',
  interactionType: '',
  date: '',
  time: '',
  attendees: [],
  topicsDiscussed: '',
  materialsShared: [],
  samplesDistributed: [],
  sentiment: null,
  outcomes: '',
  followUpActions: '',
  aiSuggestedFollowups: [],
}

const initialState = { ...emptyInteraction }

const interactionSlice = createSlice({
  name: 'interaction',
  initialState,
  reducers: {
    // Called after the AI Assistant logs or edits an interaction, to
    // reflect the latest state of the record in the read-only panel.
    hydrateFromInteraction(state, action) {
      const i = action.payload
      if (!i) return
      state.interactionId = i.id
      state.hcpName = i.hcp_name ?? state.hcpName
      state.interactionType = i.interaction_type ?? state.interactionType
      state.date = i.date ?? state.date
      state.time = i.time ?? state.time
      state.attendees = i.attendees ?? state.attendees
      state.topicsDiscussed = i.topics_discussed ?? state.topicsDiscussed
      state.materialsShared = (i.materials_shared || []).map((m) => m.name)
      state.samplesDistributed = (i.samples_distributed || []).map((m) => m.name)
      state.sentiment = i.sentiment ?? state.sentiment
      state.outcomes = i.outcomes ?? state.outcomes
      state.followUpActions = i.follow_up_actions ?? state.followUpActions
      state.aiSuggestedFollowups = i.ai_suggested_followups?.length
        ? i.ai_suggested_followups
        : state.aiSuggestedFollowups
    },
    // Start a fresh, blank record - e.g. when the rep wants to log a new,
    // unrelated interaction in the same session.
    resetInteraction() {
      return { ...emptyInteraction }
    },
  },
})

export const { hydrateFromInteraction, resetInteraction } = interactionSlice.actions
export default interactionSlice.reducer
