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

    def _get_nc_credentials(self) -> tuple[str, str]:
        user = os.environ.get("NEXTCLOUD_USER", "")
        token = os.environ.get("NEXTCLOUD_TOKEN", "")
        if not user or not token:
            raise RuntimeError("NEXTCLOUD_USER and NEXTCLOUD_TOKEN environment variables must be set.")
        return user, token

    async def _create_file_request_share(self, folder_name: str) -> str | None:
        nc_user, nc_token = self._get_nc_credentials()
        auth = aiohttp.BasicAuth(nc_user, nc_token)
        headers = {"OCS-APIRequest": "true", "Accept": "application/json"}
        folder_path = f"{NEXTCLOUD_SHARE_PATH}/{folder_name}"

        async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
            # 1. Create the folder via WebDAV
            webdav_url = f"{NEXTCLOUD_URL}/remote.php/dav/files/{nc_user}{folder_path}"
            log.debug("WebDAV MKCOL: %s", webdav_url)
            async with session.request("MKCOL", webdav_url) as resp:
                log.debug("WebDAV MKCOL status: %d body: %s", resp.status, await resp.text())
                if resp.status not in (201, 405):
                    log.error("WebDAV folder creation failed with status %d", resp.status)
                    return None

            # 2. Create File Request share (share type 4)
            share_api_url = f"{NEXTCLOUD_URL}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            payload = {
                "path": folder_path,
                "shareType": 4,
                "permissions": 4,
            }
            log.debug("Creating share for path: %s", folder_path)
            async with session.post(share_api_url, data=payload) as resp:
                body = await resp.text()
                log.debug("Share API status: %d body: %s", resp.status, body)
                if resp.status in (200, 201):
                    try:
                        import json
                        data = json.loads(body)
                        url = data["ocs"]["data"]["url"]
                        log.debug("Share URL: %s", url)
                        return url
                    except (KeyError, TypeError, ValueError) as e:
                        log.error("Failed to parse share response: %s | body: %s", e, body)
                        return None
                log.error("Share creation failed with status %d body: %s", resp.status, body)
                return None

    @red_commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if thread.parent_id != FORUM_CHANNEL_ID:
            return

        log.debug("New thread detected: %s (id=%d)", thread.name, thread.id)

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
            log.debug("mclo.gs link found, skipping.")
            return

        log.debug("No mclo.gs link found, building Nextcloud share...")

        post_creator = thread.owner
        if post_creator is None:
            try:
                post_creator = await self.bot.fetch_user(thread.owner_id)
            except discord.HTTPException:
                post_creator = None

        username = (
            post_creator.display_name
            if post_creator and hasattr(post_creator, "display_name")
            else str(thread.owner_id)
        )
        safe_username = re.sub(r"[^\w\-]", "_", username)
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{safe_username}_{date_str}"
        log.debug("Folder name: %s", folder_name)

        share_link = None
        try:
            share_link = await self._create_file_request_share(folder_name)
        except RuntimeError as e:
            log.error(str(e))

        log.debug("Share link result: %s", share_link)

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
