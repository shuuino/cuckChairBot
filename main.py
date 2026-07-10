# NOTE: variables that only depend on one 'module' can be found at the beginning of that module (yuri commands etc) to prevent clutter in the main file.

import discord

from bot_instance import bot, ACTIVITY, TOKEN

import modules.yuri
import modules.say
import modules.reactions

@bot.event
async def on_ready():
    await bot.change_presence(status=discord.Status.online, activity=discord.Activity(name=ACTIVITY, type=discord.ActivityType.watching))
    await bot.tree.sync()
    print(f'Servers: {bot.guilds}') #lowk prints out as some ugly bullshit but its good enough for me not to be bothered to fix it
    print(f'We have logged in as {bot.user}')

bot.run(TOKEN)
