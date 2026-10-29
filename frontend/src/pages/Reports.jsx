import { useState, useEffect } from 'react'
import { FileText, Download, Eye, Loader2 } from 'lucide-react'
import { api } from '../services/api'
import { useToast } from '../components/Toast'

export default function Reports() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [excludeFalsePositives, setExcludeFalsePositives] = useState(true)
  const [redactEvidence, setRedactEvidence] = useState(true)
  const [previewMd, setPreviewMd] = useState('')
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [error, setError] = useState(null)
  const { toast } = useToast()

  useEffect(() => {
    api.get('/api/projects')
      .then(data => {
        setProjects(data)
        if (data.length > 0) setSelectedProject(data[0].id)
      })
      .catch(e => setError(e.message))
  }, [])

  const fetchMarkdownPreview = async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    try {
      const token = import.meta.env.VITE_API_TOKEN
      const url = `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/api/reports/${selectedProject}/markdown?exclude_false_positives=${excludeFalsePositives}&redact_evidence=${redactEvidence}`
      const resp = await fetch(url, {
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      if (!resp.ok) throw new Error('Failed to generate report preview')
      const text = await resp.text()
      setPreviewMd(text)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (selectedProject) fetchMarkdownPreview()
  }, [selectedProject, excludeFalsePositives, redactEvidence])

  const handleDownloadPdf = async () => {
    if (!selectedProject) return
    setGenerating(true)
    try {
      const proj = projects.find(p => p.id === selectedProject)
      const name = proj ? proj.name.toLowerCase().replace(/\s+/g, '_') : 'recon'
      await api.download(
        `/api/reports/${selectedProject}/pdf?exclude_false_positives=${excludeFalsePositives}&redact_evidence=${redactEvidence}`,
        `reconforge_${name}_report.pdf`
      )
      toast.success('PDF report downloaded')
    } catch (e) {
      toast.error(e.message || 'PDF generation failed')
    } finally {
      setGenerating(false)
    }
  }

  const handleDownloadMarkdown = () => {
    const proj = projects.find(p => p.id === selectedProject)
    const name = proj ? proj.name.toLowerCase().replace(/\s+/g, '_') : 'recon'
    const blob = new Blob([previewMd], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `reconforge_${name}_report.md`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('Markdown report exported')
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-4">
        <div className="flex items-center gap-2">
          <FileText className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold dark:text-white">Assessment Reports</h1>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={handleDownloadMarkdown}
            disabled={!previewMd}
            className="flex items-center gap-2 px-3 py-2 bg-slate-700 text-white rounded-lg hover:bg-slate-800 text-sm disabled:opacity-50"
          >
            <Download className="w-4 h-4" /> Export Markdown
          </button>
          <button
            onClick={handleDownloadPdf}
            disabled={generating || !selectedProject}
            className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium disabled:opacity-50"
          >
            {generating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Download className="w-4 h-4" />}
            Download PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 bg-red-100 text-red-700 rounded-lg text-sm">{error}</div>
      )}

      {/* Configuration Controls */}
      <div className="bg-white dark:bg-slate-800 p-4 rounded-xl border border-slate-200 dark:border-slate-700 flex flex-wrap items-center gap-6">
        <div>
          <label className="text-xs font-semibold text-slate-500 uppercase block mb-1">Target Project</label>
          <select
            value={selectedProject}
            onChange={e => setSelectedProject(e.target.value)}
            className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm dark:bg-slate-700 dark:text-white"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-4 pt-4">
          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={excludeFalsePositives}
              onChange={e => setExcludeFalsePositives(e.target.checked)}
              className="rounded text-blue-600"
            />
            Exclude FALSE_POSITIVE findings
          </label>

          <label className="flex items-center gap-2 text-sm text-slate-700 dark:text-slate-300 cursor-pointer">
            <input
              type="checkbox"
              checked={redactEvidence}
              onChange={e => setRedactEvidence(e.target.checked)}
              className="rounded text-blue-600"
            />
            Redact tokens & secrets in evidence
          </label>
        </div>
      </div>

      {/* Report Preview */}
      <div className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-6">
        <div className="flex items-center justify-between mb-4 border-b pb-2 dark:border-slate-700">
          <h2 className="text-base font-semibold dark:text-white flex items-center gap-2">
            <Eye className="w-4 h-4 text-blue-500" />
            Live Report Preview
          </h2>
          {loading && <Loader2 className="w-4 h-4 animate-spin text-blue-500" />}
        </div>

        <div className="bg-slate-900 text-slate-100 p-4 rounded-lg font-mono text-xs max-h-[550px] overflow-auto whitespace-pre-wrap leading-relaxed">
          {previewMd || 'No report generated yet.'}
        </div>
      </div>
    </div>
  )
}
