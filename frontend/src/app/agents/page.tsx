'use client'

import { useEffect, useState, useRef } from 'react'
import { useSession } from 'next-auth/react'
import Link from 'next/link'

type Agent = {
  id: string
  name: string
  description: string
  color: string
  prompt?: string
  prompt_length?: number
  resource_count?: number
}

type Resource = {
  id: string
  name: string
  size: number
  uploaded_at: string
}

export default function AgentsPage() {
  const { data: session } = useSession()
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [agentDetail, setAgentDetail] = useState<Agent | null>(null)
  const [resources, setResources] = useState<Resource[]>([])
  const [editPrompt, setEditPrompt] = useState('')
  const [editName, setEditName] = useState('')
  const [editDesc, setEditDesc] = useState('')
  const [editColor, setEditColor] = useState('')
  const [saving, setSaving] = useState(false)
  const [showNewAgent, setShowNewAgent] = useState(false)
  const [newAgentId, setNewAgentId] = useState('')
  const [newAgentName, setNewAgentName] = useState('')
  const [newAgentDesc, setNewAgentDesc] = useState('')
  const [newAgentColor, setNewAgentColor] = useState('#888888')
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (session?.user) loadAgents()
  }, [session])

  const loadAgents = async () => {
    const res = await fetch('/api/agents')
    if (res.ok) setAgents(await res.json())
  }

  const selectAgent = async (agentId: string) => {
    setSelectedAgent(agentId)
    const res = await fetch(`/api/agents/${agentId}`)
    if (res.ok) {
      const data = await res.json()
      setAgentDetail(data)
      setEditPrompt(data.prompt || '')
      setEditName(data.name || '')
      setEditDesc(data.description || '')
      setEditColor(data.color || '#888')
    }
    const resRes = await fetch(`/api/agents/${agentId}/resources`)
    if (resRes.ok) setResources(await resRes.json())
  }

  const saveAgent = async () => {
    if (!selectedAgent) return
    setSaving(true)
    await fetch(`/api/agents/${selectedAgent}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: editName,
        description: editDesc,
        color: editColor,
        prompt: editPrompt,
      }),
    })
    setSaving(false)
    loadAgents()
  }

  const createAgent = async () => {
    if (!newAgentName) return
    await fetch('/api/agents', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        id: newAgentId || newAgentName.toLowerCase().replace(/\s+/g, '-'),
        name: newAgentName,
        description: newAgentDesc,
        color: newAgentColor,
      }),
    })
    setShowNewAgent(false)
    setNewAgentId('')
    setNewAgentName('')
    setNewAgentDesc('')
    setNewAgentColor('#888888')
    loadAgents()
  }

  const deleteAgent = async (agentId: string) => {
    if (!confirm(`Supprimer l'agent ${agentId} ?`)) return
    await fetch(`/api/agents/${agentId}`, { method: 'DELETE' })
    if (selectedAgent === agentId) {
      setSelectedAgent(null)
      setAgentDetail(null)
    }
    loadAgents()
  }

  const uploadResource = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file || !selectedAgent) return
    const formData = new FormData()
    formData.append('file', file)
    await fetch(`/api/agents/${selectedAgent}/resources/upload`, {
      method: 'POST',
      body: formData,
    })
    const res = await fetch(`/api/agents/${selectedAgent}/resources`)
    if (res.ok) setResources(await res.json())
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const deleteResource = async (resId: string) => {
    if (!selectedAgent) return
    await fetch(`/api/agents/${selectedAgent}/resources/${resId}`, { method: 'DELETE' })
    const res = await fetch(`/api/agents/${selectedAgent}/resources`)
    if (res.ok) setResources(await res.json())
  }

  return (
    <div className="agents-page">
      <div className="agents-header">
        <Link href="/" className="back-link">&larr; Retour au chat</Link>
        <h1>Gestion des agents</h1>
      </div>

      <div className="agents-layout">
        {/* Agent list */}
        <div className="agents-list">
          {agents.map(a => (
            <div
              key={a.id}
              className={`agent-card ${selectedAgent === a.id ? 'selected' : ''}`}
              onClick={() => selectAgent(a.id)}
            >
              <div className="agent-card-dot" style={{ background: a.color }} />
              <div className="agent-card-info">
                <span className="agent-card-name">{a.name}</span>
                <span className="agent-card-desc">{a.description}</span>
                <span className="agent-card-meta">
                  {a.prompt_length ? `${Math.round(a.prompt_length / 100) / 10}k car.` : ''}
                  {a.resource_count ? ` · ${a.resource_count} ressource${a.resource_count > 1 ? 's' : ''}` : ''}
                </span>
              </div>
              <button
                className="agent-card-delete"
                onClick={(e) => { e.stopPropagation(); deleteAgent(a.id) }}
              >
                x
              </button>
            </div>
          ))}

          {showNewAgent ? (
            <div className="new-agent-form">
              <input
                placeholder="ID (ex: alex)"
                value={newAgentId}
                onChange={e => setNewAgentId(e.target.value)}
                className="agent-input"
              />
              <input
                placeholder="Nom (ex: Alex)"
                value={newAgentName}
                onChange={e => setNewAgentName(e.target.value)}
                className="agent-input"
              />
              <input
                placeholder="Description"
                value={newAgentDesc}
                onChange={e => setNewAgentDesc(e.target.value)}
                className="agent-input"
              />
              <div className="new-agent-actions">
                <input
                  type="color"
                  value={newAgentColor}
                  onChange={e => setNewAgentColor(e.target.value)}
                  className="color-picker"
                />
                <button onClick={createAgent} className="btn-create">Creer</button>
                <button onClick={() => setShowNewAgent(false)} className="btn-cancel">Annuler</button>
              </div>
            </div>
          ) : (
            <button className="add-agent-btn" onClick={() => setShowNewAgent(true)}>
              + Ajouter un agent
            </button>
          )}
        </div>

        {/* Agent detail */}
        {agentDetail && selectedAgent ? (
          <div className="agent-detail">
            <div className="detail-section">
              <h2>
                <span className="detail-dot" style={{ background: editColor }} />
                Configuration
              </h2>
              <div className="detail-fields">
                <label>Nom</label>
                <input value={editName} onChange={e => setEditName(e.target.value)} className="agent-input" />
                <label>Description</label>
                <input value={editDesc} onChange={e => setEditDesc(e.target.value)} className="agent-input" />
                <label>Couleur</label>
                <input type="color" value={editColor} onChange={e => setEditColor(e.target.value)} className="color-picker-large" />
              </div>
            </div>

            <div className="detail-section">
              <h2>Instructions (System Prompt)</h2>
              <textarea
                value={editPrompt}
                onChange={e => setEditPrompt(e.target.value)}
                className="prompt-editor"
                rows={20}
                placeholder="Instructions pour l'agent..."
              />
              <div className="prompt-meta">
                {editPrompt.length} caracteres
              </div>
            </div>

            <div className="detail-section">
              <h2>Ressources ({resources.length})</h2>
              <p className="resources-hint">
                Documents accessibles par cet agent (methodes, frameworks, references...)
              </p>
              <button
                className="upload-resource-btn"
                onClick={() => fileInputRef.current?.click()}
              >
                + Ajouter une ressource
              </button>
              <input
                ref={fileInputRef}
                type="file"
                accept=".txt,.md,.pdf,.json"
                onChange={uploadResource}
                style={{ display: 'none' }}
              />
              <div className="resources-list">
                {resources.map(r => (
                  <div key={r.id} className="resource-item">
                    <span className="resource-name">{r.name}</span>
                    <span className="resource-size">{(r.size / 1024).toFixed(1)} KB</span>
                    <button className="resource-delete" onClick={() => deleteResource(r.id)}>x</button>
                  </div>
                ))}
              </div>
            </div>

            <div className="detail-actions">
              <button onClick={saveAgent} className="btn-save" disabled={saving}>
                {saving ? 'Sauvegarde...' : 'Sauvegarder'}
              </button>
            </div>
          </div>
        ) : (
          <div className="agent-detail-empty">
            Selectionne un agent pour le configurer
          </div>
        )}
      </div>
    </div>
  )
}
