import type { ReactElement } from 'react'
import { useState, useRef, useEffect } from 'react'

const URL_REGEX = /https?:\/\/[^\s<>"{}|\\^`[\]]+/gi

function formatMessageContent(content: string) {
  const parts: (string | ReactElement)[] = []
  let lastIndex = 0
  let match
  const re = new RegExp(URL_REGEX.source, 'gi')
  while ((match = re.exec(content)) !== null) {
    if (match.index > lastIndex) {
      parts.push(content.slice(lastIndex, match.index))
    }
    parts.push(
      <a key={match.index} href={match[0]} target="_blank" rel="noopener noreferrer">
        {match[0]}
      </a>
    )
    lastIndex = re.lastIndex
  }
  if (lastIndex < content.length) {
    parts.push(content.slice(lastIndex))
  }
  return parts.length ? parts : content
}

export interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fallback?: boolean
}

const API_BASE = '/api'

interface ChatViewProps {
  messages: Message[]
  onMessagesChange: (messages: Message[] | ((prev: Message[]) => Message[])) => void
}

export function ChatView({ messages, onMessagesChange }: ChatViewProps) {
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

  const sendMessage = async () => {
    const text = input.trim()
    if (!text || loading) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: text,
    }
    setMessages((m) => [...m, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: text }),
      })
      const textRes = await res.text()
      let data: { reply?: string; fallback?: boolean; detail?: string }
      try {
        data = textRes ? JSON.parse(textRes) : {}
      } catch {
        if (!res.ok) {
          throw new Error(textRes || `Request failed (${res.status})`)
        }
        throw new Error('Invalid response from server')
      }
      if (!res.ok) throw new Error(data.detail || textRes || 'Failed to send')

      const botMsg: Message = {
        id: crypto.randomUUID(),
        role: 'bot',
        content: data.reply ?? '',
        fallback: data.fallback,
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
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((m) => (
          <div
            key={m.id}
            className={`message-row ${m.role}`}
          >
            {m.role === 'bot' && (
              <img
                src="/beccabot-avatar.png"
                alt="BeccaBot"
                className="message-avatar"
              />
            )}
            <div
              className={`message ${m.role} ${m.fallback ? 'fallback' : ''}`}
            >
              {formatMessageContent(m.content)}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message-row bot">
            <img
              src="/beccabot-avatar.png"
              alt="BeccaBot"
              className="message-avatar"
            />
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
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage()}
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
