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

v = Variables()

########## FUNCTIONS ##########

def log(message:str):
	"""Adds a message to the 'current.txt' log with a preceding timestamp"""

	time = datetime.datetime.now().strftime("%H:%M:%S")
	message = f"{time} {message}\n"

	with open("current.txt", "w") as log_file:
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

	except Exception as e: print(e)




































@tasks.loop(seconds=10)
async def check_game_status():

	if v.game_running:
		now = datetime.datetime.now()
		start_time, headstart, gametime, endtime = v.timings

		if now > start_time + datetime.timedelta(minutes=headstart):
			if not headstart_announced:
				await BOT_CHANNEL.send("The Manhunt game has entered the main phase, and the hunters can now leave")
				log("PHASE HEADSTART END")
				headstart_announced = True

		elif now > start_time + datetime.timedelta(minutes=gametime) + datetime.timedelta(minutes=headstart):
			if not main_game_announced:
				await BOT_CHANNEL.send(f"The Manhunt game has entered the end phase. The end location is {v.end_location}")
				log("PHASE MAINGAME END")
				main_game_announced = True

		elif now > start_time + datetime.timedelta(minutes=endtime) + datetime.timedelta(minutes=gametime) + datetime.timedelta(minutes=headstart):
			if not end_time_announced:
				await BOT_CHANNEL.send("The Manhunt game has now finished")
				log("PHASE ENDTIME END")
				end_time_announced = True
				v.end_game = True

		if len(v.players['runners']) == 0:
			v.end_game = True

		if v.end_game:

			v.reset_vars()

			with open("current.txt", "r") as log_file:
				log_content = " ".join(log_file.readlines())

			if "WIN" in log_content:
				await BOT_CHANNEL.send("The Manhunt game has ended. The hunters have lost!")
				log("GAME ENDED - HUNTERS WIN")
			else:
				await BOT_CHANNEL.send("The Manhunt game has ended. The hunters have won!")
				log("GAME ENDED - HUNTERS LOSE")

			start_time_str = timings[0].strftime("%Y%m%d%H%M%S")
			log_file_path = f"logs/{start_time_str}.txt"

			with open(log_file_path, "w") as new_log_file:
				new_log_file.write(log_content)

			await LOG_CHANNEL.send(file=discord.File(log_file_path, filename="log.txt"))

	else: pass

@check_game_status.before_loop
async def before_check_game_status():
	await bot.wait_until_ready()

@bot.tree.command(name="start-game")
@app_commands.describe(headstart = "How long the runners' headstart is", gametime = "How long the main game period lasts", endtime = "How long runners have to reach the end location")
async def start_game(interaction: discord.Interaction, headstart:int=5, gametime:int=70, endtime:int=15):

		if os.path.exists("current.txt"): # This checks for an active suggestion file

			try:
				with open("current.txt", "r") as game_file:
					message_id = game_file.read() # Gets the message id of the suggestion, in order to collect all reactions

				message = await BOT_CHANNEL.fetch_message(message_id)
				reaction_data = {}

				for reaction in message.reactions:
					async for user in reaction.users():
						
						if user.id != bot.user.id: # Discounts the bot's initial reactions

							user_name = str(user)
							reaction_name = str(reaction)

							if reaction_name not in reaction_data: reaction_data[reaction_name] = []

							reaction_data[reaction_name].append(user_name)

				if RUNNER_REACTION not in reaction_data or HUNTER_REACTION not in reaction_data:
					message = "There is not enough runners / hunters to start a game. Make sure there is at least 1 of each."
					await interaction.response.send_message(message, ephemeral=True)

				elif len(reaction_data[RUNNER_REACTION]) + len(reaction_data[HUNTER_REACTION]) != len(set(reaction_data[RUNNER_REACTION] + reaction_data[HUNTER_REACTION])):
					message = 'Someone appears to have reacted to both the runner and hunter roles. Please remove duplicate reactions'
					await interaction.response.send_message(message, ephemeral=True)

				elif headstart <= 0 or gametime <= 0 or endtime <= 0:
					message = 'All game times must be greater than 0. Try again with valid game times'
					await interaction.response.send_message(message, ephemeral=True)

				else: 
					global players, timings
					timings = [datetime.datetime.now(), headstart, gametime, endtime]
					players = {}
					players['runners'] = reaction_data[RUNNER_REACTION]
					players['hunters'] = reaction_data[HUNTER_REACTION]
					player_count = len(players["hunters"]) + len(players["runners"])
					game_running = True


			except discord.errors.NotFound:

				message = f"Message with ID {message_id} not found."
				await interaction.response.send_message(message, ephemeral=True)

			if game_running:
				
				choose_random_location() # Chooses a random location and assigns it to global var end_location
				
				for player_name in players['runners']: # Gives all runners the runner role
					target_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
					member = discord.utils.get(interaction.guild.members, name=player_name)
					member.add_roles(target_role)

				for player_name in players['hunters']: # Gives all hunters the hunter role
					target_role = discord.utils.get(interaction.guild.roles, name=HUNTER_ROLE)
					member = discord.utils.get(interaction.guild.members, name=player_name)
					member.add_roles(target_role)

				with open("current.txt", "a") as game_file:
					game_file.write(f'START {str(datetime.datetime.now())}\n\n')
					game_file.write(f"PLAYERS {player_count}\n")
					for player in reaction_data[RUNNER_REACTION]:
						game_file.write(f"RUNNER {player}\n")
					for player in reaction_data[HUNTER_REACTION]:
						game_file.write(f"RUNNER {player}\n")
					game_file.write(f"\nTIMES {headstart} {gametime} {endtime}\n")
					game_file.write(f"LOCATION {end_location}\n\n")
					game_file.write(f"-----  MAIN LOG  -----\n\n")

				await HUNTER_CHANNEL.send(f"The end location is : {end_location}") # tells the hunters the end location
				
				message = f"The game has been started by {interaction.user.name}, with {player_count} players. The hunter(s) are : {' '.join(reaction_data[HUNTER_REACTION])}.\n\nReminders : \n\n1. Message your flat person\n2. Check the weather\n3. Be aware of timings, and how long it will take to get back to accommodation\n4. Do you have flat keys on you\n5. Is your phone sufficiently charged\n\nThe timings are as follows : \nHeadstart : {headstart}m\nMain game time : {gametime}m\nEnd time : {endtime}m\n\nHave fun!"
				await BOT_CHANNEL.send(message)
				

		else:
			message = "There is not currently an active game suggestion"
			await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="suggest-game")
@app_commands.describe()
async def suggest_game(interaction: discord.Interaction):

	if os.path.exists("current.txt"):
		message = 'There is already an open suggestion. Please delete this before attempting to suggest another game.'
		await interaction.response.send_message(message, ephemeral=True)
		
	else:

		message = await BOT_CHANNEL.send(f"A game of Manhunt has been suggested by {interaction.user.name}. React to this message with :bow_and_arrow: or :athletic_shoe: in order to join this game.")

		await message.add_reaction(RUNNER_REACTION)
		await message.add_reaction(HUNTER_REACTION)
		message_id = str(message.id) + '\n'

		with open("current.txt", "w") as game_file:
			game_file.write(message_id)

		message = 'A game of Manhunt has been suggested'
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="resign")
@app_commands.describe()
async def resign(interaction: discord.Interaction):

	if game_running:
		player_name = interaction.user.name

		if player_name in players['runners']:
			runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
			member = discord.utils.get(interaction.guild.members, name=player_name)
			await member.remove_roles(runner_role)
			players['runners'].remove(player_name)
			log(f"RESIGN {player_name}")
			log(f"{player_name} -> LEAVES")
			await BOT_CHANNEL.send(f"{player_name} has resigned from the game.")

		elif player_name in players['hunters']:
			hunter_role = discord.utils.get(interaction.guild.roles, name=HUNTER_ROLE)
			member = discord.utils.get(interaction.guild.members, name=player_name)
			await member.remove_roles(hunter_role)
			players['hunters'].remove(player_name)
			log(f"RESIGN {player_name}")
			log(f"{player_name} -> LEAVES")

			if len(players["hunters"]) == 0:
				await BOT_CHANNEL.send(f"{player_name} has resigned from the game. There are now 0 hunters. Please pick a new hunter")

			else:
				await BOT_CHANNEL.send(f"{player_name} has resigned from the game")

		else:
			message = "You are not currently a player in the game."
			await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "There is not an active Manhunt game"
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="add-player")
@app_commands.describe()
async def add_player(interaction: discord.Interaction):

	if game_running:
		player_name = interaction.user.name

		if player_name in players['runners'] or player_name in players['hunters']:
			message = f"You ({player_name}) are already in the game."
		else:
			players['runners'].append(player_name)
			message = f"You ({player_name}) have been added to the game as a runner."

			member = discord.utils.get(interaction.guild.members, name=player_name)
			runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
			await member.add_roles(runner_role)

			await BOT_CHANNEL.send(f"{interaction.user.name} has been added to the game as a runner.")

			log(f"LATE-PLAYER-ADD {player_name}")
			log(f"{player_name} -> RUNNER")

		await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "The game has not started yet"
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="add-hunter")
@app_commands.describe()
async def add_hunter(interaction: discord.Interaction):
	
	if game_running:
		player_name = interaction.user.name

		if player_name in players['runners']:

			member = discord.utils.get(interaction.guild.members, name=player_name)
			hunter_role = discord.utils.get(interaction.guild.roles, name=HUNTER_ROLE)
			runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
			await member.remove_roles(runner_role)
			await member.add_roles(hunter_role)

			players['runners'].remove(player_name)
			players['hunters'].append(player_name)
			message = f"You ({player_name}) have been converted from a runner to a hunter."
			log(f"PLAYER {player_name} Runner -> Hunter")
			await BOT_CHANNEL.send(f"{interaction.user.name} has made themself a hunter")

		else:
			message = "You are not a runner. Only runners can be converted to hunters."

		await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "The game has not started yet."
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="random-runner")
@app_commands.describe()
async def random_runner(interaction: discord.Interaction):

	if game_running:
		if players['runners']:
			random_runner = random.choice(players['runners'])
			message = f"The randomly selected runner is: {random_runner}"
			await BOT_CHANNEL.send('{interaction.user.name} used the random-runner command, {random_runner} was selected')
		else:
			message = "There are no runners currently in the game."

		await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "The game has not started yet."
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="catch")
@app_commands.describe(runner="The runner caught by the hunter")
async def catch(interaction: discord.Interaction, runner: discord.Member):

	if game_running:
		hunter_name = interaction.user.name

		if hunter_name in players['hunters']:

			runner_name = runner.name

			if runner_name in players['runners']:

				member = discord.utils.get(interaction.guild.members, name=runner_name)
				hunter_role = discord.utils.get(interaction.guild.roles, name=HUNTER_ROLE)
				runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
				await member.remove_roles(runner_role)
				await member.add_roles(hunter_role)				

				players['runners'].remove(runner_name)
				players['hunters'].append(runner_name)
				log(f"{hunter_name} CATCH {runner_name}")
				log(f"{runner_name} -> HUNTER")

				await BOT_CHANNEL.send("{runner_name} has been caught by {interaction.user.name}. They are now a hunter")

			else:
				message = f"{runner_name} is not currently a runner in the current game."
				await interaction.response.send_message(message, ephemeral=True)
		else:
			message = "You are not a hunter. Only hunters can use the /catch command."
			await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "There is not an active Manhunt game"
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="disqualify")
@app_commands.describe(player="The player to be disqualified", reason="Reason for disqualification")
async def disqualify(interaction: discord.Interaction, player: discord.Member, reason: str):

	if game_running:

		disqualified_name = player.name

		if disqualified_name in players['runners']:
			runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
			await player.remove_roles(runner_role)
			log(f"{interaction.user.name} DISQUALIFIES {disqualified_name} REASON: {reason}")
			log(f"{disqualified_name} -> LEAVES")
			await BOT_CHANNEL.send(f"{disqualified_name} has been disqualified by {interaction.user.name}. They are no longer a participant. Reason: {reason}")
		
		elif disqualified_name in players['hunters']:
			hunter_role = discord.utils.get(interaction.guild.roles, name=HUNTER_ROLE)
			await player.remove_roles(hunter_role)
			log(f"{interaction.user.name} DISQUALIFIES {disqualified_name} reason: {reason}")
			log(f"{disqualified_name} -> LEAVES")
			await BOT_CHANNEL.send(f"{disqualified_name} has been disqualified by {interaction.user.name}. They are no longer a participant. Reason: {reason}")

		else:
			message = f"{disqualified_name} is not currently a participant in the current game."
			await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "There is not an active Manhunt game"
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="win")
@app_commands.describe()
async def win(interaction: discord.Interaction):

	if game_running:

		winner_name = interaction.user.name

		if winner_name in players['runners']:

			winner = discord.utils.get(interaction.guild.members, name=winner_name)
			runner_role = discord.utils.get(interaction.guild.roles, name=RUNNER_ROLE)
			await winner.remove_roles(runner_role)

			log(f"WIN {winner_name}")
			log(f"{winner_name} -> LEAVES")

			await BOT_CHANNEL.send(f"{winner_name} has successfully reached the end location and won the game!")

			players['runners'].remove(winner_name)

		else:
			message = f"{winner_name} is not currently a runner in the current game."
			await interaction.response.send_message(message, ephemeral=True)
	else:
		message = "There is not an active Manhunt game"
		await interaction.response.send_message(message, ephemeral=True)

@bot.tree.command(name="extend")
@app_commands.describe(phase="The phase to extend ('headstart', 'gametime', or 'endtime')", time="The number of minutes to extend the phase")
async def extend(interaction: discord.Interaction, phase: str, time: int):

	if v.game_running:

		phases = ['headstart', 'gametime', 'endtime']

		if phase in phases:
			now = datetime.datetime.now()
			start_time, headstart, gametime, endtime = timings

			if phase == 'headstart' and start_time + datetime.timedelta(minutes=headstart) > now:
				timings[1] += time
				log(f"PHASE {phase.upper()} ADD {time}")
				await BOT_CHANNEL.send(f"{interaction.user.name} has extended {phase} by {time} minutes.")
			elif phase == 'gametime' and start_time + datetime.timedelta(minutes=gametime) + datetime.timedelta(minutes=headstart) > now:
				timings[2] += time
				log(f"PHASE {phase.upper()} ADD {time}")
				await BOT_CHANNEL.send(f"{interaction.user.name} has extended {phase} by {time} minutes.")
			elif phase == 'endtime' and start_time + datetime.timedelta(minutes=endtime) + datetime.timedelta(minutes=gametime) + datetime.timedelta(minutes=headstart) > now:
				timings[3] += time
				log(f"PHASE {phase.upper()} ADD {time}")
				await BOT_CHANNEL.send(f"{interaction.user.name} has extended {phase} by {time} minutes.")
			else:
				message = f"{phase.capitalize()} has already passed or is currently happening. You cannot extend it."
				await interaction.response.send_message(message, ephemeral=True)

		else: await interaction.response.send_message("Invalid phase. Please choose 'headstart', 'gametime', or 'endtime'", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)



































@bot.tree.command(name = "shorten", description = "Removes a given number of minutes from a given phase")
@app_commands.describe(phase = "The phase to shorten ('headstart', 'gametime', or 'endtime')", time = "The number of minutes to shorten the phase")
async def shorten(interaction: discord.Interaction, phase: str, time: int):

	if v.game_running:

		if phase in ['headstart', 'gametime', 'endtime']:

			now = datetime.datetime.now()
			start_time, headstart, gametime, endtime = v.timings

			if phase == 'headstart' and start_time + datetime.timedelta(minutes = headstart) - datetime.timedelta(minutes = time) > now and time < v.timings[1]:
				v.timings[1] -= time
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes.")

			elif phase == 'gametime' and start_time + datetime.timedelta(minutes = gametime) + datetime.timedelta(minutes = headstart) - datetime.timedelta(minutes = time) > now and time < v.timings[2]:
				v.timings[2] -= time
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes.")

			elif phase == 'endtime' and start_time + datetime.timedelta(minutes = endtime) + datetime.timedelta(minutes = gametime) + datetime.timedelta(minutes = headstart) - datetime.timedelta(minutes = time) > now and time < v.timings[3]:
				v.timings[3] -= time
				log(f"PHASE {phase.upper()} SUBTRACT {time}")
				await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has shortened **{phase}** by **{time}** minutes.")

			else: await interaction.response.send_message(f"{phase.capitalize()} has already passed, or the given time is not appropriate", ephemeral = True)

		else: await interaction.response.send_message("Invalid phase. Please choose 'headstart', 'gametime', or 'endtime'.", ephemeral = True)

	else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

@bot.tree.command(name = "set-location", description = "Changes the end location of a manhunt game")
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
					await BOT_CHANNEL.send(f"**{interaction.user.display_name}** has changed the end location.")

				else: await interaction.response.send_message(f"Location **{location}** does not exist. Please use a valid end location", ephemeral = True)

			else: await interaction.response.send_message("You can only change the location during the headstart or gametime phase.", ephemeral = True)

		else: await interaction.response.send_message("There is not an active Manhunt game", ephemeral = True)

	else: await interaction.response.send_message('You do not have the required permissions to use this command', ephemeral = True)

@bot.tree.command(name = "end-game", description = "Ends the game unconditionally")
async def end_game(interaction: discord.Interaction):

	admin_role = discord.utils.get(interaction.guild.roles, name = v.ADMIN_ROLE)

	if admin_role in interaction.user.roles:

		if v.game_running:

			log("GAME ENDED - NO WIN")

			with open("current.txt", "r") as log_file:
				log_content = log_file.read()

			start_time_str = v.timings[0].strftime("%Y%m%d%H%M%S")
			log_file_path = f"logs/{start_time_str}.txt"

			with open(log_file_path, "w") as new_log_file:
				new_log_file.write(log_content)

			runner_role = discord.utils.get(interaction.guild.roles, name = v.RUNNER_ROLE)
			for runner in v.players['runners']:
				member = discord.utils.get(interaction.guild.members, name = runner)
				if member: await member.remove_roles(runner_role)
			
			hunter_role = discord.utils.get(interaction.guild.roles, name = v.HUNTER_ROLE)
			for hunter in v.players['hunters']:
				member = discord.utils.get(interaction.guild.members, name = hunter)
				if member: await member.remove_roles(hunter_role)

			v.reset_vars()

			await LOG_CHANNEL.send(file = discord.File(log_file_path, filename = "log.txt"))
			await BOT_CHANNEL.send("The current Manhunt game has been unconditionally ended by **{interaction.user.display_name}**")

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
		"/random-runner : Picks a random runner\n\n"

		"/bot-credits : Credits for the bot\n"
		)
	
	await interaction.response.send_message(help_message, ephemeral = True)

#check_game_status.start()
bot.run('MTE4MzkzNTAyMjI3Nzg1NzM4Mg.G5ahR1.hLj-Ze1XEWIseTwEpFLprpYpqAu7aGQlJsfs9k')
