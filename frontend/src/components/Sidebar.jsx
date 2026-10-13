import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FolderKanban, Radar, Globe, Network, Database, AlertCircle, CheckSquare, Settings, Wrench, Shield, Play, GitFork, FileText, History } from 'lucide-react'
import { cn } from '../lib/utils'

const links = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Projects', to: '/projects', icon: FolderKanban },
  { name: 'Scans', to: '/scans', icon: Radar },
  { name: 'Attack Surface', to: '/attack-surface', icon: GitFork },
  { name: 'Reports', to: '/reports', icon: FileText },
  { name: 'Web Recon', to: '/web-recon', icon: Globe },
  { name: 'Network Recon', to: '/network-recon', icon: Network },
  { name: 'Database Recon', to: '/database-recon', icon: Database },
  { name: 'Findings', to: '/findings', icon: AlertCircle },
  { name: 'Checklist', to: '/checklist', icon: CheckSquare },
  { name: 'Tools', to: '/tools', icon: Wrench },
  { name: 'Proxy Manager', to: '/proxy-manager', icon: Shield },
  { name: 'Scan Jobs', to: '/scan-jobs', icon: Play },
  { name: 'Audit Logs', to: '/audit-logs', icon: History },
  { name: 'Settings', to: '/settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-slate-100 flex flex-col h-full dark:bg-slate-950">
      <div className="p-6 text-2xl font-bold tracking-wider text-blue-400">ReconForge</div>
      <nav className="flex-1 px-4 space-y-2 overflow-y-auto pb-4">
        {links.map((link) => {
          const Icon = link.icon
          return (
            <NavLink
              key={link.name}
              to={link.to}
              className={({ isActive }) =>
                cn(
                  'flex items-center gap-3 px-3 py-2 rounded-md transition-colors',
                  isActive ? 'bg-blue-600 text-white' : 'hover:bg-slate-800 text-slate-300'
                )
              }
            >
              <Icon className="w-5 h-5" />
              {link.name}
            </NavLink>
          )
        })}
      </nav>
    </div>
  )
}
