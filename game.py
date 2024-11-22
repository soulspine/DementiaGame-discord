import discord
import discord.ui as ui
import error
import modal
import language
import random
import asyncio
import datetime

GAMES:dict = {}

class Player:
    id:int
    ready:bool
    identity:str
    targetId:int
    gameMsg:discord.Message

    def __init__(self, id:int, ready:bool = False, identity:str = None):
        self.id = id
        self.ready = ready
        self.identity = identity
        self.targetId = None
        self.gameMsg = None

    def __str__(self):
        return f"Player {self.id} - {self.ready} - {self.identity} - {self.targetId}"

class Game:
    client:discord.Client
    players: dict[int, Player]
    assignmentPairs: dict[str, str] # (playerId, targetPlayerId)
    id: int
    hostId: int
    gamemode:str
    languageCode: str
    settings: dict
    lobbyStatus: str # waiting, playing, finished
    gamePhase: str # assigning, 
    playerCount: int
    readyCount: int
    winnerCount: int
    vc: discord.VoiceChannel
    msg: discord.Message
    timeoutExtension: int
    timeout: datetime.datetime
    roundOrder: list[int]
    emojis: dict = {
        "ready": "🟢",
        "notReady": "⭕",
        "playing": "<a:inProgress:1308805070577598535>"
    }


    def __init__(self, client, hostId:int, id:int, languageCode:str, gamemode:str, vc: discord.VoiceChannel, msg: discord.Message):
        self.client = client
        self.players = {
            hostId: Player(hostId, ready=False)
        }

        #self.players[1306987007779541002] = Player(1306987007779541002, ready=True) # for testing, bot itself

        self.assignmentPairs = None
        self.id = id
        self.hostId = hostId
        self.gamemode = gamemode
        self.languageCode = languageCode
        self.settings = {
            "maxGuesses": 0,    #always a number
            "timeLimit": 60,    #always a number
            "category": ""      #always a string
        }
        self.lobbyStatus = "waiting"
        self.gamePhase = None
        self.playerCount = len(self.players.keys())
        self.readyCount = len([key for key in self.players if self.players[key].ready])
        self.winnerCount = 0
        self.vc = vc
        self.msg = msg
        self.timeoutExtension = 60
        self.timeout = None
        self.roundOrder = None

        self.extendTimeout()
        self.updateChannelStatus()

    def getPlayersString(self, withReady:bool=True) -> str:
        outStr:str = ""
        for player in self.players.values():
            if withReady: outStr += f"{self.emojis["ready"] if player.ready else self.emojis["notReady"]} "
            outStr += f"<@{player.id}>\n"
        return outStr[:-1]

    def extendTimeout(self):
        self.timeout = datetime.datetime.now() + datetime.timedelta(seconds=self.timeoutExtension)

    def updateChannelStatus(self):
        langChannel = language.getModule("channel", self.languageCode)
        message:str = ""
        match self.lobbyStatus:
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
        return self.players.get(playerId) is not None

    def add_player(self, playerId:int):
        self.players[playerId] = Player(playerId)
        self.playerCount += 1
        self.updateChannelStatus()
        self.extendTimeout()

    def remove_player(self, playerId:int):
        self.players.pop(playerId)
        self.playerCount -= 1
        self.updateChannelStatus()
        self.extendTimeout()

    def setReady(self, playerId:int, ready:bool):
        self.players[playerId].ready = ready
        self.readyCount += 1 if ready else -1
        self.updateChannelStatus()
        self.extendTimeout()

    def start(self):
        self.lobbyStatus = "playing"
        self.gamePhase = "assigning"
        self.timeout = None

        players = [player.id for player in self.players.values()]
        targets = players.copy()
        
        while True:
            random.shuffle(targets)
            if all([player != target for player, target in zip(players, targets)]): break
        
        self.roundOrder = targets.copy()

        for playerId, targetId in zip(players, targets):
            self.players[playerId].targetId = targetId
            self.players[playerId].ready = False

        self.updateChannelStatus()

    async def cancel(self, reason:str):
        self.lobbyStatus = "finished"
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
            f"{langLobby["fields"]["status"]}: {langLobby["status"][self.lobbyStatus]}"
            
        if self.lobbyStatus == "waiting": description += f"\n{langLobby["fields"]["timeout"]}: <t:{int(self.timeout.timestamp())}:R>"

        match self.lobbyStatus:
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
        embed.add_field(name=f"{langLobby["fields"]["players"]} ({self.readyCount}/{self.playerCount})", value=self.getPlayersString(False if self.lobbyStatus == "playing" else True), inline=True)
        embed.add_field(name=f"{langLobby["fields"]["gamemode"]} - {langGamemodes[self.gamemode]["display"]}", value=langGamemodes[self.gamemode]["description"]["long"], inline=False)
        
        return embed
    
    def lobbyView(self) -> ui.View:
        langLobby = language.getModule("lobby", self.languageCode)
        langCodes = language.getCodes()

        view = ui.View()

        match self.lobbyStatus:
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

                    self.setReady(interaction.user.id, not self.players[interaction.user.id].ready)
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
                    await interaction.response.edit_message(embed=self.lobbyEmbed(), view=self.lobbyView())

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

                    targetPlayerId = self.players[interaction.user.id].targetId
                    unassignedPlayers = [player.id for player in self.players.values() if player.identity is None]

                    targetPlayerName:str = self.client.get_user(targetPlayerId).name

                    if targetPlayerId in unassignedPlayers:
                        await interaction.response.send_modal(modal.AssignmentModal(self, language.getModule("game", self.languageCode), interaction.user.id, targetPlayerId, targetPlayerName))
                    else:
                        await interaction.response.send_message(embed=self.gameEmbed(interaction.user.id), view=self.gameView(interaction.user.id), ephemeral=True)
                        await self.players[interaction.user.id].gameMsg.delete()
                        self.players[interaction.user.id].gameMsg = await interaction.original_response()

                openButton.callback = open_callback

                view.add_item(openButton)

        return view

    def gameEmbed(self, userId:int) -> discord.Embed:
        langGame = language.getModule("game", self.languageCode)
        
        embed = discord.Embed()
        
        match self.gamePhase:
            case "assigning":
                embed.title = langGame["assigningPhase"]["title"]
                embed.description = langGame["assigningPhase"]["description"].format(f"<@{self.players[userId].targetId}>")

                playersMessage = ""

                for playerId in self.roundOrder:
                    player = self.players[playerId]
                    playersMessage += f"{self.emojis['ready'] if player.ready else self.emojis['notReady']} <@{player.id}> - "
                    playersMessage += "||???||" if player.id == userId or player.identity == None else player.identity
                    playersMessage += "\n"

                playersMessage = playersMessage[:-1]

                embed.add_field(name=langGame["assigningPhase"]["fields"]["players"], value=playersMessage, inline=False)

        return embed

    def gameView(self, userId:int) -> ui.View:
        langGame = language.getModule("game", self.languageCode)
        view = ui.View()
        
        match self.gamePhase:
            case "assigning":
                player = self.players[userId]
                target = self.players[player.targetId]

                style = discord.ButtonStyle.green if not player.ready else discord.ButtonStyle.red
                label = langGame["assigningPhase"]["buttons"]["confirm"] if not player.ready else langGame["assigningPhase"]["buttons"]["cancel"]
                customId = "confirm" if not player.ready else "cancel" 

                confirmcancelButton = ui.Button(style=style, label=label, custom_id=f"{customId}")
                async def confirmcancel_callback(interaction:discord.Interaction):
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != self.id): await error.wrongVoice(interaction, self.languageCode); return

                    await interaction.response.defer()

                    ready = interaction.data["custom_id"] == "confirm"

                    self.setReady(userId, ready)

                    self.updateGameMessage()
                confirmcancelButton.callback = confirmcancel_callback
                view.add_item(confirmcancelButton)

                changeButton = ui.Button(style=discord.ButtonStyle.blurple, label=langGame["assigningPhase"]["buttons"]["change"], custom_id="change")
                async def change_callback(interaction:discord.Interaction):
                    if (interaction.user.voice is None): await error.noVoice(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id not in GAMES): await error.noGame(interaction, self.languageCode); return
                    if (interaction.user.voice.channel.id != self.id): await error.wrongVoice(interaction, self.languageCode); return

                    await interaction.response.send_modal(modal.AssignmentModal(self, langGame, userId, self.players[userId].targetId, self.client.get_user(self.players[userId].targetId).name))

                changeButton.callback = change_callback
                if player.ready: changeButton.disabled = True
                view.add_item(changeButton)

        return view

    def updateGameMessage(self, userId:int = None):
        if userId is not None:
            player = self.players[userId]
            if player.gameMsg is not None:
                asyncio.create_task(player.gameMsg.edit(embed=self.gameEmbed(userId), view=self.gameView(userId)))
        else:
            for player in self.players.values():
                if player.gameMsg is not None:
                    asyncio.create_task(player.gameMsg.edit(embed=self.gameEmbed(player.id), view=self.gameView(player.id)))

    def cancelledEmbed(self, reason:str) -> discord.Embed:
        lang = language.getModule("postgame", self.languageCode)
        embed = self.lobbyEmbed()
        embed.color = discord.Color.red()
        embed.add_field(name=lang["cancelField"], value=lang["cancelReasons"][reason], inline=False)
        return embed
