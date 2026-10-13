"""Fernet-based encryption helper for proxy secrets.

The encryption key is read from the ``FERNET_KEY`` environment variable.
If the env var is absent, a key is generated and persisted to ``.local/fernet.key``
inside the backend directory so the same key survives process restarts.

**Never commit the key file.**  Add ``.local/`` to ``.gitignore`` (already done).
"""

from __future__ import annotations

import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken  # pip install cryptography

_KEY_FILE = Path(__file__).resolve().parent.parent.parent / ".local" / "fernet.key"


def _load_or_create_key() -> bytes:
    """Return the Fernet key bytes, generating and persisting one if needed."""
    env_key = os.getenv("FERNET_KEY")
    if env_key:
        return env_key.encode()

    _KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if _KEY_FILE.exists():
        return _KEY_FILE.read_bytes().strip()

    key = Fernet.generate_key()
    _KEY_FILE.write_bytes(key)
    return key


_fernet = Fernet(_load_or_create_key())


def encrypt_secret(plaintext: str) -> str:
    """Return a URL-safe base-64 encoded ciphertext string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Return the original plaintext or raise ``InvalidToken`` if tampered."""
    return _fernet.decrypt(ciphertext.encode()).decode()


def is_encrypted(value: str) -> bool:
    """Quick heuristic: Fernet tokens always start with 'gAAAAA'."""
    return value.startswith("gAAAAA")
