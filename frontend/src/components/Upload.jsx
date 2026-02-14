import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import axios from 'axios'

function Upload() {
  const [dragging, setDragging] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [jobs, setJobs] = useState([])
  const fileInput = useRef(null)
  const navigate = useNavigate()

  useEffect(() => {
    loadJobs()
  }, [])

  async function loadJobs() {
    try {
      const res = await axios.get('/api/jobs')
      setJobs(res.data)
    } catch (err) {
      console.error('Failed to load jobs:', err)
    }
  }

  async function handleUpload(file) {
    if (!file) return
    setUploading(true)
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await axios.post('/api/upload', formData)
      navigate(`/job/${res.data.job_id}`)
    } catch (err) {
      alert(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  function handleDrop(e) {
    e.preventDefault()
    setDragging(false)
    const file = e.dataTransfer.files[0]
    handleUpload(file)
  }

  return (
    <div>
      <h2 style={{ fontSize: 24, color: '#fff', marginBottom: 24 }}>Dashboard</h2>

      <div className="card">
        <h2>Upload Product Data</h2>
        <div
          className={`upload-area ${dragging ? 'dragging' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
          onDragLeave={() => setDragging(false)}
          onDrop={handleDrop}
          onClick={() => fileInput.current?.click()}
        >
          <div style={{ fontSize: 40, marginBottom: 12 }}>+</div>
          <strong>{uploading ? 'Uploading...' : 'Drop file here or click to browse'}</strong>
          <p>Supports CSV, JSON, Excel (.xlsx)</p>
          <input
            ref={fileInput}
            type="file"
            accept=".csv,.json,.xlsx,.xls"
            style={{ display: 'none' }}
            onChange={(e) => handleUpload(e.target.files[0])}
          />
        </div>
      </div>

      {jobs.length > 0 && (
        <div className="card">
          <h2>Recent Jobs</h2>
          <div className="job-list">
            {jobs.map(job => (
              <div
                key={job.id}
                className="job-card"
                onClick={() => navigate(`/job/${job.id}`)}
              >
                <div>
                  <strong style={{ color: '#fff' }}>{job.filename}</strong>
                  <div style={{ fontSize: 13, color: '#666', marginTop: 4 }}>
                    {job.total_products} products
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <span className={`status-badge status-${job.status}`}>
                    {job.status}
                  </span>
                  <div style={{ fontSize: 12, color: '#666', marginTop: 4 }}>
                    {job.completed_products}/{job.total_products} done
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default Upload
