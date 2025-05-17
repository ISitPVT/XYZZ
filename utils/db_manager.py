import json
import os
import logging
from typing import Dict, List, Optional, Any, Union

logger = logging.getLogger('db_manager')

class DatabaseManager:
    """Manages the database for the trigger bot"""
    
    def __init__(self, trigger_path: str = 'data/triggers.json', prefix_path: str = 'data/prefixes.json'):
        self.trigger_path = trigger_path
        self.prefix_path = prefix_path
        
        # Ensure the directories and files exist
        self._initialize_data_files()
    
    def _initialize_data_files(self):
        """Initialize necessary data files and directories"""
        # Create directories if they don't exist
        os.makedirs('data', exist_ok=True)
        
        # Initialize triggers.json if it doesn't exist
        if not os.path.exists(self.trigger_path):
            with open(self.trigger_path, 'w') as f:
                json.dump({}, f, indent=2)
                logger.info(f"Created empty {self.trigger_path} file")
        
        # Initialize prefixes.json if it doesn't exist
        if not os.path.exists(self.prefix_path):
            with open(self.prefix_path, 'w') as f:
                json.dump({}, f, indent=2)
                logger.info(f"Created empty {self.prefix_path} file")
    
    def _load_triggers(self) -> Dict[str, Dict[str, Any]]:
        """Load triggers from the database"""
        try:
            with open(self.trigger_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading triggers: {str(e)}")
            return {}
    
    def _save_triggers(self, triggers: Dict[str, Dict[str, Any]]) -> bool:
        """Save triggers to the database"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.trigger_path), exist_ok=True)
            
            with open(self.trigger_path, 'w') as f:
                json.dump(triggers, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving triggers: {str(e)}")
            return False
    
    def _load_prefixes(self) -> Dict[str, str]:
        """Load server prefixes from the database"""
        try:
            with open(self.prefix_path, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading prefixes: {str(e)}")
            return {}
    
    def _save_prefixes(self, prefixes: Dict[str, str]) -> bool:
        """Save server prefixes to the database"""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.prefix_path), exist_ok=True)
            
            with open(self.prefix_path, 'w') as f:
                json.dump(prefixes, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Error saving prefixes: {str(e)}")
            return False
    
    # ------ Trigger Management Methods ------
    
    def trigger_exists(self, name: str) -> bool:
        """Check if a trigger exists"""
        triggers = self._load_triggers()
        return name in triggers
    
    def add_trigger(self, name: str, data: Dict[str, Any]) -> bool:
        """Add a new trigger to the database"""
        triggers = self._load_triggers()
        
        # Check if trigger already exists
        if name in triggers:
            return False
        
        # Add the trigger
        triggers[name] = data
        
        # Save the updated triggers
        return self._save_triggers(triggers)
    
    def delete_trigger(self, name: str) -> bool:
        """Delete a trigger from the database"""
        triggers = self._load_triggers()
        
        # Check if trigger exists
        if name not in triggers:
            return False
        
        # Delete the trigger
        del triggers[name]
        
        # Save the updated triggers
        return self._save_triggers(triggers)
    
    def update_trigger(self, name: str, data: Dict[str, Any]) -> bool:
        """Update an existing trigger in the database"""
        triggers = self._load_triggers()
        
        # Check if trigger exists
        if name not in triggers:
            return False
        
        # Update the trigger
        triggers[name].update(data)
        
        # Save the updated triggers
        return self._save_triggers(triggers)
    
    def get_trigger(self, name: str) -> Optional[Dict[str, Any]]:
        """Get a specific trigger from the database"""
        triggers = self._load_triggers()
        return triggers.get(name)
    
    def get_all_triggers(self) -> Dict[str, Dict[str, Any]]:
        """Get all triggers from the database"""
        return self._load_triggers()
    
    def get_triggers_by_creator(self, creator_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all triggers created by a specific user"""
        triggers = self._load_triggers()
        return {name: data for name, data in triggers.items() if data.get('creator_id') == creator_id}
    
    def get_triggers_by_guild(self, guild_id: int) -> Dict[str, Dict[str, Any]]:
        """Get all triggers created in a specific guild"""
        triggers = self._load_triggers()
        return {name: data for name, data in triggers.items() if data.get('guild_id') == guild_id}
    
    # ------ Server Prefix Methods ------
    
    def get_prefix(self, guild_id: Union[int, str], default_prefix: str = '!') -> str:
        """Get the prefix for a specific guild"""
        prefixes = self._load_prefixes()
        return prefixes.get(str(guild_id), default_prefix)
    
    def set_prefix(self, guild_id: Union[int, str], prefix: str) -> bool:
        """Set the prefix for a specific guild"""
        prefixes = self._load_prefixes()
        
        # Update the prefix
        prefixes[str(guild_id)] = prefix
        
        # Save the updated prefixes
        return self._save_prefixes(prefixes)
    
    def delete_prefix(self, guild_id: Union[int, str]) -> bool:
        """Delete the prefix for a specific guild (resets to default)"""
        prefixes = self._load_prefixes()
        
        # Check if prefix exists
        if str(guild_id) not in prefixes:
            return False
        
        # Delete the prefix
        del prefixes[str(guild_id)]
        
        # Save the updated prefixes
        return self._save_prefixes(prefixes)
    
    def get_all_prefixes(self) -> Dict[str, str]:
        """Get all server prefixes"""
        return self._load_prefixes()
