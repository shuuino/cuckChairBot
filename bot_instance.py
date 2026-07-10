import discord
from discord.ext import commands

TOKEN = "YOUR_TOKEN_HERE"
SERVER_ID = YOUR_SERVER_ID_HERE
SERVER_LOCK = True # since the bot is only meant to work in chaircord, we got a server lock so if it tries to run in other servers we don't allow it. Disable if you want for your own selfhost
ACTIVITY = "women kissing"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

def server_lock_guild_id(guild_id: int | None) -> bool:
    """Return True if the guild is allowed."""
    if not SERVER_LOCK:
        return True
    return guild_id == SERVER_ID

def server_lock_interaction(interaction: discord.Interaction) -> bool:
    """Safe server lock for slash commands / app_commands."""
    return server_lock_guild_id(interaction.guild.id if interaction.guild else None)

def server_lock_message(message: discord.Message) -> bool:
    """Safe server lock for on_message."""
    return server_lock_guild_id(message.guild.id if message.guild else None)

async def mod_lock_interaction(interaction: discord.Interaction) -> bool:
    """lock for slash commands for moderator only commands."""
    if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator): #"Cannot access attribute 'guild_permissions' for class 'User' Attribute 'guild_permissions' is unknown" shhhh little pylance don't you worry i definitely know what i'm doing
        await interaction.response.send_message(f"You don't have permission to use this command!", ephemeral=True)
        return False
    return True
