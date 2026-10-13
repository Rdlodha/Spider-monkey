"""Pydantic schemas for ProxyProfile endpoints."""

from __future__ import annotations

from typing import Literal, Optional
from pydantic import BaseModel, Field

ProxyType = Literal["DIRECT", "HTTP", "HTTPS", "SOCKS5", "BURP", "CUSTOM"]


class ProxyProfileCreate(BaseModel):
    name: str = Field(..., max_length=100)
    type: ProxyType = "DIRECT"
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None   # plaintext on the way in; encrypted at rest


class ProxyProfileUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    type: Optional[ProxyType] = None
    host: Optional[str] = None
    port: Optional[int] = Field(None, ge=1, le=65535)
    username: Optional[str] = None
    password: Optional[str] = None


class ProxyProfileOut(BaseModel):
    model_config = {"from_attributes": True}

    id: str
    name: str
    type: str
    host: Optional[str]
    port: Optional[int]
    username: Optional[str]
    has_secret: bool   # true when encrypted_password is set; never return the secret


class ProxyTestResult(BaseModel):
    outcome: Literal["Connected", "Failed", "Timeout", "Authentication failed"]
    detail: Optional[str] = None
