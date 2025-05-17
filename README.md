# Discord.py Trigger Bot - README

## Overview
This is a fully-featured Discord bot that provides trigger management functionality. The bot supports both traditional prefix commands and modern slash commands, with robust permission handling and pagination for lists.

## Features
- **Trigger Management:**
  - Create triggers with optional attachments
  - Delete triggers (owner only)
  - Get detailed information about triggers
  - List all triggers with pagination
- **Server Configuration:**
  - Customizable server prefixes
  - Permission-based command access
- **Command Types:**
  - Both traditional prefix commands and slash commands

## Requirements
- Python 3.8 or higher
- discord.py 2.0 or higher
- aiohttp

## Installation

1. Clone this repository or download the files
2. Install the required dependencies:
```bash
pip install discord.py aiohttp
```
3. Edit the `config.json` file with your bot token and owner ID

## Configuration
Edit the `config.json` file:
```json
{
  "token": "YOUR_BOT_TOKEN_HERE",
  "prefix": "!",
  "owner_id": 123456789
}
```
- `token`: Your Discord bot token from the [Discord Developer Portal](https://discord.com/developers/applications)
- `prefix`: The default command prefix (can be changed per server)
- `owner_id`: Your Discord user ID (for owner-only commands)

## File Structure
```
discord_trigger_bot/
├── config.json
├── main.py
├── cogs/
│   ├── __init__.py
│   ├── trigger_commands.py
│   └── owner_commands.py
├── utils/
│   ├── __init__.py
│   └── db_manager.py
└── data/
    ├── triggers.json
    └── prefixes.json
```

## Commands

### Trigger Commands
- **!trigger create [name] [attachment]** - Create a new trigger with optional attachment
  - Requires: Bot Owner or Manage Server permission
- **!trigger delete [name]** - Delete a trigger (shows list if no name provided)
  - Requires: Bot Owner
- **!trigger get [name]** - Get detailed information about a trigger
  - Available to everyone
- **!trigger list** - Show a paginated list of all triggers
  - Available to everyone

### Server Commands
- **!serverprefix** - Show the current server prefix
  - Available to everyone
- **!serverprefix [new_prefix]** - Change the server prefix
  - Requires: Bot Owner or Manage Server permission
- **!help** - Show help information
  - Available to everyone

## Running the Bot
Execute the main.py file:
```bash
python main.py
```

## Permissions
- Owner-only commands can only be used by the Discord user with the ID specified in config.json
- Server management commands require the "Manage Server" permission
- General commands are available to all users

## Notes
- The bot automatically creates necessary directories and files on first run
- Trigger data and server prefixes are stored in JSON files
- Attachments are referenced by URL (Discord CDN links)
