import os
import re
import aiohttp
from datetime import datetime

import discord
from redbot.core import commands as red_commands
from redbot.core.bot import Red

FORUM_CHANNEL_ID = 1376287715603124324
MCLO_GS_PATTERN = re.compile(r"https?://mclo\.gs/\S+")

NEXTCLOUD_URL = "https://nextcloud.fin-haddock.ts.net"
NEXTCLOUD_SHARE_PATH = "/log"


class LogWatcher(red_commands.Cog):
    """Watches a forum channel for new posts and checks for mclo.gs links."""

    def __init__(self, bot: Red):
        self.bot = bot
        self._nc_user: str | None = None
        self._nc_token: str | None = None

    def _get_nc_credentials(self) -> tuple[str, str]:
        """Lazily load Nextcloud credentials from environment variables."""
        if self._nc_user is None:
            self._nc_user = os.environ.get("NEXTCLOUD_USER", "")
        if self._nc_token is None:
            self._nc_token = os.environ.get("NEXTCLOUD_TOKEN", "")
        if not self._nc_user or not self._nc_token:
            raise RuntimeError(
                "NEXTCLOUD_USER and NEXTCLOUD_TOKEN environment variables must be set."
            )
        return self._nc_user, self._nc_token

    async def _create_file_request_share(self, folder_name: str) -> str | None:
        """
        Creates a folder inside NEXTCLOUD_SHARE_PATH and a File Request share for it.
        Returns the share URL or None on failure.
        """
        nc_user, nc_token = self._get_nc_credentials()
        auth = aiohttp.BasicAuth(nc_user, nc_token)
        headers = {"OCS-APIRequest": "true", "Accept": "application/json"}

        folder_path = f"{NEXTCLOUD_SHARE_PATH}/{folder_name}"

        async with aiohttp.ClientSession(auth=auth, headers=headers) as session:
            # 1. Create the folder via WebDAV
            webdav_url = (
                f"{NEXTCLOUD_URL}/remote.php/dav/files/{nc_user}{folder_path}"
            )
            async with session.request("MKCOL", webdav_url) as resp:
                # 405 means it already exists, which is fine
                if resp.status not in (201, 405):
                    return None

            # 2. Create a File Request share (share type 4) on that folder
            share_url = f"{NEXTCLOUD_URL}/ocs/v2.php/apps/files_sharing/api/v1/shares"
            payload = {
                "path": folder_path,
                "shareType": 4,  # File Request / Upload-only link
                "permissions": 4,  # create/upload only
            }
            async with session.post(share_url, data=payload) as resp:
                if resp.status in (200, 201):
                    data = await resp.json()
                    try:
                        return data["ocs"]["data"]["url"]
                    except (KeyError, TypeError):
                        return None
                return None

    @red_commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        """Fires when a new thread (forum post) is created."""
        # Only watch the configured forum channel
        if thread.parent_id != FORUM_CHANNEL_ID:
            return

        # Fetch the starter message (first post body)
        try:
            starter_message = await thread.fetch_message(thread.id)
        except (discord.NotFound, discord.HTTPException):
            # If we can't fetch it, try the first message in history
            try:
                starter_message = await thread.history(limit=1, oldest_first=True).next()
            except (discord.NoMoreItems, discord.HTTPException):
                return

        content = starter_message.content or ""

        # Also check embeds and attachments for mclo.gs links
        for embed in starter_message.embeds:
            if embed.url:
                content += f" {embed.url}"
            if embed.description:
                content += f" {embed.description}"

        if MCLO_GS_PATTERN.search(content):
            # Link found, nothing to do
            return

        # No mclo.gs link found — build the Nextcloud File Request folder name
        post_creator = thread.owner or await self.bot.fetch_user(thread.owner_id)
        username = post_creator.display_name if hasattr(post_creator, "display_name") else str(post_creator)
        # Sanitise the folder name so it's safe for Nextcloud
        safe_username = re.sub(r"[^\w\-]", "_", username)
        date_str = datetime.now().strftime("%Y-%m-%d")
        folder_name = f"{safe_username}_{date_str}"

        share_link = None
        try:
            share_link = await self._create_file_request_share(folder_name)
        except RuntimeError as e:
            # Credentials not configured — log and continue without the link
            import logging
            logging.getLogger("red.logwatcher").error(str(e))

        # Build the reply message
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
