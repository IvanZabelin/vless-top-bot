from __future__ import annotations

import asyncio
import statistics
import time
from typing import Optional

from .models import Node


async def tcp_latency_once(host: str, port: int, timeout: float) -> Optional[float]:
    start = time.perf_counter()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass
        return (time.perf_counter() - start) * 1000.0
    except Exception:
        return None


async def measure_node(node: Node, attempts: int, timeout: float, sem: asyncio.Semaphore):
    results: list[float] = []
    async with sem:
        for _ in range(attempts):
            ms = await tcp_latency_once(node.host, node.port, timeout)
            if ms is not None:
                results.append(ms)

    if not results:
        return node, None, 0

    return node, statistics.median(results), len(results)
