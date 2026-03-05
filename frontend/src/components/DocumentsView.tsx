import { useState, useEffect, useCallback } from 'react'

const API_BASE = '/api'

async function parseJsonResponse<T = unknown>(res: Response): Promise<T> {
  const text = await res.text()
  try {
    return (text ? JSON.parse(text) : {}) as T
  } catch {
    throw new Error(res.ok ? 'Invalid response from server' : text || `Request failed (${res.status})`)
  }
}

interface DocumentInfo {
  id: string
  name: string
  size?: number
  url?: string
  type?: 'file' | 'link' | 'manual'
}

interface DocumentsViewProps {
  pin?: string
  onLock?: () => void
}

export function DocumentsView({ pin, onLock }: DocumentsViewProps) {
  const headers = (): HeadersInit => {
    const h: Record<string, string> = {}
    if (pin) h['X-Documents-PIN'] = pin
    return h
  }
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [addingLink, setAddingLink] = useState(false)
  const [linkUrl, setLinkUrl] = useState('')
  const [linkTitle, setLinkTitle] = useState('')
  const [dragover, setDragover] = useState(false)
  const [manualText, setManualText] = useState('')
  const [ingesting, setIngesting] = useState(false)
  const [reindexingId, setReindexingId] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents`, { headers: headers() })
      const data = await parseJsonResponse<{ documents?: DocumentInfo[]; manualText?: string }>(res)
      setDocuments(data.documents || [])
      setManualText(data.manualText ?? '')
    } catch {
      setDocuments([])
    } finally {
      setLoading(false)
    }
  }, [pin])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  const handleUpload = async (files: FileList | null) => {
    if (!files?.length || uploading) return
    const file = files[0]
    const ext = '.' + (file.name.split('.').pop() || '').toLowerCase()
    const allowed = ['.pdf', '.docx', '.doc', '.txt', '.pptx', '.ppt', '.xlsx', '.csv']
    if (!allowed.includes(ext)) {
      alert(`Unsupported file type. Please upload: ${allowed.join(', ')}`)
      return
    }

    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch(`${API_BASE}/documents/upload`, {
        method: 'POST',
        headers: headers(),
        body: formData,
      })
      const data = await parseJsonResponse<{ detail?: string; warning?: string }>(res)
      if (!res.ok) throw new Error(data.detail || 'Upload failed')
      if (data.warning) alert(data.warning)
      await fetchDocuments()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleIngestManual = async () => {
    const text = manualText.trim()
    if (!text || ingesting) return
    setIngesting(true)
    try {
      const res = await fetch(`${API_BASE}/documents/manual`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers() },
        body: JSON.stringify({ text }),
      })
      const data = await parseJsonResponse<{ detail?: string }>(res)
      if (!res.ok) throw new Error(data.detail || 'Ingest failed')
      await fetchDocuments()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to ingest')
    } finally {
      setIngesting(false)
    }
  }

  const handleAddLink = async () => {
    const url = linkUrl.trim()
    if (!url || addingLink) return
    if (!url.startsWith('http://') && !url.startsWith('https://')) {
      alert('Please enter a valid URL starting with http:// or https://')
      return
    }
    setAddingLink(true)
    try {
      const res = await fetch(`${API_BASE}/documents/link`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers() },
        body: JSON.stringify({ url, title: linkTitle.trim() || undefined }),
      })
      const data = await parseJsonResponse<{ detail?: string; warning?: string }>(res)
      if (!res.ok) throw new Error(data.detail || 'Failed to add link')
      if (data.warning) alert(data.warning)
      setLinkUrl('')
      setLinkTitle('')
      await fetchDocuments()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to add link')
    } finally {
      setAddingLink(false)
    }
  }

  const handleReindex = async (doc: DocumentInfo) => {
    if (doc.type === 'manual') return
    setReindexingId(doc.id)
    try {
      const res = await fetch(`${API_BASE}/documents/reindex`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers() },
        body: JSON.stringify({ id: doc.id }),
      })
      const data = await parseJsonResponse<{ detail?: string; chunks?: number }>(res)
      if (!res.ok) throw new Error(data.detail || 'Reindex failed')
      if (data.chunks === 0) {
        alert('No text could be extracted. For scanned PDFs, install Tesseract OCR (see README).')
      }
      await fetchDocuments()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Reindex failed')
    } finally {
      setReindexingId(null)
    }
  }

  const handleDelete = async (doc: DocumentInfo) => {
    const label = doc.type === 'link' ? doc.name : doc.id
    if (!confirm(`Delete "${label}"? This cannot be undone.`)) return
    try {
      const res = await fetch(`${API_BASE}/documents/delete`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...headers() },
        body: JSON.stringify({ id: doc.id }),
      })
      if (!res.ok) {
        const data = await parseJsonResponse<{ detail?: string }>(res)
        throw new Error(data.detail || 'Delete failed')
      }
      await fetchDocuments()
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Delete failed')
    }
  }

  const formatSize = (bytes: number | undefined) => {
    if (bytes == null || bytes < 1024) return (bytes ?? 0) + ' B'
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  }

  return (
    <div className="documents-section">
      <div className="documents-header">
        <h2>Document library</h2>
        {onLock && (
          <button className="lock-btn" onClick={onLock} title="Lock Documents">
            🔒 Lock
          </button>
        )}
      </div>
      <p style={{ color: 'var(--gauntlet-gray)', marginBottom: '1rem' }}>
        Upload files or add links. BeccaBot will use them to answer questions.
      </p>

      <div className="add-link-section">
        <label htmlFor="manual-text">Manual notes</label>
        <p style={{ color: 'var(--gauntlet-gray)', fontSize: '0.9rem', margin: '0.25rem 0 0.5rem' }}>
          Paste or type info to add directly to BeccaBot&apos;s knowledge. Saving replaces any existing manual notes.
        </p>
        <textarea
          id="manual-text"
          className="manual-textarea"
          placeholder="Housing address: PlaceMakr, 710 E 3rd St... Emergency contact: ..."
          value={manualText}
          onChange={(e) => setManualText(e.target.value)}
          rows={4}
        />
        <button
          className="add-link-btn"
          onClick={handleIngestManual}
          disabled={ingesting || !manualText.trim()}
          style={{ marginTop: '0.5rem' }}
        >
          {ingesting ? 'Ingesting...' : 'Ingest'}
        </button>
      </div>

      <div className="add-link-section">
        <label htmlFor="link-url">Add a link</label>
        <div className="add-link-row">
          <input
            id="link-url"
            type="url"
            className="link-input"
            placeholder="https://example.com/page"
            value={linkUrl}
            onChange={(e) => setLinkUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleAddLink()}
          />
          <input
            type="text"
            className="link-title-input"
            placeholder="Title (optional)"
            value={linkTitle}
            onChange={(e) => setLinkTitle(e.target.value)}
          />
          <button
            className="add-link-btn"
            onClick={handleAddLink}
            disabled={addingLink || !linkUrl.trim()}
          >
            {addingLink ? 'Adding...' : 'Add'}
          </button>
        </div>
      </div>

      <div
        className={`upload-zone ${dragover ? 'dragover' : ''}`}
        onClick={() => document.getElementById('file-input')?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setDragover(true)
        }}
        onDragLeave={() => setDragover(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragover(false)
          handleUpload(e.dataTransfer.files)
        }}
      >
        <input
          id="file-input"
          type="file"
          accept=".pdf,.docx,.doc,.txt,.pptx,.ppt,.xlsx,.csv"
          onChange={(e) => handleUpload(e.target.files)}
        />
        <p>
          {uploading
            ? 'Uploading...'
            : 'Drop a file here or click to upload'}
        </p>
      </div>

      {loading ? (
        <div className="loading">Loading documents...</div>
      ) : documents.length === 0 ? (
        <div className="empty-state">
          No documents yet. Upload your first file above.
        </div>
      ) : (
        <ul className="doc-list">
          {documents.map((doc) => (
            <li key={doc.id} className="doc-item">
              <span>
                {doc.type === 'link' ? (
                  <>
                    <a href={doc.url} target="_blank" rel="noopener noreferrer" className="doc-link">
                      {doc.name}
                    </a>
                    <span style={{ color: 'var(--gauntlet-gray)', fontSize: '0.85em' }}> (link)</span>
                  </>
                ) : doc.type === 'manual' ? (
                  <>
                    {doc.name}{' '}
                    <span style={{ color: 'var(--gauntlet-gray)', fontSize: '0.85em' }}>(manual notes)</span>
                  </>
                ) : (
                  <>
                    {doc.name}{' '}
                    <span style={{ color: 'var(--gauntlet-gray)', fontSize: '0.85em' }}>
                      ({doc.size != null ? formatSize(doc.size) : 'file'})
                    </span>
                  </>
                )}
              </span>
              <span className="doc-actions">
                {doc.type !== 'manual' && (
                  <button
                    className="reindex-btn"
                    onClick={() => handleReindex(doc)}
                    disabled={reindexingId === doc.id}
                    aria-label={`Reindex ${doc.name}`}
                  >
                    {reindexingId === doc.id ? (
                      <>
                        <span className="reindex-spinner" aria-hidden />
                        Reindexing...
                      </>
                    ) : (
                      'Reindex'
                    )}
                  </button>
                )}
                <button
                  className="delete-btn"
                  onClick={() => handleDelete(doc)}
                  aria-label={`Delete ${doc.name}`}
                >
                  Delete
                </button>
              </span>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
