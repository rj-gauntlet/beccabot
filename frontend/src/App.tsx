import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { ChatView } from './components/ChatView'
import { DocumentsView } from './components/DocumentsView'

const API_BASE = '/api'

type View = 'chat' | 'documents'
type Theme = 'dark' | 'light'

const THEME_KEY = 'beccabot-theme'
const CHAT_HISTORY_KEY = 'beccabot-chat-history'

export const WELCOME_MESSAGE = {
  id: 'welcome',
  role: 'bot' as const,
  content:
    "Hey there! I'm BeccaBot—Rebecca's AI stand-in. Ask me anything about Gauntlet AI's programs, check the weather in Austin, or get directions between housing and the office. Go.",
  fallback: false as boolean | undefined,
}

export interface ChatMessage {
  id: string
  role: 'user' | 'bot'
  content: string
  fallback?: boolean
}

function loadChatHistory(): ChatMessage[] {
  try {
    const raw = localStorage.getItem(CHAT_HISTORY_KEY)
    if (!raw) return [WELCOME_MESSAGE as ChatMessage]
    const parsed = JSON.parse(raw)
    if (Array.isArray(parsed) && parsed.length > 0) return parsed as ChatMessage[]
  } catch {
    // ignore
  }
  return [WELCOME_MESSAGE as ChatMessage]
}

function App() {
  const [view, setView] = useState<View>('chat')
  const [chatMessages, setChatMessages] = useState(loadChatHistory)
  const [theme, setTheme] = useState<Theme>(() =>
    (localStorage.getItem(THEME_KEY) as Theme) || 'dark'
  )
  const [documentsLocked, setDocumentsLocked] = useState(false)
  const [documentsUnlocked, setDocumentsUnlocked] = useState(false)
  const [documentsPin, setDocumentsPin] = useState('')
  const [showPinModal, setShowPinModal] = useState(false)
  const [pinValue, setPinValue] = useState('')
  const [pinError, setPinError] = useState('')

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    localStorage.setItem(THEME_KEY, theme)
  }, [theme])

  useEffect(() => {
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(chatMessages))
  }, [chatMessages])

  useEffect(() => {
    fetch(`${API_BASE}/documents/locked`)
      .then((r) => r.json())
      .then((d) => setDocumentsLocked(!!d.locked))
      .catch(() => setDocumentsLocked(false))
  }, [])

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPinError('')
    const pin = pinValue.trim()
    if (!pin) return
    const res = await fetch(`${API_BASE}/documents`, {
      headers: { 'X-Documents-PIN': pin },
    })
    if (res.ok) {
      handlePinSuccess(pin)
    } else {
      setPinError('Incorrect PIN')
    }
  }

  const [settingsOpen, setSettingsOpen] = useState(false)

  const handleLock = useCallback(() => {
    setDocumentsUnlocked(false)
    setDocumentsPin('')
    setView('chat')
  }, [])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

  const openDocuments = () => {
    if (documentsLocked && !documentsUnlocked) {
      setShowPinModal(true)
      setPinValue('')
      setPinError('')
    } else {
      setView('documents')
      setSettingsOpen(false)
    }
  }

  const handlePinSuccess = (pin: string) => {
    setDocumentsUnlocked(true)
    setDocumentsPin(pin)
    setShowPinModal(false)
    setPinValue('')
    setView('documents')
    setSettingsOpen(false)
  }

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
            className={`nav-btn ${settingsOpen ? 'active' : ''}`}
            onClick={() => setSettingsOpen(true)}
            title="Settings"
          >
            ⚙️ Settings
          </button>
        </nav>
      </header>

      {settingsOpen && (
        <div
          className="settings-overlay"
          onClick={() => setSettingsOpen(false)}
          aria-hidden="true"
        />
      )}
      <div className={`settings-drawer ${settingsOpen ? 'open' : ''}`}>
        <div className="settings-drawer-header">
          <h3>Settings</h3>
          <button
            className="settings-close"
            onClick={() => setSettingsOpen(false)}
            aria-label="Close settings"
          >
            ✕
          </button>
        </div>
        <div className="settings-drawer-body">
          <div className="settings-item">
            <span>Dark mode</span>
            <button
              className="settings-toggle"
              onClick={toggleTheme}
              title={theme === 'dark' ? 'Switch to light' : 'Switch to dark'}
            >
              {theme === 'dark' ? '☀️' : '🌙'}
            </button>
          </div>
          <div className="settings-item">
            <span>Document library</span>
            <button
              className="settings-link"
              onClick={openDocuments}
              title={documentsLocked ? 'Authentication required' : 'Open documents'}
            >
              {documentsLocked ? 'Documents (auth required)' : 'Documents'}
            </button>
          </div>
        </div>
      </div>
      {showPinModal && (
        <div className="pin-modal-overlay" onClick={() => setShowPinModal(false)}>
          <div className="pin-modal" onClick={(e) => e.stopPropagation()}>
            <form onSubmit={handlePinSubmit}>
              <h3>Documents</h3>
              <p className="pin-hint">Enter PIN to access the document library.</p>
              <input
                type="password"
                inputMode="numeric"
                autoComplete="off"
                className="pin-input"
                placeholder="PIN"
                value={pinValue}
                onChange={(e) => setPinValue(e.target.value)}
                autoFocus
              />
              {pinError && <p className="pin-error">{pinError}</p>}
              <button type="submit" className="add-link-btn" disabled={!pinValue.trim()}>
                Unlock
              </button>
              <button
                type="button"
                className="pin-cancel"
                onClick={() => setShowPinModal(false)}
              >
                Cancel
              </button>
            </form>
          </div>
        </div>
      )}
      <main className={`main ${view === 'chat' ? 'main-chat' : ''}`}>
        {view === 'chat' && (
          <ChatView
            messages={chatMessages}
            onMessagesChange={setChatMessages}
          />
        )}
        {view === 'documents' && (
          <DocumentsView pin={documentsPin} onLock={documentsLocked ? handleLock : undefined} />
        )}
      </main>
    </div>
  )
}

export default App
