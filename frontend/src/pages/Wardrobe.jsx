import { useCallback, useEffect, useRef, useState } from 'react'
import api from '../api/client.js'

const LOADING_MESSAGES = [
  'Snipping away the background…',
  'Looking closely at the details…',
  'Finding its place in your closet…',
  'Almost ready for its close-up…',
]
const EDIT_FIELDS = [
  ['category', 'Category'],
  ['subcategory', 'Item type'],
  ['colour', 'Colour'],
  ['colour_detailed', 'Detailed colour'],
  ['pattern', 'Pattern'],
  ['style', 'Style'],
  ['fit', 'Fit'],
  ['season', 'Season'],
]

function imageUrl(path) {
  if (!path) return ''
  if (/^https?:\/\//i.test(path)) return path
  return `${api.defaults.baseURL}/${path.replace(/^\/+/, '')}`
}

function guessCategory(label = '') {
  const value = label.toLowerCase()
  if (/shoe|sneaker|boot|heel|pump|flat|sandal|loafer|mule|clog|wedge|slipper|trainer/.test(value)) return 'shoes'
  if (/bag|backpack|clutch|handbag|wallet|purse|hat|cap|beanie|jewell|necklace|earring|bracelet|ring|scarf|belt|sunglass|glove|tie|watch|sock|bandana|shawl|umbrella/.test(value)) return 'accessory'
  if (/dress|gown|sundress/.test(value)) return 'dress'
  if (/jacket|blazer|coat|parka|poncho|cape|kimono|anorak|shacket|windbreaker|overcoat|peacoat|raincoat/.test(value)) return 'outerwear'
  if (/jean|trouser|pant|short|legging|jogger|skirt|culotte|tights|capri|swim trunk/.test(value)) return 'bottom'
  return 'top'
}

function Photo({ src, alt, className = '' }) {
  const [failedSrc, setFailedSrc] = useState('')
  const failed = failedSrc === src
  if (!src || failed) {
    return <div className={`photo-fallback ${className}`} aria-label="Clothing image unavailable"><span>✿</span></div>
  }
  return <img className={className} src={src} alt={alt} onError={() => setFailedSrc(src)} />
}

function FieldValue({ label, value, uncertain, swatch = false }) {
  return (
    <div className={`result-field${uncertain ? ' is-uncertain' : ''}`}>
      <span className="field-label">{label}</span>
      <span className="field-value">{swatch && value && value !== 'uncertain' && <span className={`detail-swatch swatch-${value.toLowerCase().replace(/[^a-z]/g, '')}`} style={{ backgroundColor: value }} />} {value || 'Not set'}{uncertain && <span className="uncertain-dot"> ✦</span>}</span>
    </div>
  )
}

function Wardrobe() {
  const userId = Number(localStorage.getItem('user_id'))
  const fileInput = useRef(null)
  const [file, setFile] = useState(null)
  const [preview, setPreview] = useState('')
  const [items, setItems] = useState([])
  const [latest, setLatest] = useState(null)
  const [loading, setLoading] = useState(false)
  const [loadingStep, setLoadingStep] = useState(0)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [editingId, setEditingId] = useState(null)
  const [draft, setDraft] = useState({})
  const [saving, setSaving] = useState(false)

  const loadItems = useCallback(async () => {
    try {
      const response = await api.get(`/api/wardrobe/${userId}`)
      setItems(response.data)
      setError('')
    } catch {
      setError('Could not reach your closet. Check that the stylist API is running, then try again.')
    }
  }, [userId])

  useEffect(() => {
    const request = window.setTimeout(loadItems, 0)
    return () => window.clearTimeout(request)
  }, [loadItems])

  useEffect(() => {
    if (!loading) return undefined
    const timer = window.setInterval(() => setLoadingStep((step) => (step + 1) % LOADING_MESSAGES.length), 4200)
    return () => window.clearInterval(timer)
  }, [loading])

  useEffect(() => () => {
    if (preview.startsWith('blob:')) URL.revokeObjectURL(preview)
  }, [preview])

  function chooseFile(event) {
    const picked = event.target.files?.[0]
    if (!picked) return
    if (preview.startsWith('blob:')) URL.revokeObjectURL(preview)
    setFile(picked)
    setPreview(URL.createObjectURL(picked))
    setLatest(null)
    setError('')
    setNotice('')
  }

  async function upload(event) {
    event.preventDefault()
    if (!file || loading) return
    setLoading(true)
    setLoadingStep(0)
    setError('')
    setNotice('')
    const data = new FormData()
    data.append('file', file)
    data.append('user_id', String(userId))
    try {
      const response = await api.post('/api/wardrobe/upload', data)
      setLatest({ ...response.data, localPreview: preview })
      setNotice('A new piece has been tucked into your closet!')
      await loadItems()
    } catch (uploadError) {
      setError(uploadError.response?.data?.detail || 'That upload didn’t go through. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  function startEdit(item) {
    setEditingId(item.id)
    setDraft(Object.fromEntries(EDIT_FIELDS.map(([key]) => [key, item[key] ?? ''])))
  }

  async function saveEdit(event, itemId) {
    event.preventDefault()
    setSaving(true)
    setError('')
    try {
      await api.patch(`/api/wardrobe/${itemId}`, draft)
      setEditingId(null)
      setNotice('Closet note updated ✨')
      await loadItems()
    } catch (saveError) {
      setError(saveError.response?.data?.detail || 'Could not save those changes. Please try again.')
    } finally {
      setSaving(false)
    }
  }

  async function selectCandidate(item, field, value) {
    const update = field === 'subcategory'
      ? { subcategory: value, category: item.category === 'uncertain' ? guessCategory(value) : item.category }
      : { [field]: value }
    setError('')
    try {
      await api.patch(`/api/wardrobe/${item.id}`, update)
      if (latest?.id === item.id) setLatest((current) => ({ ...current, ...update }))
      setNotice('Lovely choice. Your item has been updated!')
      await loadItems()
    } catch (selectionError) {
      setError(selectionError.response?.data?.detail || 'Could not update that item.')
    }
  }

  async function deleteItem(item) {
    const itemName = item.subcategory || item.category || 'this piece'
    if (!window.confirm(`Delete ${itemName} from your wardrobe? This will also remove its photo.`)) return

    const previousItems = items
    const previousLatest = latest
    setItems((current) => current.filter((closetItem) => closetItem.id !== item.id))
    if (latest?.id === item.id) setLatest(null)
    setError('')
    setNotice('')
    try {
      await api.delete(`/api/wardrobe/${item.id}`)
      setNotice('That piece has been removed from your closet.')
    } catch (deleteError) {
      setItems(previousItems)
      setLatest(previousLatest)
      setError(deleteError.response?.data?.detail || 'Could not delete that piece. It has been restored to your closet.')
    }
  }

  const closetItems = items.filter((item) => item.id !== latest?.id)

  return (
    <main className="app-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="Closet Club home">
          <span className="brand-mark">✿</span>
          <span>closet club<span className="brand-period">.</span></span>
        </a>
        <nav className="top-nav" aria-label="Main navigation">
          <a className="nav-link active" href="/">My wardrobe</a>
          <span className="nav-link muted">Outfit studio <span className="soon-tag">soon</span></span>
        </nav>
        <div className="profile-chip"><span className="profile-avatar">♡</span><span>My little closet</span></div>
      </header>

      <section className="welcome-row">
        <div>
          <p className="eyebrow"><span className="eyebrow-star">✦</span> YOUR PERSONAL STYLE SPACE</p>
          <h1>Welcome to your <span>wardrobe</span></h1>
          <p className="welcome-copy">A little place for all your favourite pieces. Add something new and let’s make it yours.</p>
        </div>
        <div className="welcome-sticker" aria-hidden="true"><span className="sticker-sparkle">✦</span><span className="sticker-heart">♡</span><span className="sticker-caption">your style<br />starts here</span></div>
      </section>

      <section className="workspace-grid">
        <aside className="upload-window window-frame">
          <div className="window-titlebar">
            <span className="titlebar-icon">✿</span><span>add a new piece</span>
            <span className="window-controls" aria-hidden="true"><i>−</i><i>□</i><i>×</i></span>
          </div>
          <div className="upload-body">
            <p className="panel-intro">Let’s give your closet a little something new.</p>
            <form onSubmit={upload}>
              <button className={`drop-zone${file ? ' has-file' : ''}`} type="button" onClick={() => fileInput.current?.click()} onDragOver={(event) => event.preventDefault()} onDrop={(event) => { event.preventDefault(); const dropped = event.dataTransfer.files?.[0]; if (dropped) { if (preview.startsWith('blob:')) URL.revokeObjectURL(preview); setFile(dropped); setPreview(URL.createObjectURL(dropped)); setLatest(null); setError(''); setNotice('') } }}>
                {preview ? <Photo src={preview} alt="Selected clothing preview" className="upload-preview" /> : <span className="hanger-illustration" aria-hidden="true">♧</span>}
                <span className="drop-title">{file ? file.name : 'Drop a piece here'}</span>
                <span className="drop-subtitle">or click to browse your photos</span>
                <span className="browse-label">choose a photo <span>↗</span></span>
              </button>
              <input ref={fileInput} className="visually-hidden" type="file" accept="image/png,image/jpeg,image/webp,image/bmp" onChange={chooseFile} />
              <button className="primary-button upload-button" type="submit" disabled={!file || loading}>
                {loading ? <><span className="button-spinner" /> Adding a little magic…</> : <>Add to my wardrobe <span>✦</span></>}
              </button>
            </form>
            {loading && <div className="loading-note" role="status"><span className="loading-orbit">✿</span><div><strong>{LOADING_MESSAGES[loadingStep]}</strong><span>This can take up to a minute — good things take time.</span></div></div>}
            {error && <p className="message error-message" role="alert">{error}</p>}
            {notice && !loading && <p className="message success-message" role="status">{notice}</p>}
            <div className="privacy-note"><span>♡</span> Just for your closet. Your photos stay yours.</div>
          </div>
        </aside>

        <section className="closet-window window-frame" aria-labelledby="closet-heading">
          <div className="window-titlebar closet-titlebar">
            <span className="titlebar-icon">▤</span><span>my closet</span>
            <span className="item-counter">{items.length} {items.length === 1 ? 'piece' : 'pieces'}</span>
          </div>
          <div className="closet-content">
            <div className="closet-heading-row"><div><p className="section-kicker">THE GOOD STUFF</p><h2 id="closet-heading">Your collection <span>♡</span></h2></div><span className="sort-pill">✧ &nbsp; newest first</span></div>

            {latest && (
              <article className="latest-card">
                <div className="latest-ribbon">JUST ADDED ✦</div>
                <Photo src={latest.localPreview || imageUrl(latest.image_path)} alt="Recently uploaded wardrobe item" className="latest-photo" />
                <div className="latest-details">
                  <div className="latest-heading"><div><span className="mini-kicker">YOUR NEW PIECE</span><h3>{latest.subcategory && latest.subcategory !== 'uncertain' ? latest.subcategory : 'Fresh from the style studio'}</h3></div><div className="latest-actions"><button type="button" className="latest-edit-button" onClick={() => startEdit(latest)}>✎ Edit</button><button type="button" className="latest-delete-button" onClick={() => deleteItem(latest)}>Delete</button><span className="new-badge">NEW</span></div></div>
                  <div className="result-fields">
                    <FieldValue label="Category" value={latest.category} uncertain={latest.category === 'uncertain'} />
                    <FieldValue label="Colour" value={latest.colour_detailed || latest.colour} swatch />
                    <FieldValue label="Pattern" value={latest.pattern} uncertain={latest.pattern === 'uncertain'} />
                    <FieldValue label="Style" value={latest.style} uncertain={latest.style === 'uncertain'} />
                  </div>
                  {(latest.category === 'uncertain' || latest.subcategory === 'uncertain') && latest.category_candidates?.length > 0 && <CandidateRow title="Pick an item type" field="subcategory" candidates={latest.category_candidates} onPick={(field, value) => selectCandidate(latest, field, value)} />}
                  {latest.style === 'uncertain' && latest.style_candidates?.length > 0 && <CandidateRow title="Pick a style" field="style" candidates={latest.style_candidates} onPick={(field, value) => selectCandidate(latest, field, value)} />}
                  {editingId === latest.id && <form className="latest-edit-form" onSubmit={(event) => saveEdit(event, latest.id)}><div className="edit-fields">{EDIT_FIELDS.map(([field, label]) => <label key={field}>{label}<input value={draft[field] ?? ''} onChange={(event) => setDraft((current) => ({ ...current, [field]: event.target.value }))} placeholder={`Add ${label.toLowerCase()}`} /></label>)}</div><button className="primary-button save-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes ♡'}</button></form>}
                </div>
              </article>
            )}

            {closetItems.length === 0 && !latest ? (
              <div className="empty-closet"><div className="empty-illustration">♡</div><h3>Your closet is waiting for its first piece</h3><p>Upload a favourite and it’ll show up here, ready to play dress-up.</p><button type="button" className="text-button" onClick={() => fileInput.current?.click()}>Add your first piece <span>↗</span></button></div>
            ) : (
              <div className="wardrobe-grid">
                {closetItems.map((item, index) => (
                  <article className="item-card" key={item.id} style={{ '--card-delay': `${Math.min(index, 8) * 35}ms` }}>
                    <div className="item-photo-wrap"><Photo src={imageUrl(item.image_path)} alt={item.subcategory || item.category || 'Wardrobe item'} className="item-photo" /><span className="item-number">{String(index + 1).padStart(2, '0')}</span><div className="item-actions"><button className="edit-trigger" type="button" onClick={() => startEdit(item)} aria-label={`Edit ${item.subcategory || item.category}`}>✎</button><button className="delete-trigger" type="button" onClick={() => deleteItem(item)} aria-label={`Delete ${item.subcategory || item.category}`}>×</button></div></div>
                    <div className="item-card-info"><h3>{item.subcategory || item.category || 'Untitled piece'}</h3><p><span className={`tiny-swatch swatch-${(item.colour || 'cream').toLowerCase().replace(/[^a-z]/g, '')}`} />{item.colour_detailed || item.colour || 'colour not set'} <span className="info-divider">·</span> {item.pattern || 'pattern not set'}</p></div>
                    {editingId === item.id && <form className="edit-form" onSubmit={(event) => saveEdit(event, item.id)}><div className="edit-form-heading"><strong>Make it yours</strong><button type="button" onClick={() => setEditingId(null)} aria-label="Close editor">×</button></div><div className="edit-fields">{EDIT_FIELDS.map(([field, label]) => <label key={field}>{label}<input value={draft[field] ?? ''} onChange={(event) => setDraft((current) => ({ ...current, [field]: event.target.value }))} placeholder={`Add ${label.toLowerCase()}`} /></label>)}</div><button className="primary-button save-button" type="submit" disabled={saving}>{saving ? 'Saving…' : 'Save changes ♡'}</button></form>}
                  </article>
                ))}
              </div>
            )}
            {closetItems.length > 0 && <p className="closet-footnote">A closet full of possibilities <span>✦</span></p>}
          </div>
        </section>
      </section>
      <footer className="page-footer"><span>made with a little love <b>♡</b></span><span>YOUR CLOSET, YOUR RULES</span></footer>
    </main>
  )
}

function CandidateRow({ title, field, candidates, onPick }) {
  return <div className="candidate-block"><span className="candidate-title">{title} <span>— choose one to update</span></span><div className="candidate-pills">{candidates.slice(0, 3).map((candidate) => <button key={candidate.label} type="button" className="candidate-pill" onClick={() => onPick(field, candidate.label)}>{candidate.label}<span>{Math.round(candidate.score * 100)}%</span></button>)}</div></div>
}

export default Wardrobe
