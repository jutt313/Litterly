import { useEffect, useRef, useState } from 'react'

export function useWebSocket(jobId) {
  const [data, setData] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    if (!jobId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/progress/${jobId}`)

    ws.onmessage = (event) => {
      const msg = JSON.parse(event.data)
      if (msg.type === 'job_update') {
        setData(msg.data)
      }
    }

    ws.onclose = () => {
      // Auto reconnect after 3 seconds
      setTimeout(() => {
        if (wsRef.current === ws) {
          // Reconnect logic would go here
        }
      }, 3000)
    }

    wsRef.current = ws

    return () => {
      ws.close()
    }
  }, [jobId])

  return data
}
