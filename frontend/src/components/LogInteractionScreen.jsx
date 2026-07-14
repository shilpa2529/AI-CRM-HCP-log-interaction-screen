import InteractionForm from './InteractionForm'
import AIChatPanel from './AIChatPanel'

export default function LogInteractionScreen() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>Log HCP Interaction</h1>
        <p>AI-first CRM · Healthcare Professional module</p>
      </header>
      <div className="screen">
        <InteractionForm />
        <AIChatPanel />
      </div>
    </div>
  )
}
