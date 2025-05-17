import discord
from discord.ext import commands
from discord import app_commands
import sys
import asyncio
import os
from typing import Optional, Literal
import traceback
import time

class OwnerCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_check(self, ctx):
        """Check that ensures commands in this cog can only be used by the bot owner."""
        return await self.bot.is_owner(ctx.author)
    
    @commands.command(name="restart", description="Restart the bot (Owner only)")
    async def restart(self, ctx):
        """Restart the bot (Owner only)"""
        embed = discord.Embed(
            title="Restarting Bot",
            description="The bot is restarting...",
            color=discord.Color.orange()
        )
        await ctx.send(embed=embed)
        
        # Save any data that needs to be persisted
        self.bot.save_triggers()
        self.bot.save_prefixes()
        
        # Restart the bot
        python = sys.executable
        os.execl(python, python, *sys.argv)
    
    @commands.command(name="reload", description="Reload bot commands (Owner only)")
    @commands.is_owner()
    async def reload(self, ctx, *, cog: Optional[str] = None):
        """
        Reload all cogs or a specific cog
        
        Parameters:
        -----------
        cog: Optional[str]
            The name of the cog to reload. If not provided, all cogs will be reloaded.
        """
        start_time = time.time()
        
        if cog:
            # Reload a specific cog
            try:
                await self.bot.reload_extension(f"cogs.{cog}")
                end_time = time.time()
                
                embed = discord.Embed(
                    title="Cog Reloaded",
                    description=f"Successfully reloaded cog `{cog}`.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Completed in {(end_time - start_time):.2f} seconds")
                await ctx.send(embed=embed)
            except Exception as e:
                embed = discord.Embed(
                    title="Error",
                    description=f"Failed to reload cog `{cog}`:\n```python\n{str(e)}\n```",
                    color=discord.Color.red()
                )
                await ctx.send(embed=embed)
        else:
            # Reload all cogs
            embed = discord.Embed(
                title="Reloading Cogs",
                description="Reloading all cogs...",
                color=discord.Color.blue()
            )
            message = await ctx.send(embed=embed)
            
            success_count = 0
            fail_count = 0
            failed_cogs = []
            
            # Reload each cog
            for filename in os.listdir("./cogs"):
                if filename.endswith(".py") and not filename.startswith("_"):
                    cog_name = filename[:-3]
                    try:
                        await self.bot.reload_extension(f"cogs.{cog_name}")
                        success_count += 1
                    except Exception as e:
                        fail_count += 1
                        failed_cogs.append((cog_name, str(e)))
            
            end_time = time.time()
            
            # Update the embed with results
            if fail_count == 0:
                embed = discord.Embed(
                    title="Cogs Reloaded",
                    description=f"Successfully reloaded all {success_count} cogs.",
                    color=discord.Color.green()
                )
            else:
                embed = discord.Embed(
                    title="Cogs Reloaded",
                    description=f"Reloaded {success_count} cogs successfully, {fail_count} failed.",
                    color=discord.Color.yellow()
                )
                
                # Add details about failed cogs
                for cog_name, error in failed_cogs:
                    embed.add_field(
                        name=f"Failed: {cog_name}",
                        value=f"```python\n{error[:1000]}```",
                        inline=False
                    )
            
            embed.set_footer(text=f"Completed in {(end_time - start_time):.2f} seconds")
            await message.edit(embed=embed)
    
    @commands.command(name="sync", description="Sync slash commands (Owner only)")
    @commands.is_owner()
    async def sync_commands(self, ctx, guild_id: Optional[int] = None):
        """
        Sync application commands
        
        Parameters:
        -----------
        guild_id: Optional[int]
            The ID of the guild to sync commands to. If not provided, global commands will be synced.
        """
        embed = discord.Embed(
            title="Syncing Commands",
            description="Syncing application commands...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        try:
            start_time = time.time()
            
            if guild_id:
                # Sync to a specific guild
                guild = self.bot.get_guild(guild_id)
                if not guild:
                    embed = discord.Embed(
                        title="Error",
                        description=f"Guild with ID {guild_id} not found.",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed)
                    return
                
                self.bot.tree.copy_global_to(guild=guild)
                await self.bot.tree.sync(guild=guild)
                
                end_time = time.time()
                
                embed = discord.Embed(
                    title="Commands Synced",
                    description=f"Successfully synced commands to guild: {guild.name}",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Completed in {(end_time - start_time):.2f} seconds")
            else:
                # Sync globally
                await self.bot.tree.sync()
                
                end_time = time.time()
                
                embed = discord.Embed(
                    title="Commands Synced",
                    description="Successfully synced global commands.",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Completed in {(end_time - start_time):.2f} seconds")
            
            await message.edit(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to sync commands:\n```python\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await message.edit(embed=embed)


async def setup(bot):
    await bot.add_cog(OwnerCommands(bot))
