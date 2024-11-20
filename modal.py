import discord
from game import Game, GAMES
import datetime

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