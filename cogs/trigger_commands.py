import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import io
import json
import logging
import datetime
import asyncio
from typing import Optional, List, Dict, Any, Union, Literal
from utils.db_manager import DatabaseManager

logger = logging.getLogger('trigger_commands')

class TriggerView(discord.ui.View):
    """Pagination view for trigger list command"""

    def __init__(self, triggers: Dict[str, Dict], author_id: int):
        super().__init__(timeout=60)
        self.triggers = list(triggers.items())
        self.author_id = author_id
        self.current_page = 0
        self.items_per_page = 5
        self.total_pages = max(1, (len(self.triggers) + self.items_per_page - 1) // self.items_per_page)

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.primary)
    async def previous_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page = (self.current_page - 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_current_page(), view=self)

    @discord.ui.button(label="➡️", style=discord.ButtonStyle.primary)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)
            return

        self.current_page = (self.current_page + 1) % self.total_pages
        await interaction.response.edit_message(embed=self.get_current_page(), view=self)

    def get_current_page(self) -> discord.Embed:
        """Get the current page of triggers"""
        start_idx = self.current_page * self.items_per_page
        end_idx = min(start_idx + self.items_per_page, len(self.triggers))
        
        embed = discord.Embed(
            title="Trigger List",
            description=f"Page {self.current_page + 1}/{self.total_pages}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )
        
        if len(self.triggers) == 0:
            embed.add_field(name="No triggers found", value="Use the trigger create command to add triggers")
            return embed
        
        current_triggers = self.triggers[start_idx:end_idx]
        
        for name, data in current_triggers:
            created_at = datetime.datetime.fromtimestamp(data.get('created_at', 0))
            has_attachment = "Yes" if data.get('attachment_url') else "No"
            creator = data.get('creator_name', 'Unknown')
            
            embed.add_field(
                name=name,
                value=f"Created by: {creator}\nCreated at: {created_at.strftime('%Y-%m-%d %H:%M:%S')}\nHas attachment: {has_attachment}",
                inline=False
            )
        
        return embed


class TriggerCommands(commands.Cog):
    """Commands for managing triggers"""
    
    def __init__(self, bot):
        self.bot = bot
        self.db = DatabaseManager()
        self.session = None
    
    async def cog_load(self):
        """Called when the cog is loaded"""
        self.session = aiohttp.ClientSession()
    
    async def cog_unload(self):
        """Called when the cog is unloaded"""
        if self.session:
            await self.session.close()
    
    def is_owner_or_has_manage_server(self, ctx):
        """Check if the user is the bot owner or has manage server permissions"""
        if ctx.author.id == self.bot.owner_id:
            return True
        
        # Check if in DM channel
        if not ctx.guild:
            return False
            
        # Check if user has manage server permissions
        return ctx.author.guild_permissions.manage_guild
    
    @commands.group(name="trigger", invoke_without_command=True)
    async def trigger(self, ctx):
        """Base trigger command group"""
        await ctx.send(f"Please specify a subcommand. Use `{ctx.prefix}help trigger` for more information.")
    
    @trigger.command(name="create")
    async def trigger_create(self, ctx, name: str, *, attachment: Optional[discord.Attachment] = None):
        """Create a new trigger with an optional attachment"""
        # Check if user is authorized (owner or has manage guild permission)
        if not self.is_owner_or_has_manage_server(ctx):
            await ctx.send("You don't have permission to create triggers. You need to be the bot owner or have 'Manage Server' permission.")
            return
        
        # Check if trigger already exists
        if self.db.trigger_exists(name):
            await ctx.send(f"A trigger with the name `{name}` already exists.")
            return
        
        # Process attachment if provided
        attachment_url = None
        if attachment:
            try:
                # Download attachment
                attachment_bytes = await attachment.read()
                
                # Store the URL directly (Discord CDN URLs are persistent)
                attachment_url = attachment.url
                
                logger.info(f"Attachment processed for trigger {name}: {attachment_url}")
            except Exception as e:
                logger.error(f"Error processing attachment: {str(e)}")
                await ctx.send(f"Error processing attachment: {str(e)}")
                return
        
        # Create trigger data
        trigger_data = {
            "creator_id": ctx.author.id,
            "creator_name": str(ctx.author),
            "created_at": datetime.datetime.now().timestamp(),
            "guild_id": ctx.guild.id if ctx.guild else None,
            "attachment_url": attachment_url
        }
        
        # Save trigger to database
        success = self.db.add_trigger(name, trigger_data)
        
        if success:
            embed = discord.Embed(
                title="Trigger Created",
                description=f"Trigger `{name}` has been created successfully.",
                color=discord.Color.green()
            )
            embed.add_field(name="Created by", value=str(ctx.author))
            embed.add_field(name="Has attachment", value="Yes" if attachment_url else "No")
            
            await ctx.send(embed=embed)
        else:
            await ctx.send("Error creating trigger. Please try again later.")
    
    @app_commands.command(name="create", description="Create a new trigger with an optional attachment")
    @app_commands.describe(
        name="The name of the trigger to create",
        attachment="Optional attachment for the trigger"
    )
    async def slash_trigger_create(self, interaction: discord.Interaction, name: str, attachment: Optional[discord.Attachment] = None):
        """Slash command to create a new trigger"""
        # Check if user is authorized (owner or has manage guild permission)
        if not (interaction.user.id == self.bot.owner_id or 
                (interaction.guild and interaction.user.guild_permissions.manage_guild)):
            await interaction.response.send_message("You don't have permission to create triggers. You need to be the bot owner or have 'Manage Server' permission.", ephemeral=True)
            return
        
        # Check if trigger already exists
        if self.db.trigger_exists(name):
            await interaction.response.send_message(f"A trigger with the name `{name}` already exists.", ephemeral=True)
            return
        
        # Process attachment if provided
        attachment_url = None
        if attachment:
            try:
                # Store the URL directly (Discord CDN URLs are persistent)
                attachment_url = attachment.url
                
                logger.info(f"Attachment processed for trigger {name}: {attachment_url}")
            except Exception as e:
                logger.error(f"Error processing attachment: {str(e)}")
                await interaction.response.send_message(f"Error processing attachment: {str(e)}", ephemeral=True)
                return
        
        # Create trigger data
        trigger_data = {
            "creator_id": interaction.user.id,
            "creator_name": str(interaction.user),
            "created_at": datetime.datetime.now().timestamp(),
            "guild_id": interaction.guild.id if interaction.guild else None,
            "attachment_url": attachment_url
        }
        
        # Save trigger to database
        success = self.db.add_trigger(name, trigger_data)
        
        if success:
            embed = discord.Embed(
                title="Trigger Created",
                description=f"Trigger `{name}` has been created successfully.",
                color=discord.Color.green()
            )
            embed.add_field(name="Created by", value=str(interaction.user))
            embed.add_field(name="Has attachment", value="Yes" if attachment_url else "No")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("Error creating trigger. Please try again later.", ephemeral=True)
    
    @trigger.command(name="delete")
    async def trigger_delete(self, ctx, name: Optional[str] = None):
        """Delete a trigger by name. If no name is provided, shows a list of triggers"""
        # Check if user is authorized (owner only)
        if ctx.author.id != self.bot.owner_id:
            await ctx.send("This command is only available to the bot owner.")
            return
        
        # If no name is provided, list all triggers
        if name is None:
            triggers = self.db.get_all_triggers()
            if not triggers:
                await ctx.send("There are no triggers to delete.")
                return
            
            # Show triggers with a paginated view
            view = TriggerView(triggers, ctx.author.id)
            await ctx.send(embed=view.get_current_page(), view=view)
            return
        
        # Check if trigger exists
        if not self.db.trigger_exists(name):
            await ctx.send(f"No trigger found with the name `{name}`.")
            return
        
        # Delete the trigger
        success = self.db.delete_trigger(name)
        
        if success:
            await ctx.send(f"Trigger `{name}` has been deleted successfully.")
        else:
            await ctx.send("Error deleting trigger. Please try again later.")
    
    @app_commands.command(name="delete", description="Delete a trigger by name")
    @app_commands.describe(name="The name of the trigger to delete (leave empty to see the list)")
    async def slash_trigger_delete(self, interaction: discord.Interaction, name: Optional[str] = None):
        """Slash command to delete a trigger"""
        # Check if user is authorized (owner only)
        if interaction.user.id != self.bot.owner_id:
            await interaction.response.send_message("This command is only available to the bot owner.", ephemeral=True)
            return
        
        # If no name is provided, list all triggers
        if name is None:
            triggers = self.db.get_all_triggers()
            if not triggers:
                await interaction.response.send_message("There are no triggers to delete.", ephemeral=True)
                return
            
            # Show triggers with a paginated view
            view = TriggerView(triggers, interaction.user.id)
            await interaction.response.send_message(embed=view.get_current_page(), view=view)
            return
        
        # Check if trigger exists
        if not self.db.trigger_exists(name):
            await interaction.response.send_message(f"No trigger found with the name `{name}`.", ephemeral=True)
            return
        
        # Delete the trigger
        success = self.db.delete_trigger(name)
        
        if success:
            await interaction.response.send_message(f"Trigger `{name}` has been deleted successfully.")
        else:
            await interaction.response.send_message("Error deleting trigger. Please try again later.", ephemeral=True)
    
    @trigger.command(name="get")
    async def trigger_get(self, ctx, name: str):
        """Get information about a specific trigger"""
        # Check if trigger exists
        trigger_data = self.db.get_trigger(name)
        if not trigger_data:
            await ctx.send(f"No trigger found with the name `{name}`.")
            return
        
        # Create embed with trigger information
        embed = discord.Embed(
            title=f"Trigger: {name}",
            description="Trigger information",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.fromtimestamp(trigger_data.get('created_at', 0))
        )
        
        # Add fields to embed
        embed.add_field(name="Created by", value=trigger_data.get('creator_name', 'Unknown'))
        
        # Format creation time
        created_time = datetime.datetime.fromtimestamp(trigger_data.get('created_at', 0))
        embed.add_field(name="Created at", value=created_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Add guild information if available
        if trigger_data.get('guild_id'):
            guild = self.bot.get_guild(trigger_data['guild_id'])
            embed.add_field(name="Server", value=guild.name if guild else "Unknown")
        
        # Add attachment information if available
        if trigger_data.get('attachment_url'):
            embed.add_field(name="Attachment", value="Yes")
            embed.set_image(url=trigger_data['attachment_url'])
        else:
            embed.add_field(name="Attachment", value="No")
        
        # Send the embed
        await ctx.send(embed=embed)
    
    @app_commands.command(name="get", description="Get information about a specific trigger")
    @app_commands.describe(name="The name of the trigger to get information about")
    async def slash_trigger_get(self, interaction: discord.Interaction, name: str):
        """Slash command to get information about a specific trigger"""
        # Check if trigger exists
        trigger_data = self.db.get_trigger(name)
        if not trigger_data:
            await interaction.response.send_message(f"No trigger found with the name `{name}`.", ephemeral=True)
            return
        
        # Create embed with trigger information
        embed = discord.Embed(
            title=f"Trigger: {name}",
            description="Trigger information",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.fromtimestamp(trigger_data.get('created_at', 0))
        )
        
        # Add fields to embed
        embed.add_field(name="Created by", value=trigger_data.get('creator_name', 'Unknown'))
        
        # Format creation time
        created_time = datetime.datetime.fromtimestamp(trigger_data.get('created_at', 0))
        embed.add_field(name="Created at", value=created_time.strftime('%Y-%m-%d %H:%M:%S'))
        
        # Add guild information if available
        if trigger_data.get('guild_id'):
            guild = self.bot.get_guild(trigger_data['guild_id'])
            embed.add_field(name="Server", value=guild.name if guild else "Unknown")
        
        # Add attachment information if available
        if trigger_data.get('attachment_url'):
            embed.add_field(name="Attachment", value="Yes")
            embed.set_image(url=trigger_data['attachment_url'])
        else:
            embed.add_field(name="Attachment", value="No")
        
        # Send the embed
        await interaction.response.send_message(embed=embed)
    
    @trigger.command(name="list")
    async def trigger_list(self, ctx):
        """List all triggers with pagination"""
        # Get all triggers
        triggers = self.db.get_all_triggers()
        
        if not triggers:
            await ctx.send("No triggers have been created yet.")
            return
        
        # Create a paginated view
        view = TriggerView(triggers, ctx.author.id)
        await ctx.send(embed=view.get_current_page(), view=view)
    
    @app_commands.command(name="list", description="List all triggers")
    async def slash_trigger_list(self, interaction: discord.Interaction):
        """Slash command to list all triggers"""
        # Get all triggers
        triggers = self.db.get_all_triggers()
        
        if not triggers:
            await interaction.response.send_message("No triggers have been created yet.")
            return
        
        # Create a paginated view
        view = TriggerView(triggers, interaction.user.id)
        await interaction.response.send_message(embed=view.get_current_page(), view=view)


async def setup(bot):
    await bot.add_cog(TriggerCommands(bot))
    # Register app commands
    trigger_group = app_commands.Group(name="trigger", description="Commands for managing triggers")
    
    trigger_cog = bot.get_cog("TriggerCommands")
    trigger_group.add_command(trigger_cog.slash_trigger_create)
    trigger_group.add_command(trigger_cog.slash_trigger_delete)
    trigger_group.add_command(trigger_cog.slash_trigger_get)
    trigger_group.add_command(trigger_cog.slash_trigger_list)
    
    bot.tree.add_command(trigger_group)
    await bot.tree.sync()
