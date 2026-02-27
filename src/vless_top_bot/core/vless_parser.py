from __future__ import annotations

import urllib.parse
from typing import List

from .models import Node


def parse_vless_lines(text: str) -> List[Node]:
    nodes: List[Node] = []
    for raw in (ln.strip() for ln in text.splitlines()):
        if not raw or not raw.startswith("vless://"):
            continue

        u = urllib.parse.urlsplit(raw)
        name = urllib.parse.unquote(u.fragment or "").strip() or "noname"
        if "@" not in u.netloc:
            continue

        _, hostport = u.netloc.split("@", 1)
        host = hostport
        port = 443

        if hostport.startswith("["):
            if "]:" in hostport:
                host, port_s = hostport.split("]:", 1)
                host = host + "]"
                port = int(port_s)
        else:
            if ":" in hostport:
                host, port_s = hostport.rsplit(":", 1)
                port = int(port_s)

        nodes.append(Node(raw=raw, name=name, host=host.strip("[]"), port=port))

    return nodes
