#!/usr/bin/env python3

import os
import json
import discord
from discord.ext import commands
import asyncio
import logging
import sys
from typing import Optional, Dict, List, Any
from utils.db_manager import DatabaseManager
import utils

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger('trigger_bot')

# Define intents
intents = discord.Intents.default()
intents.message_content = True  # Needed to read message content for prefix commands
intents.guilds = True

async def get_prefix(bot, message):
    """Get the prefix for the guild"""
    if not message.guild:
        return commands.when_mentioned_or(bot.default_prefix)(bot, message)
    
    prefix = bot.prefixes.get(str(message.guild.id), bot.default_prefix)
    return commands.when_mentioned_or(prefix)(bot, message)

class TriggerBot(commands.Bot):
    def __init__(self):
        self.config = self.load_config()
        self.default_prefix = self.config.get('prefix', '!')
        
        # Properly handle owner_id with simpler direct approach
        self.owner_id = self.parse_owner_id(self.config.get('owner_id'))
        if self.owner_id is None:
            logger.warning("No valid owner_id found in config, some commands will be unavailable")
        else:
            logger.info(f"Owner ID set to: {self.owner_id}")
        
        self.prefixes: Dict[str, str] = {}
        self.db_manager = DatabaseManager()
        
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            case_insensitive=True,
            help_command=None  # Custom help command in OwnerCommands cog
        )
        
        # Initialize database files if they don't exist
        self.initialize_data_files()
        
        # Load prefixes
        self.load_prefixes()
    
    def parse_owner_id(self, owner_id_config):
        """Parse owner ID from config with better error handling"""
        try:
            if isinstance(owner_id_config, list) and len(owner_id_config) > 0:
                return int(owner_id_config[0])
            elif isinstance(owner_id_config, (int, str)):
                return int(owner_id_config)
            else:
                logger.error(f"Invalid owner_id format: {owner_id_config}")
                return None
        except (ValueError, TypeError) as e:
            logger.error(f"Error parsing owner_id: {e}")
            return None
    
    def load_config(self) -> Dict[str, Any]:
        """Load the bot configuration"""
        try:
            with open('config.json', 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Create default config if it doesn't exist
            default_config = {
                "token": "YOUR_BOT_TOKEN_HERE",
                "prefix": "!",
                "owner_id": 123456789  # Replace with your Discord ID
            }
            with open('config.json', 'w') as f:
                json.dump(default_config, f, indent=2)
            logger.info("Created default config.json file. Please edit it with your bot details.")
            sys.exit(1)
    
    def initialize_data_files(self):
        """Initialize necessary data files and directories"""
        # Make sure directories exist
        utils.check_directories()
        
        # Ensure prefixes.json has valid content
        prefix_path = 'data/prefixes.json'
        if not os.path.exists(prefix_path) or os.path.getsize(prefix_path) == 0:
            with open(prefix_path, 'w') as f:
                json.dump({}, f)
        
        # Ensure triggers.json has valid content
        trigger_path = 'data/triggers.json'
        if not os.path.exists(trigger_path) or os.path.getsize(trigger_path) == 0:
            with open(trigger_path, 'w') as f:
                json.dump({}, f)
    
    def load_prefixes(self):
        """Load server prefixes from the database"""
        self.prefixes = self.db_manager.get_all_prefixes()
    
    async def save_prefixes(self):
        """Save server prefixes to the database"""
        # This method is kept for backward compatibility
        # Prefixes are now directly managed by the DatabaseManager
        pass
    
    async def update_prefix(self, guild_id: int, prefix: str):
        """Update the prefix for a guild"""
        self.prefixes[str(guild_id)] = prefix
        self.db_manager.set_prefix(guild_id, prefix)
    
    async def setup_hook(self):
        """Setup hook that runs before the bot starts"""
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py') and not filename.startswith('__'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    logger.info(f"Loaded extension: {filename[:-3]}")
                except Exception as e:
                    logger.error(f"Failed to load extension {filename[:-3]}: {str(e)}")
    
    async def on_ready(self):
        """Event that triggers when the bot is ready"""
        logger.info(f'Logged in as {self.user.name} (ID: {self.user.id})')
        logger.info(f'Using discord.py version {discord.__version__}')
        logger.info(f'Owner ID: {self.owner_id}')
        
        # Set bot activity
        await self.change_presence(activity=discord.Activity(
            type=discord.ActivityType.listening, 
            name=f"{self.default_prefix}bothelp"
        ))
    
    async def on_guild_join(self, guild):
        """Event that triggers when the bot joins a guild"""
        logger.info(f"Joined new guild: {guild.name} (ID: {guild.id})")
    
    async def on_guild_remove(self, guild):
        """Event that triggers when the bot leaves a guild"""
        logger.info(f"Left guild: {guild.name} (ID: {guild.id})")
        
        # Remove guild prefix if it exists
        if str(guild.id) in self.prefixes:
            self.db_manager.delete_prefix(guild.id)
            del self.prefixes[str(guild.id)]
    
    async def on_command_error(self, ctx, error):
        """Global error handler for commands"""
        if isinstance(error, commands.CommandNotFound):
            logger.debug(f"Command not found: {ctx.message.content}")
            return  # Ignore command not found errors
        
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send(f"Missing required argument: {error.param.name}")
            return
        
        if isinstance(error, commands.BadArgument):
            await ctx.send(f"Bad argument: {str(error)}")
            return
        
        if isinstance(error, commands.CheckFailure):
            await ctx.send("You don't have permission to use this command.")
            return
        
        # Log other errors
        logger.error(f"Command error in {ctx.command}: {str(error)}")
        await ctx.send(f"An error occurred: {str(error)}")
    
    async def on_message(self, message):
        # Process commands first
        await self.process_commands(message)
        
        # We need to check if this is a trigger after processing commands
        # to avoid executing bot commands inadvertently
        # This will be handled by the TriggerCommands cog's listener

async def main():
    # Create bot instance
    bot = TriggerBot()
    
    # Get token from config
    token = bot.config.get('token')
    
    if token == "YOUR_BOT_TOKEN_HERE":
        logger.error("Please set your bot token in config.json")
        sys.exit(1)
    
    try:
        # Start the bot
        logger.info("Starting bot...")
        async with bot:
            await bot.start(token)
    except discord.errors.LoginFailure:
        logger.error("Invalid token. Please check your token in config.json")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
