# ReconForge — Tool Integration Guide for AI Agents & Developers

This document serves as the **exact, deterministic step-by-step blueprint** for adding any new security reconnaissance, scanning, or information-gathering tool to ReconForge. Any AI assistant or developer reading this file can integrate a tool in minutes without having to reverse-engineer or re-analyze the codebase.

---

## 1. Architecture Overview (The 5-Point Touch Plan)

Adding a tool requires touching exactly 5 locations:

```
[Tool Output]
      │
      ▼
1. backend/app/parsers/<tool>_parser.py    ──> Parses raw format (JSON, XML, text) into ParseResult
      │
      ▼
2. backend/app/parsers/registry.py         ──> Registers parser in _REGISTRY and TOOL_MAP
      │
      ▼
3. backend/app/services/tool_adapter.py    ──> Builds CLI command args, profiles & proxy flags
      │
      ▼
4. frontend/src/pages/Scans.jsx            ──> Adds tool to import dropdown & hint text
      │
      ▼
5. frontend/src/pages/Tools.jsx            ──> Adds tool reference card with profiles & proxy types
```

---

## 2. Step 1: Create the Parser (`backend/app/parsers/<tool>_parser.py`)

Every parser inherits from `BaseParser` and returns a `ParseResult`.

### 2.1 The Data Models (`app.parsers`)
The parser maps raw tool output into these normalized dataclasses:

```python
from app.parsers import BaseParser, ParseResult, ParsedHost, ParsedService, ParsedEndpoint

@dataclass
class ParsedHost:
    ip: str                       # Discovered IP (or hostname placeholder if IP unresolvable)
    hostname: Optional[str] = None

@dataclass
class ParsedService:
    ip: str                       # Must match the host's IP
    protocol: str                 # "tcp" or "udp"
    port: int                     # e.g., 80, 443, 8080
    state: str                    # "open", "filtered", "closed"
    name: Optional[str] = None    # "http", "ssh", "mysql"
    product: Optional[str] = None # "Apache", "Nginx", "OpenSSH"
    version: Optional[str] = None # "2.4.51", "1.21.0"

@dataclass
class ParsedEndpoint:
    url: str                      # Normalized URL (e.g. "http://example.com/api")
    path: Optional[str] = None    # "/api"
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    source_tool: Optional[str] = None # e.g. "<tool_name>" or "<tool_name>:metadata"
```

### 2.2 Template Parser Code
Save as `backend/app/parsers/<tool_name>_parser.py`:

```python
"""
<ToolName> output parser.
Expected format: <JSON-lines / JSON / XML / text lines>.
"""
import json
from app.parsers import BaseParser, ParseResult, ParsedHost, ParsedService, ParsedEndpoint

class ToolNameParser(BaseParser):
    name = "<tool_name>"  # lowercase unique name, e.g. "nuclei", "katana", "naabu"

    def can_parse(self, content: bytes) -> bool:
        """
        Content sniffer: Return True if the bytes match this tool's unique signatures.
        Always inspect safely (e.g., first 512 bytes or line-by-line). Never crash on non-matching formats.
        """
        for line in content.split(b"\n")[:5]:
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
                # Check for tool-specific distinct keys:
                return "unique_key_1" in obj and "unique_key_2" in obj
            except Exception:
                return False
        return False

    def parse(self, content: bytes) -> ParseResult:
        result = ParseResult()
        lines = content.decode("utf-8", errors="replace").splitlines()

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except Exception as e:
                result.errors.append(f"Line {i}: Parse error — {e}")
                continue

            # Populate result.hosts, result.services, or result.endpoints here
            # e.g.:
            # result.hosts.append(ParsedHost(ip=obj["ip"], hostname=obj.get("host")))
            # result.endpoints.append(ParsedEndpoint(url=obj["url"], status_code=obj.get("status"), source_tool=self.name))

        return result
```

---

## 3. Step 2: Register the Parser (`backend/app/parsers/registry.py`)

1. Import your parser:
   ```python
   from app.parsers.<tool_name>_parser import ToolNameParser
   ```
2. Add an instance to `_REGISTRY`:
   ```python
   _REGISTRY: list[BaseParser] = [
       ...
       ToolNameParser(),
       ...
   ]
   ```
   > **Important Ordering Rule for Sniffing:**
   > - Place single root-JSON parsers (`WappalyzerParser`) **before** JSON-lines parsers.
   > - Place parsers with specific hyphenated or distinctive keys (`HttpxParser`, `AmassParser`) **before** generic JSON-lines parsers (`FeroxParser`).

---

## 4. Step 3: Implement Tool Adapter (`backend/app/services/tool_adapter.py`)

The tool adapter handles profile validation, command construction (with `argv` lists, **never** `shell=True`), and proxy flag injection.

### 4.1 Update `_PROFILE_FLAGS` (around line 90)
Define standard, non-interactive execution profiles that write output to stdout (`-`) or standard files:

```python
_PROFILE_FLAGS = {
    ...
    "<tool>-default": ["--flag-1", "--flag-2", "-o", "-"],
    "<tool>-fast":    ["--flag-1", "--fast"],
}
```

### 4.2 Update `_proxy_flags_for_tool` (around line 150)
Map the decrypted proxy dict (`ptype`, `host`, `port`, `username`, `password`) into the tool's CLI flags:

```python
    elif tool == "<tool_name>":
        if ptype in {"HTTP", "HTTPS", "BURP", "CUSTOM"}:
            if username and password:
                return ["--proxy", f"http://{username}:{password}@{host}:{port}"]
            return ["--proxy", f"http://{host}:{port}"]
        elif ptype == "SOCKS5":
            return ["--proxy", f"socks5://{host}:{port}"]
        else:
            raise ValueError(f"{tool} does not support proxy type {ptype}")
```

### 4.3 Create the `ToolAdapter` Class
Add this class before `_ADAPTER_REGISTRY`:

```python
from app.parsers.<tool_name>_parser import ToolNameParser as _ToolNameParser
_tool_name_parser = _ToolNameParser()

class ToolNameAdapter(ToolAdapter):
    _VALID_PROFILES = {"<tool>-default", "<tool>-fast"}

    def validate(self, request: Dict[str, Any]) -> None:
        target = request["target"]
        if target.startswith("-"):
            raise ValueError("Target cannot start with a dash (command injection guard).")
        profile = request.get("profile")
        if profile not in self._VALID_PROFILES:
            raise ValueError(f"Unsupported profile: {profile}. Valid: {self._VALID_PROFILES}")

    def build_command(self, request: Dict[str, Any]) -> List[str]:
        target = request["target"]
        flags = list(_PROFILE_FLAGS.get(request.get("profile", "<tool>-default"), []))
        proxy_flags = _proxy_flags_for_tool("<tool_name>", request.get("proxy") or {})
        return ["<tool_binary>", *flags, *proxy_flags, target]

    async def execute(self, cmd: List[str]) -> Dict[str, Any]:
        raise NotImplementedError  # Handled centrally by job_runner.py

    def parse(self, raw_output: bytes) -> List[Dict[str, Any]]:
        result = _tool_name_parser.parse(raw_output)
        rows = []
        rows += [{**vars(h), "type": "host"} for h in result.hosts]
        rows += [{**vars(s), "type": "service"} for s in result.services]
        rows += [{**vars(e), "type": "endpoint"} for e in result.endpoints]
        return rows

    def metadata(self) -> Dict[str, Any]:
        return {
            "name": "<tool_name>",
            "version": "1.0.0",
            "profiles": list(self._VALID_PROFILES),
            "proxy_types": ["DIRECT", "HTTP", "HTTPS", "SOCKS5", "BURP"],
            "output_format": "JSON lines",
            "description": "Brief description of what this tool accomplishes.",
        }
```

### 4.4 Register in `_ADAPTER_REGISTRY`
```python
_ADAPTER_REGISTRY = {
    ...
    "<tool_name>": ToolNameAdapter(),
}
```

---

## 5. Step 4: Update Frontend Scans UI (`frontend/src/pages/Scans.jsx`)

1. Add your tool to `SUPPORTED_TOOLS`:
   ```javascript
   const SUPPORTED_TOOLS = [
     ...
     { value: '<tool_name>', label: '<Tool Name> (JSON lines, -o output.json)', group: '<Category>' },
   ]
   ```
2. Update the helper text in the file upload card (around line 120):
   ```html
   <strong><ToolName></strong> → format description
   ```

---

## 6. Step 5: Update Frontend Tools Reference UI (`frontend/src/pages/Tools.jsx`)

Add a new card object to the `TOOLS` array:

```javascript
  {
    name: '<tool_name>',
    version: '1.x',
    category: '<Subdomain Recon | Network Scanning | Web Discovery | Web Probing | Vulnerability Scanning>',
    description: 'Concise summary of tool capabilities.',
    outputFormat: 'JSON lines  (run with <example CLI flags>)',
    profiles: [
      { id: '<tool>-default', label: 'Default scan', flags: '<flags>' },
    ],
    proxyTypes: ['DIRECT', 'HTTP', 'HTTPS', 'SOCKS5', 'BURP'],
  },
```

---

## 7. Verification Checklist

Whenever you finish adding a tool, run these commands to verify that nothing is broken:

```bash
# 1. Run backend tests (must all pass)
cd backend
python -m pytest tests/ -v

# 2. Check frontend build (must build with 0 errors)
cd ../frontend
npm run build
```

---

## 8. Summary Table: Common Security Tool Formats

| Tool | Category | Standard CLI Flags | Expected Format | ReconForge Mapping |
| :--- | :--- | :--- | :--- | :--- |
| **Nuclei** | Vulnerability Scan | `-json-export output.json` | JSON lines | Endpoints + Findings |
| **Naabu** | Port Scanning | `-json -o output.json` | JSON lines | Hosts + Services |
| **ffuf** | Web Fuzzing | `-o output.json -of json` | Root JSON object (`results: []`) | Endpoints |
| **Katana** | Web Crawling | `-json -o output.json` | JSON lines | Endpoints |
| **Waybackurls** | Historical URLs | (stdout redirect) | Plain text URLs (1 per line) | Endpoints |
| **Testssl.sh** | TLS / SSL Audit | `--jsonfile output.json` | JSON array of objects | Services + Findings |
