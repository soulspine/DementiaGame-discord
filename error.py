import discord

error_language = {
    "noVoice": {
        "pl": "Musisz być na kanale głosowym, żeby to zrobić.",
        "en": "You have to be in a voice channel to do that."
    },
    "wrongVoice": {
        "pl": "Musisz być na tym samym kanale głosowym co gra.",
        "en": "You must be in the same voice channel as the game."
    },
    "gameOngoing": {
        "pl": "Na tym kanale głosowym jest już aktywna gra.",
        "en": "There is already a game ongoing in this voice channel."
    },
    "noGame": {
        "pl": "Na tym kanale głosowym nie ma aktywnej gry.",
        "en": "There is no game ongoing in this voice channel right now."
    },
    "notHost": {
        "pl": "Tylko host może to zrobić.",
        "en": "Only the host can do that."
    }
}

async def noVoice(interaction: discord.Interaction, language: str):
    return await interaction.response.send_message(error_language["noVoice"][language], ephemeral=True)

async def wrongVoice(interaction: discord.Interaction, language: str):
    return await interaction.response.send_message(error_language["wrongVoice"][language], ephemeral=True)

async def gameOngoing(interaction: discord.Interaction, language: str):
    return await interaction.response.send_message(error_language["gameOngoing"][language], ephemeral=True)

async def noGame(interaction: discord.Interaction, language: str):
    return await interaction.response.send_message(error_language["noGame"][language], ephemeral=True)

async def notHost(interaction: discord.Interaction, language: str):
    return await interaction.response.send_message(error_language["notHost"][language], ephemeral=True)
