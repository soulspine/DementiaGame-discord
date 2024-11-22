import discord
import discord.ext.commands as commands
import discord.ui as ui
from discord import app_commands
from modal import *
from game import *
import error
import language
import asyncio
import datetime

if __name__ != "__main__": exit()

token:str = None
with open('TOKEN', 'r', encoding="utf-8") as file:
    token = file.read().strip()

client = commands.Bot(intents=discord.Intents.all(), command_prefix="//", sync_commands=True)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}.')
    await client.tree.sync()

@app_commands.describe(language_code=f"Valid codes: {' | '.join([f'{key}' for key in language.getCodes().keys()])}")
@client.tree.command(name="host", description="Host a game.")
async def host(interaction:discord.Interaction, language_code:str=config.Language.defaultCode):
    print(f"host accessed by {interaction.user.name}")

    if language_code not in language.getCodes().keys():
        await interaction.response.send_message(content=f"Invalid language code. Valid codes: {' | '.join([f"{key}" for key in language.getCodes().keys()])}", ephemeral=True)
        return
    
    initialUserId = interaction.user.id

    langLobby = language.getModule("lobby", language_code)
    langGamemodes = language.getModule("gamemodes", language_code)

    modeSelectEmbed = discord.Embed(color=discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    modeSelectView = ui.View()

    modeSelect = ui.Select(placeholder=langLobby["modeSelect"], custom_id="modeSelect")
    async def modeSelect_callback(interaction:discord.Interaction):
        if interaction.user.id != initialUserId: await error.notHost(interaction, language_code); return
        if (interaction.user.voice is None): await error.noVoice(interaction, language_code); return
        elif (interaction.user.voice.channel.id in GAMES):
            if GAMES[interaction.user.voice.channel.id].lobbyStatus == "playing" or GAMES[interaction.user.voice.channel.id].hostId in [member.id for member in interaction.user.voice.channel.members]:
                await error.gameOngoing(interaction, language_code); return
        
        gameId:int = interaction.user.voice.channel.id
        GAMES[gameId] = Game(client, hostId=interaction.user.id, id=gameId, gamemode=interaction.data["values"][0], languageCode=language_code, vc=interaction.user.voice.channel, msg=interaction.message)

        embed = GAMES[gameId].lobbyEmbed()
        view = GAMES[gameId].lobbyView()

        await interaction.response.edit_message(embed=embed, view=view)

    modeSelect.callback = modeSelect_callback

    for codename in langGamemodes:
        display:str = langGamemodes[codename]["display"]
        description:str = langGamemodes[codename]["description"]["long"]
        modeSelectEmbed.add_field(name=display, value=description, inline=False)
        modeSelect.add_option(label=display, value=codename)

    modeSelectView.add_item(modeSelect)

    await interaction.response.send_message(embed=modeSelectEmbed, view=modeSelectView)

@client.tree.command(name="info", description="Info about the game.")
async def info(interaction:discord.Interaction):
    print(f"info accessed by {interaction.user.name}")

    initialUserId = interaction.user.id
    langCodes = language.getCodes()

    def getEmbed(languageCode:str):
        langInfo = language.getModule("info", languageCode)
        embed = discord.Embed(title=langInfo["title"], description=langInfo["description"], color=discord.Color.blurple())
        for field in langInfo["fields"]: embed.add_field(name=field["name"], value=field["value"], inline=False)
        return embed

    def getView(languageCode:str):
        langInfo = language.getModule("info", languageCode)
        view = ui.View()

        languageSelect = ui.Select(placeholder=langInfo["language"], custom_id="languageSelect")
        for code in langCodes[languageCode]: languageSelect.add_option(label=langCodes[languageCode][code], value=code)
        async def languageSelect_callback(interaction:discord.Interaction):
            if interaction.user.id != initialUserId: await interaction.response.defer(); return
            languageCode = interaction.data["values"][0]
            await interaction.response.edit_message(view=getView(languageCode), embed=getEmbed(languageCode))

        languageSelect.callback = languageSelect_callback
        view.add_item(languageSelect)
        return view

    await interaction.response.send_message(embed=getEmbed(config.Language.defaultCode), view=getView(config.Language.defaultCode))

async def backgroundCleaner():
    await client.wait_until_ready()
    sleepTime = config.BackgroundCleaner.sleepTime  # seconds
    while not client.is_closed():
        for gameId, game in list(GAMES.items()):
            if game.timeout is None: continue
            elif game.timeout.timestamp()-datetime.datetime.now().timestamp() < sleepTime:
                await game.cancel("timeout")
                print(f"Game {gameId} timed out.")
        await asyncio.sleep(sleepTime)

async def main():
    asyncio.create_task(backgroundCleaner())
    await client.start(token)

asyncio.run(main())