import re #regex
import random

import discord

from bot_instance import bot, server_lock_message
from modules.yuri import yuri_db_index, YURI_SFW_DB, YURI_NSFW_DB, YURI_SFW_CHANNEL, YURI_NSFW_CHANNEL

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
