#!/usr/bin/env python3
"""微信 API 出口代理解析（供 toolkit 与 scripts 共用）。

家用宽带只有动态公网 IP 时，公众号的 IP 白名单无法固定。常见做法是把请求固定从一台
固定公网 IP 的服务器出网（例如本机 SSH 隧道 + 服务器上的 tinyproxy），然后把该代理
写进 config.yaml，本模块负责把它解析成 requests 可用的 proxies。

优先级（先命中先用）：
  1. 环境变量 WECHAT_PROXY / WECHAT_HTTPS_PROXY / WECHAT_HTTP_PROXY
  2. config.yaml 的 wechat.proxy
  3. config.yaml 的 network.proxy
  4. config.yaml 的顶层 proxy

未配置时返回空 kwargs，requests 仍按自身规则出网（包括读取 HTTP(S)_PROXY 环境变量）。
设置 WECHAT_PROXY_DISABLE=1 可临时跳过配置里的代理。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

TOOLKIT_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TOOLKIT_ROOT.parent

PROXY_ENV_KEYS = ("WECHAT_PROXY", "WECHAT_HTTPS_PROXY", "WECHAT_HTTP_PROXY")
DISABLE_ENV_KEYS = ("WECHAT_PROXY_DISABLE", "WEWRITE_PROXY_DISABLE")
TRUTHY = {"1", "true", "yes", "on"}

_CACHE: dict[str, Any] = {"resolved": False, "url": ""}


def config_candidates() -> list[Path]:
    """按与发布脚本一致的顺序查找 config.yaml。"""
    paths: list[Path] = []
    for key in ("WEWRITE_PUBLISH_CONFIG", "WEWRITE_CONFIG"):
        raw = str(os.environ.get(key, "")).strip()
        if raw:
            candidate = Path(raw).expanduser()
            paths.append(candidate if candidate.is_absolute() else Path.cwd() / candidate)

    paths.extend(
        [
            Path.cwd() / "config.yaml",
            REPO_ROOT / "config.yaml",
            TOOLKIT_ROOT / "config.yaml",
            Path.home() / ".config" / "wewrite" / "config.yaml",
        ]
    )
    return paths


def _proxy_from_config() -> str:
    try:
        import yaml  # type: ignore
    except Exception:
        return ""

    for path in config_candidates():
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception:
            continue
        if not isinstance(data, dict):
            continue

        for holder in (data.get("wechat"), data.get("network")):
            if isinstance(holder, dict):
                value = str(holder.get("proxy") or holder.get("http_proxy") or "").strip()
                if value:
                    return value

        value = str(data.get("proxy") or "").strip()
        if value:
            return value

    return ""


def _proxy_disabled() -> bool:
    return any(str(os.environ.get(key, "")).strip().lower() in TRUTHY for key in DISABLE_ENV_KEYS)


def proxy_url(force_refresh: bool = False) -> str:
    """返回代理地址；未配置时返回空字符串。"""
    if _CACHE.get("resolved") and not force_refresh:
        return str(_CACHE.get("url") or "")

    url = ""
    if not _proxy_disabled():
        for key in PROXY_ENV_KEYS:
            value = str(os.environ.get(key, "")).strip()
            if value:
                url = value
                break
        if not url:
            url = _proxy_from_config()

    _CACHE["resolved"] = True
    _CACHE["url"] = url
    return url


def proxy_kwargs(extra: Optional[dict] = None) -> dict:
    """给 requests 调用附加 proxies，未配置代理时原样返回。"""
    kwargs = dict(extra or {})
    url = proxy_url()
    if url:
        kwargs["proxies"] = {"http": url, "https": url}
    return kwargs


def describe() -> str:
    """带脱敏的描述，供诊断与日志使用。"""
    url = proxy_url()
    if not url:
        return "direct (no wechat proxy configured)"

    if "@" in url:
        head, _, tail = url.rpartition("@")
        scheme = f"{head.split('://', 1)[0]}://" if "://" in head else ""
        return f"{scheme}***@{tail}"

    return url


def proxy_hint() -> str:
    """代理不可用时给用户的提示。"""
    return (
        f"WeChat proxy is configured ({describe()}) but unreachable. "
        "Start the SSH tunnel first (ssh -N -L 8888:127.0.0.1:8888 <user>@<server>), "
        "or bypass it with WECHAT_PROXY_DISABLE=1."
    )
