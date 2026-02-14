import { useState, useEffect } from 'react'
import axios from 'axios'

function Settings() {
  const [settings, setSettings] = useState(null)
  const [keys, setKeys] = useState({
    openai_api_key: '',
    anthropic_api_key: '',
    gemini_api_key: '',
    deepseek_api_key: '',
  })
  const [defaultLlm, setDefaultLlm] = useState('deepseek')
  const [defaultWorkers, setDefaultWorkers] = useState(10)
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    loadSettings()
  }, [])

  async function loadSettings() {
    try {
      const res = await axios.get('/api/settings')
      setSettings(res.data)
      setDefaultLlm(res.data.default_llm)
      setDefaultWorkers(res.data.default_workers)
    } catch (err) {
      console.error('Failed to load settings:', err)
    }
  }

  async function handleSave() {
    setSaving(true)
    try {
      const update = { default_llm: defaultLlm, default_workers: defaultWorkers }
      if (keys.openai_api_key) update.openai_api_key = keys.openai_api_key
      if (keys.anthropic_api_key) update.anthropic_api_key = keys.anthropic_api_key
      if (keys.gemini_api_key) update.gemini_api_key = keys.gemini_api_key
      if (keys.deepseek_api_key) update.deepseek_api_key = keys.deepseek_api_key

      await axios.post('/api/settings', update)
      setSaved(true)
      setTimeout(() => setSaved(false), 3000)
      await loadSettings()
    } catch (err) {
      alert('Failed to save settings')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: 24, color: '#fff', marginBottom: 24 }}>Settings</h2>

      <div className="card">
        <h2>API Keys</h2>
        <div className="settings-grid">
          <div className="form-group">
            <label>
              OpenAI API Key {settings?.has_openai_key && <span style={{ color: '#4ade80' }}>configured</span>}
            </label>
            <input
              type="password"
              placeholder="sk-..."
              value={keys.openai_api_key}
              onChange={(e) => setKeys({ ...keys, openai_api_key: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>
              Anthropic Claude Key {settings?.has_anthropic_key && <span style={{ color: '#4ade80' }}>configured</span>}
            </label>
            <input
              type="password"
              placeholder="sk-ant-..."
              value={keys.anthropic_api_key}
              onChange={(e) => setKeys({ ...keys, anthropic_api_key: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>
              Google Gemini Key {settings?.has_gemini_key && <span style={{ color: '#4ade80' }}>configured</span>}
            </label>
            <input
              type="password"
              placeholder="AI..."
              value={keys.gemini_api_key}
              onChange={(e) => setKeys({ ...keys, gemini_api_key: e.target.value })}
            />
          </div>
          <div className="form-group">
            <label>
              DeepSeek Key {settings?.has_deepseek_key && <span style={{ color: '#4ade80' }}>configured</span>}
            </label>
            <input
              type="password"
              placeholder="sk-..."
              value={keys.deepseek_api_key}
              onChange={(e) => setKeys({ ...keys, deepseek_api_key: e.target.value })}
            />
          </div>
        </div>
      </div>

      <div className="card">
        <h2>Defaults</h2>
        <div className="settings-grid">
          <div className="form-group">
            <label>Default LLM Provider</label>
            <select value={defaultLlm} onChange={(e) => setDefaultLlm(e.target.value)}>
              <option value="deepseek">DeepSeek</option>
              <option value="openai">OpenAI</option>
              <option value="claude">Claude</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>
          <div className="form-group">
            <label>Default Workers (1-20)</label>
            <input
              type="number"
              min="1"
              max="20"
              value={defaultWorkers}
              onChange={(e) => setDefaultWorkers(parseInt(e.target.value) || 10)}
            />
          </div>
        </div>
      </div>

      <button
        className={`btn ${saved ? 'btn-success' : 'btn-primary'}`}
        onClick={handleSave}
        disabled={saving}
      >
        {saved ? 'Saved!' : saving ? 'Saving...' : 'Save Settings'}
      </button>
    </div>
  )
}

export default Settings
