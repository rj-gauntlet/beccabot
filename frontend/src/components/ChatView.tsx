import { useState, useRef, useEffect } from 'react'

interface Message {
  id: string
  role: 'user' | 'bot'
  content: string
  fallback?: boolean
}

const API_BASE = '/api'

export function ChatView() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

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
        content: data.reply,
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
        {messages.length === 0 && (
          <div className="welcome">
            <h2>Hey there!</h2>
            <p>
              I'm BeccaBot. Ask me anything about Gauntlet AI's programs — I'm
              here to help. What's on your mind?
            </p>
          </div>
        )}
        {messages.map((m) => (
          <div
            key={m.id}
            className={`message ${m.role} ${m.fallback ? 'fallback' : ''}`}
          >
            {m.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>
      <div className="chat-input-row">
        <input
          type="text"
          className="chat-input"
          placeholder="Ask me anything..."
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
