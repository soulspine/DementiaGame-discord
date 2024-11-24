import discord
from game import Game
import datetime
import config
import language

class SettingsModal(discord.ui.Modal):
    game:Game

    def __init__(self, game:Game, langModule:dict):
        self.game = game
        
        self.category = discord.ui.TextInput(label=langModule["modal"]["fields"]["category"]["label"], default=self.game.settings["category"], placeholder=langModule["modal"]["fields"]["category"]["placeholder"], required=False)
        self.maxGuesses = discord.ui.TextInput(label=langModule["modal"]["fields"]["maxGuesses"]["label"], default= None if self.game.settings["maxGuesses"] == 0 else str(self.game.settings["maxGuesses"]), placeholder=langModule["modal"]["fields"]["maxGuesses"]["placeholder"], required=False)
        self.timeLimit = discord.ui.TextInput(label=langModule["modal"]["fields"]["timeLimit"]["label"], default= None if self.game.settings["timeLimit"] == 0 else str(self.game.settings["timeLimit"]), placeholder=langModule["modal"]["fields"]["timeLimit"]["placeholder"], required=False)

        super().__init__(title=langModule["modal"]["title"], timeout=None)

        self.add_item(self.category)
        self.add_item(self.maxGuesses)
        self.add_item(self.timeLimit)

    async def on_submit(self, interaction:discord.Interaction):
        try:
            if datetime.datetime.now() > self.game.timeout: await interaction.response.defer(); return
            maxGuesses = int(self.maxGuesses.value) if self.maxGuesses.value != "" else 0
            timeLimit = int(self.timeLimit.value) if self.timeLimit.value != "" else 0
            category = self.category.value

            if maxGuesses < 0 or timeLimit < 0:
                raise ValueError

            self.game.settings["maxGuesses"] = maxGuesses if maxGuesses < self.game.playerCount else 0
            self.game.settings["timeLimit"] = timeLimit
            self.game.settings["category"] = None if category == "0" else category
            await interaction.response.edit_message(embed=self.game.lobbyEmbed())
        except ValueError:
            await interaction.response.send_message("Invalid input.", ephemeral=True)
            return
    
    async def on_error(self, interaction, error):
        return await super().on_error(interaction, error)

    async def on_timeout(self, interaction:discord.Interaction):
        await interaction.response.defer()

class AssignmentModal(discord.ui.Modal):
    game:Game
    playerId:int
    targetPlayerId:int

    def __init__(self, game:Game, playerId:int, targetPlayerId:int):
        self.game = game
        self.playerId = playerId
        self.targetPlayerId = targetPlayerId
        langModule = language.getModule("game", self.game.languageCode)

        targetPlayer = self.game.guild.get_member(self.targetPlayerId)
        placeholder = targetPlayer.name if targetPlayer.display_name == targetPlayer.name else f"{targetPlayer.display_name} ({targetPlayer.name})"

        self.identity = discord.ui.TextInput(label=langModule["assigningPhase"]["modal"]["fields"]["identity"]["label"], placeholder=langModule["assigningPhase"]["modal"]["fields"]["identity"]["placeholder"].format(placeholder), required=True, max_length=config.AssignmentModal.maxChars)

        super().__init__(title=langModule["assigningPhase"]["modal"]["title"], timeout=None)

        self.add_item(self.identity)

    async def on_submit(self, interaction:discord.Interaction):
        self.game.players[self.targetPlayerId].identity = self.identity.value
        if self.game.players[self.playerId].gameMsg is None:
            await interaction.response.send_message(embed=self.game.gameEmbed(self.playerId), view=self.game.gameView(self.playerId), ephemeral=True)
            self.game.updateGameMessage()
            self.game.players[self.playerId].gameMsg = await interaction.original_response()
        else:
            await interaction.response.defer()
            self.game.updateGameMessage()

    async def on_error(self, interaction, error):
        return await super().on_error(interaction, error)

    async def on_timeout(self, interaction:discord.Interaction):
        await interaction.response.defer()

class NoteModal(discord.ui.Modal):
    game:Game
    playerId:int

    def __init__(self, game:Game, playerId:int):
        self.game = game
        self.playerId = playerId
        langModule = language.getModule("game", self.game.languageCode)

        player = self.game.guild.get_member(self.playerId)

        self.question = discord.ui.TextInput(label=langModule["roundPhase"]["noteModal"]["fields"]["question"]["label"], required=True, max_length=config.NoteModal.Question.maxChars)
        self.answer = discord.ui.TextInput(label=langModule["roundPhase"]["noteModal"]["fields"]["answer"]["label"], required=True, max_length=config.NoteModal.Note.maxChars)

        super().__init__(title=langModule["roundPhase"]["noteModal"]["title"].format(player.display_name), timeout=None)

        self.add_item(self.question)
        self.add_item(self.answer)

    async def on_submit(self, interaction:discord.Interaction):
        question = self.question.value
        answer = self.answer.value
        self.game.players[self.playerId].addNote(question, answer)

        await interaction.response.defer()
        self.game.nextRound()

    async def on_error(self, interaction, error):
        return await super().on_error(interaction, error)

    async def on_timeout(self, interaction:discord.Interaction):
        await interaction.response.defer()