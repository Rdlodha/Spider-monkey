"""
Parser registry: selects the correct parser by sniffing content or via
a manual override (tool name string).
"""
from app.parsers import BaseParser, ParseResult
from app.parsers.nmap_parser import NmapParser
from app.parsers.ferox_parser import FeroxParser
from app.parsers.gobuster_parser import GobusterParser
from app.parsers.subfinder_parser import SubfinderParser
from app.parsers.amass_parser import AmassParser
from app.parsers.httpx_parser import HttpxParser
from app.parsers.whatweb_parser import WhatWebParser
from app.parsers.wappalyzer_parser import WappalyzerParser

_REGISTRY: list[BaseParser] = [
    NmapParser(),
    # Wappalyzer must come before FeroxParser/HttpxParser because it is a single
    # JSON object (not JSON-lines); check it before the JSON-lines parsers.
    WappalyzerParser(),
    # HttpxParser must come before FeroxParser because both are JSON-lines with 'url',
    # but httpx uses 'status-code' (hyphenated) which is the distinguishing key.
    HttpxParser(),
    FeroxParser(),
    GobusterParser(),
    # SubfinderParser and AmassParser both use JSON-lines but with different key sets;
    # Amass has 'addresses', Subfinder has 'source'/'input'.
    AmassParser(),
    SubfinderParser(),
    WhatWebParser(),
]

TOOL_MAP: dict[str, BaseParser] = {p.name: p for p in _REGISTRY}


def get_parser(content: bytes, tool_override: str | None = None) -> BaseParser | None:
    """
    Return a parser for *content*.

    If *tool_override* is given (e.g. "nmap"), look up by name first;
    fall back to content sniffing only when no override is provided.
    """
    if tool_override:
        return TOOL_MAP.get(tool_override.lower())
    for parser in _REGISTRY:
        if parser.can_parse(content):
            return parser
    return None
