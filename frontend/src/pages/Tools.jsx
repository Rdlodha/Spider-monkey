import { Wrench } from 'lucide-react'

const TOOLS = [
  // ── Network & Port Scanning ────────────────────────────────────────────
  {
    name: 'nmap',
    version: '7.93',
    category: 'Network Scanning',
    description: 'Network exploration and security auditing. Discovers hosts, open ports, and service versions.',
    outputFormat: 'XML  (run with -oX output.xml)',
    profiles: [{ id: 'nmap-top-1000', label: 'Top 1000 ports', flags: '-T4 --top-ports 1000 -oX -' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP'],
  },
  // ── Web Content Discovery ─────────────────────────────────────────────
  {
    name: 'feroxbuster',
    version: '2.8.4',
    category: 'Web Discovery',
    description: 'Fast, recursive content discovery for web applications.',
    outputFormat: 'JSON lines  (run with --json -o output.json)',
    profiles: [{ id: 'ferox-common', label: 'Common wordlist', flags: '--json -w common.txt' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  {
    name: 'gobuster',
    version: '3.6.0',
    category: 'Web Discovery',
    description: 'Directory / DNS subdomain brute-force tool.',
    outputFormat: 'Plain text  (standard stdout)',
    profiles: [{ id: 'gobuster-dir', label: 'Directory mode', flags: 'dir -w common.txt' }],
    proxyTypes: ['DIRECT', 'HTTP', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  // ── Subdomain & Passive Recon ─────────────────────────────────────────
  {
    name: 'subfinder',
    version: '2.6.x',
    category: 'Subdomain Recon',
    description: 'Passive subdomain enumeration using certificate transparency, DNS datasets, Shodan, VirusTotal, and many other OSINT sources.',
    outputFormat: 'JSON lines  (run with -oJ -silent)',
    profiles: [
      { id: 'subfinder-passive', label: 'Passive only', flags: '-oJ -silent' },
      { id: 'subfinder-all',     label: 'All sources',  flags: '-oJ -silent -all' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  {
    name: 'amass',
    version: '4.x',
    category: 'Subdomain Recon',
    description: 'In-depth attack surface mapping using DNS brute-force, certificate logs, OSINT, and active enumeration. Resolves IPs for each subdomain.',
    outputFormat: 'JSON lines  (run with enum -json -d target.com)',
    profiles: [
      { id: 'amass-enum',        label: 'Passive enum',  flags: 'enum -json -passive -d' },
      { id: 'amass-enum-active', label: 'Active enum',   flags: 'enum -json -d' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'SOCKS5'],
  },
  // ── Web Probing & Technology Fingerprinting ───────────────────────────
  {
    name: 'httpx',
    version: '1.6.x',
    category: 'Web Probing',
    description: 'Fast HTTP probing tool. Checks which hosts run HTTP/HTTPS, extracts status codes, titles, web server banners, and detected technologies.',
    outputFormat: 'JSON lines  (run with -json -silent -tech-detect -status-code -web-server)',
    profiles: [
      { id: 'httpx-probe', label: 'Full probe', flags: '-json -silent -title -tech-detect -status-code -content-length -web-server' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'SOCKS5', 'BURP', 'CUSTOM'],
  },
  {
    name: 'whatweb',
    version: '0.5.x',
    category: 'Web Probing',
    description: 'Web technology fingerprinter. Detects CMS (WordPress, Drupal), frameworks (jQuery, Bootstrap), server software (Apache, Nginx), and plugin versions.',
    outputFormat: 'JSON  (run with -a 3 --log-json=output.json)',
    profiles: [
      { id: 'whatweb-default',  label: 'Aggressive (level 3)', flags: '-a 3 --log-json=-' },
      { id: 'whatweb-stealthy', label: 'Stealthy (level 1)',   flags: '-a 1 --log-json=-' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'BURP', 'CUSTOM'],
  },
  {
    name: 'wappalyzer',
    version: 'CLI',
    category: 'Web Probing',
    description: 'Browser-based technology fingerprinter. Identifies JavaScript frameworks, CMSs, CDN providers, analytics tools, and e-commerce platforms via header and DOM analysis.',
    outputFormat: 'JSON  (run with wappalyzer https://target --output=json)',
    profiles: [
      { id: 'wappalyzer-default', label: 'Default scan', flags: '--output=json' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'BURP', 'CUSTOM'],
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
              <div className="flex items-center gap-2">
                {tool.category && (
                  <span className="text-xs bg-indigo-50 dark:bg-indigo-900/40 text-indigo-700 dark:text-indigo-300 px-2 py-0.5 rounded font-medium">
                    {tool.category}
                  </span>
                )}
                {tool.importOnly && (
                  <span className="text-xs bg-amber-100 dark:bg-amber-900/40 text-amber-700 dark:text-amber-300 px-2 py-0.5 rounded font-medium">
                    Import only
                  </span>
                )}
              </div>
            </div>

            <p className="text-sm text-slate-600 dark:text-slate-300">{tool.description}</p>

            {tool.outputFormat && (
              <div className="bg-slate-50 dark:bg-slate-900/50 p-2.5 rounded-lg border border-slate-200 dark:border-slate-700/60 text-xs">
                <span className="text-slate-500 dark:text-slate-400 font-semibold block mb-0.5">Import Format:</span>
                <code className="text-slate-700 dark:text-slate-200 font-mono">{tool.outputFormat}</code>
              </div>
            )}

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
