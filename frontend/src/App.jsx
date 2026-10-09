import { BrowserRouter, Routes, Route } from 'react-router-dom'
import MainLayout from './layouts/MainLayout'
import Dashboard from './pages/Dashboard'
import Projects from './pages/Projects'
import Scans from './pages/Scans'
import WebRecon from './pages/WebRecon'
import NetworkRecon from './pages/NetworkRecon'
import DatabaseRecon from './pages/DatabaseRecon'
import Findings from './pages/Findings'
import Checklist from './pages/Checklist'
import Settings from './pages/Settings'

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout />}>
          <Route index element={<Dashboard />} />
          <Route path="projects" element={<Projects />} />
          <Route path="web-recon" element={<WebRecon />} />
          <Route path="network-recon" element={<NetworkRecon />} />
          <Route path="database-recon" element={<DatabaseRecon />} />
          <Route path="findings" element={<Findings />} />
          <Route path="checklist" element={<Checklist />} />
          <Route path="settings" element={<Settings />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}

export default App
