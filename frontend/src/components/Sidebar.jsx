import { NavLink } from 'react-router-dom'
import { LayoutDashboard, FolderKanban, Globe, Network, Database, AlertCircle, CheckSquare, Settings } from 'lucide-react'
import { cn } from '../lib/utils'

const links = [
  { name: 'Dashboard', to: '/', icon: LayoutDashboard },
  { name: 'Projects', to: '/projects', icon: FolderKanban },
  { name: 'Web Recon', to: '/web-recon', icon: Globe },
  { name: 'Network Recon', to: '/network-recon', icon: Network },
  { name: 'Database Recon', to: '/database-recon', icon: Database },
  { name: 'Findings', to: '/findings', icon: AlertCircle },
  { name: 'Checklist', to: '/checklist', icon: CheckSquare },
  { name: 'Settings', to: '/settings', icon: Settings },
]

export default function Sidebar() {
  return (
    <div className="w-64 bg-slate-900 text-slate-100 flex flex-col h-full dark:bg-slate-950">
      <div className="p-6 text-2xl font-bold tracking-wider text-blue-400">ReconForge</div>
      <nav className="flex-1 px-4 space-y-2">
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
