from __future__ import annotations

import asyncio

from vless_top_bot.core.latency_checker import measure_node
from vless_top_bot.core.ranking import render_report, split_and_sort, top_nodes
from vless_top_bot.core.subscription import fetch_subscription, maybe_base64_decode
from vless_top_bot.core.vless_parser import parse_vless_lines
from vless_top_bot.core.youtube_checker import YouTubeCheckConfig, check_youtube_for_top


class CheckService:
    async def run_check(
        self,
        subscription_url: str,
        top: int,
        attempts: int,
        timeout: float,
        fetch_timeout: float,
        concurrency: int,
        youtube_check_timeout: float,
        youtube_tunnel_start_timeout: float,
        youtube_strict_mode: bool,
        youtube_strict_attempts: int,
    ) -> tuple[str, list[str]]:
        raw = fetch_subscription(subscription_url, timeout=fetch_timeout)
        text = maybe_base64_decode(raw)
        nodes = parse_vless_lines(text)
        if not nodes:
            return "Не нашёл строк vless:// в подписке.", []

        sem = asyncio.Semaphore(concurrency)
        results = await asyncio.gather(
            *[measure_node(n, attempts=attempts, timeout=timeout, sem=sem) for n in nodes]
        )

        ok, bad = split_and_sort(results)
        if not ok:
            return "Ни один узел не ответил по TCP.", []

        top_list = top_nodes(ok, top)
        yt_status = await check_youtube_for_top(
            top_list,
            YouTubeCheckConfig(
                check_timeout=youtube_check_timeout,
                tunnel_start_timeout=youtube_tunnel_start_timeout,
                strict_mode=youtube_strict_mode,
                strict_attempts=youtube_strict_attempts,
            ),
        )

        report = render_report(len(nodes), ok, bad, top, youtube_status=yt_status)
        links = [n.raw for n in top_list]
        return report, links
