# Let's also fix the trigger_commands.py file to ensure slash commands work properly

import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Optional
import asyncio
import datetime

class TriggerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
    @commands.hybrid_group(name="trigger", description="Manage trigger commands")
    async def trigger(self, ctx):
        """Group command for managing triggers"""
        if ctx.invoked_subcommand is None:
            prefix = self.bot.server_prefixes.get(str(ctx.guild.id), self.bot.config['default_prefix'])
            embed = discord.Embed(
                title="Trigger Commands",
                description=f"Use `{prefix}help trigger` for more information.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Available Commands", value=(
                f"`{prefix}trigger create <name> <response>` - Create a new trigger\n"
                f"`{prefix}trigger delete <name>` - Delete a trigger\n"
                f"`{prefix}trigger get <name>` - Get information about a trigger\n"
                f"`{prefix}trigger list` - List all triggers"
            ))
            embed.set_footer(text="You can also use these as slash commands!")
            await ctx.send(embed=embed)
    
    @trigger.command(name="create", description="Create a new trigger")
    @app_commands.describe(
        name="The name of the trigger",
        response="The response text or attachment"
    )
    async def create_trigger(self, ctx, name: str, *, response: Optional[str] = None):
        """
        Create a new trigger
        
        Parameters:
        -----------
        name: str
            The name of the trigger
        response: Optional[str]
            The response text
        """
        # Check if user is owner or has manage messages permission
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.manage_messages:
            embed = discord.Embed(
                title="Permission Denied",
                description="You need the 'Manage Messages' permission to create triggers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Check for attachment
        attachment_url = None
        if hasattr(ctx.message, 'attachments') and ctx.message.attachments:
            attachment_url = ctx.message.attachments[0].url
        
        # If no response text is provided but there's an attachment, use the attachment URL
        if response is None and attachment_url:
            response = attachment_url
        # If neither is provided, return an error
        elif response is None:
            embed = discord.Embed(
                title="Error",
                description="You must provide a response text or attachment.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Create the trigger
        guild_id = str(ctx.guild.id)
        if guild_id not in self.bot.triggers:
            self.bot.triggers[guild_id] = {}
        
        # Check if trigger already exists
        if name.lower() in [t.lower() for t in self.bot.triggers[guild_id]]:
            embed = discord.Embed(
                title="Error",
                description=f"Trigger '{name}' already exists.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        # Add the trigger
        current_time = datetime.datetime.utcnow().isoformat()
        self.bot.triggers[guild_id][name] = {
            "response": response,
            "creator_id": ctx.author.id,
            "created_at": current_time
        }
        
        # Save triggers
        self.bot.save_triggers()
        
        embed = discord.Embed(
            title="Trigger Created",
            description=f"Trigger '{name}' has been created successfully.",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)
    
    # The rest of your methods remain the same...
    @trigger.command(name="delete", description="Delete a trigger")
    @app_commands.describe(
        name="The name of the trigger to delete"
    )
    async def delete_trigger(self, ctx, *, name: Optional[str] = None):
        """
        Delete a trigger
        
        Parameters:
        -----------
        name: Optional[str]
            The name of the trigger to delete
        """
        # Check if user is owner or has manage messages permission
        if not await self.bot.is_owner(ctx.author) and not ctx.author.guild_permissions.manage_messages:
            embed = discord.Embed(
                title="Permission Denied",
                description="You need the 'Manage Messages' permission to delete triggers.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        guild_id = str(ctx.guild.id)
        
        # If no name is provided, show a list of triggers to choose from
        if name is None:
            if guild_id not in self.bot.triggers or not self.bot.triggers[guild_id]:
                embed = discord.Embed(
                    title="No Triggers",
                    description="This server has no triggers.",
                    color=discord.Color.orange()
                )
                await ctx.send(embed=embed)
                return
            
            triggers_list = list(self.bot.triggers[guild_id].keys())
            
            # Create an embed with the list of triggers
            embed = discord.Embed(
                title="Select a Trigger to Delete",
                description="Type the number of the trigger you want to delete or 'cancel' to abort.",
                color=discord.Color.blue()
            )
            
            for i, trigger_name in enumerate(triggers_list, 1):
                embed.add_field(
                    name=f"{i}. {trigger_name}",
                    value=self.bot.triggers[guild_id][trigger_name]["response"][:50] + "..." if len(self.bot.triggers[guild_id][trigger_name]["response"]) > 50 else self.bot.triggers[guild_id][trigger_name]["response"],
                    inline=False
                )
            
            message = await ctx.send(embed=embed)
            
            def check(m):
                return m.author == ctx.author and m.channel == ctx.channel
            
            try:
                response = await self.bot.wait_for('message', check=check, timeout=30.0)
                
                if response.content.lower() == 'cancel':
                    await ctx.send("Trigger deletion cancelled.")
                    return
                
                try:
                    index = int(response.content)
                    if 1 <= index <= len(triggers_list):
                        name = triggers_list[index - 1]
                    else:
                        await ctx.send("Invalid number. Deletion cancelled.")
                        return
                except ValueError:
                    # Check if the user typed a trigger name instead of a number
                    if response.content in self.bot.triggers[guild_id]:
                        name = response.content
                    else:
                        await ctx.send("Invalid input. Deletion cancelled.")
                        return
            
            except asyncio.TimeoutError:
                await ctx.send("Timed out. Trigger deletion cancelled.")
                return
        
        # Delete the specified trigger
        if guild_id in self.bot.triggers and name in self.bot.triggers[guild_id]:
            del self.bot.triggers[guild_id][name]
            self.bot.save_triggers()
            
            embed = discord.Embed(
                title="Trigger Deleted",
                description=f"Trigger '{name}' has been deleted successfully.",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
                title="Error",
                description=f"Trigger '{name}' not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @trigger.command(name="get", description="Get information about a trigger")
    @app_commands.describe(
        name="The name of the trigger to get information about"
    )
    async def get_trigger(self, ctx, *, name: str):
        """
        Get information about a trigger
        
        Parameters:
        -----------
        name: str
            The name of the trigger to get information about
        """
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.bot.triggers or name not in self.bot.triggers[guild_id]:
            embed = discord.Embed(
                title="Trigger Not Found",
                description=f"Trigger '{name}' not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        trigger_data = self.bot.triggers[guild_id][name]
        creator = self.bot.get_user(trigger_data["creator_id"])
        creator_name = creator.name if creator else f"Unknown User ({trigger_data['creator_id']})"
        
        embed = discord.Embed(
            title=f"Trigger: {name}",
            color=discord.Color.blue()
        )
        
        # Check if the response is an image URL
        response = trigger_data["response"]
        if response.startswith("http") and any(response.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
            embed.set_image(url=response)
            embed.add_field(name="Response", value="[Image](" + response + ")", inline=False)
        else:
            embed.add_field(name="Response", value=response, inline=False)
        
        embed.add_field(name="Created By", value=creator_name, inline=True)
        
        # Format the created_at date nicely
        try:
            created_at = trigger_data["created_at"].split("T")[0]  # Just take the date part
        except (KeyError, AttributeError, IndexError):
            created_at = "Unknown"
            
        embed.add_field(name="Created At", value=created_at, inline=True)
        
        await ctx.send(embed=embed)
    
    @trigger.command(name="list", description="List all triggers")
    async def list_triggers(self, ctx):
        """List all triggers in the server"""
        guild_id = str(ctx.guild.id)
        
        if guild_id not in self.bot.triggers or not self.bot.triggers[guild_id]:
            embed = discord.Embed(
                title="No Triggers",
                description="This server has no triggers.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
        triggers = self.bot.triggers[guild_id]
        
        # Create a paginated embed
        embed = discord.Embed(
            title=f"Triggers in {ctx.guild.name}",
            description=f"Total triggers: {len(triggers)}",
            color=discord.Color.blue()
        )
        
        # Sort triggers alphabetically
        sorted_triggers = sorted(triggers.keys())
        
        # Add all triggers to the embed (with pagination if needed)
        fields_per_page = 25  # Maximum fields per embed
        
        if len(sorted_triggers) <= fields_per_page:
            # Single page - add all triggers
            for trigger_name in sorted_triggers:
                response = triggers[trigger_name]["response"]
                # Truncate the response if it's too long
                if len(response) > 50:
                    response = response[:47] + "..."
                # If it's an image URL, show a placeholder
                if response.startswith("http") and any(response.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                    response = "[Image]"
                
                embed.add_field(
                    name=trigger_name,
                    value=response,
                    inline=True
                )
            
            await ctx.send(embed=embed)
        else:
            # Multiple pages needed
            pages = []
            for i in range(0, len(sorted_triggers), fields_per_page):
                page_embed = discord.Embed(
                    title=f"Triggers in {ctx.guild.name} (Page {i//fields_per_page + 1}/{(len(sorted_triggers)-1)//fields_per_page + 1})",
                    description=f"Total triggers: {len(triggers)}",
                    color=discord.Color.blue()
                )
                
                # Add triggers for this page
                page_triggers = sorted_triggers[i:i+fields_per_page]
                for trigger_name in page_triggers:
                    response = triggers[trigger_name]["response"]
                    # Truncate the response if it's too long
                    if len(response) > 50:
                        response = response[:47] + "..."
                    # If it's an image URL, show a placeholder
                    if response.startswith("http") and any(response.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                        response = "[Image]"
                    
                    page_embed.add_field(
                        name=trigger_name,
                        value=response,
                        inline=True
                    )
                
                pages.append(page_embed)
            
            # Send first page
            current_page = 0
            message = await ctx.send(embed=pages[current_page])
            
            # Add navigation reactions if there's more than one page
            if len(pages) > 1:
                navigation_emojis = ['⬅️', '➡️']
                for emoji in navigation_emojis:
                    await message.add_reaction(emoji)
                
                def check(reaction, user):
                    return user == ctx.author and str(reaction.emoji) in navigation_emojis and reaction.message.id == message.id
                
                # Wait for reactions
                while True:
                    try:
                        reaction, user = await self.bot.wait_for('reaction_add', timeout=60.0, check=check)
                        
                        if str(reaction.emoji) == '⬅️' and current_page > 0:
                            current_page -= 1
                            await message.edit(embed=pages[current_page])
                        elif str(reaction.emoji) == '➡️' and current_page < len(pages) - 1:
                            current_page += 1
                            await message.edit(embed=pages[current_page])
                            
                        # Remove the user's reaction
                        try:
                            await message.remove_reaction(reaction.emoji, user)
                        except discord.errors.Forbidden:
                            pass  # Bot doesn't have permission to remove reactions
                    
                    except asyncio.TimeoutError:
                        # Timeout - remove all reactions
                        try:
                            await message.clear_reactions()
                        except discord.errors.Forbidden:
                            pass  # Bot doesn't have permission to clear reactions
                        break

    @commands.hybrid_command(name="serverprefix", description="Change the server's command prefix")
    @commands.has_permissions(administrator=True)
    @app_commands.describe(
        new_prefix="The new prefix for this server"
    )
    async def serverprefix(self, ctx, new_prefix: str = None):
        """
        Change the server's command prefix or view the current prefix
        
        Parameters:
        -----------
        new_prefix: Optional[str]
            The new prefix for this server
        """
        if not ctx.guild:
            await ctx.send("This command can only be used in a server.")
            return
        
        guild_id = str(ctx.guild.id)
        
        # If no prefix is provided, show the current prefix
        if new_prefix is None:
            current_prefix = self.bot.server_prefixes.get(guild_id, self.bot.config['default_prefix'])
            embed = discord.Embed(
                title="Server Prefix",
                description=f"Current prefix: `{current_prefix}`",
                color=discord.Color.blue()
            )
            await ctx.send(embed=embed)
            return
        
        # Update the prefix
        if len(new_prefix) > 5:
            embed = discord.Embed(
                title="Error",
                description="Prefix cannot be longer than 5 characters.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        self.bot.server_prefixes[guild_id] = new_prefix
        self.bot.save_prefixes()
        
        embed = discord.Embed(
            title="Prefix Updated",
            description=f"Server prefix changed to: `{new_prefix}`",
            color=discord.Color.green()
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(TriggerCommands(bot))
