import discord
from discord.ext import commands
from discord import app_commands
import sys
import asyncio
import os
from typing import Optional, Literal, List
import traceback
import time
import platform
import psutil
import json

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
    async def sync_commands(self, ctx, target: Optional[Literal["global", "guild"]] = "guild"):
        """
        Sync application commands
        
        Parameters:
        -----------
        target: Optional[Literal["global", "guild"]]
            Where to sync commands. "global" for global commands, "guild" for the current guild.
        """
        embed = discord.Embed(
            title="Syncing Commands",
            description="Syncing application commands...",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        try:
            start_time = time.time()
            
            if target == "guild":
                # Sync to the current guild
                guild = ctx.guild
                if not guild:
                    embed = discord.Embed(
                        title="Error",
                        description="This command must be used in a guild when using 'guild' target.",
                        color=discord.Color.red()
                    )
                    await message.edit(embed=embed)
                    return
                
                self.bot.tree.copy_global_to(guild=guild)
                synced = await self.bot.tree.sync(guild=guild)
                
                end_time = time.time()
                
                embed = discord.Embed(
                    title="Commands Synced",
                    description=f"Successfully synced {len(synced)} commands to {guild.name}",
                    color=discord.Color.green()
                )
                embed.set_footer(text=f"Completed in {(end_time - start_time):.2f} seconds")
            else:
                # Sync globally
                synced = await self.bot.tree.sync()
                
                end_time = time.time()
                
                embed = discord.Embed(
                    title="Commands Synced",
                    description=f"Successfully synced {len(synced)} global commands.",
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
    
    @commands.command(name="botinfo", description="Get detailed information about the bot (Owner only)")
    async def botinfo(self, ctx):
        """Get detailed information about the bot"""
        # Collect system info
        python_version = platform.python_version()
        discord_version = discord.__version__
        system_info = f"{platform.system()} {platform.release()}"
        
        # Process info
        process = psutil.Process()
        memory_usage = process.memory_info().rss / 1024**2  # Convert to MB
        cpu_usage = psutil.cpu_percent()
        
        # Bot info
        uptime = time.time() - self.bot.startup_time if hasattr(self.bot, 'startup_time') else 0
        days, remainder = divmod(int(uptime), 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s" if uptime > 0 else "Just started"
        
        guild_count = len(self.bot.guilds)
        user_count = sum(g.member_count for g in self.bot.guilds)
        
        # Cog info
        loaded_cogs = [cog for cog in self.bot.cogs]
        
        # Create embed
        embed = discord.Embed(
            title=f"{self.bot.user.name} Info",
            description="Detailed bot information and statistics",
            color=discord.Color.blue()
        )
        
        if self.bot.user.avatar:
            embed.set_thumbnail(url=self.bot.user.avatar.url)
            
        # General section
        embed.add_field(name="General", value=(
            f"**ID:** {self.bot.user.id}\n"
            f"**Guilds:** {guild_count}\n"
            f"**Users:** {user_count}\n"
            f"**Uptime:** {uptime_str}\n"
            f"**Latency:** {round(self.bot.latency * 1000)}ms"
        ), inline=False)
        
        # System section
        embed.add_field(name="System", value=(
            f"**Python:** {python_version}\n"
            f"**Discord.py:** {discord_version}\n"
            f"**OS:** {system_info}\n"
            f"**Memory:** {memory_usage:.2f} MB\n"
            f"**CPU:** {cpu_usage}%"
        ), inline=False)
        
        # Cogs section
        embed.add_field(name=f"Loaded Cogs ({len(loaded_cogs)})", value=(
            ", ".join(loaded_cogs) if loaded_cogs else "None"
        ), inline=False)
        
        await ctx.send(embed=embed)
    
    @commands.command(name="shutdown", description="Shut down the bot (Owner only)")
    async def shutdown(self, ctx):
        """Shut down the bot (Owner only)"""
        embed = discord.Embed(
            title="Shutting Down",
            description="The bot is shutting down...",
            color=discord.Color.red()
        )
        await ctx.send(embed=embed)
        
        # Save any data that needs to be persisted
        self.bot.save_triggers()
        self.bot.save_prefixes()
        
        # Close the bot
        await self.bot.close()
    
    @commands.command(name="eval", description="Evaluate Python code (Owner only)")
    async def eval_command(self, ctx, *, code: str):
        """
        Evaluate Python code (Owner only)
        
        Parameters:
        -----------
        code: str
            The Python code to evaluate
        """
        # Remove code blocks if present
        if code.startswith("```python") or code.startswith("```py"):
            code = code.split("\n", 1)[1].rsplit("```", 1)[0]
        elif code.startswith("```"):
            code = code.split("\n", 1)[1].rsplit("```", 1)[0]
        
        # Create a local environment
        env = {
            'bot': self.bot,
            'ctx': ctx,
            'channel': ctx.channel,
            'author': ctx.author,
            'guild': ctx.guild,
            'message': ctx.message,
            'discord': discord,
            'commands': commands
        }
        env.update(globals())
        
        # Set up the execution function
        code_func = f"""
async def _eval_func():
    try:
{chr(10).join(f"        {line}" for line in code.splitlines())}
    except Exception as e:
        return f"```py\\n{chr(123)}e{chr(125).__class__.__name__}: {chr(123)}e{chr(125)}\\n```"
"""
        
        try:
            # Create the _eval_func
            exec(code_func, env)
            # Execute the function
            result = await env['_eval_func']()
            
            # Format the result
            if result is None:
                result = "Code executed successfully, but returned no value."
            
            # Send the result
            embed = discord.Embed(
                title="Code Evaluation",
                color=discord.Color.green()
            )
            
            # Add result field, handling long outputs
            if isinstance(result, str) and len(result) > 1000:
                # Truncate long results
                embed.add_field(name="Result (truncated)", value=result[:997] + "...", inline=False)
            else:
                embed.add_field(name="Result", value=result, inline=False)
            
            await ctx.send(embed=embed)
        
        except Exception as e:
            # Handle errors in executing the code
            error_traceback = traceback.format_exc()
            embed = discord.Embed(
                title="Evaluation Error",
                description=f"An error occurred while executing the code:\n```python\n{error_traceback[:1000]}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="backup", description="Backup bot data (Owner only)")
    async def backup(self, ctx):
        """Backup bot data to a new directory (Owner only)"""
        # Create backup directory with timestamp
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        backup_dir = f"backups/backup_{timestamp}"
        os.makedirs(backup_dir, exist_ok=True)
        
        try:
            # Copy config files
            if os.path.exists("config.json"):
                with open("config.json", "r") as source:
                    config_data = json.load(source)
                    # Censor token for security
                    if "token" in config_data:
                        config_data["token"] = "[CENSORED]"
                    with open(f"{backup_dir}/config.json", "w") as dest:
                        json.dump(config_data, dest, indent=4)
            
            # Copy data files
            os.makedirs(f"{backup_dir}/data", exist_ok=True)
            data_files = ["triggers.json", "prefixes.json"]
            for file in data_files:
                src_path = f"data/{file}"
                if os.path.exists(src_path):
                    with open(src_path, "r") as source:
                        with open(f"{backup_dir}/data/{file}", "w") as dest:
                            dest.write(source.read())
            
            # Create an info file about the backup
            guild_count = len(self.bot.guilds)
            trigger_count = sum(len(triggers) for triggers in self.bot.triggers.values())
            with open(f"{backup_dir}/backup_info.txt", "w") as info_file:
                info_file.write(f"Backup created: {timestamp}\n")
                info_file.write(f"Bot name: {self.bot.user.name}\n")
                info_file.write(f"Bot ID: {self.bot.user.id}\n")
                info_file.write(f"Guild count: {guild_count}\n")
                info_file.write(f"Trigger count: {trigger_count}\n")
            
            embed = discord.Embed(
                title="Backup Created",
                description=f"Successfully created backup at `{backup_dir}`",
                color=discord.Color.green()
            )
            embed.add_field(name="Statistics", value=(
                f"Guilds: {guild_count}\n"
                f"Triggers: {trigger_count}"
            ))
            await ctx.send(embed=embed)
        
        except Exception as e:
            embed = discord.Embed(
                title="Backup Error",
                description=f"Failed to create backup:\n```python\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
    
    @commands.command(name="guilds", description="List all guilds the bot is in (Owner only)")
    async def list_guilds(self, ctx):
        """List all guilds the bot is in (Owner only)"""
        guilds = sorted(self.bot.guilds, key=lambda g: g.member_count, reverse=True)
        
        # Create a paginated embed
        pages = []
        guilds_per_page = 10
        
        for i in range(0, len(guilds), guilds_per_page):
            page_guilds = guilds[i:i+guilds_per_page]
            
            embed = discord.Embed(
                title=f"Bot Guilds ({i+1}-{min(i+guilds_per_page, len(guilds))} of {len(guilds)})",
                color=discord.Color.blue()
            )
            
            for guild in page_guilds:
                trigger_count = len(self.bot.triggers.get(str(guild.id), {}))
                prefix = self.bot.server_prefixes.get(str(guild.id), self.bot.config['default_prefix'])
                
                embed.add_field(
                    name=f"{guild.name} (ID: {guild.id})",
                    value=(
                        f"Members: {guild.member_count}\n"
                        f"Owner: {guild.owner.name if guild.owner else 'Unknown'}\n"
                        f"Triggers: {trigger_count}\n"
                        f"Prefix: `{prefix}`"
                    ),
                    inline=False
                )
            
            pages.append(embed)
        
        if not pages:
            # No guilds
            embed = discord.Embed(
                title="Bot Guilds",
                description="The bot is not in any guilds.",
                color=discord.Color.orange()
            )
            await ctx.send(embed=embed)
            return
        
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
    
    @commands.command(name="leave", description="Make the bot leave a guild (Owner only)")
    async def leave_guild(self, ctx, guild_id: int = None):
        """
        Make the bot leave a guild
        
        Parameters:
        -----------
        guild_id: Optional[int]
            The ID of the guild to leave. If not provided, the bot will leave the current guild.
        """
        if guild_id is None and ctx.guild is None:
            embed = discord.Embed(
                title="Error",
                description="You must provide a guild ID when using this command in DMs.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        target_guild = self.bot.get_guild(guild_id) if guild_id else ctx.guild
        
        if not target_guild:
            embed = discord.Embed(
                title="Error",
                description=f"Guild with ID {guild_id} not found.",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="Leaving Guild",
            description=f"Leaving guild: {target_guild.name} (ID: {target_guild.id})",
            color=discord.Color.yellow()
        )
        await ctx.send(embed=embed)
        
        try:
            await target_guild.leave()
            
            # Send confirmation if we're not leaving the current guild
            if target_guild.id != ctx.guild.id:
                embed = discord.Embed(
                    title="Guild Left",
                    description=f"Successfully left guild: {target_guild.name} (ID: {target_guild.id})",
                    color=discord.Color.green()
                )
                await ctx.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                title="Error",
                description=f"Failed to leave guild:\n```python\n{str(e)}\n```",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)


async def setup(bot):
    # Add startup time to the bot if it doesn't exist yet
    if not hasattr(bot, 'startup_time'):
        bot.startup_time = time.time()
    
    # Make sure backups directory exists
    os.makedirs("backups", exist_ok=True)
    
    # Add the cog to the bot
    await bot.add_cog(OwnerCommands(bot))
