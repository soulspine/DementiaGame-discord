import discord
import discord.ui as ui
import error
import modal
import language
import random
import asyncio
import datetime

GAMES:dict = {}

class Game:
    players: list[tuple[int, bool]] = []
    id: int
    hostId: int
    gamemode:str
    languageCode: str = language.defaultCode
    settings: dict
    status: str = "waiting"
    playerCount: int
    readyCount: int
    winnerCount: int
    vc: discord.VoiceChannel
    msg: discord.Message
    timeoutExtension: int = 60
    timeout: datetime.datetime
    emojis: dict = {
        "ready": "🟢",
        "notReady": "⭕",
        "playing": "<a:inProgress:1308805070577598535>"
    }

    def __init__(self, hostId:int, id:int, languageCode:str, gamemode:str, vc: discord.VoiceChannel, msg: discord.Message):
        self.hostId = hostId
        self.players = [(hostId, False)]
        self.id = id
        self.languageCode = languageCode
        self.gamemode = gamemode
        self.vc = vc
        self.msg = msg
        self.settings = {
            "maxGuesses": 0,    #always a number
            "timeLimit": 60,    #always a number
            "category": ""      #always a string
        }
        self.playerCount = 1
        self.readyCount = 0
        self.winnerCount = 0

        self.extendTimeout()
        self.updateChannelStatus()

    def getPlayersString(self) -> str:
        outStr:str = ""
        for player in self.players: outStr += f"{self.emojis["ready"] if player[1] else self.emojis["notReady"]} <@{player[0]}>\n"
        return outStr[:-1]

    def extendTimeout(self):
        self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=self.timeoutExtension)

    def updateChannelStatus(self):
        langChannel = language.getModule("channel", self.languageCode)
        message:str = ""
        match self.status:
            case "waiting":
                message = f"{langChannel["waiting"]} ({self.readyCount}/{self.playerCount})"
            case "playing":
                message = f"{self.emojis["playing"]} {langChannel["playing"]} ({self.winnerCount}/{self.playerCount})"

        asyncio.create_task(self.vc.edit(status=message))

    def setLanguage(self, languageCode:str):
        self.languageCode = languageCode.lower()
        self.updateChannelStatus()
        self.extendTimeout()

    def isPlayer(self, playerId:int) -> bool:
        return playerId in [player[0] for player in self.players]

    def add_player(self, playerId:int):
        self.players.append((playerId, False))
        self.playerCount += 1
        self.updateChannelStatus()
        self.extendTimeout()

    def remove_player(self, playerId:int):
        self.players = [player for player in self.players if player[0] != playerId]
        self.playerCount -= 1
        self.updateChannelStatus()
        self.extendTimeout()

    def readyState(self, playerId:int) -> bool:
        for player in self.players:
            if player[0] == playerId: return player[1]
        return False

    def setReady(self, playerId:int, ready:bool):
        for i, player in enumerate(self.players):
            if player[0] == playerId:
                self.players[i] = (playerId, ready)
                break
        self.readyCount += 1 if ready else -1
        self.updateChannelStatus()
        self.extendTimeout()

    def start(self):
        self.status = "playing"
        self.updateChannelStatus()
        self.extendTimeout()

    async def cancel(self, reason:str):
        self.status = "finished"
        self.updateChannelStatus()
        await self.msg.edit(embed=self.cancelledEmbed(reason), view=None)
        GAMES.pop(self.id)
        del self

    def lobbyEmbed(self) -> discord.Embed:
        langLobby = language.getModule("lobby", self.languageCode)
        langGamemodes = language.getModule("gamemodes", self.languageCode)

        description = \
            f"{langLobby["fields"]["host"]}: <@{self.hostId}>\n" + \
            f"{langLobby["fields"]["channel"]}: <#{self.id}>\n" + \
            f"{langLobby["fields"]["status"]}: {langLobby["status"][self.status]}\n" + \
            f"{langLobby["fields"]["timeout"]}: <t:{int(self.timeout.timestamp())}:R>\n"

        match self.status:
            case "waiting": color = discord.Color.from_rgb(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
            case "playing": color = discord.Color.blurple()
            case "finished": color = discord.Color.green()

        embed = discord.Embed(
            title=langLobby["title"],
            description=description,
            color=color
        )

        settings = []

        for setting in self.settings:
            val = self.settings[setting]
            if val in [0, "0", None, "None", ""]: setting += "0"
            settings.append(langLobby["settings"][setting].format(val))
        

        embed.add_field(name=langLobby["fields"]["settings"], value="\n".join(settings), inline=True)
        embed.add_field(name=f"{langLobby["fields"]["players"]} ({self.readyCount}/{self.playerCount})", value=self.getPlayersString(), inline=True)
        embed.add_field(name=f"{langLobby["fields"]["gamemode"]} - {langGamemodes[self.gamemode]["display"]}", value=langGamemodes[self.gamemode]["description"]["long"], inline=False)
        
        return embed
    
    def lobbyView(self) -> ui.View:
        langLobby = language.getModule("lobby", self.languageCode)
        langCodes = language.getCodes()

        view = ui.View()

        match self.status:
            case "waiting":
                joinButton = ui.Button(style=discord.ButtonStyle.green, label=langLobby["buttons"]["join"], custom_id=f"join-{self.id}")
                leaveButton = ui.Button(style=discord.ButtonStyle.red, label=langLobby["buttons"]["leave"], custom_id=f"leave-{self.id}")
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
                                await interaction.response.edit_message(embed=self.lobbyEmbed())
                        case "leave":
                            if self.hostId == interaction.user.id:
                                await interaction.response.defer()
                                await self.cancel("byHost")
                            else:
                                self.remove_player(interaction.user.id)
                                await interaction.response.edit_message(embed=self.lobbyEmbed())

                joinButton.callback = joinleave_callback
                leaveButton.callback = joinleave_callback

                settingsButton = ui.Button(emoji="<a:settings:1308796814106955776>", label=langLobby["buttons"]["settings"], custom_id=f"settings-{self.id}")
                async def settings_callback(interaction:discord.Interaction):
                    gameId:int = int(interaction.data["custom_id"].split("-")[1])
                    if (interaction.user.id != self.hostId): await error.notHost(interaction, self.languageCode); return
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

                    self.extendTimeout()
                    await interaction.response.send_modal(modal.SettingsModal(self, langLobby))

                settingsButton.callback = settings_callback

                languageSelect = ui.Select(placeholder=langLobby["buttons"]["language"], custom_id=f"language-{self.id}")
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
                    embed = self.lobbyEmbed()
                    await interaction.response.edit_message(embed=embed, view=self.lobbyView())

                languageSelect.callback = languageSelect_callback

                readyButton = ui.Button(style=discord.ButtonStyle.blurple, label=langLobby["buttons"]["ready"], custom_id=f"ready-{self.id}")
                async def ready_callback(interaction:discord.Interaction):
                    gameId:int = int(interaction.data["custom_id"].split("-")[1])
                    if (not self.isPlayer(interaction.user.id)): await error.notInGame(interaction, self.languageCode); return
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

                    self.setReady(interaction.user.id, not self.readyState(interaction.user.id))
                    await interaction.response.edit_message(embed=self.lobbyEmbed(), view=self.lobbyView())

                readyButton.callback = ready_callback

                startButton = ui.Button(style=discord.ButtonStyle.blurple, label="Start", custom_id=f"start-{self.id}")
                async def start_callback(interaction:discord.Interaction):
                    gameId:int = int(interaction.data["custom_id"].split("-")[1])
                    if (interaction.user.id != self.hostId): await error.notHost(interaction, self.languageCode); return
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

                    self.start()
                    await interaction.response.edit_message(embed=self.lobbyEmbed(), view=self.gameView())

                startButton.callback = start_callback
                if (self.readyCount != self.playerCount or self.playerCount < 2): startButton.disabled = True

                view.add_item(joinButton)
                view.add_item(settingsButton)
                view.add_item(leaveButton)
                view.add_item(readyButton)
                view.add_item(startButton)
                view.add_item(languageSelect)

            case "playing":
                openButton = ui.Button(style=discord.ButtonStyle.blurple, label=langLobby["buttons"]["openGame"], custom_id=f"open-{self.id}")
                async def open_callback(interaction:discord.Interaction):
                    gameId:int = int(interaction.data["custom_id"].split("-")[1])
                    if (not self.isPlayer(interaction.user.id)): await error.notInGame(interaction, self.languageCode); return
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != gameId): await error.wrongVoice(interaction, self.languageCode); return

                    await interaction.response.send_message(embed=self.gameEmbed(), view=self.gameView(), ephemeral=True)

                openButton.callback = open_callback

                view.add_item(openButton)

        return view

    def gameEmbed(self) -> discord.Embed:
        pass

    def gameView(self) -> ui.View:
        pass

    def cancelledEmbed(self, reason:str) -> discord.Embed:
        lang = language.getModule("postgame", self.languageCode)
        embed = self.lobbyEmbed()
        embed.color = discord.Color.red()
        embed.add_field(name=lang["cancelField"], value=lang["cancelReasons"][reason], inline=False)
        return embed
