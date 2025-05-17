import discord
from discord.ext import commands
import asyncio
import json
import os
import logging
from typing import Dict, List, Optional, Union

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('TriggerBot')

# Ensure data directory exists
os.makedirs('data', exist_ok=True)

# Load configuration
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
except FileNotFoundError:
    logger.error("Config file not found. Please create a config.json file.")
    exit(1)
except json.JSONDecodeError:
    logger.error("Invalid JSON in config file.")
    exit(1)

# Initialize prefixes dictionary
server_prefixes = {}
try:
    if os.path.exists('data/prefixes.json') and os.path.getsize('data/prefixes.json') > 0:
        with open('data/prefixes.json', 'r') as f:
            server_prefixes = json.load(f)
    else:
        # Create empty prefixes file if it doesn't exist or is empty
        with open('data/prefixes.json', 'w') as f:
            json.dump({}, f, indent=4)
        logger.info("Created empty prefixes file")
except Exception as e:
    logger.error(f"Error loading prefixes: {e}")
    server_prefixes = {}
    # Create empty prefixes file
    with open('data/prefixes.json', 'w') as f:
        json.dump({}, f, indent=4)
    logger.info("Created new empty prefixes file")


def get_prefix(bot, message):
    if not message.guild:
        return commands.when_mentioned_or(config['default_prefix'])(bot, message)
    
    guild_id = str(message.guild.id)
    prefix = server_prefixes.get(guild_id, config['default_prefix'])
    return commands.when_mentioned_or(prefix)(bot, message)


class TriggerBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            description=config.get('description', 'A Discord bot with trigger commands'),
            case_insensitive=True
        )
        
        self.config = config
        self.server_prefixes = server_prefixes
        self.owner_ids = set(config.get('owner_ids', []))
        
        # Initialize triggers
        self.triggers = {}
        self.load_triggers()
        
    async def setup_hook(self):
        """Sets up the bot's cogs and syncs commands."""
        logger.info("Loading cogs...")
        await self.load_cogs()
        
        logger.info("Syncing slash commands...")
        try:
            # Sync globally
            synced = await self.tree.sync()
            logger.info(f"Synced {len(synced)} command(s) globally")
            
            # You can also sync to specific guilds if needed
            if 'test_guild_id' in self.config:
                test_guild = discord.Object(id=self.config['test_guild_id'])
                self.tree.copy_global_to(guild=test_guild)
                guild_synced = await self.tree.sync(guild=test_guild)
                logger.info(f"Synced {len(guild_synced)} command(s) to test guild")
        except Exception as e:
            logger.error(f"Failed to sync commands: {e}")
        
    async def load_cogs(self):
        """Load all cogs from the cogs directory."""
        if not os.path.exists("./cogs"):
            os.makedirs("./cogs", exist_ok=True)
            logger.info("Created cogs directory")
            
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and not filename.startswith("_"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    logger.info(f"Loaded cog: {filename}")
                except Exception as e:
                    logger.error(f"Failed to load cog {filename}: {e}")
    
    def load_triggers(self):
        """Load triggers from the JSON file."""
        try:
            triggers_file = 'data/triggers.json'
            if os.path.exists(triggers_file) and os.path.getsize(triggers_file) > 0:
                with open(triggers_file, 'r') as f:
                    self.triggers = json.load(f)
                logger.info(f"Loaded triggers for {len(self.triggers)} guild(s)")
            else:
                self.triggers = {}
                self.save_triggers()
                logger.info("Created empty triggers file")
        except json.JSONDecodeError as e:
            logger.error(f"Error parsing triggers file: {e}")
            self.triggers = {}
            self.save_triggers()
            logger.info("Created new empty triggers file due to parsing error")
        except Exception as e:
            logger.error(f"Error loading triggers: {e}")
            self.triggers = {}
    
    def save_triggers(self):
        """Save triggers to the JSON file."""
        try:
            with open('data/triggers.json', 'w') as f:
                json.dump(self.triggers, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving triggers: {e}")
    
    def save_prefixes(self):
        """Save server prefixes to the JSON file."""
        try:
            with open('data/prefixes.json', 'w') as f:
                json.dump(self.server_prefixes, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving prefixes: {e}")
    
    async def on_ready(self):
        """Called when the bot is ready."""
        logger.info(f"Logged in as {self.user.name} | {self.user.id}")
        logger.info(f"Default prefix: {config['default_prefix']}")
        await self.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"for triggers | {config['default_prefix']}help"
            )
        )
    
    async def on_message(self, message):
        """Handle messages and check for triggers."""
        if message.author.bot:
            return
        
        # Process commands first
        await self.process_commands(message)
        
        # Then check for triggers
        if message.guild:
            guild_id = str(message.guild.id)
            if guild_id in self.triggers:
                content = message.content.lower()
                for trigger_name, trigger_data in self.triggers[guild_id].items():
                    # Check if the trigger is in the message
                    if trigger_name.lower() in content:
                        # Send the response
                        response = trigger_data["response"]
                        if response.startswith("http") and any(response.endswith(ext) for ext in [".png", ".jpg", ".jpeg", ".gif"]):
                            # If it's an image URL, send it as an embed
                            embed = discord.Embed()
                            embed.set_image(url=response)
                            await message.channel.send(embed=embed)
                        else:
                            # Otherwise send as plain text
                            await message.channel.send(response)
                        break
    
    async def on_guild_join(self, guild):
        """Called when the bot joins a guild."""
        logger.info(f"Joined guild: {guild.name} ({guild.id})")
        
        # Create default entry for this guild
        guild_id = str(guild.id)
        if guild_id not in self.server_prefixes:
            self.server_prefixes[guild_id] = self.config['default_prefix']
            self.save_prefixes()
        
        # Sync commands to this guild
        try:
            guild_obj = discord.Object(id=guild.id)
            self.tree.copy_global_to(guild=guild_obj)
            await self.tree.sync(guild=guild_obj)
            logger.info(f"Synced commands to new guild: {guild.name}")
        except Exception as e:
            logger.error(f"Failed to sync commands to new guild: {e}")
        
    async def on_guild_remove(self, guild):
        """Called when the bot leaves or is removed from a guild."""
        logger.info(f"Left guild: {guild.name} ({guild.id})")
        
        # Clean up guild data if necessary
        guild_id = str(guild.id)
        if guild_id in self.triggers:
            del self.triggers[guild_id]
            self.save_triggers()
            
        if guild_id in self.server_prefixes:
            del self.server_prefixes[guild_id]
            self.save_prefixes()
    
    def is_owner(self, user):
        """Check if a user is the bot owner."""
        if user.id in self.owner_ids:
            return True
        return False


async def main():
    """Main entry point for the bot."""
    bot = TriggerBot()
    async with bot:
        try:
            logger.info("Starting bot...")
            await bot.start(config['token'])
        except discord.LoginFailure:
            logger.error("Invalid token. Please check your config.json file.")
        except Exception as e:
            logger.error(f"An error occurred while running the bot: {e}")


if __name__ == "__main__":
    asyncio.run(main())
