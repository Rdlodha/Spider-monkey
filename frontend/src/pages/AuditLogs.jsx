import { useState, useEffect } from 'react'
import { History, Filter, RefreshCw, Loader2, ShieldCheck } from 'lucide-react'
import { api } from '../services/api'

export default function AuditLogs() {
  const [logs, setLogs] = useState([])
  const [actionFilter, setActionFilter] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const fetchLogs = async () => {
    setLoading(true)
    setError(null)
    try {
      const q = actionFilter ? `?action=${encodeURIComponent(actionFilter)}` : ''
      const data = await api.get(`/api/audit${q}`)
      setLogs(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [actionFilter])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <History className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold dark:text-white">Security Audit Log</h1>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-white dark:bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-700">
            <Filter className="w-4 h-4 text-slate-400" />
            <input
              type="text"
              placeholder="Filter by action..."
              value={actionFilter}
              onChange={e => setActionFilter(e.target.value)}
              className="text-xs bg-transparent focus:outline-none dark:text-white"
            />
          </div>
          <button
            onClick={fetchLogs}
            className="p-2 bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-200 rounded-lg hover:bg-slate-200"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400">
        <ShieldCheck className="w-4 h-4 text-emerald-500" />
        <span>Append-only security verification log. Records cannot be modified or deleted.</span>
      </div>

      {error && <div className="p-3 bg-red-100 text-red-700 rounded-lg text-sm">{error}</div>}

      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 overflow-hidden shadow-sm">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-slate-50 dark:bg-slate-900 border-b border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400 uppercase font-semibold">
              <tr>
                <th className="px-4 py-3">Timestamp (UTC)</th>
                <th className="px-4 py-3">Actor</th>
                <th className="px-4 py-3">Action</th>
                <th className="px-4 py-3">Target / Resource</th>
                <th className="px-4 py-3">Tool</th>
                <th className="px-4 py-3">Result</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-700/60 font-mono">
              {logs.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-slate-400">
                    {loading ? 'Loading audit records...' : 'No audit records found.'}
                  </td>
                </tr>
              ) : (
                logs.map(log => (
                  <tr key={log.id} className="hover:bg-slate-50/50 dark:hover:bg-slate-700/30 transition-colors">
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400 whitespace-nowrap">
                      {log.ts ? new Date(log.ts).toLocaleString() : '—'}
                    </td>
                    <td className="px-4 py-2.5 text-slate-700 dark:text-slate-300 font-semibold">{log.actor}</td>
                    <td className="px-4 py-2.5">
                      <span className="px-2 py-0.5 rounded bg-blue-50 dark:bg-blue-900/40 text-blue-700 dark:text-blue-300 font-bold">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-600 dark:text-slate-300 max-w-xs truncate" title={log.target}>
                      {log.target || '—'}
                    </td>
                    <td className="px-4 py-2.5 text-slate-500 dark:text-slate-400">{log.tool || '—'}</td>
                    <td className="px-4 py-2.5">
                      <span className={`px-2 py-0.5 rounded text-[11px] ${
                        log.result?.toLowerCase().includes('ok') || log.result?.toLowerCase().includes('queued') || log.result?.toLowerCase().includes('completed')
                          ? 'bg-emerald-100 dark:bg-emerald-900/40 text-emerald-800 dark:text-emerald-300'
                          : 'bg-slate-100 dark:bg-slate-700 text-slate-700 dark:text-slate-300'
                      }`}>
                        {log.result || '—'}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
