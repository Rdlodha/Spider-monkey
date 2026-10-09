import { useLocation } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { Moon, Sun } from 'lucide-react'

const routeTitles = {
  '/': 'Dashboard',
  '/projects': 'Projects',
  '/web-recon': 'Web Recon',
  '/network-recon': 'Network Recon',
  '/database-recon': 'Database Recon',
  '/findings': 'Findings',
  '/checklist': 'Checklist',
  '/settings': 'Settings',
}

export default function TopBar() {
  const location = useLocation()
  const title = routeTitles[location.pathname] || 'ReconForge'
  const [darkMode, setDarkMode] = useState(() => localStorage.getItem('darkMode') === 'true')

  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark')
      localStorage.setItem('darkMode', 'true')
    } else {
      document.documentElement.classList.remove('dark')
      localStorage.setItem('darkMode', 'false')
    }
  }, [darkMode])

  return (
    <div className="h-16 bg-white dark:bg-slate-900 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-6">
      <h1 className="text-xl font-semibold text-slate-800 dark:text-slate-100">{title}</h1>
      <button
        onClick={() => setDarkMode(!darkMode)}
        className="p-2 rounded-md hover:bg-slate-100 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 transition-colors"
      >
        {darkMode ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
      </button>
    </div>
  )
}
