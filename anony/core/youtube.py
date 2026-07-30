# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic


import os
import re
import yt_dlp
import random
import asyncio
import aiohttp
from pathlib import Path

from py_yt import Playlist, VideosSearch

from anony import logger
from anony.helpers import Track, utils


class YouTube:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.cookies = []
        self.checked = False
        self.cookie_dir = "anony/cookies"
        self.warned = False
        self.regex = re.compile(
            r"(https?://)?(www\.|m\.|music\.)?"
            r"(youtube\.com/(watch\?v=|shorts/|playlist\?list=)|youtu\.be/)"
            r"([A-Za-z0-9_-]{11}|PL[A-Za-z0-9_-]+)([&?][^\s]*)?"
        )
        self.iregex = re.compile(
            r"https?://(?:www\.|m\.|music\.)?(?:youtube\.com|youtu\.be)"
            r"(?!/(watch\?v=[A-Za-z0-9_-]{11}|shorts/[A-Za-z0-9_-]{11}"
            r"|playlist\?list=PL[A-Za-z0-9_-]+|[A-Za-z0-9_-]{11}))\S*"
        )

    def get_cookies(self):
        # Always scan the directory so cookies saved after startup are found
        cookies = [
            f"{self.cookie_dir}/{f}"
            for f in os.listdir(self.cookie_dir)
            if f.endswith(".txt")
        ]
        if not cookies:
            if not self.warned:
                self.warned = True
                logger.warning("Cookies are missing; downloads might fail.")
            return None
        self.warned = False
        chosen = random.choice(cookies)
        logger.info(f"Using cookie file: {chosen} (size: {os.path.getsize(chosen)} bytes)")
        return chosen

    async def save_cookies(self, urls: list[str]) -> None:
        logger.info("Saving cookies from urls...")
        async with aiohttp.ClientSession() as session:
            for url in urls:
                name = url.split("/")[-1]
                link = "https://batbin.me/raw/" + name
                async with session.get(link) as resp:
                    resp.raise_for_status()
                    with open(f"{self.cookie_dir}/{name}.txt", "wb") as fw:
                        fw.write(await resp.read())
        logger.info(f"Cookies saved in {self.cookie_dir}.")

    def valid(self, url: str) -> bool:
        return bool(re.match(self.regex, url))

    def invalid(self, url: str) -> bool:
        return bool(re.match(self.iregex, url))

    async def search(self, query: str, m_id: int, video: bool = False) -> Track | None:
        try:
            _search = VideosSearch(query, limit=1, with_live=False)
            results = await _search.next()
        except Exception:
            return None
        if results and results["result"]:
            data = results["result"][0]
            return Track(
                id=data.get("id"),
                channel_name=data.get("channel", {}).get("name"),
                duration=data.get("duration"),
                duration_sec=utils.to_seconds(data.get("duration")),
                message_id=m_id,
                title=data.get("title")[:25],
                thumbnail=data.get("thumbnails", [{}])[-1].get("url").split("?")[0],
                url=data.get("link"),
                view_count=data.get("viewCount", {}).get("short"),
                video=video,
            )
        return None

    async def playlist(self, limit: int, user: str, url: str, video: bool) -> list[Track | None]:
        tracks = []
        try:
            plist = await Playlist.get(url)
            for data in plist["videos"][:limit]:
                track = Track(
                    id=data.get("id"),
                    channel_name=data.get("channel", {}).get("name", ""),
                    duration=data.get("duration"),
                    duration_sec=utils.to_seconds(data.get("duration")),
                    title=data.get("title")[:25],
                    thumbnail=data.get("thumbnails")[-1].get("url").split("?")[0],
                    url=data.get("link").split("&list=")[0],
                    user=user,
                    view_count="",
                    video=video,
                )
                tracks.append(track)
        except Exception:
            pass
        return tracks

    async def download(self, video_id: str, video: bool = False) -> str | None:
        url = self.base + video_id
        ext = "mp4" if video else "webm"
        filename = f"downloads/{video_id}.{ext}"

        if Path(filename).exists():
            return filename

        cookie = self.get_cookies()
        base_opts = {
            "outtmpl": "downloads/%(id)s.%(ext)s",
            "quiet": True,
            "noplaylist": True,
            "geo_bypass": True,
            "no_warnings": True,
            "overwrites": False,
            "nocheckcertificate": True,
            "cookiefile": cookie,
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
                "Accept-Language": "en-US,en;q=0.9",
            },
        }

        # Try multiple strategies to bypass YouTube restrictions
        strategies = [
            # Strategy 1: Android client
            {**base_opts, "extractor_args": {"youtube": {"player_client": ["android"]}}},
            # Strategy 2: iOS client
            {**base_opts, "extractor_args": {"youtube": {"player_client": ["ios"]}}},
            # Strategy 3: tv_embedded client
            {**base_opts, "extractor_args": {"youtube": {"player_client": ["tv_embedded"]}}},
            # Strategy 4: Invidious instance as source
            {**base_opts, "extractor_args": {"youtube": {"player_client": ["web"]}}},
        ]

        if video:
            fmt_opts = {
                "format": "(bestvideo[height<=?720][width<=?1280][ext=mp4])+(bestaudio[ext=m4a])/best[ext=mp4]/best",
                "merge_output_format": "mp4",
            }
        else:
            fmt_opts = {
                "format": "bestaudio[ext=webm]/bestaudio[ext=m4a]/bestaudio/best",
            }

        def _try_download(opts):
            full_opts = {**opts, **fmt_opts}
            with yt_dlp.YoutubeDL(full_opts) as ydl:
                try:
                    ydl.download([url])
                    return filename if Path(filename).exists() else None
                except Exception:
                    return None

        for strategy in strategies:
            result = await asyncio.to_thread(_try_download, strategy)
            if result:
                return result

        logger.warning(f"All download strategies failed for {video_id}")
        return None
