from __future__ import annotations

import hashlib


def hash_message(message: str) -> str:
    return hashlib.sha256(message.strip().lower().encode("utf-8")).hexdigest()
