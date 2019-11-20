"""
	Commands and utilities related to Juveniles.
"""
import time
import random
import math

import ewcfg
import ewutils
import ewcmd
import ewitem
import ewmap
import ewrolemgr
import ewstats
import ewworldevent

from ewitem import EwItem
from ew import EwUser
from ewmarket import EwMarket
from ewdistrict import EwDistrict
from ewworldevent import EwWorldEvent

# Map of user ID to a map of recent miss-mining time to count. If the count
# exceeds 11 in 20 seconds, you die.
last_mismined_times = {}

juviesrow_mines = {}
toxington_mines = {}
cratersville_mines = {}

mines_map = {
	ewcfg.poi_id_mine: juviesrow_mines,
	ewcfg.poi_id_tt_mines: toxington_mines,
	ewcfg.poi_id_cv_mines: cratersville_mines
}


class EwMineGrid:
	grid_type = ""
	
	grid = []

	message = ""
	wall_message = ""

	times_edited = 0

	time_last_posted = 0

	cells_mined = 0

	def __init__(self, grid = [], grid_type = ""):
		self.grid = grid
		self.grid_type = grid_type
		self.message = ""
		self.wall_message = ""
		self.times_edited = 0
		self.time_last_posted = 0
		self.cells_mined = 0


""" player enlists in a faction/gang """
async def enlist(cmd):
	user_data = EwUser(member = cmd.message.author)
	user_slimes = user_data.slimes
	time_now = int(time.time())
	bans = user_data.get_bans()
	vouchers = user_data.get_vouchers()

	if user_data.life_state == ewcfg.life_state_corpse:
		response = "You're dead, bitch."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	elif user_slimes < ewcfg.slimes_toenlist:
		response = "You need to mine more slime to rise above your lowly station. ({}/{})".format(user_slimes, ewcfg.slimes_toenlist)
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if cmd.tokens_count > 1:
		desired_faction = cmd.tokens[1].lower()
	else:
		response = "Which faction? Say '{} {}' or '{} {}'.".format(ewcfg.cmd_enlist, ewcfg.faction_killers, ewcfg.cmd_enlist, ewcfg.faction_rowdys)
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if desired_faction == ewcfg.faction_killers:
		if ewcfg.faction_killers in bans:
			response = "You are banned from enlisting in the {}.".format(ewcfg.faction_killers)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		elif ewcfg.faction_killers not in vouchers and user_data.faction != ewcfg.faction_killers:
			response = "You need a current gang member's permission to join the {}.".format(ewcfg.faction_killers)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		elif user_data.life_state in [ewcfg.life_state_enlisted, ewcfg.life_state_kingpin] and user_data.faction == ewcfg.faction_killers:
			response = "You are already enlisted in the {}! Look, your name is purple! Get a clue, idiot.".format(user_data.faction)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		elif user_data.faction == ewcfg.faction_rowdys:
			response = "Traitor! You can only {} in the {}, you treacherous cretin. Ask for a {} if you're that weak-willed.".format(ewcfg.cmd_enlist, user_data.faction, ewcfg.cmd_pardon)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		else:
			response = "Enlisting in the {}.".format(ewcfg.faction_killers)
			user_data.life_state = ewcfg.life_state_enlisted
			user_data.faction = ewcfg.faction_killers
			user_data.time_lastenlist = time_now + ewcfg.cd_enlist
			user_data.persist()
			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

	elif desired_faction == ewcfg.faction_rowdys:
		if ewcfg.faction_rowdys in bans:
			response = "You are banned from enlisting in the {}.".format(ewcfg.faction_rowdys)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		if ewcfg.faction_rowdys not in vouchers and user_data.faction != ewcfg.faction_rowdys:
			response = "You need a current gang member's permission to join the {}.".format(ewcfg.faction_rowdys)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		elif user_data.life_state in [ewcfg.life_state_enlisted, ewcfg.life_state_kingpin] and user_data.faction == ewcfg.faction_rowdys:
			response = "You are already enlisted in the {}! Look, your name is pink! Get a clue, idiot.".format(user_data.faction)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		elif user_data.faction == ewcfg.faction_killers:
			response = "Traitor! You can only {} in the {}, you treacherous cretin. Ask for a {} if you're that weak-willed.".format(ewcfg.cmd_enlist, user_data.faction, ewcfg.cmd_pardon)
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		else:
			response = "Enlisting in the {}.".format(ewcfg.faction_rowdys)
			user_data.life_state = ewcfg.life_state_enlisted
			user_data.faction = ewcfg.faction_rowdys
			user_data.time_lastenlist = time_now + ewcfg.cd_enlist
			user_data.persist()
			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

	else:
		response = "That's not a valid gang you can enlist in, bitch."

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def renounce(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.life_state == ewcfg.life_state_corpse:
		response = "You're dead, bitch."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	elif user_data.life_state != ewcfg.life_state_enlisted:
		response = "What exactly are you renouncing? Your lackadaisical, idyllic life free of vice and violence? You aren't actually currently enlisted in any gang, retard."

	elif user_data.poi not in [ewcfg.poi_id_rowdyroughhouse, ewcfg.poi_id_copkilltown]:
		response = "To turn in your badge, you must return to your soon-to-be former gang base."

	else:
		renounce_fee = int(user_data.slimes) / 2
		user_data.change_slimes(n = -renounce_fee)
		faction = user_data.faction
		user_data.life_state = ewcfg.life_state_juvenile
		user_data.weapon = -1
		user_data.persist()
		response = "You are no longer enlisted in the {}, but you are not free of association with them. Your former teammates immediately begin to beat the shit out of you, knocking {} slime out of you before you're able to get away.".format(faction, renounce_fee)
		await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" mine for slime (or endless rocks) """
async def mine(cmd):
	market_data = EwMarket(id_server = cmd.message.author.server.id)
	user_data = EwUser(member = cmd.message.author)
	mutations = user_data.get_mutations()
	time_now = int(time.time())
	poi = ewcfg.id_to_poi.get(user_data.poi)

	response = ""
	# Kingpins can't mine.
	if user_data.life_state == ewcfg.life_state_kingpin or user_data.life_state == ewcfg.life_state_grandfoe:
		return

	# ghosts cant mine (anymore)
	if user_data.life_state == ewcfg.life_state_corpse:
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You can't mine while you're dead. Try {}.".format(ewcfg.cmd_revive)))

	# Enlisted players only mine at certain times.
	if user_data.life_state == ewcfg.life_state_enlisted:
		if user_data.faction == ewcfg.faction_rowdys and (market_data.clock < 8 or market_data.clock > 17):
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Rowdies only mine in the daytime. Wait for full daylight at 8am.".format(ewcfg.cmd_revive)))

		if user_data.faction == ewcfg.faction_killers and (market_data.clock < 20 and market_data.clock > 5):
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Killers only mine under cover of darkness. Wait for nightfall at 8pm.".format(ewcfg.cmd_revive)))

	# Mine only in the mines.
	if cmd.message.channel.name in [ewcfg.channel_mines, ewcfg.channel_cv_mines, ewcfg.channel_tt_mines]:

		if user_data.hunger >= user_data.get_hunger_max():
			return await mismine(cmd, user_data, "exhaustion")
			#return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You've exhausted yourself from mining. You'll need some refreshment before getting back to work."))

		else:
			printgrid = True
			hunger_cost_mod = ewutils.hunger_cost_mod(user_data.slimelevel)
			extra = hunger_cost_mod - int(hunger_cost_mod)  # extra is the fractional part of hunger_cost_mod

			world_events = ewworldevent.get_world_events(id_server = cmd.message.server.id)
			minigame_event = None
			for id_event in world_events:
				if world_events.get(id_event) in ewcfg.grid_type_by_mining_event:
					event_data = EwWorldEvent(id_event = id_event)
					if event_data.event_props.get('poi') == user_data.poi:
						minigame_event = event_data.event_type
				if world_events.get(id_event) == ewcfg.event_type_minecollapse:
					event_data = EwWorldEvent(id_event = id_event)
					if event_data.event_props.get('id_user') == user_data.id_user and event_data.event_props.get('poi') == user_data.poi:
						captcha = event_data.event_props.get('captcha').lower()
						tokens_lower = []
						for token in cmd.tokens[1:]:
							tokens_lower.append(token.lower())

						if captcha in tokens_lower:
							ewworldevent.delete_world_event(id_event = id_event)
							response = "You escape from the collapsing mineshaft."
							return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
						else:
							return await mismine(cmd, user_data, ewcfg.event_type_minecollapse)

			if user_data.poi not in mines_map:
				response = "You can't mine here! Go to the mines in Juvie's Row, Toxington, or Cratersville!"
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
			elif user_data.id_server not in mines_map.get(user_data.poi):
				init_grid(user_data.poi, user_data.id_server)
				printgrid = True

			grid_cont = mines_map.get(user_data.poi).get(user_data.id_server)
			grid = grid_cont.grid

			grid_type = ewcfg.grid_type_by_mining_event.get(minigame_event)
			if grid_type != grid_cont.grid_type:
				init_grid(user_data.poi, user_data.id_server)
				printgrid = True
				grid_cont = mines_map.get(user_data.poi).get(user_data.id_server)
				grid = grid_cont.grid

			#minesweeper = True
			#grid_multiplier = grid_cont.cells_mined ** 0.4
			#flag = False
			mining_yield = get_mining_yield_by_grid_type(cmd, grid_cont)

			if type(mining_yield) == type(""):
				response = mining_yield
				if len(response) > 0:
					await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
				return await print_grid(cmd)
					


			if mining_yield == 0:
				user_data.hunger += ewcfg.hunger_permine * int(hunger_cost_mod)
				user_data.persist()
				#response = "This vein has already been mined dry."
				#await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
				if printgrid:
					return await print_grid(cmd)
				else:
					return



			has_pickaxe = False

			if user_data.weapon >= 0:
				weapon_item = EwItem(id_item = user_data.weapon)
				weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
				if weapon.id_weapon == ewcfg.weapon_id_pickaxe:
					has_pickaxe = True

			# Determine if an item is found.
			unearthed_item = False
			unearthed_item_amount = 0

			# juvies get items 4 times as often as enlisted players
			unearthed_item_chance = 1 / ewcfg.unearthed_item_rarity
			if user_data.life_state == ewcfg.life_state_juvenile:
				unearthed_item_chance *= 2
			if has_pickaxe == True:
				unearthed_item_chance *= 1.5
			if ewcfg.mutation_id_lucky in mutations:
				unearthed_item_chance *= 1.33

			# event bonus
			for id_event in world_events:

				if world_events.get(id_event) == ewcfg.event_type_slimefrenzy:
					event_data = EwWorldEvent(id_event = id_event)
					if event_data.event_props.get('poi') == user_data.poi and event_data.event_props.get('id_user') == user_data.id_user:
						mining_yield *= 2

				if world_events.get(id_event) == ewcfg.event_type_poudrinfrenzy:
					event_data = EwWorldEvent(id_event = id_event)
					if event_data.event_props.get('poi') == user_data.poi and event_data.event_props.get('id_user') == user_data.id_user:
						unearthed_item_chance = 1

			if random.random() < 0.05:
				id_event = create_mining_event(cmd)
				event_data = EwWorldEvent(id_event = id_event)

				if event_data.id_event == -1:
					return ewutils.logMsg("Error couldn't find world event with id {}".format(id_event))

				if event_data.event_type == ewcfg.event_type_slimeglob:
					mining_yield *= 4
					ewworldevent.delete_world_event(id_event = id_event)

				if event_data.time_activate <= time.time():

					event_def = ewcfg.event_type_to_def.get(event_data.event_type)
					if event_def == None:
						return ewutils.logMsg("Error, couldn't find event def for event type {}".format(event_data.event_type))
					str_event_start = event_def.str_event_start
					if event_data.event_type == ewcfg.event_type_minecollapse:
						str_event_start = str_event_start.format(cmd = ewcfg.cmd_mine, captcha = event_data.event_props.get('captcha'))
					response += str_event_start + "\n"
				if event_data.event_type in [ewcfg.event_type_minesweeper, ewcfg.event_type_pokemine, ewcfg.event_type_bubblebreaker]:
					init_grid(poi = event_data.event_props.get('poi'), id_server = event_data.id_server)
					printgrid = True

			if random.random() < unearthed_item_chance:
				unearthed_item = True
				unearthed_item_amount = 1 if random.randint(1, 3) != 1 else 2  # 33% chance of extra drop

			if unearthed_item == True:
				# If there are multiple possible products, randomly select one.
				item = random.choice(ewcfg.mine_results)

				item_props = ewitem.gen_item_props(item)

				for creation in range(unearthed_item_amount):
					ewitem.item_create(
						item_type = item.item_type,
						id_user = cmd.message.author.id,
						id_server = cmd.message.server.id,
						item_props = item_props
					)

				if unearthed_item_amount == 1:
					response += "You unearthed a {}! ".format(item.str_name)
				elif unearthed_item_amount == 2:
					response += "You unearthed two (2) {}! ".format(item.str_name)


				ewstats.change_stat(user = user_data, metric = ewcfg.stat_lifetime_poudrins, n = unearthed_item_amount)

				ewutils.logMsg('{} has found {} {}(s)!'.format(cmd.message.author.display_name, item.str_name, unearthed_item_amount))

			user_initial_level = user_data.slimelevel

			# Add mined slime to the user.
			slime_bylevel = ewutils.slime_bylevel(user_data.slimelevel)

			#mining_yield = math.floor((slime_bylevel / 10) + 1)
			#alternate_yield = math.floor(200 + slime_bylevel ** (1 / math.e))

			#mining_yield = min(mining_yield, alternate_yield)

			if poi.is_subzone:
				district_data = EwDistrict(district = poi.mother_district, id_server = cmd.message.server.id)
			else:
				district_data = EwDistrict(district = poi.id_poi, id_server = cmd.message.server.id)

			if district_data.controlling_faction != "" and district_data.controlling_faction == user_data.faction:
				mining_yield *= 2

			if has_pickaxe == True:
				mining_yield *= 2
			if user_data.life_state == ewcfg.life_state_juvenile:
				mining_yield *= 2
			# Fatigue the miner.

			user_data.hunger += ewcfg.hunger_permine * int(hunger_cost_mod)
			if extra > 0:  # if hunger_cost_mod is not an integer
				# there's an x% chance that an extra stamina is deducted, where x is the fractional part of hunger_cost_mod in percent (times 100)
				if random.randint(1, 100) <= extra * 100:
					user_data.hunger += ewcfg.hunger_permine

			levelup_response = user_data.change_slimes(n = mining_yield, source = ewcfg.source_mining)

			was_levelup = True if user_initial_level < user_data.slimelevel else False

			# Tell the player their slime level increased and/or they unearthed an item.
			if was_levelup:
				response += levelup_response

			user_data.persist()

			if printgrid:
				await print_grid(cmd)


	else:
		return await mismine(cmd, user_data, "channel")
		#response = "You can't mine here! Go to the mines in Juvie's Row, Toxington, or Cratersville!"

	if len(response) > 0:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" mine for slime (or endless rocks) """
async def flag(cmd):
	market_data = EwMarket(id_server = cmd.message.author.server.id)
	user_data = EwUser(member = cmd.message.author)
	mutations = user_data.get_mutations()
	time_now = int(time.time())

	response = ""
	# Kingpins can't mine.
	if user_data.life_state == ewcfg.life_state_kingpin or user_data.life_state == ewcfg.life_state_grandfoe:
		return

	# ghosts cant mine (anymore)
	if user_data.life_state == ewcfg.life_state_corpse:
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You can't mine while you're dead. Try {}.".format(ewcfg.cmd_revive)))

	# Enlisted players only mine at certain times.
	if user_data.life_state == ewcfg.life_state_enlisted:
		if user_data.faction == ewcfg.faction_rowdys and (market_data.clock < 8 or market_data.clock > 17):
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Rowdies only mine in the daytime. Wait for full daylight at 8am.".format(ewcfg.cmd_revive)))

		if user_data.faction == ewcfg.faction_killers and (market_data.clock < 20 and market_data.clock > 5):
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Killers only mine under cover of darkness. Wait for nightfall at 8pm.".format(ewcfg.cmd_revive)))

	# Mine only in the mines.
	if cmd.message.channel.name in [ewcfg.channel_mines, ewcfg.channel_cv_mines, ewcfg.channel_tt_mines]:

		if user_data.hunger >= user_data.get_hunger_max():
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You've exhausted yourself from mining. You'll need some refreshment before getting back to work."))

		else:
			printgrid = True
			hunger_cost_mod = ewutils.hunger_cost_mod(user_data.slimelevel)
			extra = hunger_cost_mod - int(hunger_cost_mod)  # extra is the fractional part of hunger_cost_mod

			world_events = ewworldevent.get_world_events(id_server = cmd.message.server.id)
			minigame_event = None
			for id_event in world_events:
				if world_events.get(id_event) in ewcfg.grid_type_by_mining_event:
					event_data = EwWorldEvent(id_event = id_event)
					if event_data.event_props.get('poi') == user_data.poi:
						minigame_event = event_data.event_type

			if minigame_event != ewcfg.event_type_minesweeper:
				response = "What do you think you can flag here?"
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

			if user_data.poi not in mines_map:
				response = "You can't mine here! Go to the mines in Juvie's Row, Toxington, or Cratersville!"
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
			elif user_data.id_server not in mines_map.get(user_data.poi):
				init_grid(user_data.poi, user_data.id_server)
				printgrid = True

			grid_cont = mines_map.get(user_data.poi).get(user_data.id_server)
			grid = grid_cont.grid

			grid_type = ewcfg.grid_type_by_mining_event.get(minigame_event)
			if grid_type != grid_cont.grid_type:
				init_grid(user_data.poi, user_data.id_server)
				printgrid = True
				grid_cont = mines_map.get(user_data.poi).get(user_data.id_server)
				grid = grid_cont.grid

			
			row = -1
			col = -1
			if cmd.tokens_count < 2:
				response = "Please specify which vein to mine."
				return response

			for token in cmd.tokens[1:]:
				
				coords = token.lower()
				if col < 1:
		
					for char in coords:
						if char in ewcfg.alphabet:
							col = ewcfg.alphabet.index(char)
							coords = coords.replace(char, "")
				if row < 1: 
					try:
						row = int(coords)
					except:
						row = -1



			row -= 1
			
			if row not in range(len(grid)) or col not in range(len(grid[row])):
				response = "Invalid vein."


			elif grid[row][col] == ewcfg.cell_empty_marked:
				grid[row][col] = ewcfg.cell_empty

			elif grid[row][col] == ewcfg.cell_mine_marked:
				grid[row][col] = ewcfg.cell_mine

			elif grid[row][col] == ewcfg.cell_empty_open:
				response = "This vein has already been mined dry."

			elif grid[row][col] == ewcfg.cell_mine:
				grid[row][col] = ewcfg.cell_mine_marked

			elif grid[row][col] == ewcfg.cell_empty:
				grid[row][col] = ewcfg.cell_empty_marked


			if printgrid:
				await print_grid(cmd)


	else:
		response = "You can't mine here! Go to the mines in Juvie's Row, Toxington, or Cratersville!"

	if len(response) > 0:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


"""
	Mining in the wrong channel or while exhausted. This is deprecated anyway but let's sorta keep it around in case we need it.
"""
async def mismine(cmd, user_data, cause):
	time_now = int(time.time())
	global last_mismined_times

	mismined = last_mismined_times.get(cmd.message.author.id)

	if mismined is None:
		mismined = {
			'time': time_now,
			'count': 0
		}

	if time_now - mismined['time'] < 20:
		mismined['count'] += 1
	else:
		# Reset counter.
		mismined['time'] = time_now
		mismined['count'] = 1

	last_mismined_times[cmd.message.author.id] = mismined

	world_events = ewworldevent.get_world_events(id_server = cmd.message.server.id)
	event_data = None
	captcha = None
	for id_event in world_events:
		if world_events.get(id_event) == ewcfg.event_type_minecollapse:
			event_data = EwWorldEvent(id_event = id_event)
			if event_data.event_props.get('id_user') == user_data.id_user:
				mine_collapse = True
				captcha = event_data.event_props.get('captcha')
	
	if mismined['count'] >= 11:  # up to 6 messages can be buffered by discord and people have been dying unfairly because of that
		if cause == ewcfg.event_type_minecollapse:
			if event_data != None:
				ewworldevent.delete_world_event(id_event = event_data.id_event)
			else:
				return
		# Lose some slime
		last_mismined_times[cmd.message.author.id] = None
		# user_data.die(cause = ewcfg.cause_mining)

		user_data.change_slimes(n = -(user_data.slimes / 2))
		user_data.persist()

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You have lost an arm and a leg in a mining accident. Tis but a scratch."))
		# await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
		# sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
		# await ewutils.send_message(cmd.client, sewerchannel, "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(cmd.message.author, "You have died in a mining accident. {}".format(ewcfg.emote_slimeskull)))
	else:
		if cause == "exhaustion":
			response = "You've exhausted yourself from mining. You'll need some refreshment before getting back to work."
		elif cause == ewcfg.event_type_minecollapse:
			if captcha != None:
				response = "The mineshaft is collapsing around you! Get out of there! ({cmd} {captcha})".format(cmd = ewcfg.cmd_mine, captcha = captcha)
			else:
				return
		else:
			response = "You can't mine in this channel. Go elsewhere."

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" scavenge for slime """
async def scavenge(cmd):
	market_data = EwMarket(id_server = cmd.message.author.server.id)
	user_data = EwUser(member = cmd.message.author)
	mutations = user_data.get_mutations()

	time_now = int(time.time())
	response = ""

	time_since_last_scavenge = time_now - user_data.time_lastscavenge

	# Kingpins can't scavenge.
	if user_data.life_state == ewcfg.life_state_kingpin or user_data.life_state == ewcfg.life_state_grandfoe:
		return

	# ghosts cant scavenge 
	if user_data.life_state == ewcfg.life_state_corpse:
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "What would you want to do that for? You're a ghost, you have no need for such lowly materialistic possessions like slime. You only engage in intellectual pursuits now. {} if you want to give into your base human desire to see numbers go up.".format(ewcfg.cmd_revive)))
	# currently not active - no cooldown
	if time_since_last_scavenge < ewcfg.cd_scavenge:
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Slow down, you filthy hyena."))

	# Scavenge only in location channels
	if ewmap.channel_name_is_poi(cmd.message.channel.name) == True:
		if user_data.hunger >= user_data.get_hunger_max():
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You are too exhausted to scrounge up scraps of slime off the street! Go get some grub!"))
		else:
			district_data = EwDistrict(district = user_data.poi, id_server = cmd.message.author.server.id)

			user_initial_level = user_data.slimelevel
			# add scavenged slime to user
			if ewcfg.mutation_id_trashmouth in mutations:
				time_since_last_scavenge *= 3

			time_since_last_scavenge = min(max(1, time_since_last_scavenge), 30)


			scavenge_mod = 0.003 * (time_since_last_scavenge ** 0.9)

			if ewcfg.mutation_id_whitenationalist in mutations and market_data.weather == "snow":
				scavenge_mod *= 1.5

			if ewcfg.mutation_id_webbedfeet in mutations:
				district_slimelevel = len(str(district_data.slimes))
				scavenge_mod *= max(1, min(district_slimelevel - 3, 4))

			scavenge_yield = math.floor(scavenge_mod * district_data.slimes)

			levelup_response = user_data.change_slimes(n = scavenge_yield, source = ewcfg.source_scavenging)
			district_data.change_slimes(n = -1 * scavenge_yield, source = ewcfg.source_scavenging)
			district_data.persist()

			if levelup_response != "":
				response += levelup_response + "\n\n"
			#response += "You scrape together {} slime from the streets.\n\n".format(scavenge_yield)
			if cmd.tokens_count > 1:
				item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
				loot_resp = ewitem.item_lootspecific(
					id_server = user_data.id_server,
					id_user = user_data.id_user,
					item_search = item_search
				)

				response += loot_resp

			else:
				loot_multiplier = 1.0 + ewitem.get_inventory_size(owner = user_data.poi, id_server = user_data.id_server)
				loot_chance = loot_multiplier / ewcfg.scavenge_item_rarity
				if ewcfg.mutation_id_dumpsterdiver in mutations:
					loot_chance *= 10
				if random.random() < loot_chance:
					loot_resp = ewitem.item_lootrandom(
						id_server = user_data.id_server,
						id_user = user_data.id_user
					)
					response += loot_resp


			# Fatigue the scavenger.
			hunger_cost_mod = ewutils.hunger_cost_mod(user_data.slimelevel)
			extra = hunger_cost_mod - int(hunger_cost_mod)  # extra is the fractional part of hunger_cost_mod

			user_data.hunger += ewcfg.hunger_perscavenge * int(hunger_cost_mod)
			if extra > 0:  # if hunger_cost_mod is not an integer
				# there's an x% chance that an extra stamina is deducted, where x is the fractional part of hunger_cost_mod in percent (times 100)
				if random.randint(1, 100) <= extra * 100:
					user_data.hunger += ewcfg.hunger_perscavenge

			user_data.time_lastscavenge = time_now

			user_data.persist()

			if not response == "":
				await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	else:
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You'll find no slime here, this place has been picked clean. Head into the city to try and scavenge some slime."))

async def crush(cmd):
	member = cmd.message.author
	user_data = EwUser(member=member)
	response = "" # if it's not overwritten
	crush_slimes = ewcfg.crush_slimes
	
	if user_data.life_state == ewcfg.life_state_corpse:
		response = "Alas, you try to shatter the item, but your ghostly form cannot firmly grasp it."
		return 	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
	item_sought = ewitem.find_item(item_search = item_search, id_user = user_data.id_user, id_server = user_data.id_server)

	if item_sought:
		sought_id = item_sought.get('id_item')
		item_data = EwItem(id_item=sought_id)

		response = "The item doesn't have !crush functionality"  # if it's not overwritten

		if item_data.item_props.get("id_item") == ewcfg.item_id_slimepoudrin:
			# delete a slime poudrin from the player's inventory
			ewitem.item_delete(id_item=sought_id)

			status_effects = user_data.getStatusEffects()
			sap_resp = ""
			if ewcfg.status_sapfatigue_id not in status_effects:
				sap_gain = 5
				sap_gain = max(0, min(sap_gain, user_data.slimelevel - (user_data.hardened_sap + user_data.sap)))
				if sap_gain > 0:
					user_data.sap += sap_gain
					user_data.applyStatus(id_status = ewcfg.status_sapfatigue_id, source = user_data.id_user)
					sap_resp = " and {} sap".format(sap_gain)

			levelup_response = user_data.change_slimes(n = crush_slimes, source = ewcfg.source_crush)
			user_data.persist()

			response = "You crush the hardened slime crystal with your bare hands.\nYou gain {} slime{}. Sick, dude!!".format(crush_slimes, sap_resp)
			
			if len(levelup_response) > 0:
				response += "\n\n" + levelup_response
			
	else:
		if item_search:  # if they didnt forget to specify an item and it just wasn't found
			response = "You don't have one."
		else:
			response = "Crush which item? (check **!inventory**)"
		
	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

def init_grid(poi, id_server):
	world_events = ewworldevent.get_world_events(id_server = id_server)
	minigame_event = None
	for id_event in world_events:
		if world_events.get(id_event) in [ewcfg.event_type_minesweeper, ewcfg.event_type_pokemine, ewcfg.event_type_bubblebreaker]:
			event_data = EwWorldEvent(id_event = id_event)
			if event_data.event_props.get('poi') == poi:
				minigame_event = event_data.event_type

	if minigame_event == ewcfg.event_type_minesweeper:
		return init_grid_minesweeper(poi, id_server)
	elif minigame_event == ewcfg.event_type_pokemine:
		return init_grid_pokemine(poi, id_server)
	elif minigame_event == ewcfg.event_type_bubblebreaker:
		return init_grid_bubblebreaker(poi, id_server)
	else:
		return init_grid_none(poi, id_server)

def init_grid_minesweeper(poi, id_server):
	grid = []
	num_rows = 13
	num_cols = 13
	for i in range(num_rows):
		row = []
		for j in range(num_cols):
			row.append(ewcfg.cell_empty)
		grid.append(row)

	num_mines = 20

	row = random.randrange(num_rows)
	col = random.randrange(num_cols)
	for mine in range(num_mines):
		while grid[row][col] == ewcfg.cell_mine:
			row = random.randrange(num_rows)
			col = random.randrange(num_cols)
		grid[row][col] = ewcfg.cell_mine

			
	if poi in mines_map:
		grid_cont = EwMineGrid(grid = grid, grid_type = ewcfg.mine_grid_type_minesweeper)
		mines_map.get(poi)[id_server] = grid_cont

def init_grid_pokemine(poi,id_server):
	return init_grid_none(poi, id_server)# TODO

def init_grid_bubblebreaker(poi, id_server):
	grid = []
	num_rows = 13
	num_cols = 13
	for i in range(num_rows):
		row = []
		for j in range(num_cols):
			if i > 8:
				row.append(ewcfg.cell_bubble_empty)
				continue
			cell = random.choice(ewcfg.cell_bubbles)
			randomn = random.random()
			if randomn < 0.15 and j > 0:
				cell = row[-1]
			elif randomn < 0.3 and i > 0:
				cell = grid[-1][j]

			row.append(cell)
		grid.append(row)


			
	if poi in mines_map:
		grid_cont = EwMineGrid(grid = grid, grid_type = ewcfg.mine_grid_type_bubblebreaker)
		mines_map.get(poi)[id_server] = grid_cont

def init_grid_none(poi, id_server):
	if poi in mines_map:
		grid_cont = EwMineGrid(grid = None, grid_type = None)
		mines_map.get(poi)[id_server] = grid_cont

async def print_grid(cmd):
	user_data = EwUser(member = cmd.message.author)
	poi = user_data.poi
	id_server = cmd.message.server.id
	if poi in mines_map:
		grid_map = mines_map.get(poi)
		if id_server not in grid_map:
			init_grid(poi, id_server)
		grid_cont = grid_map.get(id_server)

		grid = grid_cont.grid
	
		if grid_cont.grid_type == ewcfg.mine_grid_type_minesweeper:
			return await print_grid_minesweeper(cmd)
		elif grid_cont.grid_type == ewcfg.mine_grid_type_pokemine:
			return await print_grid_pokemine(cmd)
		elif grid_cont.grid_type == ewcfg.mine_grid_type_bubblebreaker:
			return await print_grid_bubblebreaker(cmd)

async def print_grid_minesweeper(cmd):
	grid_str = ""
	user_data = EwUser(member = cmd.message.author)
	poi = user_data.poi
	id_server = cmd.message.server.id
	time_now = int(time.time())
	if poi in mines_map:
		grid_map = mines_map.get(poi)
		if id_server not in grid_map:
			init_grid_minesweeper(poi, id_server)
		grid_cont = grid_map.get(id_server)

		grid = grid_cont.grid

		grid_str += "   "
		for j in range(len(grid[0])):
			letter = ewcfg.alphabet[j]
			grid_str += "{} ".format(letter)
		grid_str += "\n"
		for i in range(len(grid)):
			row = grid[i]
			if i+1 < 10:
				grid_str += " "

			grid_str += "{} ".format(i+1)
			for j in range(len(row)):
				cell = row[j]
				cell_str = ""
				if cell == ewcfg.cell_empty_open:
					neighbor_mines = 0
					for ci in range(max(0, i-1), min(len(grid), i+2)):
						for cj in range(max(0, j-1), min(len(row), j+2)):
							if grid[ci][cj] > 0:
								neighbor_mines += 1
					cell_str = str(neighbor_mines)

				else:
					cell_str = ewcfg.symbol_map_ms.get(cell)
				grid_str += cell_str + " "

			grid_str += "{}".format(i+1)
			grid_str += "\n"


		grid_str += "   "
		for j in range(len(grid[0])):
			letter = ewcfg.alphabet[j]
			grid_str += "{} ".format(letter)

		grid_edit = "\n```\n{}\n```".format(grid_str)

		if time_now > grid_cont.time_last_posted + 10 or grid_cont.times_edited > 3 or grid_cont.message == "":
			grid_cont.message = await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, grid_edit))
			grid_cont.time_last_posted = time_now
			grid_cont.times_edited = 0
		else:
			await ewutils.edit_message(cmd.client, grid_cont.message, ewutils.formatMessage(cmd.message.author, grid_edit))
			grid_cont.times_edited += 1

		if grid_cont.wall_message == "":
			wall_channel = ewcfg.mines_wall_map.get(poi)
			resp_cont = ewutils.EwResponseContainer(id_server = id_server)
			resp_cont.add_channel_response(wall_channel, grid_edit)
			msg_handles = await resp_cont.post()
			grid_cont.wall_message = msg_handles[0]
		else:
			await ewutils.edit_message(cmd.client, grid_cont.wall_message, grid_edit)
	

async def print_grid_pokemine(cmd):
	return #TODO

async def print_grid_bubblebreaker(cmd):
	grid_str = ""
	user_data = EwUser(member = cmd.message.author)
	poi = user_data.poi
	id_server = cmd.message.server.id
	time_now = int(time.time())
	use_emotes = False
	if poi in mines_map:
		grid_map = mines_map.get(poi)
		if id_server not in grid_map:
			init_grid(poi, id_server)
		grid_cont = grid_map.get(id_server)

		grid = grid_cont.grid

		#grid_str += "   "
		for j in range(len(grid[0])):
			letter = ewcfg.alphabet[j]
			grid_str += "{} ".format(letter)
		grid_str += "\n"
		for i in range(len(grid)):
			row = grid[i]
			#if i+1 < 10:
			#	grid_str += " "

			#grid_str += "{} ".format(i+1)
			for j in range(len(row)):
				cell = row[j]
				cell_str = get_cell_symbol_bubblebreaker(cell)
				if use_emotes:
					cell_str = ewcfg.number_emote_map.get(int(cell))
				grid_str += cell_str + " "
			#grid_str += "{}".format(i+1)
			grid_str += "\n"


		#grid_str += "   "
		for j in range(len(grid[0])):
			letter = ewcfg.alphabet[j]
			grid_str += "{} ".format(letter)

		grid_edit = "\n```\n{}\n```".format(grid_str)
		if use_emotes:
			grid_edit = "\n" + grid_str
		if time_now > grid_cont.time_last_posted + 10 or grid_cont.times_edited > 8 or grid_cont.message == "":
			grid_cont.message = await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, grid_edit))
			grid_cont.time_last_posted = time_now
			grid_cont.times_edited = 0
		else:
			await ewutils.edit_message(cmd.client, grid_cont.message, ewutils.formatMessage(cmd.message.author, grid_edit))
			grid_cont.times_edited += 1

		if grid_cont.wall_message == "":
			wall_channel = ewcfg.mines_wall_map.get(poi)
			resp_cont = ewutils.EwResponseContainer(id_server = id_server)
			resp_cont.add_channel_response(wall_channel, grid_edit)
			msg_handles = await resp_cont.post()
			grid_cont.wall_message = msg_handles[0]
		else:
			await ewutils.edit_message(cmd.client, grid_cont.wall_message, grid_edit)

# for pokemining
def get_cell_symbol_bubblebreaker(cell):
	if cell == ewcfg.cell_bubble_empty:
		return " "
	return cell

def get_cell_symbol_pokemine(cell):
	cell_str = " "
	#if cell > 2 * ewcfg.slimes_invein:
	#	cell_str = "&"
	#elif cell > 1.5 * ewcfg.slimes_invein:
	#	cell_str = "S"
	if cell > 0.4 * ewcfg.slimes_invein:
		cell_str = "~"
	#elif cell > 0.5 * ewcfg.slimes_invein:
	#	cell_str = ";"
	elif cell > 0:
		cell_str = ";"
	elif cell > -40 * ewcfg.slimes_pertile:
		cell_str = " "
	#elif cell > -40 * ewcfg.slimes_pertile:
	#	cell_str = "+"
	else:
		cell_str = "X"
	return cell_str

# for bubblebreaker
def apply_gravity(grid):
	cells_to_check = []
	for row in range(1,len(grid)):
		for col in range(len(grid[row])):
			coords = (row, col)
			new_coords = bubble_fall(grid, (row,col))
			if coords != new_coords:
				cells_to_check.append(new_coords)

	return cells_to_check

#for bubblebreaker
def bubble_fall(grid, coords):
	row = coords[0]
	col = coords[1]
	if grid[row][col] == ewcfg.cell_bubble_empty:
		return coords
	falling_bubble = grid[row][col]
	while row > 0 and grid[row-1][col] == ewcfg.cell_bubble_empty:
		row -= 1

	grid[coords[0]][coords[1]] = ewcfg.cell_bubble_empty
	grid[row][col] = falling_bubble
	return (row,col)

# for bubblebreaker
def check_and_explode(grid, cells_to_check):
	slime_yield = 0

	for coords in cells_to_check:
		bubble = grid[coords[0]][coords[1]]
		if bubble == ewcfg.cell_bubble_empty:
			continue

		bubble_cluster = [coords]
		to_check = [coords]
		while len(to_check) > 0:
			to_check_next = []
			for coord in to_check:
				neighs = neighbors(grid, coord)
				for neigh in neighs:
					if neigh in bubble_cluster:
						continue
					if grid[neigh[0]][neigh[1]] == bubble:
						bubble_cluster.append(neigh)
						to_check_next.append(neigh)
			to_check = to_check_next
						

		if len(bubble_cluster) >= ewcfg.bubbles_to_burst:
			for coord in bubble_cluster:
				grid[coord[0]][coord[1]] = ewcfg.cell_bubble_empty
				slime_yield += 1

	return slime_yield
		
# for bubblebreaker
def neighbors(grid, coords):
	neighs = []
	row = coords[0]
	col = coords[1]
	if row-1 >= 0:
		neighs.append((row-1,col))
	if row+1 < len(grid):
		neighs.append((row+1,col))
	if col-1 >= 0:
		neighs.append((row,col-1))
	if col+1 < len(grid[row]):
		neighs.append((row,col+1))
	return neighs

# for bubblebreaker
def add_row(grid):
	new_row = []
	for i in range(len(grid[0])):
		
		cell = random.choice(ewcfg.cell_bubbles)
		randomn = random.random()
		if randomn < 0.15 and i > 0:
			cell = new_row[-1]
		elif randomn < 0.3:
			cell = grid[0][i]
		if cell == ewcfg.cell_bubble_empty:
			cell = random.choice(ewcfg.cell_bubbles)

		new_row.append(cell)
	grid.insert(0, new_row)
	return grid.pop(-1)

# for bubblebreaker
def get_height(grid):
	row = 0

	while row < len(grid):
		is_empty = True
		for cell in grid[row]:
			if cell != ewcfg.cell_bubble_empty:
				is_empty = False
				break
		if is_empty:
			break
		row += 1

	return row
	
def get_unmined_cell_count(grid_cont):
	grid = grid_cont.grid
	unmined_cells = 0
	for row in grid:
		for cell in row:
			if cell in [ewcfg.cell_empty, ewcfg.cell_empty_marked]:
				unmined_cells += 1
	return unmined_cells
	
def get_mining_yield_by_grid_type(cmd, grid_cont):
	if grid_cont.grid_type == ewcfg.mine_grid_type_minesweeper:
		return get_mining_yield_minesweeper(cmd, grid_cont)
	elif grid_cont.grid_type == ewcfg.mine_grid_type_pokemine:
		return get_mining_yield_pokemine(cmd, grid_cont)
	elif grid_cont.grid_type == ewcfg.mine_grid_type_bubblebreaker:
		return get_mining_yield_bubblebreaker(cmd, grid_cont)
	else:
		return get_mining_yield_default(cmd)

def get_mining_yield_minesweeper(cmd, grid_cont):
	user_data = EwUser(member = cmd.message.author)
	grid = grid_cont.grid
	grid_multiplier = grid_cont.cells_mined ** 0.4

	hunger_cost_mod = ewutils.hunger_cost_mod(user_data.slimelevel)

	row = -1
	col = -1
	if cmd.tokens_count < 2:
		response = "Please specify which vein to mine."
		return response

	for token in cmd.tokens[1:]:
				
		coords = token.lower()
		if coords == "reset":
			user_data.hunger += int(ewcfg.hunger_perminereset * hunger_cost_mod)
			user_data.persist()
			init_grid_minesweeper(user_data.poi, user_data.id_server)
			return ""

		if col < 1:
		
			for char in coords:
				if char in ewcfg.alphabet:
					col = ewcfg.alphabet.index(char)
					coords = coords.replace(char, "")
		if row < 1:
			try:
				row = int(coords)
			except:
				row = -1



	row -= 1
			
	if row not in range(len(grid)) or col not in range(len(grid[row])):
		response = "Invalid vein."
		return response


	mining_yield = 0
	mining_accident = False


	if grid[row][col] in [ewcfg.cell_empty_marked, ewcfg.cell_mine_marked]:
		response = "This vein has been flagged as dangerous. Remove the flag to mine here."
		return response

	elif grid[row][col] == ewcfg.cell_empty_open:
		response = "This vein has already been mined dry."
		return response

	elif grid[row][col] == ewcfg.cell_mine:
		mining_accident = True

	elif grid[row][col] == ewcfg.cell_empty:
		grid[row][col] = ewcfg.cell_empty_open
		grid_cont.cells_mined += 1
		mining_yield = grid_multiplier * 5 * get_mining_yield_default(cmd)

	unmined_cells = get_unmined_cell_count(grid_cont)

	if unmined_cells == 0:
		init_grid_minesweeper(user_data.poi, user_data.id_server)

	if mining_accident:
		slimes_lost = 0.1 * grid_multiplier * user_data.slimes
		if slimes_lost <= 0:
			response = "You barely avoided getting into a mining accident."
		else:
			user_data.change_slimes(n = -slimes_lost)
			user_data.persist()
			response = "You have lost an arm and a leg in a mining accident. Tis but a scratch."

		init_grid_minesweeper(user_data.poi, user_data.id_server)

		return response

	else:
		return mining_yield

def get_mining_yield_pokemine(cmd, grid_cont):
	return "TODO"

def get_mining_yield_bubblebreaker(cmd, grid_cont):
	
	user_data = EwUser(member = cmd.message.author)
	grid = grid_cont.grid

	row = -1
	col = -1
	bubble_add = None
	if cmd.tokens_count < 2:
		response = "Please specify which vein to mine."
		return response

	for token in cmd.tokens[1:]:
		token_lower = token.lower()

		if col < 1:
			for char in token_lower:
				if char in ewcfg.alphabet:
					col = ewcfg.alphabet.index(char)
					token_lower = token_lower.replace(char, "")
		if bubble_add == None:
			bubble = token_lower
			if bubble in ewcfg.cell_bubbles:
				bubble_add = bubble


	row = len(grid)
	row -= 1
			
	if col not in range(len(grid[0])):
		response = "Invalid vein."
		return response

	if bubble_add == None:
		response = "Invalid bubble."
		return response

	mining_yield = 0
	mining_accident = False

	cells_to_clear = []
	
	slimes_pertile = 3 * get_mining_yield_default(cmd)
	if grid[row][col] != ewcfg.cell_bubble_empty:
		mining_accident = True
	else:
		grid[row][col] = bubble_add

		cells_to_check = apply_gravity(grid)

		cells_to_check.append((row,col))

		while len(cells_to_check) > 0:
			mining_yield += slimes_pertile * check_and_explode(grid, cells_to_check)
			
			cells_to_check = apply_gravity(grid)

	grid_cont.cells_mined += 1
	grid_height = get_height(grid)

	if grid_cont.cells_mined % 4 == 3 or grid_height < 5:
		if grid_height < len(grid):
			add_row(grid)
		else:
			mining_accident = True

	if mining_accident:
		user_data.change_slimes(n = -(user_data.slimes * 0.5))
		user_data.persist()
		response = "You have lost an arm and a leg in a mining accident. Tis but a scratch."

		init_grid_bubblebreaker(user_data.poi, user_data.id_server)

		return response
	else:
		return mining_yield

def get_mining_yield_default(cmd):
	return 200

def create_mining_event(cmd):
	randomn = random.random()
	time_now = int(time.time())
	user_data = EwUser(member = cmd.message.author)

	# common event
	if randomn < 0.6:
		randomn = random.random()
		
		# 4x glob of slime
		if randomn < 0.5:
			event_props = {}
			event_props['id_user'] = cmd.message.author.id
			event_props['poi'] = user_data.poi
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_slimeglob,
				time_activate = time_now,
				event_props = event_props
			)
		# 30 seconds slimefrenzy
		else:
			event_props = {}
			event_props['id_user'] = cmd.message.author.id
			event_props['poi'] = user_data.poi
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_slimefrenzy,
				time_activate = time_now,
				time_expir = time_now + 30,
				event_props = event_props
			)
			
	# uncommon event
	elif randomn < 0.9:
		randomn = random.random()

		# mine shaft collapse
		if randomn < 0.5:
			event_props = {}
			event_props['id_user'] = cmd.message.author.id
			event_props['poi'] = user_data.poi
			event_props['captcha'] = ewutils.generate_captcha(n = 8)
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_minecollapse,
				time_activate = time_now,
				time_expir = time_now + 60,
				event_props = event_props
			)
		# 10 second poudrin frenzy
		else:
			event_props = {}
			event_props['id_user'] = cmd.message.author.id
			event_props['poi'] = user_data.poi
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_poudrinfrenzy,
				time_activate = time_now,
				time_expir = time_now + 5,
				event_props = event_props
			)
			
	# rare event
	else:
		randomn = random.random()

		# minesweeper
		if randomn < 1/2:
			event_props = {}
			event_props['poi'] = user_data.poi
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_minesweeper,
				time_activate = time_now,
				time_expir = time_now + 60*3,
				event_props = event_props
			)
		
		# bubblebreaker
		else:
			event_props = {}
			event_props['poi'] = user_data.poi
			return ewworldevent.create_world_event(
				id_server = cmd.message.server.id,
				event_type = ewcfg.event_type_bubblebreaker,
				time_activate = time_now,
				time_expir = time_now + 60*3,
				event_props = event_props
			)
