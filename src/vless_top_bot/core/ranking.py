from __future__ import annotations

from .models import Node


def split_and_sort(results):
    ok = [(n, ms, succ) for (n, ms, succ) in results if ms is not None]
    bad = [(n, ms, succ) for (n, ms, succ) in results if ms is None]
    ok.sort(key=lambda x: x[1])
    return ok, bad


def top_nodes(ok_results, top_n: int) -> list[Node]:
    return [n for (n, _, _) in ok_results[:top_n]]


def render_report(total: int, ok_results, bad_results, top_n: int) -> str:
    lines = [
        f"Всего узлов: {total}",
        f"Доступны: {len(ok_results)}",
        f"Недоступны: {len(bad_results)}",
        "",
        f"ТОП-{top_n} по TCP latency:",
    ]

    for i, (n, ms, succ) in enumerate(ok_results[:top_n], 1):
        lines.append(f"{i}. {ms:.1f} ms ({succ} ok) {n.name} -> {n.host}:{n.port}")

    return "\n".join(lines)
