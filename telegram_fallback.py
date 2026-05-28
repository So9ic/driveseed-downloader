#!/usr/bin/env python3
"""Telegram fallback downloader using Telethon for tgseed links.

Environment variables required:
- TELEGRAM_API_ID
- TELEGRAM_API_HASH

Optional:
- TELEGRAM_SESSION (default: tgseed_session)
- TELEGRAM_TIMEOUT (seconds, default: 180)
"""

import asyncio
import os
import re
import time
from html import unescape
from urllib.parse import parse_qs, urlparse

from env_loader import load_env_file, resolve_session_name

load_env_file()


class TelegramDownloadError(RuntimeError):
    pass


def _parse_tgseed_link(tgseed_url: str) -> tuple[str, str]:
    normalized_url = unescape(tgseed_url).strip()
    parsed = urlparse(normalized_url)
    if "tgseed.link" not in parsed.netloc:
        raise TelegramDownloadError("Not a tgseed link")

    qs = parse_qs(parsed.query)
    start_param = qs.get("start", [None])[0]
    bot_name = qs.get("bot", [None])[0]

    if not start_param or not bot_name:
        raise TelegramDownloadError("Invalid tgseed link: missing start/bot parameters")

    return start_param, bot_name.lstrip("@").strip()


def _telethon_config() -> tuple[int, str, str, int]:
    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION", "tgseed_session").strip() or "tgseed_session"
    session_name = resolve_session_name(session_name)
    timeout_raw = os.getenv("TELEGRAM_TIMEOUT", "180").strip()

    if not api_id_raw or not api_hash:
        raise TelegramDownloadError(
            "Telethon not configured. Set TELEGRAM_API_ID and TELEGRAM_API_HASH."
        )

    try:
        api_id = int(api_id_raw)
    except ValueError as exc:
        raise TelegramDownloadError("TELEGRAM_API_ID must be an integer") from exc

    try:
        timeout = max(30, int(timeout_raw))
    except ValueError:
        timeout = 180

    return api_id, api_hash, session_name, timeout


def _safe_filename(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*]', "_", name)


def _pick_filename(message, fallback_name: str) -> str:
    file_name = None
    file_obj = getattr(message, "file", None)
    if file_obj is not None:
        file_name = getattr(file_obj, "name", None)

    if not file_name and getattr(message, "document", None):
        for attr in message.document.attributes:
            candidate = getattr(attr, "file_name", None)
            if candidate:
                file_name = candidate
                break

    if not file_name:
        stamp = int(time.time())
        file_name = fallback_name or f"telegram_file_{stamp}.bin"

    return _safe_filename(file_name)


async def _download_from_tgseed_async(
    tgseed_url: str,
    output_dir: str,
    fallback_name: str | None = None,
) -> str:
    try:
        from telethon import TelegramClient
    except Exception as exc:  # pragma: no cover - depends on local env
        raise TelegramDownloadError(
            "Telethon is not installed. Install with: pip install telethon"
        ) from exc

    start_param, bot_name = _parse_tgseed_link(tgseed_url)
    api_id, api_hash, session_name, timeout = _telethon_config()

    os.makedirs(output_dir, exist_ok=True)

    client = TelegramClient(session_name, api_id, api_hash)
    await client.connect()

    try:
        authorized = await client.is_user_authorized()
        if not authorized:
            raise TelegramDownloadError(
                "Telegram session not authorized. Run a one-time Telethon login first."
            )

        entity = await client.get_entity(bot_name)
        latest_before = await client.get_messages(entity, limit=1)
        min_id = latest_before[0].id if latest_before else 0

        await client.send_message(entity, f"/start {start_param}")

        deadline = time.time() + timeout
        while time.time() < deadline:
            messages = await client.get_messages(entity, limit=20, min_id=min_id)
            for msg in messages:
                if getattr(msg, "document", None):
                    filename = _pick_filename(msg, fallback_name or "telegram_file.bin")
                    final_path = os.path.join(output_dir, filename)
                    if os.path.exists(final_path):
                        return final_path

                    part_path = final_path + ".part"
                    await msg.download_media(file=part_path)
                    os.replace(part_path, final_path)
                    return final_path
            await asyncio.sleep(2)

        raise TelegramDownloadError("Timed out waiting for Telegram bot file response")
    finally:
        await client.disconnect()


def download_from_tgseed(
    tgseed_url: str,
    output_dir: str,
    fallback_name: str | None = None,
) -> str:
    """Blocking wrapper for Telegram fallback download."""
    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        running_loop = None

    if running_loop and running_loop.is_running():
        loop = asyncio.new_event_loop()
        try:
            return loop.run_until_complete(
                _download_from_tgseed_async(tgseed_url, output_dir, fallback_name)
            )
        finally:
            loop.close()

    return asyncio.run(_download_from_tgseed_async(tgseed_url, output_dir, fallback_name))
