import discord
from discord import app_commands
from redbot.core import commands as red_commands
from redbot.core.bot import Red


# ---------------------------------------------------------------------------
# Instructions content
# ---------------------------------------------------------------------------

INSTRUCTIONS: dict[str, str] = {
    "modrinth": (
        "## 📋 Finding your logs — Modrinth App\n\n"
        "1. Open the **Modrinth App**.\n"
        "2. Click on your modpack / instance.\n"
        "3. Click the **three-dot menu (⋮)** next to the instance.\n"
        "4. Select **Open Folder** — this opens the instance directory.\n"
        "5. Navigate into the **`logs`** folder.\n"
        "6. Open **`latest.log`** with any text editor (e.g. Notepad).\n"
        "7. Copy **all** of the content.\n"
        "8. Go to **[mclo.gs](https://mclo.gs)**, paste it in, and click **Save**.\n"
        "9. Copy the link and paste it in your support post. ✅"
    ),
    "curseforge": (
        "## 📋 Finding your logs — CurseForge App\n\n"
        "1. Open the **CurseForge App**.\n"
        "2. Click on **Minecraft** → find your modpack.\n"
        "3. Click the **three-dot menu (⋮)** next to the instance.\n"
        "4. Select **Open Folder** — this opens the instance directory.\n"
        "5. Navigate into the **`logs`** folder.\n"
        "6. Open **`latest.log`** with any text editor (e.g. Notepad).\n"
        "7. Copy **all** of the content.\n"
        "8. Go to **[mclo.gs](https://mclo.gs)**, paste it in, and click **Save**.\n"
        "9. Copy the link and paste it in your support post. ✅"
    ),
    "prism": (
        "## 📋 Finding your logs — Prism Launcher\n\n"
        "1. Open **Prism Launcher**.\n"
        "2. Right-click your instance → **Folder** → **Open .minecraft**.\n"
        "   *Alternatively: select the instance, then click **Folder** in the right panel.*\n"
        "3. Navigate into the **`logs`** folder.\n"
        "4. Open **`latest.log`** with any text editor.\n"
        "5. Copy **all** of the content.\n"
        "6. Go to **[mclo.gs](https://mclo.gs)**, paste it in, and click **Save**.\n"
        "7. Copy the link and paste it in your support post. ✅\n\n"
        "> 💡 **Tip:** Prism also has a built-in log viewer — right-click the instance → "
        "**Minecraft Log** — but mclo.gs makes sharing much easier."
    ),
    "other_windows": (
        "## 📋 Finding your logs — Other launcher (Windows)\n\n"
        "1. Press **Win + R**, type `%appdata%\\.minecraft` and hit **Enter**.\n"
        "   *(If your launcher uses a custom directory, open that instead.)*\n"
        "2. Open the **`logs`** folder.\n"
        "3. Open **`latest.log`** with Notepad or any text editor.\n"
        "4. Press **Ctrl + A** to select all, then **Ctrl + C** to copy.\n"
        "5. Go to **[mclo.gs](https://mclo.gs)**, paste it in (**Ctrl + V**), and click **Save**.\n"
        "6. Copy the link and paste it in your support post. ✅"
    ),
    "other_linux": (
        "## 📋 Finding your logs — Other launcher (Linux)\n\n"
        "1. Open a terminal and run:\n"
        "   ```\n"
        "   xdg-open ~/.minecraft/logs\n"
        "   ```\n"
        "   *(Adjust the path if your launcher uses a custom directory.)*\n"
        "2. Open **`latest.log`** with any text editor (e.g. `gedit`, `kate`, `nano`).\n"
        "3. Copy **all** of the content.\n"
        "4. Go to **[mclo.gs](https://mclo.gs)**, paste it in, and click **Save**.\n"
        "5. Copy the link and paste it in your support post. ✅"
    ),
    "other_macos": (
        "## 📋 Finding your logs — Other launcher (macOS)\n\n"
        "1. Open **Finder**, press **Cmd + Shift + G** and type:\n"
        "   `~/Library/Application Support/minecraft/logs`\n"
        "   *(Adjust the path if your launcher uses a custom directory.)*\n"
        "2. Open **`latest.log`** with TextEdit or any text editor.\n"
        "3. Press **Cmd + A** to select all, then **Cmd + C** to copy.\n"
        "4. Go to **[mclo.gs](https://mclo.gs)**, paste it in, and click **Save**.\n"
        "5. Copy the link and paste it in your support post. ✅"
    ),
}


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------

class OsSelectView(discord.ui.View):
    """Second-level view: OS selection for 'Other' launchers."""

    def __init__(self):
        super().__init__(timeout=120)

    async def _send_instructions(self, interaction: discord.Interaction, key: str, label: str):
        embed = discord.Embed(
            description=INSTRUCTIONS[key],
            color=discord.Color.green(),
        )
        embed.set_footer(text="Need more help? Ask in this thread!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🪟 Windows", style=discord.ButtonStyle.secondary)
    async def windows(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "other_windows", "Windows")

    @discord.ui.button(label="🐧 Linux", style=discord.ButtonStyle.secondary)
    async def linux(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "other_linux", "Linux")

    @discord.ui.button(label="🍎 macOS", style=discord.ButtonStyle.secondary)
    async def macos(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "other_macos", "macOS")


class LauncherSelectView(discord.ui.View):
    """Top-level view: launcher selection."""

    def __init__(self):
        super().__init__(timeout=120)

    async def _send_instructions(self, interaction: discord.Interaction, key: str):
        embed = discord.Embed(
            description=INSTRUCTIONS[key],
            color=discord.Color.green(),
        )
        embed.set_footer(text="Need more help? Ask in this thread!")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="🌿 Modrinth App", style=discord.ButtonStyle.primary)
    async def modrinth(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "modrinth")

    @discord.ui.button(label="⚡ CurseForge", style=discord.ButtonStyle.primary)
    async def curseforge(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "curseforge")

    @discord.ui.button(label="🔷 Prism Launcher", style=discord.ButtonStyle.primary)
    async def prism(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self._send_instructions(interaction, "prism")

    @discord.ui.button(label="❓ Other", style=discord.ButtonStyle.secondary)
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🖥️ What operating system are you on?",
            description="Select your OS below so I can give you the right instructions.",
            color=discord.Color.blurple(),
        )
        await interaction.response.send_message(
            embed=embed,
            view=OsSelectView(),
            ephemeral=True,
        )


# ---------------------------------------------------------------------------
# Cog
# ---------------------------------------------------------------------------

class LogsHelp(red_commands.Cog):
    """Provides a /logs slash command with interactive launcher/OS guidance."""

    def __init__(self, bot: Red):
        self.bot = bot

    @app_commands.command(
        name="logs",
        description="Get step-by-step instructions on how to find and upload your Minecraft logs.",
    )
    async def logs(self, interaction: discord.Interaction):
        """Slash command: /logs"""
        embed = discord.Embed(
            title="📜 How to upload your Minecraft logs",
            description=(
                "To help you faster, I need your **log file** uploaded to "
                "[mclo.gs](https://mclo.gs).\n\n"
                "Select your **launcher** below and I'll walk you through it!"
            ),
            color=discord.Color.blurple(),
        )
        embed.set_footer(text="Saucy • Mod-Sauce Discord Bot")
        await interaction.response.send_message(
            embed=embed,
            view=LauncherSelectView(),
            ephemeral=True,
        )
