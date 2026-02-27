from __future__ import annotations

import base64
import urllib.request


def fetch_subscription(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "vless-top-bot/0.1",
            "Accept": "*/*",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        data = resp.read()
    return data.decode("utf-8", errors="replace").strip()


def maybe_base64_decode(text: str) -> str:
    if "vless://" in text:
        return text

    compact = "".join(text.split())
    pad = (-len(compact)) % 4
    compact_padded = compact + ("=" * pad)
    try:
        decoded = base64.b64decode(compact_padded, validate=False).decode("utf-8", errors="replace")
        if "vless://" in decoded:
            return decoded.strip()
    except Exception:
        pass
    return text
