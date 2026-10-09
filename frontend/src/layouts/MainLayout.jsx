import { Outlet } from 'react-router-dom'
import Sidebar from '../components/Sidebar'
import TopBar from '../components/TopBar'

export default function MainLayout() {
  return (
    <div className="flex h-screen overflow-hidden bg-slate-50 dark:bg-slate-950 transition-colors">
      <Sidebar />
      <div className="flex-1 flex flex-col h-full overflow-hidden">
        <TopBar />
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
