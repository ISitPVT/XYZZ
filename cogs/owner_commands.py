import discord
from discord.ext import commands
from discord import app_commands
import logging
from typing import Optional, Dict, List, Any

logger = logging.getLogger('owner_commands')

class HelpPageView(discord.ui.View):
    """Pagination view for help command"""
    
    def __init__(self, pages: List[discord.Embed], author_id: int):
        super().__init__(timeout=60)
        self.pages = pages
        self.author_id = author_id
        self.current_page = 0
        self.total_pages = len(pages)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page = (self.current_page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page = (self.current_page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)


class OwnerCommands(commands.Cog):
    """Commands available to server managers and the bot owner"""
    
    def __init__(self, bot):
        self.bot = bot
    
    def is_owner_or_has_manage_server(self, ctx):
        """Check if the user is the bot owner or has manage server permissions"""
        if ctx.author.id == self.bot.owner_id:
            return True
        
        # Check if in DM channel
        if not ctx.guild:
            return False
            
        # Check if user has manage server permissions
        return ctx.author.guild_permissions.manage_guild
    
    @commands.command(name="bothelp")
    async def help_command(self, ctx, command: Optional[str] = None):
        """Show help for all commands or a specific command"""
        if command:
            # Show help for a specific command
            cmd = self.bot.get_command(command)
            if not cmd:
                await ctx.send(f"No command called `{command}` found.")
                return
            
            embed = discord.Embed(
                title=f"Help: {cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue()
            )
            
            # Add usage information
            usage = f"{ctx.prefix}{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            # Add aliases if any
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in cmd.aliases]), inline=False)
            
            await ctx.send(embed=embed)
        else:
            # Create multiple help pages
            pages = self.create_help_pages(ctx)
            
            # Send the first page with pagination
            view = HelpPageView(pages, ctx.author.id)
            await ctx.send(embed=pages[0], view=view)
    
    @app_commands.command(name="help", description="Show help for bot commands")
    @app_commands.describe(command="Optional command name to get specific help")
    async def slash_help_command(self, interaction: discord.Interaction, command: Optional[str] = None):
        """Slash command to show help for all commands or a specific command"""
        if command:
            # Show help for a specific command
            cmd = self.bot.get_command(command)
            if not cmd:
                await interaction.response.send_message(f"No command called `{command}` found.", ephemeral=True)
                return
            
            embed = discord.Embed(
                title=f"Help: {cmd.name}",
                description=cmd.help or "No description available.",
                color=discord.Color.blue()
            )
            
            # Add usage information
            prefix = self.bot.prefixes.get(str(interaction.guild_id), self.bot.default_prefix) if interaction.guild else self.bot.default_prefix
            usage = f"{prefix}{cmd.name}"
            if cmd.signature:
                usage += f" {cmd.signature}"
            embed.add_field(name="Usage", value=f"`{usage}`", inline=False)
            
            # Add aliases if any
            if cmd.aliases:
                embed.add_field(name="Aliases", value=", ".join([f"`{alias}`" for alias in cmd.aliases]), inline=False)
            
            await interaction.response.send_message(embed=embed)
        else:
            # Create multiple help pages
            pages = self.create_help_pages(interaction)
            
            # Send the first page with pagination
            view = HelpPageView(pages, interaction.user.id)
            await interaction.response.send_message(embed=pages[0], view=view)
    
    def create_help_pages(self, ctx_or_interaction):
        """Create help pages for all commands"""
        pages = []
        
        # Main help page
        main_page = discord.Embed(
            title="Trigger Bot Help",
            description="Welcome to the Trigger Bot! Here's an overview of available commands.",
            color=discord.Color.blue()
        )
        
        # Get the appropriate prefix
        if isinstance(ctx_or_interaction, commands.Context):
            prefix = ctx_or_interaction.prefix
            user = ctx_or_interaction.author
        else:  # discord.Interaction
            prefix = self.bot.prefixes.get(str(ctx_or_interaction.guild_id), self.bot.default_prefix) if ctx_or_interaction.guild else self.bot.default_prefix
            user = ctx_or_interaction.user
        
        main_page.add_field(
            name="Command Categories",
            value=f"""
            • **Trigger Commands** - Create and manage triggers
            • **Server Commands** - Manage server-specific settings
            
            Use `{prefix}bothelp <command>` for more details on a command.
            """,
            inline=False
        )
        
        main_page.set_footer(text=f"Requested by {user}")
        pages.append(main_page)
        
        # Trigger commands page
        trigger_page = discord.Embed(
            title="Trigger Commands",
            description="Commands to create and manage triggers",
            color=discord.Color.green()
        )
        
        trigger_page.add_field(
            name=f"{prefix}trigger create <name> [content]",
            value="Create a new trigger with optional text content and/or attachment\n(Requires: Bot Owner or Manage Server)",
            inline=False
        )
        
        trigger_page.add_field(
            name=f"{prefix}trigger delete [name]",
            value="Delete a trigger. If no name is provided, shows a list of triggers\n(Requires: Bot Owner)",
            inline=False
        )
        
        trigger_page.add_field(
            name=f"{prefix}trigger get <name>",
            value="Get information about a specific trigger",
            inline=False
        )
        
        trigger_page.add_field(
            name=f"{prefix}trigger list",
            value="List all triggers with pagination",
            inline=False
        )
        
        trigger_page.add_field(
            name="Automatic Triggering",
            value="Just type a trigger name in any message and the bot will respond with the trigger content!",
            inline=False
        )
        
        trigger_page.set_footer(text=f"Page 2 of 3 • Requested by {user}")
        pages.append(trigger_page)
        
        # Server commands page
        server_page = discord.Embed(
            title="Server Commands",
            description="Commands to manage server-specific settings",
            color=discord.Color.gold()
        )
        
        server_page.add_field(
            name=f"{prefix}serverprefix",
            value="Show the current server prefix",
            inline=False
        )
        
        server_page.add_field(
            name=f"{prefix}serverprefix <new_prefix>",
            value="Change the server prefix\n(Requires: Bot Owner or Manage Server)",
            inline=False
        )
        
        server_page.add_field(
            name=f"{prefix}bothelp",
            value="Show this help message",
            inline=False
        )
        
        server_page.set_footer(text=f"Page 3 of 3 • Requested by {user}")
        pages.append(server_page)
        
        return pages
    
    @commands.command(name="serverprefix")
    async def server_prefix(self, ctx, new_prefix: Optional[str] = None):
        """Get or set the server prefix"""
        # If no new prefix is provided, show the current prefix
        if new_prefix is None:
            current_prefix = self.bot.prefixes.get(str(ctx.guild.id), self.bot.default_prefix) if ctx.guild else self.bot.default_prefix
            embed = discord.Embed(
                title="Server Prefix",
                description=f"The current prefix for this server is: `{current_prefix}`",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Check if user is authorized to change the prefix
        if not self.is_owner_or_has_manage_server(ctx):
            await ctx.send("You don't have permission to change the server prefix. You need to be the bot owner or have 'Manage Server' permission.")
            return
        
        # Validate prefix
        if len(new_prefix) > 5:
            await ctx.send("The prefix cannot be longer than 5 characters.")
            return
        
        # Update the prefix
        if ctx.guild:
            await self.bot.update_prefix(ctx.guild.id, new_prefix)
            
            embed = discord.Embed(
                title="Prefix Updated",
                description=f"The server prefix has been updated to: `{new_prefix}`",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            await ctx.send("You can't change the prefix in DMs.")
    
    @app_commands.command(name="serverprefix", description="Get or set the server prefix")
    @app_commands.describe(new_prefix="The new prefix to set for this server")
    async def slash_server_prefix(self, interaction: discord.Interaction, new_prefix: Optional[str] = None):
        """Slash command to get or set the server prefix"""
        # If no new prefix is provided, show the current prefix
        if new_prefix is None:
            current_prefix = self.bot.prefixes.get(str(interaction.guild_id), self.bot.default_prefix) if interaction.guild else self.bot.default_prefix
            embed = discord.Embed(
                title="Server Prefix",
                description=f"The current prefix for this server is: `{current_prefix}`",
                color=discord.Color.blue()
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Check if user is authorized to change the prefix
        if not (interaction.user.id == self.bot.owner_id or 
                (interaction.guild and interaction.user.guild_permissions.manage_guild)):
            await interaction.response.send_message("You don't have permission to change the server prefix. You need to be the bot owner or have 'Manage Server' permission.", ephemeral=True)
            return
        
        # Validate prefix
        if len(new_prefix) > 5:
            await interaction.response.send_message("The prefix cannot be longer than 5 characters.", ephemeral=True)
            return
        
        # Update the prefix
        if interaction.guild:
            await self.bot.update_prefix(interaction.guild.id, new_prefix)
            
            embed = discord.Embed(
                title="Prefix Updated",
                description=f"The server prefix has been updated to: `{new_prefix}`",
                color=discord.Color.green()
            )
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("You can't change the prefix in DMs.", ephemeral=True)

async def setup(bot):
    # First, disable the default help command
    bot.help_command = None
    
    # Then add our custom cog
    await bot.add_cog(OwnerCommands(bot))
    
    # Register app commands
    owner_cog = bot.get_cog("OwnerCommands")
    
    # Add help command
    bot.tree.add_command(owner_cog.slash_help_command)
    
    # Add serverprefix command
    bot.tree.add_command(owner_cog.slash_server_prefix)
    
    await bot.tree.sync()
