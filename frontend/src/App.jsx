import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import { ToastProvider } from './components/Toast'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import Scans from './pages/Scans'
import WebRecon from './pages/WebRecon'
import NetworkRecon from './pages/NetworkRecon'
import DatabaseRecon from './pages/DatabaseRecon'
import Findings from './pages/Findings'
import Checklist from './pages/Checklist'
import Tools from './pages/Tools'
import ProxyManager from './pages/ProxyManager'
import ScanJobs from './pages/ScanJobs'
import AttackSurface from './pages/AttackSurface'
import Reports from './pages/Reports'
import AuditLogs from './pages/AuditLogs'
import Settings from './pages/Settings'

function App() {
  return (
    <ToastProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="projects" element={<Projects />} />
            <Route path="scans" element={<Scans />} />
            <Route path="attack-surface" element={<AttackSurface />} />
            <Route path="reports" element={<Reports />} />
            <Route path="web-recon" element={<WebRecon />} />
            <Route path="network-recon" element={<NetworkRecon />} />
            <Route path="database-recon" element={<DatabaseRecon />} />
            <Route path="findings" element={<Findings />} />
            <Route path="checklist" element={<Checklist />} />
            <Route path="tools" element={<Tools />} />
            <Route path="proxy-manager" element={<ProxyManager />} />
            <Route path="scan-jobs" element={<ScanJobs />} />
            <Route path="audit-logs" element={<AuditLogs />} />
            <Route path="settings" element={<Settings />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ToastProvider>
  )
}

export default App
