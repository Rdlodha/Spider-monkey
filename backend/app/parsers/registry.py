"""
Parser registry: selects the correct parser by sniffing content or via
a manual override (tool name string).
"""
from app.parsers import BaseParser, ParseResult
from app.parsers.nmap_parser import NmapParser
from app.parsers.ferox_parser import FeroxParser
from app.parsers.gobuster_parser import GobusterParser

_REGISTRY: list[BaseParser] = [
    NmapParser(),
    FeroxParser(),
    GobusterParser(),
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
