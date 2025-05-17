import json
import os
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger('TriggerBot.DBManager')

class DatabaseManager:
    """A simple JSON-based database manager for the bot."""
    
    def __init__(self, bot):
        self.bot = bot
        self.data_dir = 'data'
        
        # Create data directory if it doesn't exist
        os.makedirs(self.data_dir, exist_ok=True)
    
    async def get_triggers(self, guild_id: str) -> Dict[str, Any]:
        """
        Get all triggers for a guild
        
        Parameters:
        -----------
        guild_id: str
            The ID of the guild
            
        Returns:
        --------
        Dict[str, Any]
            A dictionary of triggers
        """
        if guild_id in self.bot.triggers:
            return self.bot.triggers[guild_id]
        return {}
    
    async def add_trigger(self, guild_id: str, name: str, response: str, creator_id: int) -> bool:
        """
        Add a new trigger
        
        Parameters:
        -----------
        guild_id: str
            The ID of the guild
        name: str
            The name of the trigger
        response: str
            The response text or URL
        creator_id: int
            The ID of the user who created the trigger
            
        Returns:
        --------
        bool
            True if the trigger was added successfully, False otherwise
        """
        try:
            if guild_id not in self.bot.triggers:
                self.bot.triggers[guild_id] = {}
            
            # Check if trigger already exists
            if name.lower() in [t.lower() for t in self.bot.triggers[guild_id]]:
                return False
            
            # Add the trigger
            self.bot.triggers[guild_id][name] = {
                "response": response,
                "creator_id": creator_id,
                "created_at": self.bot.utils.utcnow().isoformat()
            }
            
            # Save triggers
            self.bot.save_triggers()
            return True
        
        except Exception as e:
            logger.error(f"Error adding trigger: {e}")
            return False
    
    async def remove_trigger(self, guild_id: str, name: str) -> bool:
        """
        Remove a trigger
        
        Parameters:
        -----------
        guild_id: str
            The ID of the guild
        name: str
            The name of the trigger
            
        Returns:
        --------
        bool
            True if the trigger was removed successfully, False otherwise
        """
        try:
            if guild_id in self.bot.triggers and name in self.bot.triggers[guild_id]:
                del self.bot.triggers[guild_id][name]
                self.bot.save_triggers()
                return True
            return False
        
        except Exception as e:
            logger.error(f"Error removing trigger: {e}")
            return False
    
    async def get_prefix(self, guild_id: str) -> str:
        """
        Get the prefix for a guild
        
        Parameters:
        -----------
        guild_id: str
            The ID of the guild
            
        Returns:
        --------
        str
            The prefix for the guild
        """
        return self.bot.server_prefixes.get(guild_id, self.bot.config['default_prefix'])
    
    async def set_prefix(self, guild_id: str, prefix: str) -> bool:
        """
        Set the prefix for a guild
        
        Parameters:
        -----------
        guild_id: str
            The ID of the guild
        prefix: str
            The new prefix
            
        Returns:
        --------
        bool
            True if the prefix was set successfully, False otherwise
        """
        try:
            self.bot.server_prefixes[guild_id] = prefix
            self.bot.save_prefixes()
            return True
        except Exception as e:
            logger.error(f"Error setting prefix: {e}")
            return False
