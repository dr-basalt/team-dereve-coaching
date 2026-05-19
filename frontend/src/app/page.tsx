'use client'

import { useChat } from 'ai/react'
import { useEffect, useRef } from 'react'

export default function Home() {
  const { messages, input, handleInputChange, handleSubmit, isLoading } = useChat({
    api: '/api/chat',
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  return (
    <div className="app">
      <div className="header">
        <h1>Team Dereve - Coaching IA</h1>
        <p>Plateforme de coaching avec intelligence artificielle</p>
        <div className="coaches">
          <span className="coach-badge coach-max">Max - Business</span>
          <span className="coach-badge coach-forge">Forge - Sport</span>
          <span className="coach-badge coach-myriam">Myriam - Emotions</span>
        </div>
      </div>

      <div className="messages">
        {messages.length === 0 && (
          <div className="empty-state">
            Pose ta question. L&apos;IA la redirige automatiquement<br />
            vers le coach le plus pertinent.
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={`message message-${m.role}`}>
            {m.content}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <form onSubmit={handleSubmit} className="input-form">
          <input
            className="input-field"
            value={input}
            onChange={handleInputChange}
            placeholder="Dis-moi ce qui t'amène..."
            disabled={isLoading}
          />
          <button type="submit" className="send-btn" disabled={isLoading || !input.trim()}>
            {isLoading ? '...' : 'Envoyer'}
          </button>
        </form>
      </div>
    </div>
  )
}
