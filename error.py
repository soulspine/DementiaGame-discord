import discord
import language

async def send(interaction: discord.Interaction, error: str, languageCode: str):
    return await interaction.response.send_message(str(language.getModule("errors", languageCode)[error]), ephemeral=True)

async def noVoice(interaction: discord.Interaction, languageCode: str):
    return await send(interaction, "noVoice", languageCode)

async def wrongVoice(interaction: discord.Interaction, languageCode: str):
    return await send(interaction, "wrongVoice", languageCode)

async def gameOngoing(interaction: discord.Interaction, languageCode: str):
    return await send(interaction, "gameOngoing", languageCode)

async def noGame(interaction: discord.Interaction, languageCode: str):
    return await send(interaction, "noGame", languageCode)

async def notHost(interaction: discord.Interaction, languageCode: str):
    return await send(interaction, "notHost", languageCode)
