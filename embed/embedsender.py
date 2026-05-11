import discord
from discord.ext import commands
from redbot.core import Config, commands as red_commands
from redbot.core.bot import Red
from redbot.core.commands import Context

class EmbedSender(red_commands.Cog):
    """A cog for sending custom preconfigured embed messages."""

    def __init__(self, bot: Red):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=1234567890, force_registration=True)

        self.config.register_guild(
            embeds={}
        )

    @red_commands.group()
    async def embed(self, ctx: Context):
        """Commands for managing and sending embeds."""
        pass

    @embed.command(name="create")
    async def embed_create(self, ctx: Context, name: str,
                           title: str = None,
                           description: str = None,
                           color: str = None,
                           thumbnail_url: str = None,
                           image_url: str = None):
        """Create a new preconfigured embed.

        Args:
            name: The name to save this embed as
            title: The embed title
            description: The embed description
            color: Embed color (hex code or name like 'red', 'blue')
            thumbnail_url: URL for thumbnail image
            image_url: URL for main image
        """
        embed_data = {
            "title": title,
            "description": description,
            "color": color,
            "thumbnail_url": thumbnail_url,
            "image_url": image_url
        }

        async with self.config.guild(ctx.guild).embeds() as embeds:
            embeds[name] = embed_data

        await ctx.send(f"✅ Embed '{name}' has been created!")

    @embed.command(name="send")
    async def embed_send(self, ctx: Context, name: str, channel: discord.TextChannel = None, *, message_content: str = ""):
        """Send a preconfigured embed to a specific channel or thread.

        Args:
            name: The name of the preconfigured embed
            channel: The channel or thread to send to (defaults to current)
            message_content: Optional text to include with the embed
        """
        embeds = await self.config.guild(ctx.guild).embeds()

        if name not in embeds:
            await ctx.send(f"❌ Embed '{name}' not found. Use `{ctx.prefix}embed list` to see available embeds.")
            return

        embed_data = embeds[name]
        embed = self._create_embed_from_data(embed_data)

        # Use specified channel or current context
        target_channel = channel or ctx.channel

        # Send to the target channel (could be channel or thread)
        if message_content:
            await target_channel.send(content=message_content, embed=embed)
        else:
            await target_channel.send(embed=embed)

        await ctx.send(f"✅ Embed '{name}' sent to {target_channel.mention}!")

    @embed.command(name="list")
    async def embed_list(self, ctx: Context):
        """List all available preconfigured embeds."""
        embeds = await self.config.guild(ctx.guild).embeds()

        if not embeds:
            await ctx.send("❌ No preconfigured embeds found. Use `{ctx.prefix}embed create` to create one.")
            return

        embed_list = "\n".join([f"• **{name}**" for name in embeds.keys()])

        description = f"**Available Embeds:**\n{embed_list}"
        embed = discord.Embed(
            title="📋 Preconfigured Embeds",
            description=description,
            color=discord.Color.blue()
        )

        await ctx.send(embed=embed)

    @embed.command(name="delete")
    async def embed_delete(self, ctx: Context, name: str):
        """Delete a preconfigured embed.

        Args:
            name: The name of the embed to delete
        """
        async with self.config.guild(ctx.guild).embeds() as embeds:
            if name not in embeds:
                await ctx.send(f"❌ Embed '{name}' not found.")
                return

            del embeds[name]

        await ctx.send(f"✅ Embed '{name}' has been deleted!")

    @embed.command(name="info")
    async def embed_info(self, ctx: Context, name: str):
        """Show information about a preconfigured embed.

        Args:
            name: The name of the embed to show info for
        """
        embeds = await self.config.guild(ctx.guild).embeds()

        if name not in embeds:
            await ctx.send(f"❌ Embed '{name}' not found.")
            return

        embed_data = embeds[name]

        info_lines = [
            f"**Title:** {embed_data.get('title') or 'None'}",
            f"**Description:** {embed_data.get('description') or 'None'}",
            f"**Color:** {embed_data.get('color') or 'Default'}",
            f"**Thumbnail URL:** {embed_data.get('thumbnail_url') or 'None'}",
            f"**Image URL:** {embed_data.get('image_url') or 'None'}"
        ]

        embed = discord.Embed(
            title=f"ℹ️ Embed Info: {name}",
            description="\n".join(info_lines),
            color=discord.Color.green()
        )

        await ctx.send(embed=embed)

    @embed.command(name="custom")
    async def embed_custom(self, ctx: Context,
                          title: str = None,
                          description: str = None,
                          color: str = None,
                          channel: discord.TextChannel = None):
        """Send a custom embed without saving it.

        Args:
            title: The embed title
            description: The embed description
            color: Embed color (hex code or name like 'red', 'blue')
            channel: The channel or thread to send to (defaults to current)
        """
        embed_data = {
            "title": title,
            "description": description,
            "color": color
        }

        embed = self._create_embed_from_data(embed_data)

        # Use specified channel or current context
        target_channel = channel or ctx.channel
        await target_channel.send(embed=embed)

        await ctx.send(f"✅ Custom embed sent to {target_channel.mention}!")

    def _create_embed_from_data(self, embed_data: dict) -> discord.Embed:
        """Create a Discord embed from the stored data."""
        color = self._parse_color(embed_data.get("color"))

        embed = discord.Embed(
            title=embed_data.get("title"),
            description=embed_data.get("description"),
            color=color
        )

        if embed_data.get("thumbnail_url"):
            embed.set_thumbnail(url=embed_data["thumbnail_url"])

        if embed_data.get("image_url"):
            embed.set_image(url=embed_data["image_url"])

        return embed

    def _parse_color(self, color_str: str) -> discord.Color:
        """Parse color string to Discord Color."""
        if not color_str:
            return discord.Color.default()

        # Try to parse as hex
        if color_str.startswith("#"):
            try:
                return discord.Color(int(color_str[1:], 16))
            except ValueError:
                pass

        # Try to parse as integer
        try:
            return discord.Color(int(color_str))
        except ValueError:
            pass

        # Try to get named color
        color_map = {
            "red": discord.Color.red(),
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "yellow": discord.Color.yellow(),
            "orange": discord.Color.orange(),
            "purple": discord.Color.purple(),
            "pink": discord.Color.pink(),
            "teal": discord.Color.teal(),
            "magenta": discord.Color.magenta(),
            "gold": discord.Color.gold(),
            "dark_blue": discord.Color.dark_blue(),
            "dark_green": discord.Color.dark_green(),
            "dark_red": discord.Color.dark_red(),
            "dark_gold": discord.Color.dark_gold(),
            "dark_grey": discord.Color.dark_grey(),
            "dark_orange": discord.Color.dark_orange(),
            "dark_purple": discord.Color.dark_purple(),
            "dark_magenta": discord.Color.dark_magenta(),
            "dark_teal": discord.Color.dark_teal(),
            "light_grey": discord.Color.light_grey(),
            "lighter_grey": discord.Color.lighter_grey(),
            "blurple": discord.Color.blurple(),
            "greyple": discord.Color.greyple(),
        }

        return color_map.get(color_str.lower(), discord.Color.default())