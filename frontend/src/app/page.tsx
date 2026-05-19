'use client'

import { useChat } from 'ai/react'
import { useEffect, useRef, useState, useCallback } from 'react'
import { useSession, signOut } from 'next-auth/react'

type Conversation = {
  id: string
  title: string
  updated_at: string
  message_count: number
}

type Document = {
  id: string
  name: string
  type: string
  size: number
  uploaded_at: string
}

export default function Home() {
  const { data: session } = useSession()
  const [conversations, setConversations] = useState<Conversation[]>([])
  const [currentConvoId, setCurrentConvoId] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [sidebarTab, setSidebarTab] = useState<'history' | 'docs'>('history')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const { messages, input, handleInputChange, handleSubmit, isLoading, setMessages } = useChat({
    api: '/api/chat',
    onFinish: () => {
      if (currentConvoId) saveConversation(currentConvoId)
    },
  })

  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  // Load conversations and documents on mount
  useEffect(() => {
    if (session?.user) {
      loadConversations()
      loadDocuments()
    }
  }, [session])

  const loadConversations = async () => {
    const res = await fetch('/api/conversations')
    if (res.ok) setConversations(await res.json())
  }

  const loadDocuments = async () => {
    const res = await fetch('/api/documents')
    if (res.ok) setDocuments(await res.json())
  }

  const saveConversation = useCallback(async (convoId: string) => {
    const currentMessages = document.querySelectorAll('.message')
    const msgs = Array.from(currentMessages).map(el => ({
      role: el.classList.contains('message-user') ? 'user' : 'assistant',
      content: el.textContent || '',
    }))
    if (msgs.length === 0) return

    const title = msgs[0]?.content?.slice(0, 50) || 'Nouvelle conversation'
    await fetch(`/api/conversations/${convoId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: msgs, title }),
    })
    loadConversations()
  }, [])

  const newConversation = async () => {
    // Save current conversation first
    if (currentConvoId && messages.length > 0) {
      await saveCurrentConvo()
    }
    const res = await fetch('/api/conversations', { method: 'POST' })
    if (res.ok) {
      const convo = await res.json()
      setCurrentConvoId(convo.id)
      setMessages([])
      loadConversations()
    }
  }

  const saveCurrentConvo = async () => {
    if (!currentConvoId || messages.length === 0) return
    const title = messages[0]?.content?.slice(0, 50) || 'Nouvelle conversation'
    await fetch(`/api/conversations/${currentConvoId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages: messages.map(m => ({ role: m.role, content: m.content })),
        title,
      }),
    })
  }

  const loadConversation = async (convoId: string) => {
    if (currentConvoId && messages.length > 0) {
      await saveCurrentConvo()
    }
    const res = await fetch(`/api/conversations/${convoId}`)
    if (res.ok) {
      const convo = await res.json()
      setCurrentConvoId(convoId)
      setMessages(
        (convo.messages || []).map((m: { role: string; content: string }, i: number) => ({
          id: `${convoId}-${i}`,
          role: m.role as 'user' | 'assistant',
          content: m.content,
        }))
      )
    }
  }

  const deleteConversation = async (convoId: string, e: React.MouseEvent) => {
    e.stopPropagation()
    await fetch(`/api/conversations/${convoId}`, { method: 'DELETE' })
    if (currentConvoId === convoId) {
      setCurrentConvoId(null)
      setMessages([])
    }
    loadConversations()
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const formData = new FormData()
    formData.append('file', file)
    formData.append('doc_type', 'document')
    await fetch('/api/documents/upload', { method: 'POST', body: formData })
    loadDocuments()
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const deleteDocument = async (docId: string) => {
    await fetch(`/api/documents/${docId}`, { method: 'DELETE' })
    loadDocuments()
  }

  const handleFormSubmit = async (e: React.FormEvent) => {
    if (!currentConvoId) {
      const res = await fetch('/api/conversations', { method: 'POST' })
      if (res.ok) {
        const convo = await res.json()
        setCurrentConvoId(convo.id)
        loadConversations()
      }
    }
    handleSubmit(e)
  }

  return (
    <div className="layout">
      {/* Sidebar */}
      <div className={`sidebar ${sidebarOpen ? 'open' : 'closed'}`}>
        <div className="sidebar-header">
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

        <button onClick={newConversation} className="new-convo-btn">
          + Nouvelle conversation
        </button>

        <div className="sidebar-tabs">
          <button
            className={`tab ${sidebarTab === 'history' ? 'active' : ''}`}
            onClick={() => setSidebarTab('history')}
          >
            Historique
          </button>
          <button
            className={`tab ${sidebarTab === 'docs' ? 'active' : ''}`}
            onClick={() => setSidebarTab('docs')}
          >
            Documents
          </button>
        </div>

        {sidebarTab === 'history' ? (
          <div className="convo-list">
            {conversations.map(c => (
              <div
                key={c.id}
                className={`convo-item ${currentConvoId === c.id ? 'active' : ''}`}
                onClick={() => loadConversation(c.id)}
              >
                <span className="convo-title">{c.title}</span>
                <button
                  className="convo-delete"
                  onClick={(e) => deleteConversation(c.id, e)}
                >
                  x
                </button>
              </div>
            ))}
            {conversations.length === 0 && (
              <p className="sidebar-empty">Aucune conversation</p>
            )}
          </div>
        ) : (
          <div className="docs-list">
            <button
              className="upload-btn"
              onClick={() => fileInputRef.current?.click()}
            >
              Ajouter un document
            </button>
            <input
              ref={fileInputRef}
              type="file"
              accept=".txt,.md,.pdf,.json"
              onChange={handleFileUpload}
              style={{ display: 'none' }}
            />
            {documents.map(d => (
              <div key={d.id} className="doc-item">
                <span className="doc-name">{d.name}</span>
                <button
                  className="doc-delete"
                  onClick={() => deleteDocument(d.id)}
                >
                  x
                </button>
              </div>
            ))}
            {documents.length === 0 && (
              <p className="sidebar-empty">Aucun document</p>
            )}
            <p className="docs-hint">
              Les documents uploades sont automatiquement accessibles par les coaches.
            </p>
          </div>
        )}
      </div>

      {/* Toggle sidebar on mobile */}
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen(!sidebarOpen)}
      >
        {sidebarOpen ? '\u2190' : '\u2192'}
      </button>

      {/* Main chat area */}
      <div className="main">
        <div className="header">
          <h1>Team Dereve - Coaching IA</h1>
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
          <form onSubmit={handleFormSubmit} className="input-form">
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
    </div>
  )
}
