import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import api from '../api/client.js'

function Home() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  async function enterCloset(event) {
    event.preventDefault()
    if (loading) return
    setError('')

    const existingUserId = localStorage.getItem('user_id')
    if (existingUserId) {
      navigate('/wardrobe')
      return
    }

    setLoading(true)
    try {
      const response = await api.post('/api/users', { name: name.trim() || 'Guest' })
      localStorage.setItem('user_id', String(response.data.id))
      navigate('/wardrobe')
    } catch (requestError) {
      setError(requestError.response?.data?.detail || 'Could not open your closet. Is the stylist API running?')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="home-page">
      <div className="home-desktop-note" aria-hidden="true">STYLE_OS // PERSONAL EDITION <span>● ● ●</span></div>
      <section className="home-window" aria-labelledby="home-title">
        <div className="home-titlebar">
          <span className="home-program-icon">♡</span>
          <span className="home-program-name">closet_club.exe</span>
          <div className="home-window-controls" aria-hidden="true"><span>−</span><span>×</span></div>
        </div>

        <div className="home-content">
          <div className="home-badge" aria-hidden="true"><span>♡</span><i>✦</i></div>
          <p className="home-overline">YOUR VERY OWN STYLE SPACE</p>
          <h1 id="home-title">closet club<span>.</span></h1>
          <p className="home-tagline">a little closet, a lot of possibilities</p>

          <form className="home-login-card" onSubmit={enterCloset}>
            <label htmlFor="closet-name">&gt; what should we call you?</label>
            <input
              id="closet-name"
              name="name"
              type="text"
              autoComplete="given-name"
              maxLength={80}
              placeholder="your lovely name"
              value={name}
              onChange={(event) => setName(event.target.value)}
            />
            {error && <p className="home-error" role="alert">{error}</p>}
            <button className="home-enter-button" type="submit" disabled={loading}>
              {loading ? 'making your closet…' : 'enter my closet'} <span>↗</span>
            </button>
          </form>

          <div className="home-swatches" aria-label="Decorative palette">
            <span title="Coral" className="palette-coral" />
            <span title="Pink" className="palette-pink" />
            <span title="Purple" className="palette-purple" />
            <span title="Teal" className="palette-teal" />
          </div>
          <p className="home-footer-code">NO PASSWORDS, JUST PERSONAL STYLE <span>♡</span></p>
        </div>
      </section>
      <p className="desktop-footer" aria-hidden="true">WELCOME TO YOUR HAPPY PLACE&nbsp; ✿ &nbsp; EST. RIGHT NOW</p>
    </main>
  )
}

export default Home
