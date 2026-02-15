import { useState, useEffect, useRef } from 'react'
import axios from 'axios'

function ChatPanel({ jobId, isOpen, onToggle }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const messagesEndRef = useRef(null)
  const inputRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    if (isOpen && inputRef.current) {
      inputRef.current.focus()
    }
  }, [isOpen])

  async function sendMessage() {
    if (!input.trim() || loading) return

    const userMessage = input.trim()
    setInput('')

    const newMessages = [...messages, { role: 'user', content: userMessage }]
    setMessages(newMessages)
    setLoading(true)

    try {
      const res = await axios.post(`/api/jobs/${jobId}/chat`, {
        message: userMessage,
        conversation_history: newMessages.map(m => ({
          role: m.role,
          content: m.content,
        })),
      })

      setMessages([
        ...newMessages,
        { role: 'assistant', content: res.data.response },
      ])
    } catch (err) {
      console.error('Chat error:', err)
      setMessages([
        ...newMessages,
        {
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please check that the backend is running and an LLM provider is configured.',
        },
      ])
    } finally {
      setLoading(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  function handleQuickQuestion(question) {
    setInput(question)
    setTimeout(() => {
      sendMessage()
    }, 0)
  }

  // Quick question helper — set input and trigger send on next render
  useEffect(() => {
    if (input && input.startsWith('__quick__')) {
      const msg = input.replace('__quick__', '')
      setInput('')
      const fakeMessages = [...messages, { role: 'user', content: msg }]
      setMessages(fakeMessages)
      setLoading(true)

      axios.post(`/api/jobs/${jobId}/chat`, {
        message: msg,
        conversation_history: fakeMessages.map(m => ({ role: m.role, content: m.content })),
      }).then(res => {
        setMessages([...fakeMessages, { role: 'assistant', content: res.data.response }])
      }).catch(() => {
        setMessages([...fakeMessages, { role: 'assistant', content: 'Sorry, something went wrong.' }])
      }).finally(() => {
        setLoading(false)
      })
    }
  }, [input])

  function askQuick(question) {
    if (loading) return
    setInput('__quick__' + question)
  }

  return (
    <>
      {/* Toggle button */}
      <button
        className={`chat-toggle ${isOpen ? 'chat-toggle-open' : ''}`}
        onClick={onToggle}
        title={isOpen ? 'Close Litterly' : 'Open Litterly'}
      >
        {isOpen ? '\u2715' : '\u{1F4AC}'}
      </button>

      {/* Chat panel */}
      <div className={`chat-panel ${isOpen ? 'open' : ''}`}>
        <div className="chat-header">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <div>
              <h3>Litterly</h3>
              <p>AI Assistant</p>
            </div>
            <button
              className="chat-clear"
              onClick={() => setMessages([])}
              title="Clear chat"
            >
              Clear
            </button>
          </div>
        </div>

        <div className="chat-messages">
          {messages.length === 0 && (
            <div className="chat-welcome">
              <p>Hi! I'm <strong>Litterly</strong>, your AI assistant.</p>
              <p>I can help you with:</p>
              <div className="chat-suggestions">
                <button onClick={() => askQuick("What's the job status?")}>
                  Job status
                </button>
                <button onClick={() => askQuick("Why did products fail?")}>
                  Error diagnosis
                </button>
                <button onClick={() => askQuick("Show me the CSV data")}>
                  CSV preview
                </button>
                <button onClick={() => askQuick("How does the pipeline work?")}>
                  How it works
                </button>
              </div>
            </div>
          )}

          {messages.map((msg, idx) => (
            <div key={idx} className={`chat-message ${msg.role}`}>
              <div className="message-content">
                {msg.role === 'assistant' ? (
                  <div dangerouslySetInnerHTML={{ __html: formatMarkdown(msg.content) }} />
                ) : (
                  msg.content
                )}
              </div>
            </div>
          ))}

          {loading && (
            <div className="chat-message assistant">
              <div className="message-content loading-dots">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        <div className="chat-input">
          <textarea
            ref={inputRef}
            value={input.startsWith('__quick__') ? '' : input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask Litterly anything..."
            rows={2}
            disabled={loading}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading || input.startsWith('__quick__')}
            className="btn btn-primary chat-send"
          >
            Send
          </button>
        </div>
      </div>
    </>
  )
}

/**
 * Simple markdown to HTML converter for chat responses.
 */
function formatMarkdown(text) {
  if (!text) return ''
  let html = text
    // Escape HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // Bold
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    // Inline code
    .replace(/`(.+?)`/g, '<code>$1</code>')
    // Bullet lists
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    // Numbered lists
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    // Wrap consecutive <li> in <ul>
    .replace(/((?:<li>.*<\/li>\n?)+)/g, '<ul>$1</ul>')
    // Line breaks
    .replace(/\n\n/g, '<br/><br/>')
    .replace(/\n/g, '<br/>')

  return html
}

export default ChatPanel
