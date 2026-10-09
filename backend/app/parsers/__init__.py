"""
Parser interface for ReconForge tool output parsing.
All parsers return ParseResult containing normalized objects.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class ParsedHost:
    ip: str
    hostname: Optional[str] = None


@dataclass
class ParsedService:
    ip: str
    protocol: str
    port: int
    state: str
    name: Optional[str] = None
    product: Optional[str] = None
    version: Optional[str] = None


@dataclass
class ParsedEndpoint:
    url: str
    path: Optional[str] = None
    status_code: Optional[int] = None
    content_length: Optional[int] = None
    source_tool: Optional[str] = None


@dataclass
class ParseResult:
    hosts: list[ParsedHost] = field(default_factory=list)
    services: list[ParsedService] = field(default_factory=list)
    endpoints: list[ParsedEndpoint] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


class BaseParser:
    """All parsers must implement this interface."""
    name: str = ""

    def can_parse(self, content: bytes) -> bool:
        raise NotImplementedError

    def parse(self, content: bytes) -> ParseResult:
        raise NotImplementedError
