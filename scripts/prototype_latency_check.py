#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import statistics
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class Node:
    raw: str
    name: str
    host: str
    port: int


def fetch_subscription(url: str, timeout: float = 15.0) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "vless-latency-check/1.1",
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


async def tcp_latency_once(host: str, port: int, timeout: float) -> Optional[float]:
    start = time.perf_counter()
    try:
        reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        end = time.perf_counter()
        return (end - start) * 1000.0
    except Exception:
        return None


async def measure_node(node: Node, attempts: int, timeout: float, sem: asyncio.Semaphore):
    results: List[float] = []
    async with sem:
        for _ in range(attempts):
            ms = await tcp_latency_once(node.host, node.port, timeout)
            if ms is not None:
                results.append(ms)
    if not results:
        return node, None, 0
    return node, statistics.median(results), len(results)


def save_top_links(path: str, top_nodes: List[Node]) -> None:
    content = "\n".join(n.raw for n in top_nodes) + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


async def main_async(args) -> int:
    raw = fetch_subscription(args.url, timeout=args.fetch_timeout)
    text = maybe_base64_decode(raw)
    nodes = parse_vless_lines(text)

    if not nodes:
        print("Не нашёл строк vless:// в подписке.")
        return 2

    sem = asyncio.Semaphore(args.concurrency)
    results = await asyncio.gather(*[
        measure_node(n, attempts=args.attempts, timeout=args.timeout, sem=sem) for n in nodes
    ])

    ok = [(n, ms, succ) for (n, ms, succ) in results if ms is not None]
    bad = [(n, ms, succ) for (n, ms, succ) in results if ms is None]
    ok.sort(key=lambda x: x[1])

    print(f"Всего узлов: {len(nodes)} | Успешно: {len(ok)} | Недоступны: {len(bad)}")

    top = ok[: args.top]
    if not top:
        print("Ни один узел не ответил по TCP.")
        return 3

    print(f"ТОП-{args.top}:")
    for i, (n, ms, succ) in enumerate(top, 1):
        print(f"{i:>2}. {ms:>7.1f} ms ({succ}/{args.attempts} ok) {n.name} -> {n.host}:{n.port}")

    top_nodes = [n for (n, _, _) in top]
    save_top_links(args.out, top_nodes)
    print(f"Сохранил: {args.out}")

    if args.print_links:
        print("\nСсылки:")
        for n in top_nodes:
            print(n.raw)

    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Select top VLESS nodes by TCP latency")
    p.add_argument("url", help="Subscription URL")
    p.add_argument("--top", type=int, default=5)
    p.add_argument("--attempts", type=int, default=3)
    p.add_argument("--timeout", type=float, default=2.0)
    p.add_argument("--fetch-timeout", type=float, default=15.0)
    p.add_argument("--concurrency", type=int, default=50)
    p.add_argument("--out", default="top_vless.txt")
    p.add_argument("--print-links", action="store_true")
    return p


def main() -> None:
    args = build_parser().parse_args()
    code = asyncio.run(main_async(args))
    raise SystemExit(code)


if __name__ == "__main__":
    main()
