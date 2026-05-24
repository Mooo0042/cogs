import logging
import os
import re
import aiohttp
from datetime import datetime

import discord
from redbot.core import commands as red_commands
from redbot.core.bot import Red

log = logging.getLogger("red.logwatcher")

FORUM_CHANNEL_ID = 1376287715603124324
MCLO_GS_PATTERN = re.compile(r"https?://mclo\.gs/\S+")

NEXTCLOUD_URL = "https://nextcloud.fin-haddock.ts.net"
NEXTCLOUD_SHARE_PATH = "/log"


class LogWatcher(red_commands.Cog):
    """Watches a forum channel for new posts and checks for mclo.gs links."""

    def __init__(self, bot: Red):
        self.bot = bot

    def _get_nc_credentials(self) -> tuple[str, str, str]:
        """
        Returns (login, token, dav_username).
        - login:        email/username used for HTTP Basic Auth (NEXTCLOUD_LOGIN)
        - token:        app password (NEXTCLOUD_TOKEN)
        - dav_username: internal NC username used in the WebDAV path (NEXTCLOUD_USER)
        """
        login = os.environ.get("NEXTCLOUD_LOGIN", "")
        token = os.environ.get("NEXTCLOUD_TOKEN", "")
        dav_user = os.environ.get("NEXTCLOUD_USER", "")
        if not login or not token or not dav_user:
            raise RuntimeError(
                "NEXTCLOUD_LOGIN, NEXTCLOUD_USER, and NEXTCLOUD_TOKEN "
                "environment variables must all be set."
            )
        return login, token, dav_user

    async def _create_upload_share(self, folder_name: str) -> str | None:
        """
        Creates a folder inside NEXTCLOUD_SHARE_PATH and returns a
        public upload-only share link (share type 3, permissions 4).
        """
        login, token, dav_user = self._get_nc_credentials()
        auth = aiohttp.BasicAuth(login, token)
        headers = {"OCS-APIRequest": "true", "Accept": "application/json"}
        folder_path = f"{NEXTCLOUD_SHARE_PATH}/{folder_name}"

        async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
            # 1. Create the folder via WebDAV (uses internal username in path)
            webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{dav_user}{folder_path}"
            async with session.request("MKCOL", webdav_url) as resp:
                # 201 = created, 405 = already exists — both are fine
                if resp.status not in (201, 405):
                    log.error("WebDAV MKCOL failed: HTTP %d", resp.status)
                    return None

            # 2. Create a public upload-only share link (type 3, permissions 4)
            share_api_url = f"{NEXTCLOUD_URL}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            payload = {
                "path": folder_path,
                "shareType": 3,   # public link
                "permissions": 4, # create/upload only
            }
            async with session.post(share_api_url, data=payload) as resp:
                body = await resp.text()
                if resp.status in (200, 201):
                    try:
                        import json
                        data = json.loads(body)
                        return data["ocs"]["data"]["url"]
                    except (KeyError, TypeError, ValueError) as e:
                        log.error("Failed to parse share response: %s | body: %s", e, body)
                        return None
                log.error("Share API failed: HTTP %d | body: %s", resp.status, body)
                return None

    @red_commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if thread.parent_id != FORUM_CHANNEL_ID:
            return

        # Fetch the starter message
        try:
            starter_message = await thread.fetch_message(thread.id)
        except (discord.NotFound, discord.HTTPException):
            try:
                starter_message = await thread.history(limit=1, oldest_first=True).next()
            except (discord.NoMoreItems, discord.HTTPException):
                log.error("Could not fetch starter message for thread %d", thread.id)
                return

        content = starter_message.content or ""
        for embed in starter_message.embeds:
            if embed.url:
                content += f" {embed.url}"
            if embed.description:
                content += f" {embed.description}"

        if MCLO_GS_PATTERN.search(content):
            return

        # Resolve the post author's display name for the folder name
        post_creator = thread.owner
        if post_creator is None:
            try:
                post_creator = await self.bot.fetch_user(thread.owner_id)
            except discord.HTTPException:
                pass

        username = (
            post_creator.display_name
            if post_creator and hasattr(post_creator, "display_name")
            else str(thread.owner_id)
        )
        safe_username = re.sub(r"[^\w\-]", "_", username)
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{safe_username}_{date_str}"

        share_link = None
        try:
            share_link = await self._create_upload_share(folder_name)
        except RuntimeError as e:
            log.error(str(e))

        if share_link:
            upload_line = (
                f"If mclo.gs says your file is too big or has too many characters, "
                f"you can upload it directly here instead: {share_link}"
            )
        else:
            upload_line = (
                "If mclo.gs says your file is too big or has too many characters, "
                "please attach the log file directly to a reply in this thread."
            )

        message = (
            "👋 Hello! I'm **Saucy**, the Mod-Sauce Discord bot.\n\n"
            "I wasn't able to find a link to your logs ([mclo.gs](https://mclo.gs)) "
            "in your post. Please upload your logs there and paste the link here.\n\n"
            f"{upload_line}\n\n"
            "If you don't know how to find or upload your logs, type `/logs` and "
            "I'll walk you through it! 🪵"
        )

        await thread.send(message)
