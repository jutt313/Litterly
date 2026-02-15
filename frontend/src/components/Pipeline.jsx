import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import axios from 'axios'

function Pipeline() {
  const { jobId } = useParams()
  const navigate = useNavigate()
  const [job, setJob] = useState(null)
  const [llmProvider, setLlmProvider] = useState('deepseek')
  const [workers, setWorkers] = useState(10)
  const wsRef = useRef(null)

  useEffect(() => {
    loadJob()
    return () => {
      if (wsRef.current) wsRef.current.close()
    }
  }, [jobId])

  async function loadJob() {
    try {
      const res = await axios.get(`/api/jobs/${jobId}`)
      setJob(res.data)
      setLlmProvider(res.data.llm_provider || 'deepseek')
      setWorkers(res.data.workers || 10)

      if (res.data.status === 'running') {
        connectWebSocket()
      }
    } catch (err) {
      console.error('Failed to load job:', err)
    }
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress/${jobId}`)

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'job_update') {
        setJob(prev => ({ ...prev, ...msg.data }))
      }
    }

    ws.onclose = () => {
      setTimeout(() => {
        if (job?.status === 'running') connectWebSocket()
      }, 3000)
    }

    wsRef.current = ws
  }

  async function handleStart() {
    try {
      await axios.post(`/api/jobs/${jobId}/start`, {
        llm_provider: llmProvider,
        workers: workers,
      })
      await loadJob()
      connectWebSocket()
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to start job')
    }
  }

  async function handleStop() {
    try {
      await axios.post(`/api/jobs/${jobId}/stop`)
      await loadJob()
    } catch (err) {
      alert('Failed to stop job')
    }
  }

  if (!job) return <div>Loading...</div>

  const progress = job.total_products > 0
    ? Math.round(((job.completed_products + job.failed_products) / job.total_products) * 100)
    : 0

  return (
    <div>
      <h2 style={{ fontSize: 24, color: '#fff', marginBottom: 24 }}>
        {job.filename}
      </h2>

      {/* Stats */}
      <div className="stats">
        <div className="stat">
          <div className="value">{job.total_products}</div>
          <div className="label">Total Products</div>
        </div>
        <div className="stat">
          <div className="value" style={{ color: '#4ade80' }}>{job.completed_products}</div>
          <div className="label">Completed</div>
        </div>
        <div className="stat">
          <div className="value" style={{ color: '#f87171' }}>{job.failed_products}</div>
          <div className="label">Failed</div>
        </div>
        <div className="stat">
          <div className="value">{progress}%</div>
          <div className="label">Progress</div>
        </div>
      </div>

      {/* Progress bar */}
      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
      </div>

      {/* Controls */}
      <div className="card">
        <h2>Pipeline Controls</h2>
        <div style={{ display: 'flex', gap: 16, alignItems: 'end', flexWrap: 'wrap' }}>
          <div className="form-group" style={{ marginBottom: 0, width: 180 }}>
            <label>LLM Provider</label>
            <select value={llmProvider} onChange={(e) => setLlmProvider(e.target.value)} disabled={job.status === 'running'}>
              <option value="deepseek">DeepSeek</option>
              <option value="openai">OpenAI</option>
              <option value="claude">Claude</option>
              <option value="gemini">Gemini</option>
            </select>
          </div>
          <div className="form-group" style={{ marginBottom: 0, width: 120 }}>
            <label>Workers (1-20)</label>
            <input
              type="number"
              min="1"
              max="20"
              value={workers}
              onChange={(e) => setWorkers(parseInt(e.target.value) || 10)}
              disabled={job.status === 'running'}
            />
          </div>
          {job.status !== 'running' ? (
            <button className="btn btn-primary" onClick={handleStart}>
              Start Pipeline
            </button>
          ) : (
            <button className="btn btn-danger" onClick={handleStop}>
              Stop
            </button>
          )}
        </div>
      </div>

      {/* Job Folder & Downloads */}
      {(job.job_folder || job.status === 'running' || job.output_file) && (
        <div className="card">
          <h2>Output</h2>

          {job.job_folder && (
            <div style={{ marginBottom: 16 }}>
              <label>Job Folder</label>
              <div style={{
                background: '#252525',
                border: '1px solid #333',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: 13,
                color: '#60a5fa',
                fontFamily: 'monospace',
                wordBreak: 'break-all',
              }}>
                {job.job_folder}
              </div>
            </div>
          )}

          <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
            {/* Live CSV — show while running or if completed products exist */}
            {(job.status === 'running' || job.completed_products > 0) && (
              <button
                className="btn btn-primary"
                onClick={() => window.open(`/api/jobs/${jobId}/export/live`, '_blank')}
              >
                Download Live CSV ({job.completed_products} products)
              </button>
            )}

            {/* Final CSV — show only after job is done */}
            {job.output_file && (
              <button
                className="btn btn-success"
                onClick={() => window.open(`/api/jobs/${jobId}/export`, '_blank')}
              >
                Download Final CSV
              </button>
            )}
          </div>
        </div>
      )}

      {/* Product list */}
      <div className="card">
        <h2>Products</h2>
        <div className="product-list">
          {(job.products || []).map((product) => (
            <div key={product.product_id} className="product-item">
              <div>
                <span className="title">{product.title || product.product_id}</span>
                {product.current_agent && product.status !== 'completed' && product.status !== 'error' && (
                  <span style={{ fontSize: 12, color: '#60a5fa', marginLeft: 8 }}>
                    {product.current_agent}...
                  </span>
                )}
              </div>
              <span className={`status-badge status-${product.status}`}>
                {product.status}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default Pipeline
