'use client'

import { useChat } from 'ai/react'
import { useEffect, useRef } from 'react'
import { useSession, signOut } from 'next-auth/react'

export default function Home() {
  const { data: session } = useSession()
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
        <div className="header-top">
          {session?.user && (
            <div className="user-info">
              {session.user.image && (
                <img src={session.user.image} alt="" className="user-avatar" />
              )}
              <span className="user-name">{session.user.name}</span>
            </div>
          )}
          <button onClick={() => signOut()} className="signout-btn">
            Deconnexion
          </button>
        </div>
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
            placeholder="Dis-moi ce qui t'amene..."
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
