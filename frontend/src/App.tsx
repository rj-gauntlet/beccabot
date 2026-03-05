import { useCallback, useEffect, useState } from 'react'
import './App.css'
import { ChatView } from './components/ChatView'
import { DocumentsView } from './components/DocumentsView'

const API_BASE = '/api'

type View = 'chat' | 'documents'
type Theme = 'dark' | 'light'

const THEME_KEY = 'beccabot-theme'

function App() {
  const [view, setView] = useState<View>('chat')
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
    fetch(`${API_BASE}/documents/locked`)
      .then((r) => r.json())
      .then((d) => setDocumentsLocked(!!d.locked))
      .catch(() => setDocumentsLocked(false))
  }, [])

  const handleDocumentsClick = useCallback(() => {
    if (documentsLocked && !documentsUnlocked) {
      setShowPinModal(true)
      setPinValue('')
      setPinError('')
    } else {
      setView('documents')
    }
  }, [documentsLocked, documentsUnlocked])

  const handlePinSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setPinError('')
    const pin = pinValue.trim()
    if (!pin) return
    const res = await fetch(`${API_BASE}/documents`, {
      headers: { 'X-Documents-PIN': pin },
    })
    if (res.ok) {
      setDocumentsUnlocked(true)
      setDocumentsPin(pin)
      setShowPinModal(false)
      setPinValue('')
      setView('documents')
    } else {
      setPinError('Incorrect PIN')
    }
  }

  const handleLock = useCallback(() => {
    setDocumentsUnlocked(false)
    setDocumentsPin('')
    setView('chat')
  }, [])

  const toggleTheme = () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))

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
            onClick={handleDocumentsClick}
          >
            {documentsLocked ? 'Documents 🔒' : 'Documents'}
          </button>
          <button
            className="nav-btn theme-toggle"
            onClick={toggleTheme}
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
        </nav>
      </header>
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
        {view === 'chat' && <ChatView />}
        {view === 'documents' && (
          <DocumentsView pin={documentsPin} onLock={documentsLocked ? handleLock : undefined} />
        )}
      </main>
    </div>
  )
}

export default App
