from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import tempfile
import urllib.parse
import urllib.request
from urllib.error import HTTPError
from dataclasses import dataclass
from pathlib import Path

from .models import Node


@dataclass(frozen=True)
class YouTubeCheckConfig:
    check_timeout: float = 6.0
    tunnel_start_timeout: float = 4.0
    strict_mode: bool = True
    strict_attempts: int = 2


@dataclass(frozen=True)
class VlessSpec:
    uuid: str
    host: str
    port: int
    server_name: str | None
    security: str
    flow: str | None
    fingerprint: str | None
    reality_public_key: str | None
    reality_short_id: str | None
    network: str
    ws_path: str | None
    ws_host: str | None


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return int(s.getsockname()[1])


def _parse_vless(raw: str) -> VlessSpec:
    u = urllib.parse.urlsplit(raw)
    if "@" not in u.netloc:
        raise ValueError("bad netloc")

    user, hostport = u.netloc.split("@", 1)
    if not user:
        raise ValueError("missing uuid")

    host = hostport
    port = 443
    if hostport.startswith("[") and "]:" in hostport:
        host, port_s = hostport.split("]:", 1)
        host = host + "]"
        port = int(port_s)
    elif ":" in hostport:
        host, port_s = hostport.rsplit(":", 1)
        port = int(port_s)

    q = urllib.parse.parse_qs(u.query)

    security = (q.get("security", ["tls"])[0] or "tls").lower()
    network = (q.get("type", ["tcp"])[0] or "tcp").lower()

    sni = q.get("sni", [None])[0]
    flow = q.get("flow", [None])[0]
    fingerprint = q.get("fp", [None])[0]
    pbk = q.get("pbk", [None])[0]
    sid = q.get("sid", [None])[0]

    ws_path = q.get("path", [None])[0]
    ws_host = q.get("host", [None])[0]

    return VlessSpec(
        uuid=user,
        host=host.strip("[]"),
        port=port,
        server_name=sni,
        security=security,
        flow=flow,
        fingerprint=fingerprint,
        reality_public_key=pbk,
        reality_short_id=sid,
        network=network,
        ws_path=ws_path,
        ws_host=ws_host,
    )


def _build_singbox_config(spec: VlessSpec, local_port: int) -> dict:
    outbound: dict = {
        "type": "vless",
        "tag": "proxy",
        "server": spec.host,
        "server_port": spec.port,
        "uuid": spec.uuid,
    }

    if spec.flow:
        outbound["flow"] = spec.flow

    tls_cfg: dict = {}
    if spec.security in {"tls", "reality"}:
        tls_cfg = {
            "enabled": True,
            "server_name": spec.server_name or spec.host,
            "insecure": False,
        }

        if spec.security == "reality":
            if not spec.reality_public_key:
                raise ValueError("reality without pbk")
            tls_cfg["reality"] = {
                "enabled": True,
                "public_key": spec.reality_public_key,
                "short_id": spec.reality_short_id or "",
            }
            # Для reality в sing-box обязателен uTLS fingerprint.
            tls_cfg["utls"] = {
                "enabled": True,
                "fingerprint": spec.fingerprint or "chrome",
            }

    if tls_cfg:
        outbound["tls"] = tls_cfg

    if spec.network == "ws":
        outbound["transport"] = {
            "type": "ws",
            "path": spec.ws_path or "/",
            "headers": {"Host": spec.ws_host} if spec.ws_host else {},
        }
    elif spec.network in {"tcp", "grpc"}:
        if spec.network == "grpc":
            outbound["transport"] = {"type": "grpc"}
    else:
        raise ValueError(f"unsupported network: {spec.network}")

    return {
        "log": {"disabled": True},
        "inbounds": [
            {
                "type": "mixed",
                "tag": "mixed-in",
                "listen": "127.0.0.1",
                "listen_port": local_port,
            }
        ],
        "outbounds": [
            outbound,
            {"type": "direct", "tag": "direct"},
        ],
        "route": {"final": "proxy"},
    }


def _http_via_proxy(url: str, proxy_port: int, timeout: float) -> bool:
    opener = urllib.request.build_opener(
        urllib.request.ProxyHandler(
            {
                "http": f"http://127.0.0.1:{proxy_port}",
                "https": f"http://127.0.0.1:{proxy_port}",
            }
        )
    )
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "vless-top-bot/0.1",
            "Accept": "*/*",
            "Range": "bytes=0-1",
        },
    )
    try:
        with opener.open(req, timeout=timeout) as resp:
            code = getattr(resp, "status", 200)
        return 200 <= code < 500
    except HTTPError as e:
        return 200 <= int(getattr(e, "code", 0) or 0) < 500


async def _wait_proxy_ready(proxy_port: int, timeout: float) -> bool:
    loop = asyncio.get_running_loop()
    deadline = loop.time() + max(0.2, timeout)
    while loop.time() < deadline:
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection("127.0.0.1", proxy_port), timeout=0.6
            )
            writer.close()
            await writer.wait_closed()
            return True
        except Exception:
            await asyncio.sleep(0.12)
    return False


async def _run_youtube_probe(raw_vless: str, cfg: YouTubeCheckConfig) -> str:
    sing_box = shutil.which("sing-box")
    if not sing_box:
        return "⚪ sing-box не найден"

    try:
        spec = _parse_vless(raw_vless)
        local_port = _pick_free_port()
        config = _build_singbox_config(spec, local_port)
    except Exception as e:
        return f"⚪ пропуск ({e})"

    with tempfile.TemporaryDirectory(prefix="vless-yt-") as td:
        config_path = Path(td) / "config.json"
        config_path.write_text(json.dumps(config, ensure_ascii=False), encoding="utf-8")

        proc = await asyncio.create_subprocess_exec(
            sing_box,
            "run",
            "-c",
            os.fspath(config_path),
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        try:
            ready = await _wait_proxy_ready(local_port, cfg.tunnel_start_timeout)
            if not ready:
                return "⚪ tunnel timeout"

            web_targets = [
                "https://www.youtube.com/generate_204",
                "https://m.youtube.com/generate_204",
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "https://www.youtube.com/",
            ]
            stream_targets = [
                "https://rr1---sn-a5mekn7e.googlevideo.com/generate_204",
                "https://rr2---sn-a5mekn7e.googlevideo.com/generate_204",
            ]
            control_targets = [
                "https://www.google.com/generate_204",
                "https://www.gstatic.com/generate_204",
            ]

            attempts = max(1, cfg.strict_attempts if cfg.strict_mode else 1)

            async def probe_any(urls: list[str]) -> bool:
                for _ in range(attempts):
                    for url in urls:
                        try:
                            ok = await asyncio.to_thread(_http_via_proxy, url, local_port, cfg.check_timeout)
                            if ok:
                                return True
                        except Exception:
                            pass
                    await asyncio.sleep(0.15)
                return False

            web_ok = await probe_any(web_targets)
            stream_ok = await probe_any(stream_targets)
            control_ok = await probe_any(control_targets)

            if web_ok:
                return "✅ OK" if stream_ok else "⚠️ partial"
            if stream_ok:
                return "⚠️ partial"
            if control_ok:
                return "❌ blocked"
            return "⚠️ uncertain"
        except Exception:
            return "⚠️ uncertain"
        finally:
            if proc.returncode is None:
                proc.terminate()
                try:
                    await asyncio.wait_for(proc.wait(), timeout=2.0)
                except Exception:
                    proc.kill()
                    try:
                        await asyncio.wait_for(proc.wait(), timeout=1.5)
                    except Exception:
                        pass


async def check_youtube_for_top(nodes: list[Node], cfg: YouTubeCheckConfig) -> dict[str, str]:
    result: dict[str, str] = {}
    for node in nodes:
        result[node.raw] = await _run_youtube_probe(node.raw, cfg)
    return result
