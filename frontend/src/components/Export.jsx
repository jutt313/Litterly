import { useParams } from 'react-router-dom'

function Export() {
  const { jobId } = useParams()

  return (
    <div>
      <h2 style={{ fontSize: 24, color: '#fff', marginBottom: 24 }}>Export</h2>

      <div className="card">
        <h2>Download Matrixify CSV</h2>
        <p style={{ color: '#999', marginBottom: 16 }}>
          Download the generated product data in Matrixify-compatible CSV format, ready to upload to Shopify.
        </p>
        <button
          className="btn btn-primary"
          onClick={() => window.open(`/api/jobs/${jobId}/export`, '_blank')}
        >
          Download CSV
        </button>
      </div>
    </div>
  )
}

export default Export
