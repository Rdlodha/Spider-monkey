import { useState, useEffect, useCallback } from 'react'
import { api } from '../services/api'
import { Link } from 'react-router-dom'
import {
  Server,
  Network,
  Globe,
  AlertTriangle,
  CheckSquare,
  ShieldAlert,
  ArrowRight,
  FolderKanban,
  Radar
} from 'lucide-react'

export default function Dashboard() {
  const [health, setHealth] = useState(null)
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  // Load API Health and Projects
  useEffect(() => {
    api.get('/api/health').then(setHealth).catch((err) => setError(err.message))
    api.get('/api/projects')
      .then((data) => {
        setProjects(data)
        if (data.length > 0) {
          setSelectedProject(data[0].id)
        }
      })
      .catch((err) => setError(err.message))
  }, [])

  // Load Project Stats
  const fetchStats = useCallback(async () => {
    if (!selectedProject) return
    setLoading(true)
    try {
      const data = await api.get(`/api/dashboard/${selectedProject}`)
      setStats(data)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }, [selectedProject])

  useEffect(() => {
    fetchStats()
  }, [fetchStats])

  const checklistPercent =
    stats && stats.checklist_total > 0
      ? Math.round((stats.checklist_completed / stats.checklist_total) * 100)
      : 0

  return (
    <div className="p-6 space-y-6 text-slate-100">
      {/* Top Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold">Recon Dashboard</h1>
          <p className="text-sm text-slate-400">
            Unified target intelligence, findings summary, and methodology progress
          </p>
        </div>

        <div className="flex items-center gap-3">
          {health && (
            <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded text-xs">
              <div className="w-2.5 h-2.5 bg-green-500 rounded-full animate-pulse" />
              <span className="text-slate-300">API {health.status}</span>
            </div>
          )}

          <div className="flex items-center gap-2 bg-slate-800 border border-slate-700 px-3 py-1.5 rounded text-sm">
            <FolderKanban className="w-4 h-4 text-slate-400" />
            <select
              value={selectedProject}
              onChange={(e) => setSelectedProject(e.target.value)}
              className="bg-transparent text-white focus:outline-none"
            >
              {projects.map((p) => (
                <option key={p.id} value={p.id} className="bg-slate-800">
                  {p.name}
                </option>
              ))}
            </select>
          </div>
        </div>
      </div>

      {error && (
        <div className="bg-red-900/50 border border-red-500 text-red-200 text-sm px-4 py-3 rounded">
          {error}
        </div>
      )}

      {/* Main Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Live Hosts */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Live Hosts</p>
            <p className="text-2xl font-bold text-white mt-1">{stats?.host_count ?? 0}</p>
            <p className="text-xs text-slate-500 mt-1">Discovered IP targets</p>
          </div>
          <div className="p-3 bg-blue-500/10 text-blue-400 rounded-lg border border-blue-500/20">
            <Server className="w-6 h-6" />
          </div>
        </div>

        {/* Open Ports / Services */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Open Ports</p>
            <p className="text-2xl font-bold text-white mt-1">{stats?.open_port_count ?? 0}</p>
            <p className="text-xs text-slate-500 mt-1">Active network services</p>
          </div>
          <div className="p-3 bg-purple-500/10 text-purple-400 rounded-lg border border-purple-500/20">
            <Network className="w-6 h-6" />
          </div>
        </div>

        {/* Endpoints */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Web Endpoints</p>
            <p className="text-2xl font-bold text-white mt-1">{stats?.endpoint_count ?? 0}</p>
            <p className="text-xs text-slate-500 mt-1">Enumerated URLs & paths</p>
          </div>
          <div className="p-3 bg-cyan-500/10 text-cyan-400 rounded-lg border border-cyan-500/20">
            <Globe className="w-6 h-6" />
          </div>
        </div>

        {/* Findings */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-5 flex items-center justify-between">
          <div>
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Findings</p>
            <div className="flex items-baseline gap-2 mt-1">
              <span className="text-2xl font-bold text-white">{stats?.finding_count ?? 0}</span>
              {(stats?.critical_finding_count > 0 || stats?.high_finding_count > 0) && (
                <span className="text-xs text-red-400 font-semibold">
                  ({stats.critical_finding_count} crit, {stats.high_finding_count} high)
                </span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-1">Security observations</p>
          </div>
          <div className="p-3 bg-red-500/10 text-red-400 rounded-lg border border-red-500/20">
            <ShieldAlert className="w-6 h-6" />
          </div>
        </div>
      </div>

      {/* Methodology & Quick Actions */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Checklist Progress Overview Card */}
        <div className="lg:col-span-2 bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CheckSquare className="w-5 h-5 text-blue-400" />
              <h2 className="font-bold text-lg text-white">Testing Methodology Progress</h2>
            </div>
            <span className="text-xl font-bold text-blue-400">{checklistPercent}%</span>
          </div>

          <div className="w-full bg-slate-700 h-3 rounded-full overflow-hidden">
            <div
              className="bg-blue-500 h-full transition-all duration-300"
              style={{ width: `${checklistPercent}%` }}
            />
          </div>

          <p className="text-sm text-slate-300">
            {stats?.checklist_completed ?? 0} of {stats?.checklist_total ?? 0} checklist items completed across all targets in this project.
          </p>

          <Link
            to="/checklist"
            className="inline-flex items-center gap-1.5 text-sm text-blue-400 hover:text-blue-300 font-medium"
          >
            Open Project Checklist <ArrowRight className="w-4 h-4" />
          </Link>
        </div>

        {/* Quick Launch Shortcuts */}
        <div className="bg-slate-800 border border-slate-700 rounded-lg p-6 space-y-4">
          <h2 className="font-bold text-lg text-white">Workbench Shortcuts</h2>
          <div className="space-y-2 text-sm">
            <Link
              to="/scans"
              className="flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded border border-slate-600/50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <Radar className="w-4 h-4 text-blue-400" />
                <span className="text-slate-200">Import Scans</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </Link>

            <Link
              to="/findings"
              className="flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded border border-slate-600/50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <AlertTriangle className="w-4 h-4 text-red-400" />
                <span className="text-slate-200">Manage Findings</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </Link>

            <Link
              to="/projects"
              className="flex items-center justify-between p-3 bg-slate-700/50 hover:bg-slate-700 rounded border border-slate-600/50 transition-colors"
            >
              <div className="flex items-center gap-2.5">
                <FolderKanban className="w-4 h-4 text-emerald-400" />
                <span className="text-slate-200">Configure Targets</span>
              </div>
              <ArrowRight className="w-4 h-4 text-slate-400" />
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}
