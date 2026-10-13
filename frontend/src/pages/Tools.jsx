import { Wrench } from 'lucide-react'

const TOOLS = [
  {
    name: 'nmap',
    version: '7.93',
    description: 'Network exploration and security auditing. Supports host discovery, port scanning, and service detection.',
    profiles: [{ id: 'nmap-top-1000', label: 'Top 1000 ports', flags: '-T4 --top-ports 1000 -oX' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP'],
  },
  {
    name: 'feroxbuster',
    version: '2.8.4',
    description: 'Fast, recursive content discovery tool for web applications. Outputs JSON for reliable parsing.',
    profiles: [{ id: 'ferox-common', label: 'Common wordlist', flags: '--json -w common.txt' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  {
    name: 'gobuster',
    version: '3.6.0',
    description: 'Directory/file brute-forcing tool for web servers and DNS subdomain enumeration.',
    profiles: [{ id: 'gobuster-dir', label: 'Directory mode', flags: 'dir -w common.txt' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  {
    name: 'sqlmap',
    version: 'N/A',
    description: 'SQL injection detection and exploitation. Import-only: paste or upload sqlmap output for parsing.',
    profiles: [],
    proxyTypes: [],
    importOnly: true,
  },
]

export default function Tools() {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-2">
        <Wrench className="w-6 h-6 text-blue-500" />
        <h1 className="text-2xl font-bold dark:text-white">Tools</h1>
      </div>

      <p className="text-sm text-slate-500 dark:text-slate-400">
        Supported scanning tools. Commands are built centrally from allowlisted scan profiles — no raw flags accepted.
        Wordlists are served from the server-side allowlisted directory only.
      </p>

      <div className="grid gap-4 sm:grid-cols-2">
        {TOOLS.map(tool => (
          <div
            key={tool.name}
            className="bg-white dark:bg-slate-800 rounded-xl border border-slate-200 dark:border-slate-700 p-5 space-y-3"
          >
            <div className="flex items-center justify-between">
              <div>
                <span className="font-mono text-lg font-bold dark:text-white">{tool.name}</span>
                <span className="ml-2 text-xs text-slate-400 dark:text-slate-500">v{tool.version}</span>
              </div>
              {tool.importOnly && (
                <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded font-medium">
                  Import only
                </span>
              )}
            </div>

            <p className="text-sm text-slate-600 dark:text-slate-300">{tool.description}</p>

            {tool.profiles.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">Scan Profiles</p>
                <div className="space-y-1">
                  {tool.profiles.map(p => (
                    <div key={p.id} className="flex items-center gap-2 text-xs">
                      <span className="bg-blue-50 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300 px-2 py-0.5 rounded font-mono">
                        {p.id}
                      </span>
                      <span className="text-slate-500 dark:text-slate-400">{p.label}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {tool.proxyTypes.length > 0 && (
              <div>
                <p className="text-xs font-semibold text-slate-500 dark:text-slate-400 mb-1">Supported Proxy Types</p>
                <div className="flex flex-wrap gap-1">
                  {tool.proxyTypes.map(pt => (
                    <span
                      key={pt}
                      className="text-xs bg-slate-100 dark:bg-slate-700 text-slate-600 dark:text-slate-300 px-2 py-0.5 rounded font-mono"
                    >
                      {pt}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}
