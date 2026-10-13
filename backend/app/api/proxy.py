"""Proxy Manager API.

Endpoints:
  POST   /api/proxy-profiles          – create
  GET    /api/proxy-profiles          – list  (no secrets returned)
  GET    /api/proxy-profiles/{id}     – detail
  PATCH  /api/proxy-profiles/{id}     – update
  DELETE /api/proxy-profiles/{id}     – delete
  POST   /api/proxy-profiles/{id}/test – connectivity test

The encrypted_password column is NEVER returned; callers receive `has_secret: true/false`.
"""

from __future__ import annotations

import os
import socket
from typing import Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.projects import get_db
from app.core.audit import audit
from app.core.crypto import encrypt_secret, decrypt_secret
from app.models.base import ProxyProfile
from app.schemas.proxy import (
    ProxyProfileCreate,
    ProxyProfileUpdate,
    ProxyProfileOut,
    ProxyTestResult,
)

router = APIRouter()

# Fixed health-check URL for proxy tests – configurable, not user-supplied.
_PROXY_CHECK_URL = os.getenv("PROXY_CHECK_URL", "https://httpbin.org/ip")
# Short timeout for proxy tests (seconds).
_PROXY_TEST_TIMEOUT = float(os.getenv("PROXY_TEST_TIMEOUT", "8"))


# ── helpers ──────────────────────────────────────────────────────────────────

def _to_out(profile: ProxyProfile) -> ProxyProfileOut:
    return ProxyProfileOut(
        id=profile.id,
        name=profile.name,
        type=profile.type,
        host=profile.host,
        port=profile.port,
        username=profile.username,
        has_secret=bool(profile.encrypted_password),
    )


def _proxy_url(profile: ProxyProfile, plaintext_password: Optional[str] = None) -> Optional[str]:
    """Build a proxy URL string for httpx from a profile row.

    The password is either already stored (and decrypted here) or passed in for a
    freshly-created profile before the first DB commit.
    """
    if profile.type == "DIRECT":
        return None

    scheme_map = {
        "HTTP": "http",
        "HTTPS": "https",
        "SOCKS5": "socks5",
        "BURP": "http",   # Burp Suite is an HTTP proxy on a custom port
        "CUSTOM": "http",
    }
    scheme = scheme_map.get(profile.type, "http")

    password: Optional[str] = None
    if profile.encrypted_password:
        try:
            password = decrypt_secret(profile.encrypted_password)
        except Exception:
            password = None
    elif plaintext_password:
        password = plaintext_password

    host = profile.host or "127.0.0.1"
    port = profile.port or 8080

    if profile.username and password:
        return f"{scheme}://{profile.username}:{password}@{host}:{port}"
    elif profile.username:
        return f"{scheme}://{profile.username}@{host}:{port}"
    else:
        return f"{scheme}://{host}:{port}"


# ── CRUD ─────────────────────────────────────────────────────────────────────

@router.post("", response_model=ProxyProfileOut, status_code=status.HTTP_201_CREATED)
def create_proxy_profile(body: ProxyProfileCreate, db: Session = Depends(get_db)):
    encrypted_pw = encrypt_secret(body.password) if body.password else None
    profile = ProxyProfile(
        name=body.name,
        type=body.type,
        host=body.host,
        port=body.port,
        username=body.username,
        encrypted_password=encrypted_pw,
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    audit(db, action="proxy_profile_created", target=profile.id, result=profile.type)
    return _to_out(profile)


@router.get("", response_model=list[ProxyProfileOut])
def list_proxy_profiles(db: Session = Depends(get_db)):
    return [_to_out(p) for p in db.query(ProxyProfile).all()]


@router.get("/{profile_id}", response_model=ProxyProfileOut)
def get_proxy_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.get(ProxyProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Proxy profile not found")
    return _to_out(profile)


@router.patch("/{profile_id}", response_model=ProxyProfileOut)
def update_proxy_profile(profile_id: str, body: ProxyProfileUpdate, db: Session = Depends(get_db)):
    profile = db.get(ProxyProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Proxy profile not found")

    if body.name is not None:
        profile.name = body.name
    if body.type is not None:
        profile.type = body.type
    if body.host is not None:
        profile.host = body.host
    if body.port is not None:
        profile.port = body.port
    if body.username is not None:
        profile.username = body.username
    if body.password is not None:
        profile.encrypted_password = encrypt_secret(body.password)

    db.commit()
    db.refresh(profile)
    audit(db, action="proxy_profile_updated", target=profile.id)
    return _to_out(profile)


@router.delete("/{profile_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_proxy_profile(profile_id: str, db: Session = Depends(get_db)):
    profile = db.get(ProxyProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Proxy profile not found")
    db.delete(profile)
    db.commit()
    audit(db, action="proxy_profile_deleted", target=profile_id)


# ── Proxy test ────────────────────────────────────────────────────────────────

@router.post("/{profile_id}/test", response_model=ProxyTestResult)
def test_proxy_profile(profile_id: str, db: Session = Depends(get_db)):
    """Test proxy connectivity.

    The test request goes to a **fixed, configurable URL** (``PROXY_CHECK_URL``),
    never to a user-supplied address.

    Returns one of four outcomes as per the spec:
    - ``Connected``
    - ``Failed``
    - ``Timeout``
    - ``Authentication failed``
    """
    profile = db.get(ProxyProfile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Proxy profile not found")

    proxy_url = _proxy_url(profile)

    try:
        with httpx.Client(proxy=proxy_url, timeout=_PROXY_TEST_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(_PROXY_CHECK_URL)

        if resp.status_code == 407:
            outcome = "Authentication failed"
        elif resp.status_code < 400:
            outcome = "Connected"
        else:
            outcome = "Failed"

    except httpx.TimeoutException:
        outcome = "Timeout"
    except httpx.ProxyError as exc:
        # httpx raises ProxyError with 407 details wrapped inside
        if "407" in str(exc):
            outcome = "Authentication failed"
        else:
            outcome = "Failed"
    except Exception:
        outcome = "Failed"

    audit(db, action="proxy_profile_tested", target=profile_id, result=outcome)
    return ProxyTestResult(outcome=outcome)
