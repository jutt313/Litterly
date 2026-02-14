import { Routes, Route, Link, useLocation } from 'react-router-dom'
import Upload from './components/Upload'
import Settings from './components/Settings'
import Pipeline from './components/Pipeline'
import ProductDetail from './components/ProductDetail'
import Export from './components/Export'

function App() {
  const location = useLocation()

  return (
    <div className="app">
      <nav className="sidebar">
        <div className="logo">
          <h1>Litterly</h1>
          <span className="tagline">AI Product Enrichment</span>
        </div>
        <ul>
          <li className={location.pathname === '/' ? 'active' : ''}>
            <Link to="/">Dashboard</Link>
          </li>
          <li className={location.pathname === '/settings' ? 'active' : ''}>
            <Link to="/settings">Settings</Link>
          </li>
        </ul>
      </nav>

      <main className="content">
        <Routes>
          <Route path="/" element={<Upload />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/job/:jobId" element={<Pipeline />} />
          <Route path="/job/:jobId/product/:productId" element={<ProductDetail />} />
          <Route path="/job/:jobId/export" element={<Export />} />
        </Routes>
      </main>
    </div>
  )
}

export default App
