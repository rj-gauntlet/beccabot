import { useState } from 'react'
import './App.css'
import { ChatView } from './components/ChatView'
import { DocumentsView } from './components/DocumentsView'

type View = 'chat' | 'documents'

function App() {
  const [view, setView] = useState<View>('chat')

  return (
    <div className="app">
      <header className="header">
        <span className="logo">BeccaBot</span>
        <nav className="nav">
          <button
            className={`nav-btn ${view === 'chat' ? 'active' : ''}`}
            onClick={() => setView('chat')}
          >
            Chat
          </button>
          <button
            className={`nav-btn ${view === 'documents' ? 'active' : ''}`}
            onClick={() => setView('documents')}
          >
            Documents
          </button>
        </nav>
      </header>
      <main className="main">
        {view === 'chat' && <ChatView />}
        {view === 'documents' && <DocumentsView />}
      </main>
    </div>
  )
}

export default App
