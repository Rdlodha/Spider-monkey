import { useState, useEffect, useCallback } from 'react'
import ReactFlow, {
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
} from 'reactflow'
import 'reactflow/dist/style.css'
import { Network, FolderKanban, Info, Loader2 } from 'lucide-react'
import { api } from '../services/api'

export default function AttackSurface() {
  const [projects, setProjects] = useState([])
  const [selectedProject, setSelectedProject] = useState('')
  const [nodes, setNodes, onNodesChange] = useNodesState([])
  const [edges, setEdges, onEdgesChange] = useEdgesState([])
  const [selectedNode, setSelectedNode] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.get('/api/projects')
      .then(data => {
        setProjects(data)
        if (data.length > 0) setSelectedProject(data[0].id)
      })
      .catch(e => setError(e.message))
  }, [])

  const loadGraph = useCallback(async () => {
    if (!selectedProject) return
    setLoading(true)
    setError(null)
    setSelectedNode(null)
    try {
      const data = await api.get(`/api/graph/${selectedProject}`)
      // Add custom styles based on node type
      const styledNodes = (data.nodes || []).map(n => {
        let bg = '#3B82F6'
        let border = '#1D4ED8'
        let text = '#FFFFFF'

        if (n.type === 'project') {
          bg = '#1E293B'
          border = '#0F172A'
        } else if (n.type === 'target') {
          bg = '#6366F1'
          border = '#4338CA'
        } else if (n.type === 'host') {
          bg = n.data?.is_interesting ? '#EAB308' : '#0EA5E9'
          border = '#0284C7'
          text = n.data?.is_interesting ? '#000000' : '#FFFFFF'
        } else if (n.type === 'service') {
          bg = '#10B981'
          border = '#047857'
        } else if (n.type === 'endpoint') {
          bg = '#8B5CF6'
          border = '#6D28D9'
        } else if (n.type === 'finding') {
          const sev = n.data?.severity
          bg = sev === 'CRITICAL' || sev === 'HIGH' ? '#EF4444' : '#F97316'
          border = '#B91C1C'
        }

        return {
          ...n,
          style: {
            background: bg,
            color: text,
            border: `2px solid ${border}`,
            borderRadius: '8px',
            padding: '8px 12px',
            fontSize: '11px',
            fontWeight: '600',
            textAlign: 'center',
            boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
            minWidth: 100,
          },
        }
      })

      setNodes(styledNodes)
      setEdges(data.edges || [])
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [selectedProject, setNodes, setEdges])

  useEffect(() => {
    loadGraph()
  }, [loadGraph])

  const onNodeClick = (_, node) => {
    setSelectedNode(node)
  }

  return (
    <div className="space-y-4 h-[calc(100vh-100px)] flex flex-col">
      <div className="flex items-center justify-between flex-wrap gap-4 shrink-0">
        <div className="flex items-center gap-2">
          <Network className="w-6 h-6 text-blue-500" />
          <h1 className="text-2xl font-bold dark:text-white">Attack Surface Graph</h1>
        </div>

        <div className="flex items-center gap-3">
          <label className="text-xs font-semibold text-slate-500 uppercase">Project</label>
          <select
            value={selectedProject}
            onChange={e => setSelectedProject(e.target.value)}
            className="border border-slate-300 dark:border-slate-600 rounded-lg px-3 py-1.5 text-sm dark:bg-slate-700 dark:text-white"
          >
            {projects.map(p => (
              <option key={p.id} value={p.id}>{p.name}</option>
            ))}
          </select>
          <button
            onClick={loadGraph}
            className="px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 flex items-center gap-1"
          >
            {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Refresh'}
          </button>
        </div>
      </div>

      {error && <div className="p-3 bg-red-100 text-red-700 rounded-lg text-sm shrink-0">{error}</div>}

      {/* Main Flow Canvas with Side Inspector */}
      <div className="flex-1 flex gap-4 min-h-0 relative">
        <div className="flex-1 bg-slate-900 rounded-xl overflow-hidden border border-slate-800 shadow-inner">
          <ReactFlow
            nodes={nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
          >
            <Background color="#334155" gap={16} />
            <Controls />
            <MiniMap nodeColor="#3B82F6" className="bg-slate-800!" />
          </ReactFlow>
        </div>

        {/* Selected Node Details Side Panel */}
        {selectedNode && (
          <div className="w-72 bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-4 shrink-0 shadow-lg flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between border-b pb-2 mb-3 dark:border-slate-700">
                <span className="text-xs font-semibold uppercase px-2 py-0.5 rounded bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200">
                  {selectedNode.data?.type || 'Node'}
                </span>
                <button
                  onClick={() => setSelectedNode(null)}
                  className="text-xs text-slate-400 hover:text-slate-600"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-3 text-xs">
                <div>
                  <span className="text-slate-400 block font-medium">Identifier</span>
                  <p className="font-mono text-slate-800 dark:text-slate-200 break-all">
                    {selectedNode.id}
                  </p>
                </div>

                <div>
                  <span className="text-slate-400 block font-medium">Label</span>
                  <p className="font-semibold text-slate-900 dark:text-white whitespace-pre-wrap">
                    {selectedNode.data?.label}
                  </p>
                </div>

                {selectedNode.data?.severity && (
                  <div>
                    <span className="text-slate-400 block font-medium">Severity</span>
                    <span className="px-2 py-0.5 rounded text-white font-bold inline-block mt-0.5 bg-red-600">
                      {selectedNode.data.severity}
                    </span>
                  </div>
                )}

                {selectedNode.data?.code && (
                  <div>
                    <span className="text-slate-400 block font-medium">HTTP Code</span>
                    <span className="font-mono text-slate-200">{selectedNode.data.code}</span>
                  </div>
                )}
              </div>
            </div>

            <div className="pt-4 border-t dark:border-slate-700 text-center">
              <span className="text-[10px] text-slate-400">Target → Host → Port → Endpoint → Finding</span>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
