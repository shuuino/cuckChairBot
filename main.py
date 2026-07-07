# NOTE: variables that only depend on one 'module' can be found at the beginning of that module (yuri commands etc) to prevent clutter at the start.
# will move modules to local files once i feel like it

import discord
from discord import app_commands
from discord.ext import commands
import re #regex
import random
from datetime import date
import os
import csv
import asyncio

TOKEN = "YOUR_TOKEN_HERE"
SERVER_ID = YOUR_SERVER_ID_HERE
SERVER_LOCK = True # since the bot is only meant to work in chaircord, we got a server lock so if it tries to run in other servers we don't allow it. Disable if you want for your own selfhost
ACTIVITY = "women kissing"

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=ACTIVITY, type=discord.ActivityType.watching))
    await bot.tree.sync()
    print(f'Servers: {bot.guilds}') #lowk prints out as some ugly bullshit but its good enough for me not to be bothered to fix it
    print(f'We have logged in as {bot.user}')

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





# -------------------------------------------
# yuri db
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
    if not server_lock_interaction(interaction):
        return
    if not (interaction.user.guild_permissions.manage_messages or interaction.user.guild_permissions.administrator): #"Cannot access attribute 'guild_permissions' for class 'User' Attribute 'guild_permissions' is unknown" shhhh little pylance don't you worry i definitely know what i'm doing
        await interaction.response.send_message(f"You don't have permission to use this command!", ephemeral=True)
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





# -------------------------------------------
# woof & nya regex + message match dictionary
wanMatch = [
    r'^(w+o{2,}f+)$',
    r'^(bark)+$',
    r'^(ba+u+)$',
    r'^(a+r+f+)$',
    r'^(w?r+u+f+)$',
    r'^(wan)+\b',
    r'^(a(w?)ru?f+)$',
    r'^(b(w+)o{2,}f+)$',
    r'^(w(r+)u+f+)$',
]
nyaMatch = [ #nyan
    r'^(m(r{2,})p)$',
    r'^((m+)(e+)(o+)(w+))$',
    r'^(p(u+)(r{2,}))$',
    r'^(m(e+)(w+))$',
    r'^(n(y+)(a+)+)$',
    r'^((ps+))$',
    r'^(m(i+)(a+)(u+))$',
    r'^(m(y+)(a+)(u+))$',
    r'^(m(a+)(u+))$',
    r'^(m(a+)(o+))$',
]
wanCompiled = [re.compile(p) for p in wanMatch]
nyaCompiled = [re.compile(p) for p in nyaMatch]
woofList = ['woof', 'woooof', 'wooooof', 'woooooof', 'bow', 'bawoof', 'bawooof', 'bawooooof', 'bawoooooof', 'woofwoof', 'wwoof', 'wwwoof', 'wwwwoof']
nyaList = ['mrrp', 'mrrrp', 'mrrrrp', 'mrrrrrp', 'meow', 'nya', 'nyaa', 'nyaaa', 'mrow', 'mrrow', 'mrrrow', 'mrrrrow', 'mew', 'purr', 'purrr', 'purrrr', 'purrrrr', 'miau', 'miauu', 'myau', 'myauu']; 
kaomoji = [' :3', ' >w<', ' >_<', ' >_<;;', ' >.<', ' (๑╹ω╹๑ )', ' ^^', '>.<<~', '<3', '(=^･ω･^=)'];

@bot.event
async def on_message(message):
    if not server_lock_message(message):
        return
    
    if message.author.bot:
        return
    
    content = message.content.lower()
    # cuck, chud, yurislopper, beer, chair, true, false
    if "cuck" in content:
        await message.add_reaction("🪑") # HARDCODED EMOJIS YAYYY!!!
    if "chud" in content:
        await message.add_reaction("<:steamtrue:1501438785269796944>")
    if "yurislopper" in content:
        await message.channel.send("https://cdn.discordapp.com/attachments/1362825086335455397/1500132347402780692/ezgif-1c652d41a455ed70.gif?ex=6a4d041e&is=6a4bb29e&hm=3862dbccd7942031468dbc15d029e0cbe89dc47216ced1b7a87486af8d5b07a0&")
    if "beer" == content:
        await message.channel.send("BEER!")
    if "chair" == content:
        await message.channel.send("table")
    if "amazing" == content:
        await message.channel.send("Umazing!")
    if "true" == content:
        await message.add_reaction("<:steamtrue:1501438785269796944>")
    if "false" == content:
        await message.add_reaction("<:steamfalse:1515767607909941378>")

    # woofMatch & nyaMatch
    if any(rx.search(content) is not None for rx in wanCompiled):
        await message.channel.send(f'{random.choice(woofList)} {random.choice(kaomoji)}')
    if any(rx.search(content) is not None for rx in nyaCompiled):
        await message.channel.send(f'{random.choice(nyaList)} {random.choice(kaomoji)}')

    #yuri db
    if (message.channel.id == YURI_SFW_CHANNEL) & (message.attachments != []):
        for e in message.attachments:
            await yuri_db_index(YURI_SFW_DB, e.url)

    if (message.channel.id == YURI_NSFW_CHANNEL) & (message.attachments != []):
        for e in message.attachments:
            await yuri_db_index(YURI_NSFW_DB, e.url)

    await bot.process_commands(message)









bot.run(TOKEN)