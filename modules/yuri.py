import os
import random
import asyncio

import discord
from discord import app_commands

from bot_instance import bot, server_lock_interaction, server_lock_message, mod_lock_interaction

# -------------------------------------------
# yuri db. Note that some code for this is also contained in reactions.py due to it being an on_message event.
YURI_SFW_DB = "yuri-db.csv"
YURI_NSFW_DB = "yuri-nsfw-db.csv"
YURI_SFW_CHANNEL = 1495700579568062475
YURI_NSFW_CHANNEL = 1495700579807399982
yuri_db_lock = asyncio.Lock()
async def yuri_db_index(file, content=""):
    """returns a random line if content is empty. Otherwise, adds content to file."""
    async with yuri_db_lock:
        content = content or ""
        if content.strip() == "":
            with open(file, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f]
            if not lines:
                return ""
            return random.choice(lines)
        if os.path.exists(file):
            with open(file, "a", encoding="utf-8") as f:
                f.write(f"{content}\n")
        else:
            with open(file, "w", encoding="utf-8") as f:
                f.write(f"{content}\n")
        return None

@bot.command(name="yuri")
async def yuri_prefix(ctx):
    """!yuri command. same as slash command"""
    if not server_lock_message(ctx.message):
        return
    if ctx.channel.nsfw:
        await ctx.reply(await yuri_db_index(YURI_NSFW_DB))
    else:
        await ctx.reply(await yuri_db_index(YURI_SFW_DB))

@bot.tree.command(name="yuri", description="Sends a random image from the yuri channel.")
async def yuri_slash(interaction: discord.Interaction):
    if not server_lock_interaction(interaction):
        return
    if interaction.channel.nsfw:
        await interaction.response.send_message(await yuri_db_index(YURI_NSFW_DB))
    else:
        await interaction.response.send_message(await yuri_db_index(YURI_SFW_DB))

@bot.tree.command(name="yuri_remove", description="Remove a link from the yuri database.")
@app_commands.describe(category="sfw or nsfw", link="The exact link to remove")
@app_commands.choices(category=[
    app_commands.Choice(name="sfw", value="sfw"),
    app_commands.Choice(name="nsfw", value="nsfw"),
])
async def yuri_remove_slash(interaction: discord.Interaction, category: app_commands.Choice[str], link: str):
    """checks if a user has permission to use command (delete messages perm or admin). Then removes line"""
    if not (server_lock_interaction(interaction) & await mod_lock_interaction(interaction)):
        return
    
    file = YURI_SFW_DB if category.value == "sfw" else YURI_NSFW_DB

    async with yuri_db_lock:
        if not os.path.exists(file):
            await interaction.response.send_message(f"`{file}` doesn't exist.", ephemeral=True)
            return

        with open(file, "r", encoding="utf-8") as f:
            lines = [line.rstrip("\n") for line in f]

        if link not in lines:
            await interaction.response.send_message("Link not found in the database.", ephemeral=True)
            return

        lines.remove(link)

        with open(file, "w", encoding="utf-8") as f:
            for l in lines:
                f.write(f"{l}\n")

    await interaction.response.send_message(f"Removed link from `{category.value}` database.", ephemeral=True)
