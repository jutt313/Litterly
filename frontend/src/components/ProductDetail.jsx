import { useState, useEffect } from 'react'
import { useParams } from 'react-router-dom'
import axios from 'axios'

function ProductDetail() {
  const { jobId, productId } = useParams()
  const [product, setProduct] = useState(null)

  useEffect(() => {
    loadProduct()
  }, [jobId, productId])

  async function loadProduct() {
    try {
      const res = await axios.get(`/api/jobs/${jobId}/products`)
      const found = res.data.find(p => p.product_id === productId)
      setProduct(found)
    } catch (err) {
      console.error('Failed to load product:', err)
    }
  }

  if (!product) return <div>Loading...</div>

  return (
    <div>
      <h2 style={{ fontSize: 24, color: '#fff', marginBottom: 24 }}>
        {product.title || product.product_id}
      </h2>

      <div className="card">
        <h2>Status</h2>
        <span className={`status-badge status-${product.status}`}>
          {product.status}
        </span>
        {product.error && (
          <p style={{ color: '#f87171', marginTop: 12 }}>{product.error}</p>
        )}
      </div>
    </div>
  )
}

export default ProductDetail
