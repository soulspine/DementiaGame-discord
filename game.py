import discord
import discord.ui as ui
import error
import modal
import language
import random

GAMES:dict = {}

class Game:
    players: list[int] = []
    id: int = None
    hostId: int = None
    gamemode:str = None
    languageCode: str = language.defaultCode
    settings: dict = {
        "maxGuesses": 0,    #always a number
        "timeLimit": 60,    #always a number
        "category": ""      #always a string
    }
    status: str = "waiting"
    playerCount: int = 1

    def __init__(self, hostId:int, id:int, languageCode:str, gamemode:str):
        self.hostId = hostId
        self.players = [hostId]
        self.id = id
        self.languageCode = languageCode
        self.gamemode = gamemode

    def getPlayersString(self) -> str:
        return "\n".join([f"<@{playerId}>" for playerId in self.players])

    def setLanguage(self, languageCode:str):
        self.languageCode = languageCode.lower()

    def isPlayer(self, playerId:int) -> bool:
        return playerId in self.players

    def add_player(self, playerId:int):
        self.players.append(playerId)
        self.playerCount += 1

    def remove_player(self, playerId:int):
        self.players.remove(playerId)
        self.playerCount -= 1

    def hostEmbed(self) -> discord.Embed:
        langHost = language.getModule("host", self.languageCode)
        langGamemodes = language.getModule("gamemodes", self.languageCode)

        description = \
            f"{langHost["fields"]["host"]}: <@{self.hostId}>\n" + \
            f"{langHost["fields"]["channel"]}: <#{self.id}>\n" + \
            f"{langHost["fields"]["status"]}: {langHost["status"][self.status]}\n"

        match self.status:
            case "waiting": color = discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            case "playing": color = discord.Color.blurple()
            case "finished": color = discord.Color.green()

        embed = discord.Embed(
            title=langHost["title"],
            description=description,
            color=color
        )

        settings = []

        for setting in self.settings:
            val = self.settings[setting]
            if val in [0, "0", None, "None", ""]: setting += "0"
            settings.append(langHost["settings"][setting].format(val))
        

        embed.add_field(name=langHost["fields"]["settings"], value="\n".join(settings), inline=True)
        embed.add_field(name=f"{langHost["fields"]["players"]} ({self.playerCount})", value=self.getPlayersString(), inline=True)
        embed.add_field(name=f"{langHost["fields"]["gamemode"]} - {langGamemodes[self.gamemode]["display"]}", value=langGamemodes[self.gamemode]["description"]["long"], inline=False)
        
        return embed
    
    def hostView(self):
        lang = language.getModule("host", self.languageCode)
        langCodes = language.getCodes()

        view = ui.View()
        joinButton = ui.Button(style=discord.ButtonStyle.green, label=lang["buttons"]["join"], custom_id=f"join-{self.id}")
        leaveButton = ui.Button(style=discord.ButtonStyle.red, label=lang["buttons"]["leave"], custom_id=f"leave-{self.id}")
        async def joinleave_callback(interaction:discord.Interaction):
            method:str = interaction.data["custom_id"].split("-")[0]
            gameId:int = int(interaction.data["custom_id"].split("-")[1])
            if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

            match method:
                case "join":
                    if self.isPlayer(interaction.user.id): await interaction.response.defer(); return
                    else:
                        self.add_player(interaction.user.id)
                        await interaction.response.edit_message(embed=self.hostEmbed())
                case "leave":
                    if self.hostId == interaction.user.id:
                        self.status = "finished"
                        await interaction.response.edit_message(embed=self.cancelledEmbed("byHost"), view=None)
                        del GAMES[gameId]
                    else:
                        self.remove_player(interaction.user.id)
                        await interaction.response.edit_message(embed=self.hostEmbed())

        joinButton.callback = joinleave_callback
        leaveButton.callback = joinleave_callback

        settingsButton = ui.Button(emoji="⚙️", label=lang["buttons"]["settings"], custom_id=f"settings-{self.id}")
        async def settings_callback(interaction:discord.Interaction):
            gameId:int = int(interaction.data["custom_id"].split("-")[1])
            if (interaction.user.id != self.hostId): await error.notHost(interaction, self.languageCode); return
            if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

            await interaction.response.send_modal(modal.SettingsModal(self, lang))

        settingsButton.callback = settings_callback

        languageSelect = ui.Select(placeholder=lang["buttons"]["language"], custom_id=f"language-{self.id}")
        for langCode in langCodes[self.languageCode]:
            languageSelect.add_option(label=langCodes[self.languageCode][langCode], value=langCode)

        async def languageSelect_callback(interaction:discord.Interaction):
            gameId:int = int(interaction.data["custom_id"].split("-")[1])
            language = interaction.data["values"][0]
            if (interaction.user.id != self.hostId): await error.notHost(interaction, self.languageCode); return
            if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

            if language == self.languageCode: await interaction.response.defer(); return

            self.setLanguage(language)
            embed = self.hostEmbed()
            await interaction.response.edit_message(embed=embed, view=self.hostView())

        languageSelect.callback = languageSelect_callback

        startButton = ui.Button(style=discord.ButtonStyle.blurple, label="Start", custom_id=f"start-{self.id}")
        async def start_callback(interaction:discord.Interaction):
            gameId:int = int(interaction.data["custom_id"].split("-")[1])
            if (interaction.user.id != self.hostId): await error.notHost(interaction, self.languageCode); return
            if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
            if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

            self.status = "playing"
            await interaction.response.edit_message(embed=self.hostEmbed(), view=None)

        startButton.callback = start_callback
        if (self.playerCount < 2): startButton.disabled = True

        view.add_item(joinButton)
        view.add_item(settingsButton)
        view.add_item(leaveButton)
        view.add_item(startButton)
        view.add_item(languageSelect)
        return view
    
    def cancelledEmbed(self, reason:str) -> discord.Embed:
        lang = language.getModule("postgame", self.languageCode)
        embed = self.hostEmbed()
        embed.color = discord.Color.red()
        embed.add_field(name=lang["cancelField"], value=lang["cancelReasons"][reason], inline=False)
        return embed
