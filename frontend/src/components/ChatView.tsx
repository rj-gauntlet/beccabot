import type { ReactNode } from 'react'
import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'

export interface SourceInfo {
  id: string
  name: string
  url: string | null
}

export interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fallback?: boolean
  timestamp?: string
  sources?: SourceInfo[]
}

const API_BASE = '/api'

function formatTimestamp(): string {
  const d = new Date()
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

interface ChatViewProps {
  messages: Message[]
  onMessagesChange: (messages: Message[] | ((prev: Message[]) => Message[])) => void
  onClearChat?: () => void
}

export function ChatView({ messages, onMessagesChange, onClearChat }: ChatViewProps) {
  const setMessages = (updater: Message[] | ((prev: Message[]) => Message[])) => {
    onMessagesChange(updater)
  }
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, loading])

  const buildHistory = (): { role: string; content: string }[] => {
    const out: { role: string; content: string }[] = []
    for (const m of messages) {
      if (m.role === 'user' || m.role === 'bot') {
        out.push({ role: m.role === 'bot' ? 'assistant' : 'user', content: m.content })
      }
    }
    return out
  }

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
      timestamp: formatTimestamp(),
    }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)

    const history = buildHistory()
    if (history.length > 0) history.pop() // exclude the message we just added

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: text,
          history: history.map((h) => ({ role: h.role, content: h.content })),
        }),
      })
      const textRes = await res.text()
      let data: {
        reply?: string
        fallback?: boolean
        detail?: string
        sources?: SourceInfo[]
      }
      try {
        data = textRes ? JSON.parse(textRes) : {}
      } catch {
        if (!res.ok) throw new Error(textRes || `Request failed (${res.status})`)
        throw new Error('Invalid response from server')
      }
      if (!res.ok) throw new Error(data.detail || textRes || 'Failed to send')

      const botMsg: Message = {
        id: crypto.randomUUID(),
        role: 'bot',
        content: data.reply ?? '',
        fallback: data.fallback,
        timestamp: formatTimestamp(),
        sources: data.sources?.length ? data.sources : undefined,
      }
      setMessages((m) => [...m, botMsg])
    } catch (err) {
      let errMsg = err instanceof Error ? err.message : 'Something went wrong'
      if (errMsg.includes('Internal Server Error') || errMsg.includes('500')) {
        errMsg = 'The server ran into an issue. Please try again.'
      }
      setMessages((m) => [
        ...m,
        {
          id: crypto.randomUUID(),
          role: 'bot',
          content: `Sorry, I couldn't get a response: ${errMsg}. Try again or reach out to Rebecca!`,
          fallback: true,
          timestamp: formatTimestamp(),
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
    if (e.key === 'Enter' && e.ctrlKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  const copyMessage = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content)
    } catch {
      // ignore
    }
  }

  const shareMessage = async (content: string) => {
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'BeccaBot',
          text: content,
        })
      } catch {
        // User cancelled or error - ignore
      }
    } else {
      copyMessage(content)
    }
  }

  const renderBotContent = (content: string): ReactNode => {
    return (
      <ReactMarkdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noopener noreferrer">
              {children}
            </a>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    )
  }

  return (
    <div className="chat-container">
      {onClearChat && (
        <div className="chat-header">
          <button type="button" className="clear-chat-btn" onClick={onClearChat} title="New conversation">
            New chat
          </button>
        </div>
      )}
      <div className="messages">
        {messages.map((m) => (
          <div key={m.id} className={`message-row ${m.role}`}>
            {m.role === 'bot' && (
              <img src="/beccabot-avatar.png" alt="BeccaBot" className="message-avatar" />
            )}
            <div className={`message-wrapper ${m.role}`}>
              <div className={`message ${m.role} ${m.fallback ? 'fallback' : ''}`}>
                {m.role === 'bot' ? renderBotContent(m.content) : m.content}
              </div>
              {(m.timestamp || (m.role === 'bot' && m.sources && m.sources.length > 0) || m.role === 'bot') && (
                <div className="message-meta">
                  {m.timestamp && <span className="message-time">{m.timestamp}</span>}
                  {m.role === 'bot' && m.sources && m.sources.length > 0 && (
                    <div className="message-sources">
                      Sources:{' '}
                      {m.sources.map((s) =>
                        s.url ? (
                          <a key={s.id} href={s.url} target="_blank" rel="noopener noreferrer">
                            {s.name}
                          </a>
                        ) : (
                          <span key={s.id} className="source-name">
                            {s.name}
                          </span>
                        )
                      )}
                    </div>
                  )}
                  {m.role === 'bot' && (
                    <div className="message-actions">
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => copyMessage(m.content)}
                        title="Copy"
                      >
                        Copy
                      </button>
                      <button
                        type="button"
                        className="message-action-btn"
                        onClick={() => shareMessage(m.content)}
                        title="Share"
                      >
                        Share
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-row bot">
            <img src="/beccabot-avatar.png" alt="BeccaBot" className="message-avatar" />
            <div className="message bot typing-indicator">
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-row">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask away. I'm ready."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={loading}
        />
        <button
          className="send-btn"
          onClick={sendMessage}
          disabled={loading || !input.trim()}
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
