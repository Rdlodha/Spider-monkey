import { useState, useEffect } from 'react'
import { api } from '../services/api'

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/api/health')
      .then(setHealth)
      .catch(err => setError(err.message))
  }, [])

  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-bold text-slate-800 dark:text-slate-100">System Status</h2>
      
      {error && (
        <div className="p-4 bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400 rounded-md border border-red-200 dark:border-red-800">
          Error connecting to backend: {error}
        </div>
      )}

      {health && (
        <div className="p-6 bg-white dark:bg-slate-900 rounded-lg shadow-sm border border-slate-200 dark:border-slate-800 max-w-sm">
          <div className="flex items-center gap-4">
            <div className="w-3 h-3 bg-green-500 rounded-full animate-pulse"></div>
            <div>
              <p className="text-sm text-slate-500 dark:text-slate-400">API Status</p>
              <p className="text-lg font-semibold text-slate-800 dark:text-slate-100">Online</p>
            </div>
          </div>
          <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-800">
            <p className="text-sm text-slate-600 dark:text-slate-300">
              Application: <span className="font-medium">{health.application}</span>
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
