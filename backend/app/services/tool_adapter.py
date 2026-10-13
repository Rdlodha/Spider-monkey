"""ToolAdapter abstract base and concrete adapters for supported scanning tools.

The design follows the specification in *M4_TOOL_ENGINE.md* (Part A).

- `ToolAdapter` defines the contract used by the job runner.
- Concrete adapters (`NmapAdapter`, `FeroxbusterAdapter`, `GobusterAdapter`) implement:
  * `validate` – basic request sanity checks (no leading dash, allowed profile, wordlist existence).
  * `build_command` – returns a list of argv strings (no shell usage).
  * `execute` – delegated to the job runner; here we only expose the interface.
  * `parse` – calls the existing parser modules (`nmap_parser`, `ferox_parser`, `gobuster_parser`).
  * `metadata` – static tool metadata (name, version, supported profiles).

Only a minimal stub implementation is provided now – the heavy‑lifting (subprocess execution) lives in
`backend/app/services/job_runner.py`.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Dict, List

# Import parser classes from the existing parsers package.
from app.parsers.nmap_parser import NmapParser as _NmapParser
from app.parsers.ferox_parser import FeroxParser as _FeroxParser
from app.parsers.gobuster_parser import GobusterParser as _GobusterParser

_nmap_parser = _NmapParser()
_ferox_parser = _FeroxParser()
_gobuster_parser = _GobusterParser()

# ---------------------------------------------------------------------------
# Abstract base
# ---------------------------------------------------------------------------

class ToolAdapter(ABC):
    """Contract for a scanning tool.

    The job runner will instantiate a concrete adapter based on the ``tool`` field of a
    :class:`Job` record and interact with it via these methods.
    """

    @abstractmethod
    def validate(self, request: Dict[str, Any]) -> None:
        """Validate the incoming scan request.

        Should raise ``ValueError`` with a helpful message if validation fails.
        """

    @abstractmethod
    def build_command(self, request: Dict[str, Any]) -> List[str]:
        """Return the command as an ``argv`` list.

        The list must **not** be joined into a single string – the runner will pass it
        directly to ``asyncio.create_subprocess_exec``.
        """

    @abstractmethod
    async def execute(self, cmd: List[str]) -> Dict[str, Any]:
        """Placeholder – the actual execution is performed by ``job_runner``.

        The method signature is kept for symmetry with other adapters that may wish
        to implement their own execution strategy.
        """

    @abstractmethod
    def parse(self, raw_output: bytes) -> List[Dict[str, Any]]:
        """Parse raw tool output and return a list of *entity* dictionaries.

        The entities are later fed to the existing import service (`run_import`).
        """

    @abstractmethod
    def metadata(self) -> Dict[str, Any]:
        """Static metadata (e.g. name, version, supported profiles)."""

# ---------------------------------------------------------------------------
# Concrete adapters
# ---------------------------------------------------------------------------

# Helper for profile‑to‑flag mapping – in a real project this would be driven by a
# configuration file.  Here we keep it simple.
_PROFILE_FLAGS = {
    "nmap-top-1000": ["-T4", "--top-ports", "1000", "-oX", "-"],
    "ferox-common": ["--json", "-w", "common.txt"],
    "gobuster-dir": ["dir", "-w", "common.txt"],
}

_ALLOWED_WORDLIST_DIR = Path(os.getenv("WORDLIST_DIR", "./wordlists")).resolve()



def _proxy_flags_for_tool(tool: str, proxy: Dict[str, Any]) -> List[str]:
    """Translate a proxy profile dict into argv flags for a given tool.

    ``proxy`` is expected to have keys: ``type``, ``host``, ``port``, ``username``,
    ``password`` (plaintext, decrypted by the caller before passing here).

    Raises ``ValueError`` if the tool does not support the requested proxy type.
    """
    if not proxy or proxy.get("type") == "DIRECT":
        return []

    ptype = proxy.get("type", "DIRECT")
    host = proxy.get("host", "127.0.0.1")
    port = proxy.get("port", 8080)
    username = proxy.get("username")
    password = proxy.get("password")

    if tool == "nmap":
        # nmap supports --proxies with http/socks4 only (no auth)
        if ptype in {"HTTP", "BURP"}:
            return [f"--proxies", f"http://{host}:{port}"]
        elif ptype == "SOCKS5":
            return [f"--proxies", f"socks5://{host}:{port}"]
        else:
            raise ValueError(f"nmap does not support proxy type {ptype}")

    elif tool == "feroxbuster":
        # feroxbuster: --proxy <url>
        if ptype in {"HTTP", "HTTPS", "BURP", "CUSTOM"}:
            if username and password:
                url = f"http://{username}:{password}@{host}:{port}"
            else:
                url = f"http://{host}:{port}"
            return ["--proxy", url]
        elif ptype == "SOCKS5":
            url = f"socks5://{host}:{port}"
            return ["--proxy", url]
        else:
            raise ValueError(f"feroxbuster does not support proxy type {ptype}")

    elif tool == "gobuster":
        # gobuster: --proxy <url>
        if ptype in {"HTTP", "HTTPS", "BURP", "CUSTOM"}:
            if username and password:
                url = f"http://{username}:{password}@{host}:{port}"
            else:
                url = f"http://{host}:{port}"
            return ["--proxy", url]
        elif ptype == "SOCKS5":
            url = f"socks5://{host}:{port}"
            return ["--proxy", url]
        else:
            raise ValueError(f"gobuster does not support proxy type {ptype}")

    return []


class NmapAdapter(ToolAdapter):
    def validate(self, request: Dict[str, Any]) -> None:
        target = request["target"]
        if target.startswith("-"):
            raise ValueError("Target cannot start with a dash (possible command injection).")
        profile = request.get("profile")
        if profile not in {"nmap-top-1000"}:
            raise ValueError(f"Unsupported nmap profile: {profile}")
        # Validate proxy compatibility
        proxy = request.get("proxy")
        if proxy and proxy.get("type") not in {"DIRECT", "HTTP", "SOCKS5", "BURP"}:
            raise ValueError(f"nmap does not support proxy type '{proxy.get('type')}'.")

    def build_command(self, request: Dict[str, Any]) -> List[str]:
        target = request["target"]
        profile = request.get("profile")
        flags = list(_PROFILE_FLAGS.get(profile, []))
        proxy_flags = _proxy_flags_for_tool("nmap", request.get("proxy") or {})
        return ["nmap", *flags, *proxy_flags, target]

    async def execute(self, cmd: List[str]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def parse(self, raw_output: bytes) -> List[Dict[str, Any]]:
        result = _nmap_parser.parse(raw_output)
        return [{"type": "host", **vars(h)} for h in result.hosts] + \
               [{"type": "service", **vars(s)} for s in result.services]

    def metadata(self) -> Dict[str, Any]:
        return {"name": "nmap", "version": "7.93", "profiles": ["nmap-top-1000"],
                "proxy_types": ["DIRECT", "HTTP", "SOCKS5", "BURP"]}


class FeroxbusterAdapter(ToolAdapter):
    def validate(self, request: Dict[str, Any]) -> None:
        target = request["target"]
        if target.startswith("-"):
            raise ValueError("Target cannot start with a dash.")
        profile = request.get("profile")
        if profile not in {"ferox-common"}:
            raise ValueError(f"Unsupported feroxbuster profile: {profile}")
        # Wordlist safety
        wordlist = "common.txt"
        wl_path = (_ALLOWED_WORDLIST_DIR / wordlist).resolve()
        if not wl_path.is_file():
            raise ValueError("Wordlist not found on server.")
        # Validate proxy compatibility
        proxy = request.get("proxy")
        if proxy and proxy.get("type") == "HTTPS":
            raise ValueError("feroxbuster proxy: use HTTP type for TLS interception proxies.")

    def build_command(self, request: Dict[str, Any]) -> List[str]:
        target = request["target"]
        profile = request.get("profile")
        flags = list(_PROFILE_FLAGS.get(profile, []))
        proxy_flags = _proxy_flags_for_tool("feroxbuster", request.get("proxy") or {})
        return ["feroxbuster", *flags, *proxy_flags, "--url", target]

    async def execute(self, cmd: List[str]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def parse(self, raw_output: bytes) -> List[Dict[str, Any]]:
        result = _ferox_parser.parse(raw_output)
        return [{"type": "endpoint", **vars(e)} for e in result.endpoints]

    def metadata(self) -> Dict[str, Any]:
        return {"name": "feroxbuster", "version": "2.8.4", "profiles": ["ferox-common"],
                "proxy_types": ["DIRECT", "HTTP", "SOCKS5", "BURP", "CUSTOM"]}


class GobusterAdapter(ToolAdapter):
    def validate(self, request: Dict[str, Any]) -> None:
        target = request["target"]
        if target.startswith("-"):
            raise ValueError("Target cannot start with a dash.")
        profile = request.get("profile")
        if profile not in {"gobuster-dir"}:
            raise ValueError(f"Unsupported gobuster profile: {profile}")
        proxy = request.get("proxy")
        if proxy and proxy.get("type") == "HTTPS":
            raise ValueError("gobuster proxy: use HTTP type for TLS interception proxies.")

    def build_command(self, request: Dict[str, Any]) -> List[str]:
        target = request["target"]
        profile = request.get("profile")
        flags = list(_PROFILE_FLAGS.get(profile, []))
        proxy_flags = _proxy_flags_for_tool("gobuster", request.get("proxy") or {})
        return ["gobuster", *flags, *proxy_flags, "-u", target]

    async def execute(self, cmd: List[str]) -> Dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    def parse(self, raw_output: bytes) -> List[Dict[str, Any]]:
        result = _gobuster_parser.parse(raw_output)
        return [{"type": "endpoint", **vars(e)} for e in result.endpoints]

    def metadata(self) -> Dict[str, Any]:
        return {"name": "gobuster", "version": "3.6.0", "profiles": ["gobuster-dir"],
                "proxy_types": ["DIRECT", "HTTP", "SOCKS5", "BURP", "CUSTOM"]}


# ---------------------------------------------------------------------------
# Adapter factory – used by the job runner.
# ---------------------------------------------------------------------------

_ADAPTER_REGISTRY = {
    "nmap": NmapAdapter(),
    "feroxbuster": FeroxbusterAdapter(),
    "gobuster": GobusterAdapter(),
}


def get_adapter(name: str) -> ToolAdapter:
    """Return the registered adapter for *name*.

    Raises ``KeyError`` if the tool is unknown.
    """
    try:
        return _ADAPTER_REGISTRY[name]
    except KeyError as exc:
        raise KeyError(f"No adapter registered for tool '{name}'.") from exc

"""End of tool_adapter module"""
