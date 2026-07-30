# Copyright (c) 2025 AnonymousX1025
# Licensed under the MIT License.
# This file is part of AnonXMusic
#
# Modified: replaced MongoDB with in-memory storage so the bot runs
# without an external database. Data is lost on restart, but all
# functionality works normally during the session.

from random import randint
from time import time

from anony import config, logger, userbot


class MongoDB:
    def __init__(self):
        self.admin_list = {}
        self.active_calls = {}
        self.admin_play = []
        self.blacklisted = []
        self.cmd_delete = []
        self.loop = {}
        self.notified = []
        self.logger = False

        self.assistant = {}
        self._assistant_db = {}

        self.auth = {}

        self.chats = []
        self._chats_db = {}

        self.lang = {}

        self.users = []

        self._sudoers = []
        self._bl_users = []

    # ── CONNECTION ────────────────────────────────────────────────────────────

    async def connect(self) -> None:
        start = time()
        logger.info(f"In-memory database ready. ({time() - start:.4f}s)")

    async def close(self) -> None:
        logger.info("In-memory database closed.")

    # ── CALL CACHE ────────────────────────────────────────────────────────────

    async def get_call(self, chat_id: int) -> bool:
        return chat_id in self.active_calls

    async def add_call(self, chat_id: int) -> None:
        self.active_calls[chat_id] = 1

    async def remove_call(self, chat_id: int) -> None:
        self.active_calls.pop(chat_id, None)

    async def playing(self, chat_id: int, paused: bool = None) -> bool | None:
        if paused is not None:
            self.active_calls[chat_id] = int(not paused)
        return bool(self.active_calls.get(chat_id, 0))

    # ── ADMINS ────────────────────────────────────────────────────────────────

    async def get_admins(self, chat_id: int, reload: bool = False) -> list[int]:
        from anony.helpers._admins import reload_admins
        if chat_id not in self.admin_list or reload:
            self.admin_list[chat_id] = await reload_admins(chat_id)
        return self.admin_list[chat_id]

    # ── LOOP ──────────────────────────────────────────────────────────────────

    async def get_loop(self, chat_id: int) -> int:
        return self.loop.get(chat_id, 0)

    async def set_loop(self, chat_id: int, count: int) -> None:
        self.loop[chat_id] = count

    # ── AUTH ──────────────────────────────────────────────────────────────────

    async def _get_auth(self, chat_id: int) -> set[int]:
        if chat_id not in self.auth:
            self.auth[chat_id] = set()
        return self.auth[chat_id]

    async def is_auth(self, chat_id: int, user_id: int) -> bool:
        return user_id in await self._get_auth(chat_id)

    async def add_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        users.add(user_id)

    async def rm_auth(self, chat_id: int, user_id: int) -> None:
        users = await self._get_auth(chat_id)
        users.discard(user_id)

    # ── ASSISTANT ─────────────────────────────────────────────────────────────

    async def set_assistant(self, chat_id: int) -> int:
        from anony import anon
        num = randint(1, len(anon.clients))
        self._assistant_db[chat_id] = num
        self.assistant[chat_id] = num
        return num

    async def get_assistant(self, chat_id: int):
        from anony import anon
        if chat_id not in self.assistant:
            num = self._assistant_db.get(chat_id)
            if not num or num > len(anon.clients):
                num = await self.set_assistant(chat_id)
            self.assistant[chat_id] = num
        return anon.clients[self.assistant[chat_id] - 1]

    async def get_client(self, chat_id: int):
        if chat_id not in self.assistant:
            await self.get_assistant(chat_id)
        num = self.assistant[chat_id]
        return {1: userbot.one, 2: userbot.two, 3: userbot.three}.get(num)

    # ── BLACKLIST ─────────────────────────────────────────────────────────────

    async def add_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id not in self.blacklisted:
                self.blacklisted.append(chat_id)
        else:
            if chat_id not in self._bl_users:
                self._bl_users.append(chat_id)

    async def del_blacklist(self, chat_id: int) -> None:
        if str(chat_id).startswith("-"):
            if chat_id in self.blacklisted:
                self.blacklisted.remove(chat_id)
        else:
            if chat_id in self._bl_users:
                self._bl_users.remove(chat_id)

    async def get_blacklisted(self, chat: bool = False) -> list[int]:
        return self.blacklisted if chat else list(self._bl_users)

    # ── CHATS ─────────────────────────────────────────────────────────────────

    async def is_chat(self, chat_id: int) -> bool:
        return chat_id in self.chats

    async def add_chat(self, chat_id: int) -> None:
        if chat_id not in self.chats:
            self.chats.append(chat_id)

    async def rm_chat(self, chat_id: int) -> None:
        if chat_id in self.chats:
            self.chats.remove(chat_id)

    async def get_chats(self) -> list:
        return self.chats

    # ── COMMAND DELETE ────────────────────────────────────────────────────────

    async def get_cmd_delete(self, chat_id: int) -> bool:
        return chat_id in self.cmd_delete

    async def set_cmd_delete(self, chat_id: int, delete: bool = False) -> None:
        if delete:
            if chat_id not in self.cmd_delete:
                self.cmd_delete.append(chat_id)
        else:
            if chat_id in self.cmd_delete:
                self.cmd_delete.remove(chat_id)

    # ── LANGUAGE ──────────────────────────────────────────────────────────────

    async def set_lang(self, chat_id: int, lang_code: str):
        self.lang[chat_id] = lang_code

    async def get_lang(self, chat_id: int) -> str:
        return self.lang.get(chat_id, config.LANG_CODE)

    # ── LOGGER ────────────────────────────────────────────────────────────────

    async def is_logger(self) -> bool:
        return self.logger

    async def get_logger(self) -> bool:
        return self.logger

    async def set_logger(self, status: bool) -> None:
        self.logger = status

    # ── PLAY MODE ─────────────────────────────────────────────────────────────

    async def get_play_mode(self, chat_id: int) -> bool:
        return chat_id in self.admin_play

    async def set_play_mode(self, chat_id: int, remove: bool = False) -> None:
        if remove:
            if chat_id in self.admin_play:
                self.admin_play.remove(chat_id)
        else:
            if chat_id not in self.admin_play:
                self.admin_play.append(chat_id)

    # ── SUDO ──────────────────────────────────────────────────────────────────

    async def add_sudo(self, user_id: int) -> None:
        if user_id not in self._sudoers:
            self._sudoers.append(user_id)

    async def del_sudo(self, user_id: int) -> None:
        if user_id in self._sudoers:
            self._sudoers.remove(user_id)

    async def get_sudoers(self) -> list[int]:
        return list(self._sudoers)

    # ── USERS ─────────────────────────────────────────────────────────────────

    async def is_user(self, user_id: int) -> bool:
        return user_id in self.users

    async def add_user(self, user_id: int) -> None:
        if user_id not in self.users:
            self.users.append(user_id)

    async def rm_user(self, user_id: int) -> None:
        if user_id in self.users:
            self.users.remove(user_id)

    async def get_users(self) -> list:
        return list(self.users)

    # ── CACHE LOAD (no-op for in-memory) ─────────────────────────────────────

    async def load_cache(self) -> None:
        logger.info("Database cache loaded.")

    async def migrate_coll(self) -> None:
        pass
