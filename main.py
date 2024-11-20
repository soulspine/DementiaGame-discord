import discord
import discord.ext.commands as commands
import discord.ui as ui
from modal import *
from game import *
import error
import language

if __name__ != "__main__": exit()

token:str = None
with open('TOKEN', 'r', encoding="utf-8") as file:
    token = file.read().strip()

client = commands.Bot(intents=discord.Intents.all(), command_prefix="//", sync_commands=True)

@client.event
async def on_ready():
    print(f'Logged in as {client.user.name}.')
    await client.tree.sync()

@client.tree.command(name="host", description="Host a game of Dementia.")
async def host(interaction:discord.Interaction, language_code:str=language.defaultCode):
    print(f"host accessed by {interaction.user.name}")

    if language_code not in language.getCodes().keys():
        await interaction.response.send_message(content=f"Invalid language code. Valid codes: {', '.join([f"`{key}`" for key in language.getCodes().keys()])}", ephemeral=True)
        return
    
    initialUserId = interaction.user.id

    langHost = language.getModule("host", language_code)
    langGamemodes = language.getModule("gamemodes", language_code)

    modeSelectEmbed = discord.Embed(color=discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)))
    modeSelectView = ui.View()

    modeSelect = ui.Select(placeholder=langHost["modeSelect"], custom_id="modeSelect")
    async def modeSelect_callback(interaction:discord.Interaction):
        if interaction.user.id != initialUserId: await error.notHost(interaction, language_code); return
        if (interaction.user.voice is None): await error.noVoice(interaction, language_code); return
        elif (interaction.user.voice.channel.id in GAMES):
            if GAMES[interaction.user.voice.channel.id].status == "playing" or GAMES[interaction.user.voice.channel.id].hostId in [member.id for member in interaction.user.voice.channel.members]:
                await error.gameOngoing(interaction, language_code); return
        
        gameId:int = interaction.user.voice.channel.id
        GAMES[gameId] = Game(hostId=interaction.user.id, id=gameId, gamemode=interaction.data["values"][0], languageCode=language_code)

        embed = GAMES[gameId].hostEmbed()
        view = GAMES[gameId].hostView()

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
    lang = language.getModule("info", "pl")
    embed = discord.Embed(title=lang["title"], description=lang["description"], color=discord.Color.blurple())
    for field in lang["fields"]: embed.add_field(name=field["name"], value=field["value"], inline=False)
    await interaction.response.send_message(embed=embed)

client.run(token)