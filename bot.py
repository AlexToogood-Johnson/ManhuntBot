#bot.py
"""The code for the EMS Accommodation Manhunt Discord bot"""

############ IMPORTS ############

import discord
from discord import app_commands
from discord.ext import commands, tasks
from fuzzywuzzy import fuzz
import os, datetime, random

########## CONSTANTS ##########

intents = discord.Intents.all()
intents.members = True
bot = commands.Bot(command_prefix='/', intents=intents)

class Variables:
	"""Stores all of the variables and flags for the discord bot"""

	def __init__(self):

		self.RUNNER_REACTION = '👟'
		self.HUNTER_REACTION = '🏹'

		self.RUNNER_ROLE = 'Runner'
		self.HUNTER_ROLE = 'Hunter'
		self.ADMIN_ROLE = 'Admin'

		self.headstart_announced = False
		self.main_game_announced = False
		self.end_time_announced = False
		self.end_game = False
		self.game_running = False

		self.end_location = ''
		self.players = {'hunters' : [], 'runners' : []}
		self.timings = []

		self.winner = False

	def reset_vars(self):
		"""Resets all of the variables to their default values"""

		self.headstart_announced = False
		self.main_game_announced = False
		self.end_time_announced = False
		self.end_game = False
		self.game_running = False

		self.end_location = ''
		self.players = {'hunters' : [], 'runners' : []}
		self.timings = []

		self.winner = False

v = Variables()

########## FUNCTIONS ##########

def log(message:str):
	"""Adds a message to the 'current.txt' log with a preceding timestamp"""

	time = datetime.datetime.now().strftime("%H:%M:%S")
	message = f"{time} {message}\n"

	with open("current.txt", "a") as log_file:
		log_file.write(message)

def choose_random_location():
	"""Retrieves a random location from 'locations.txt'"""

	with open("locations.txt", "r") as locations_file:
		locations = locations_file.readlines()

	v.end_location = random.choice(locations)

########## COMMANDS ##########

@bot.event
async def on_ready():

	print(f"Bot is online! Logged in as {bot.user.name} ({bot.user.id})")
	await bot.change_presence(activity = discord.Game(name = "Manhunt"))

	try:
		synced = await bot.tree.sync()
		print(f"Synced {len(synced)} commands")

		global BOT_CHANNEL, HUNTER_CHANNEL, LOG_CHANNEL

		LOG_CHANNEL = bot.get_channel(1183924999069909042)
		BOT_CHANNEL = bot.get_channel(1183925092820979713)
		HUNTER_CHANNEL = bot.get_channel(1183925277504585938)

		check_game_status.start()

	except Exception as e: print(e)

@tasks.loop(seconds = 10)
async def check_game_status():

	if v.game_running:
		now = datetime.datetime.now()
		start_time, headstart, gametime, endtime = v.timings

		if now > start_time + headstart and not v.headstart_announced:
			await BOT_CHANNEL.send("The Manhunt game has entered the main phase, and the hunters can now leave")
			await HUNTER_CHANNEL.send("You can now leave")
			log("PHASE HEADSTART END")
			v.headstart_announced = True

		if now > start_time + headstart + gametime and not v.main_game_announced:
			await BOT_CHANNEL.send(f"The Manhunt game has entered the end phase. The end location is {v.end_location}")
			log("PHASE MAINGAME END")
			v.main_game_announced = True

		if now > start_time + headstart + gametime + endtime and not v.end_time_announced:
			await BOT_CHANNEL.send("The Manhunt game has now finished")
			log("PHASE ENDTIME END")
			v.end_time_announced = True
			v.end_game = True

		if len(v.players['runners']) == 0:
			v.end_game = True

		if v.end_game:

			runner_role = discord.utils.get(BOT_CHANNEL.guild.roles, name = v.RUNNER_ROLE)
			for runner_name in v.players['runners']:
				member = discord.utils.get(BOT_CHANNEL.guild.members, display_name = runner_name)
				if member: await member.remove_roles(runner_role)

			hunter_role = discord.utils.get(BOT_CHANNEL.guild.roles, name = v.HUNTER_ROLE)
			for hunter_name in v.players['hunters']:
				member = discord.utils.get(BOT_CHANNEL.guild.members, display_name = hunter_name)
				if member: await member.remove_roles(hunter_role)

			if v.winner:
				await BOT_CHANNEL.send("The Manhunt game has ended. The hunters have lost!")
				log("GAME ENDED - HUNTERS LOSE")
			else:
				await BOT_CHANNEL.send("The Manhunt game has ended. The hunters have won!")
				log("GAME ENDED - HUNTERS WIN")

			with open("current.txt", "r") as log_file:
				log_content = " ".join(log_file.readlines())

			start_time_str = v.timings[0].strftime("%d%m%Y%H%M%S")
			log_file_path = f"logs/{start_time_str}.txt"

			with open(log_file_path, "w") as new_log_file:
				new_log_file.write(log_content)

			await LOG_CHANNEL.send(file = discord.File(log_file_path, filename = "log.txt"))

			os.remove("current.txt")

			v.reset_vars()

@check_game_status.before_loop
async def before_check_game_status():
	await bot.wait_until_ready()

@bot.tree.command(name = "start-game", description = "Starts an active suggestion as a game of Manhunt")
@app_commands.describe(headstart = "How long the runners' headstart is", gametime = "How long the main game period lasts", endtime = "How long runners have to reach the end location")
async def start_game(interaction: discord.Interaction, headstart: int = 5, gametime: int = 70, endtime: int = 15):

	if os.path.exists("current.txt") and not v.game_running: # This checks for an active suggestion file

		try:
			with open("current.txt", "r") as game_file:
				message_id = game_file.read() # Gets the message id of the suggestion, in order to collect all reactions

			message = await BOT_CHANNEL.fetch_message(message_id)

			for reaction in message.reactions: # Combines all the reactions into v.players dict to get all the players
				async for user in reaction.users():
					
					if user.id != bot.user.id: # Discounts the bot's initial reactions

						name = user.display_name
						reaction = reaction.emoji

						if reaction == v.RUNNER_REACTION: v.players['runners'].append(name)
						elif reaction == v.HUNTER_REACTION: v.players['hunters'].append(name)

			if len(v.players['runners']) < 1 or len(v.players['hunters']) < 1:
				await interaction.response.send_message("There must be at least 1 hunter and 1 runner in order to start a game", ephemeral = True)

			elif len(v.players['runners']) + len(v.players['hunters']) != len(set(v.players['runners'] + v.players['hunters'])):
				await interaction.response.send_message('Someone appears to have reacted to both the runner and hunter roles. Please remove duplicate reactions', ephemeral = True)

			elif headstart <= 0 or gametime <= 0 or endtime <= 0:
				await interaction.response.send_message('All game times must be greater than 0. Try again with valid game times', ephemeral = True)

			else: # This section here starts the game
				v.game_running = True
				v.timings = [datetime.datetime.now(), datetime.timedelta(minutes = headstart), datetime.timedelta(minutes = gametime), datetime.timedelta(minutes = endtime)]
				player_count = len(v.players["hunters"]) + len(v.players["runners"])
				choose_random_location() # Assigns random end location to v.end_location

				runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
				hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)

				for player_name in v.players['runners']: # Gives all runners the runner role
					member = discord.utils.get(interaction.guild.members, display_name = player_name)
					await member.add_roles(runner_role)

				for player_name in v.players['hunters']: # Gives all hunters the hunter role
					member = discord.utils.get(interaction.guild.members, display_name = player_name)
					await member.add_roles(hunter_role)

				message = f"\nSTART {v.timings[0]}\n\nPLAYERS {player_count}\n"
				for player in v.players['runners']:
					message += f"RUNNER {player}\n"
				for player in v.players['hunters']:
					message += f"HUNTER {player}\n"
				message += f"\nTIMES {headstart} {gametime} {endtime}\nLOCATION {v.end_location}\n-----  MAIN LOG  -----\n\n"

				with open("current.txt", "w") as game_file: # Puts all the 'metadata' in the log
					game_file.write(message)

				await HUNTER_CHANNEL.send(f"The end location is : **{v.end_location}**")
				await interaction.response.send_message("Game successfully started", ephemeral = True)

				message = f"The game was started by **{interaction.user.display_name}**.\n\nThe hunters are : {', '.join(v.players['hunters'])}\n\nThe runners are : {', '.join(v.players['runners'])}\n\nYou have **{headstart}** minutes headstart, **{gametime}** minutes of main game time, and **{endtime}** minutes to reach the end location, which is given to you at the start of the end phase"
				message += "\n\nA reminder of the following things : \n1. Make sure your phone has sufficient charge\n2. Make sure to text your flat person\n3. Make sure you have appropriate clothing, for weather and road safety\n4. Make sure you can get back to accommodation before 10\n5. It is advisable to have accomodation keys on you"
				message += "\n\nMake sure to turn your Glympse tracker on, and turn off Snapmap etc.\n\nHave fun!"

				await BOT_CHANNEL.send(message)

		except discord.errors.NotFound: # The program cannot find the reaction message

			await interaction.response.send_message(f"Message with ID **{message_id}** not found.", ephemeral = True)
			await BOT_CHANNEL.send(f"**{interaction.user.display_name}** tried to start a game, but the reaction message was not found. Please unsuggest and create a new suggestion")

		except Exception as e: # Some other error occurred

			await interaction.response.send_message(f"You may want to create a new suggestion. The following error occured : **{e}**", ephemeral = True)

	else: await interaction.response.send_message("There is not currently an active game suggestion, or there is a game in progress", ephemeral = True)

@bot.tree.command(name = "suggest-game", description = "Creates a reaction message so people can join a proposed game")
async def suggest_game(interaction: discord.Interaction):

	if os.path.exists("current.txt"): 
		await interaction.response.send_message('There is already an open suggestion. Please delete this before attempting to suggest another game', ephemeral = True)
		
	else:
		message = await BOT_CHANNEL.send(f"A game of Manhunt has been suggested by **{interaction.user.display_name}**. React to this message with :bow_and_arrow: or :athletic_shoe: in order to join this game.")

		await message.add_reaction(v.RUNNER_REACTION)
		await message.add_reaction(v.HUNTER_REACTION)

		message_id = str(message.id) + '\n'

		with open("current.txt", "w") as game_file:
			game_file.write(message_id)

		await interaction.response.send_message('A game of Manhunt has been suggested', ephemeral = True)

@bot.tree.command(name = "resign", description = "The player who runs this command leaves the game")
async def resign(interaction: discord.Interaction):

	if v.game_running:
		player_name = interaction.user.display_name

		if player_name in v.players['runners']:
			runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
			member = discord.utils.get(interaction.guild.members, display_name = player_name)
			await member.remove_roles(runner_role)
			v.players['runners'].remove(player_name)
			log(f"RESIGN {player_name}")
			log(f"{player_name} -> LEAVES")
			await BOT_CHANNEL.send(f"{player_name} has resigned from the game")
			await interaction.response.send_message("You have successfully resigned as a runner", ephemeral = True)

		elif player_name in v.players['hunters']:
			hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)
			member = discord.utils.get(interaction.guild.members, display_name = player_name)
			await member.remove_roles(hunter_role)
			v.players['hunters'].remove(player_name)
			log(f"RESIGN {player_name}")
			log(f"{player_name} -> LEAVES")

			if len(v.players["hunters"]) == 0:
				await BOT_CHANNEL.send(f"**{player_name}** has resigned from the game. There are now 0 hunters. Please pick a new hunter")

			else:
				await BOT_CHANNEL.send(f"**{player_name}** has resigned from the game. There are now {len(v.players['hunters'])} hunters")

			await interaction.response.send_message("You have successfully resigned as a hunter", ephemeral = True)

		else: await interaction.response.send_message("You are not currently a player in the game", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "add-player", description = "The Discord member who uses this command will get added to a current game as a runner")
async def add_player(interaction: discord.Interaction):

	if v.game_running:

		player_name = interaction.user.display_name

		if player_name in v.players['runners'] or player_name in v.players['hunters']:
			message = f"You are already in the game."

		else:
			v.players['runners'].append(player_name)
			message = f"You have been added to the game as a runner."

			member = discord.utils.get(interaction.guild.members, display_name = player_name)
			runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
			await member.add_roles(runner_role)

			await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has been added to the game as a runner.")

			log(f"LATE-PLAYER-ADD {player_name}")
			log(f"{player_name} -> RUNNER")

		await interaction.response.send_message(message, ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "add-hunter", description = "A runner who uses this command will become a hunter")
async def add_hunter(interaction: discord.Interaction):
	
	if v.game_running:

		runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)

		if runner_role in interaction.user.roles:

			hunter_role = discord.utils.get(interaction.guild.roles, name=v.HUNTER_ROLE)

			await interaction.user.remove_roles(runner_role)
			await interaction.user.add_roles(hunter_role)

			v.players['runners'].remove(interaction.user.display_name)
			v.players['hunters'].append(interaction.user.display_name)
			log(f"PLAYER {interaction.user.display_name} Runner -> Hunter")

			await interaction.response.send_message(f"You have been converted from a runner to a hunter", ephemeral = True)
			await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has made themself a hunter")

		else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "random-runner", description = "Picks a random runner")
async def random_runner(interaction: discord.Interaction):

	if v.game_running:

		try:
			random_runner = random.choice(v.players['runners'])
			await BOT_CHANNEL.send(f"**{interaction.user.display_name}** used the random-runner command, **{random_runner}** was selected")
			await interaction.response.send_message(f"The runner randomly selected is **{random_runner}**", ephemeral = True)

		except IndexError: await interaction.response.send_message("An error occured. Please try again", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "catch", description = "The hunter who uses this command catches the given runner")
@app_commands.describe(runner = "The runner caught by the hunter")
async def catch(interaction: discord.Interaction, runner: discord.Member):

	if v.game_running:

		hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)

		if hunter_role in interaction.user.roles:

			if runner.display_name in v.players['runners']:

				runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)

				await runner.remove_roles(runner_role)
				await runner.add_roles(hunter_role)				

				v.players['runners'].remove(runner.display_name)
				v.players['hunters'].append(runner.display_name)
				log(f"{interaction.user.display_name} CATCH {runner.display_name}")
				log(f"{runner.display_name} -> HUNTER")

				await BOT_CHANNEL.send(f"**{runner.display_name}** has been caught by **{interaction.user.display_name}**. They are now a hunter")

			else: await interaction.response.send_message(f"**{runner.display_name}** is not a runner in the current game.", ephemeral = True)

		else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "disqualify", description = "Disqualifies a player from the game")
@app_commands.describe(player = "The player to be disqualified", reason = "Reason for disqualification")
async def disqualify(interaction: discord.Interaction, player: discord.Member, reason: str):

	if v.game_running:

		admin_role = discord.utils.get(interaction.guild.roles, name = v.ADMIN_ROLE)

		if admin_role in interaction.user.roles:

			if player.display_name in v.players['runners']:

				runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
				await player.remove_roles(runner_role)
				log(f"{interaction.user.display_name} DISQUALIFIES {player.display_name} REASON: {reason}")
				log(f"{player.display_name} -> LEAVES")
				await BOT_CHANNEL.send(f"**{player.display_name}** has been disqualified by **{interaction.user.display_name}**. Reason: **{reason}**")
			
			elif player.display_name in v.players['hunters']:

				hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)
				await player.remove_roles(hunter_role)
				log(f"{interaction.user.display_name} DISQUALIFIES {player.display_name} reason: {reason}")
				log(f"{player.display_name} -> LEAVES")
				await BOT_CHANNEL.send(f"**{player.display_name}** has been disqualified by **{interaction.user.display_name}**. Reason: **{reason}**")

			else: await interaction.response.send_message(f"**{player.display_name}** is not currently a participant in the current game", ephemeral = True)

		else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "comment", description = "Add an observation to the game log")
@app_commands.describe(note = "The observation you want to record")
async def comment(interaction: discord.Interaction, note:str):

	if v.game_running:

		admin_role = discord.utils.get(interaction.guild.roles, name = v.ADMIN_ROLE)

		if admin_role in interaction.user.roles:

			log(f"COMMENT {interaction.user.display_name} {note}")

		else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "win", description = "The runner who uses this command has made it to the end location")
async def win(interaction: discord.Interaction):

	if v.game_running and v.end_time_announced:

		runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)

		if runner_role in interaction.user.roles:

			winner = interaction.user.display_name
			if winner in v.players['runners']:

				winner = discord.utils.get(interaction.guild.members, display_name = winner)
				await winner.remove_roles(runner_role)

				log(f"WIN {winner}")
				log(f"{winner} -> LEAVES")

				await BOT_CHANNEL.send(f"**{winner}** has successfully reached the end location and is a winner")

				v.players['runners'].remove(winner)

				v.winner = True

		else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game in the end phase", ephemeral = True)

@bot.tree.command(name = "extend", description = "Extends a given phase by a given number of minutes")
@app_commands.describe(phase = "The phase to extend ('headstart', 'gametime', or 'endtime')", time = "The number of minutes to extend the phase")
async def extend(interaction: discord.Interaction, phase: str, time: int):

	if v.game_running:

		if phase in ['headstart', 'gametime', 'endtime']:

			if phase == 'headstart':
				if not v.main_game_announced:
					v.timings[1] += datetime.timedelta(minutes = time)
					log(f"PHASE {phase.upper()} ADD {time}")
					await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has extended **{phase}** by **{time}** minutes")

			elif phase == 'gametime':
				if not v.end_time_announced:
					v.timings[2] += datetime.timedelta(minutes = time)
					log(f"PHASE {phase.upper()} ADD {time}")
					await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has extended **{phase}** by **{time}** minutes")

			elif phase == 'endtime':
				v.timings[3] += datetime.timedelta(minutes = time)
				log(f"PHASE {phase.upper()} ADD {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has extended **{phase}** by **{time}** minutes")

			else: await interaction.response.send_message(f"{phase.capitalize()} has already passed and cannot be extended", ephemeral = True)

		else: await interaction.response.send_message("Invalid phase. Please choose 'headstart', 'gametime', or 'endtime'", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "shorten", description = "Removes a given number of minutes from a given phase")
@app_commands.describe(phase = "The phase to shorten ('headstart', 'gametime', or 'endtime')", time = "The number of minutes to shorten the phase")
async def shorten(interaction: discord.Interaction, phase: str, time: int):

	if v.game_running:

		if phase in ['headstart', 'gametime', 'endtime']:

			now = datetime.datetime.now()
			start_time, headstart, gametime, endtime = v.timings
			time_format = datetime.timedelta(minutes = time)

			if phase == 'headstart' and start_time + headstart - time_format > now and time_format < v.timings[1]:
				v.timings[1] -= time_format
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes")

			elif phase == 'gametime' and start_time + gametime + headstart - time_format > now and time_format < v.timings[2]:
				v.timings[2] -= time_format
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes")

			elif phase == 'endtime' and start_time + headstart + gametime + endtime - time_format > now and time_format < v.timings[3]:
				v.timings[3] -= time_format
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes")

			else: await interaction.response.send_message(f"{phase.capitalize()} has already passed, or the given time is not appropriate", ephemeral = True)

		else: await interaction.response.send_message("Invalid phase. Please choose 'headstart', 'gametime', or 'endtime'", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "set-location", description = "Changes the end location of a Manhunt game")
@app_commands.describe(location = "The new location for the game's end")
async def set_location(interaction: discord.Interaction, location: str):

	hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)

	if hunter_role in interaction.user.roles:

		if v.game_running:

			if not v.end_time_announced:

				with open("locations.txt", "r") as locations_file:
					all_locations = locations_file.readlines()
				
				if location in all_locations:

					log(f"CHANGE-LOCATION {interaction.user.display_name} {location}")
					v.end_location = location

					await HUNTER_CHANNEL.send(f"The end location has been changed to **{v.end_location}**")
					await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has changed the end location")

				else: await interaction.response.send_message(f"Location **{location}** does not exist. Please use a valid end location", ephemeral = True)

			else: await interaction.response.send_message("You can only change the location during the headstart or gametime phase", ephemeral = True)

		else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

	else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

@bot.tree.command(name = "end-game", description = "Ends the game unconditionally")
async def end_game(interaction: discord.Interaction):

	admin_role = discord.utils.get(interaction.guild.roles, name = v.ADMIN_ROLE)

	if admin_role in interaction.user.roles:

		if v.game_running:

			v.game_running = False

			log("GAME ENDED - NO WIN")

			with open("current.txt", "r") as log_file:
				log_content = log_file.read()

			start_time_str = v.timings[0].strftime("%d%m%Y%H%M%S")
			log_file_path = f"logs/{start_time_str}.txt"

			with open(log_file_path, "w") as new_log_file:
				new_log_file.write(log_content)

			runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
			for runner in v.players['runners']:
				member = discord.utils.get(interaction.guild.members, display_name = runner)
				if member: await member.remove_roles(runner_role)
			
			hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)
			for hunter in v.players['hunters']:
				member = discord.utils.get(interaction.guild.members, display_name = hunter)
				if member: await member.remove_roles(hunter_role)

			v.reset_vars()

			os.remove("current.txt")

			await LOG_CHANNEL.send(file = discord.File(log_file_path, filename = "log.txt"))
			await BOT_CHANNEL.send(f"The current Manhunt game has been unconditionally ended by **{interaction.user.display_name}**")

		else: await interaction.response.send_message("There is no active Manhunt game", ephemeral = True)

	else: await interaction.response.send_message("You do not have the required permissions to use this command", ephemeral = True)

@bot.tree.command(name="players-list", description = "Lists all the players in a running game")
async def players_list(interaction: discord.Interaction):

	if v.game_running:

		message = ''

		for player in v.players['runners']: message = message + player + ' - Runner\n'

		for player in v.players['hunters']:
			message = message + player + ' - Hunter\n'

	else: message = 'There is not currently an active game'

	await interaction.response.send_message(message, ephemeral = True)

@bot.tree.command(name="unsuggest", description = "Removes any outstanding game suggestions")
async def unsuggest(interaction: discord.Interaction):

	if os.path.exists("current.txt") and not v.game_running:
		os.remove("current.txt")

		await BOT_CHANNEL.send(f"The current Manhunt suggestion was removed by **{interaction.user.display_name}**")
		await interaction.response.send_message("The current suggestion was deleted", ephemeral = True)

	else: await interaction.response.send_message('There is not currently a Manhunt game suggestion', ephemeral = True)

@bot.tree.command(name = "del-location", description = "Deletes a location from the end locations list")
@app_commands.describe(location = "Location to delete from the locations list")
async def del_location(interaction: discord.Interaction, location: str):

	with open("locations.txt", "r") as locations_file:
		all_locations = locations_file.readlines()

	for existing_location in all_locations:

		if location == existing_location.removesuffix('\n'):

			all_locations.remove(existing_location)
			with open("locations.txt", "w") as locations_file:
				locations_file.writelines(all_locations)

			await BOT_CHANNEL.send(f"**{location}** deleted from end locations list by **{interaction.user.display_name}**")
			await interaction.response.send_message(f"**{location}** deleted from the list of end locations", ephemeral = True)
			break

	else: await interaction.response.send_message(f"Location **{location}** not found in end locations list", ephemeral = True)

@bot.tree.command(name = "add-location", description = "Adds a location to the end locations list")
@app_commands.describe(location = "Location to add to the locations list")
async def add_location(interaction: discord.Interaction, location: str):

	with open("locations.txt", "r") as location_list:
		all_locations = location_list.readlines()

	for existing_location in all_locations:
		if fuzz.ratio(location, existing_location) >= 75:
			await interaction.response.send_message(f"**{location}** too closely matches **{existing_location}**", ephemeral = True)
			break

	else:
		with open("locations.txt", "a") as location_list:
			location_list.write(location + '\n')

		await BOT_CHANNEL.send(f"**{location}** added to end locations list by **{interaction.user.display_name}**")
		await interaction.response.send_message(f"**{location}** added to the list of end locations", ephemeral = True)

@bot.tree.command(name = "locations", description = "Lists all the possible end locations for Manhunt")
async def locations(interaction: discord.Interaction):

	with open("locations.txt", "r") as location_list:
		all_locations = "".join(location_list.readlines())

	await interaction.response.send_message(all_locations, ephemeral = True)

@bot.tree.command(name = "bot-credits", description = "Lists the credits for the bot")
async def bot_credits(interaction: discord.Interaction):

	await interaction.response.send_message("This bot was coded by Alex T-J (EMS 2023)", ephemeral = True)

@bot.tree.command(name = "manhunt-help", description = "Explains all of the Manhunt bot commands")
async def manhunt_help(interaction: discord.Interaction):

	help_message = (

		"\n/suggest-game  : Suggests a game of Manhunt, people react to join\n"
		"/unsuggest : Deletes any outstanding game suggestions\n"
		"/start-game <headstart> <runtime> <endtime>: Starts the current suggestion as a game\n"
		"/end-game : Ends the current game, regardless of the game state\n\n"

		"/locations : Lists all the possible end locations\n"
		"/add-location <location> : Adds a location to the possible end location list\n"
		"/del-location <location> : Deletes a location from the possible end location list\n\n"

		"/catch <runner> : A hunter has caught a specific runner\n"
		"/resign : A player resigns\n"
		"/disqualify <player> : A player is disqualified\n"
		"/win : A runner has made it to the end location successfully\n\n"

		"/extend <phase> <time> : Extends a given phase by a given number of minutes\n"
		"/shorten <phase> <time> : Shortens a given phase by a given number of minutes\n"
		"/set-location <location> : Changes the end location for a game\n\n"

		"/add-player <discord-name> : Adds a player to the game as a runner, after it has started\n"
		"/add-hunter <name | random> : Makes a random / chosen player a hunter\n\n"

		"/players-list : Lists the players in the current game, and their current status\n"
		"/comment : Add an observation to the game log of a current game\n"
		"/random-runner : Picks a random runner\n\n"

		"/bot-credits : Credits for the bot\n"
		)
	
	await interaction.response.send_message(help_message, ephemeral = True)

v.reset_vars()
bot.run('')
