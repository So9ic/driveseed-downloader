#!/usr/bin/env python3
"""One-time Telethon login setup.

Usage:
  export TELEGRAM_API_ID=123456
  export TELEGRAM_API_HASH=your_hash
  export TELEGRAM_SESSION=tgseed_session
  python3 telegram_login.py
"""

import os
import asyncio
from pathlib import Path

from env_loader import load_env_file, resolve_session_name

load_env_file()


async def main():
    try:
        from telethon import TelegramClient
    except Exception:
        print("Telethon not installed. Install with: pip install telethon")
        raise SystemExit(1)

    api_id_raw = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash = os.getenv("TELEGRAM_API_HASH", "").strip()
    session_name = os.getenv("TELEGRAM_SESSION", "tgseed_session").strip() or "tgseed_session"
    session_name = resolve_session_name(session_name)

    if not api_id_raw or not api_hash:
        print("Missing TELEGRAM_API_ID / TELEGRAM_API_HASH environment variables")
        raise SystemExit(1)

    try:
        api_id = int(api_id_raw)
    except ValueError:
        print("TELEGRAM_API_ID must be an integer")
        raise SystemExit(1)

    async with TelegramClient(session_name, api_id, api_hash) as client:
        me = await client.get_me()
        display_name = me.username or me.first_name or str(me.id)
        session_file = Path(session_name)
        if session_file.suffix != ".session":
            session_file = Path(f"{session_file}.session")
        print(f"Session authorized as: {display_name}")
        print(f"Session file: {session_file}")


if __name__ == "__main__":
    asyncio.run(main())
