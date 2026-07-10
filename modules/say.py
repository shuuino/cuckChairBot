import discord
from discord import app_commands

from bot_instance import bot, server_lock_interaction, mod_lock_interaction

# -------------------------------------------
#say command
@bot.tree.command(name="say", description="say shit fr ong no cap skibidi rizz") # i hate myself
@app_commands.describe(text="the shit to say, smartass", reply="optional, link of message to reply to")
async def say(interaction: discord.Interaction, text: str, reply: str | None = None):
    if not (server_lock_interaction(interaction) & await mod_lock_interaction(interaction)):
        return
    
    if reply:
        parts = reply.split("/")
        channel_id = int(parts[-2])
        message_id = int(parts[-1])

        channel = interaction.guild.get_channel(channel_id)
        if channel is None or not isinstance(channel, discord.abc.Messageable):
            await interaction.response.send_message("Invalid reply link (channel not found).", ephemeral=True)
            return

        target_msg = await channel.fetch_message(message_id)

        await interaction.response.send_message("sent", ephemeral=True)
        await channel.send(text, reference=target_msg)
    else:
        await interaction.channel.send(text)
    await interaction.response.send_message("sent", ephemeral=True)
