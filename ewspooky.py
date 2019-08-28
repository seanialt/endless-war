from ewdistrict import EwDistrict

"""
	Commands and utilities related to dead players.
"""
import time
import random
import re
import asyncio

import ewcmd
import ewcfg
import ewutils
import ewmap
import ewrolemgr
import ewslimeoid
from ew import EwUser
from ewmarket import EwMarket
from ewslimeoid import EwSlimeoid

""" revive yourself from the dead. """
async def revive(cmd):
	time_now = int(time.time())
	response = ""

	if cmd.message.channel.name != ewcfg.channel_endlesswar and cmd.message.channel.name != ewcfg.channel_sewers:
		response = "Come to me. I hunger. #{}.".format(ewcfg.channel_sewers)
	else:
		player_data = EwUser(member = cmd.message.author)
		slimeoid = EwSlimeoid(member = cmd.message.author)

		if player_data.life_state == ewcfg.life_state_corpse:
			market_data = EwMarket(id_server = cmd.message.server.id)

			# Endless War collects his fee.
			fee = (player_data.slimecoin / 10)
			player_data.change_slimecoin(n = -fee, coinsource = ewcfg.coinsource_revival)
			market_data.slimes_revivefee += fee
			player_data.busted = False
			
			# Preserve negaslime
			if player_data.slimes < 0:
				#market_data.negaslime += player_data.slimes
				player_data.change_slimes(n = -player_data.slimes) # set to 0

			# Give player some initial slimes.
			player_data.slimelevel = 0
			player_data.change_slimes(n = ewcfg.slimes_onrevive)

			# Set time of last revive. This used to provied spawn protection, but currently isn't used.
			player_data.time_lastrevive = time_now

			# Set life state. This is what determines whether the player is actually alive.
			player_data.life_state = ewcfg.life_state_juvenile

			# Get the player out of the sewers.
			player_data.poi = ewcfg.poi_id_endlesswar

			player_data.persist()
			market_data.persist()

			# Shower every district in the city with slime from the sewers.
			sewer_data = EwDistrict(district = ewcfg.poi_id_thesewers, id_server = cmd.message.server.id)
			# the amount of slime showered is divided equally amongst the districts
			districts_amount = len(ewcfg.capturable_districts)
			geyser_amount = int(0.5 * sewer_data.slimes / districts_amount)
			# Get a list of all the districts
			for poi in ewcfg.capturable_districts:
				district_data = EwDistrict(district = poi, id_server = cmd.message.server.id)


				district_data.change_slimes(n = geyser_amount)
				sewer_data.change_slimes(n = -1 * geyser_amount)

				district_data.persist()
				sewer_data.persist()

			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

			response = '{slime4} Geysers of fresh slime erupt from every manhole in the city, showering their surrounding districts. {slime4} {name} has been reborn in slime. {slime4}'.format(
				slime4 = ewcfg.emote_slime4, name = cmd.message.author.display_name)
		else:
			response = 'You\'re not dead just yet.'

	#	deathreport = "You were {} by {}. {}".format(kill_descriptor, cmd.message.author.display_name, ewcfg.emote_slimeskull)
	#	deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(member, deathreport)

		if slimeoid.life_state == ewcfg.slimeoid_state_active:
			reunite = ""
			brain = ewcfg.brain_map.get(slimeoid.ai)
			reunite += brain.str_revive.format(
			slimeoid_name = slimeoid.name
			)
			new_poi = ewcfg.id_to_poi.get(player_data.poi)
			revivechannel = ewutils.get_channel(cmd.message.server, new_poi.channel)
			reunite = ewutils.formatMessage(cmd.message.author, reunite)
			await ewutils.send_message(cmd.client, revivechannel, reunite)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" haunt living players to steal slime """
async def haunt(cmd):
	time_now = int(time.time())
	response = ""
	resp_cont = ewutils.EwResponseContainer(id_server = cmd.message.server.id)

	if cmd.mentions_count > 1:
		response = "You can only spook one person at a time. Who do you think you are, the Lord of Ghosts?"
	elif cmd.mentions_count == 1:
		# Get the user and target data from the database.
		user_data = EwUser(member = cmd.message.author)

		member = cmd.mentions[0]
		haunted_data = EwUser(member = member)
		market_data = EwMarket(id_server = cmd.message.server.id)

		if user_data.life_state != ewcfg.life_state_corpse:
			# Only dead players can haunt.
			response = "You can't haunt now. Try {}.".format(ewcfg.cmd_suicide)
		elif haunted_data.life_state == ewcfg.life_state_kingpin:
			# Disallow haunting of generals.
			response = "He is too far from the sewers in his ivory tower, and thus cannot be haunted."
		elif (time_now - user_data.time_lasthaunt) < ewcfg.cd_haunt:
			# Disallow haunting if the user has haunted too recently.
			response = "You're being a little TOO spooky lately, don't you think?"
		elif ewmap.channel_name_is_poi(cmd.message.channel.name) == False:
			response = "You can't commit violence from here."
		elif not ewutils.is_otp(haunted_data):
			# Require the target to be flagged for PvP
			response = "{} is not mired in the ENDLESS WAR right now.".format(member.display_name)
		elif haunted_data.life_state == ewcfg.life_state_corpse:
			# Dead players can't be haunted.
			response = "{} is already dead.".format(member.display_name)
		elif haunted_data.life_state == ewcfg.life_state_grandfoe:
			# Grand foes can't be haunted.
			response = "{} is invulnerable to ghosts.".format(member.display_name)
		elif haunted_data.life_state == ewcfg.life_state_enlisted or haunted_data.life_state == ewcfg.life_state_juvenile:
			# Target can be haunted by the player.
			haunted_slimes = int(haunted_data.slimes / ewcfg.slimes_hauntratio)
			#if user_data.poi == haunted_data.poi:  # when haunting someone face to face, there is no cap and you get double the amount
			#	haunted_slimes *= 2
			if haunted_slimes > ewcfg.slimes_hauntmax:
				haunted_slimes = ewcfg.slimes_hauntmax

			#if -user_data.slimes < haunted_slimes:  # cap on for how much you can haunt
			#	haunted_slimes = -user_data.slimes

			haunted_data.change_slimes(n = -haunted_slimes, source = ewcfg.source_haunted)
			user_data.change_slimes(n = -haunted_slimes, source = ewcfg.source_haunter)
			market_data.negaslime -= haunted_slimes
			user_data.time_lasthaunt = time_now
			user_data.busted = False

			# Persist changes to the database.
			user_data.persist()
			haunted_data.persist()
			market_data.persist()

			response = "{} has been haunted by the ghost of {}! Slime has been lost!".format(member.display_name, cmd.message.author.display_name)

			haunted_channel = ewcfg.id_to_poi.get(haunted_data.poi).channel
			haunt_message = "You feel a cold shiver run down your spine"
			if cmd.tokens_count > 2:
				haunt_message_content = re.sub("<.+>", "", cmd.message.content[(len(cmd.tokens[0])):]).strip()
				# Cut down really big messages so discord doesn't crash
				if len(haunt_message_content) > 500:
					haunt_message_content = haunt_message_content[:-500]
				haunt_message += " and faintly hear the words \"{}\"".format(haunt_message_content)
			haunt_message += "."
			haunt_message = ewutils.formatMessage(member, haunt_message)
			resp_cont.add_channel_response(haunted_channel, haunt_message)
		else:
			# Some condition we didn't think of.
			response = "You cannot haunt {}.".format(member.display_name)
	else:
		# No mentions, or mentions we didn't understand.
		response = "Your spookiness is appreciated, but ENDLESS WAR didn\'t understand that name."

	# Send the response to the player.
	resp_cont.add_channel_response(cmd.message.channel.name, response)
	await resp_cont.post()
	#await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def negaslime(cmd):
	# Add persisted negative slime.
	market_data = EwMarket(id_server = cmd.message.server.id)
	negaslime = market_data.negaslime

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "The dead have amassed {:,} negative slime.".format(negaslime)))

async def summon_negaslimeoid(cmd):
	response = ""
	user_data = EwUser(member = cmd.message.author)
	if user_data.life_state != ewcfg.life_state_corpse:
		response = "Only the dead have the occult knowledge required to summon a cosmic horror."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.poi not in ewcfg.capturable_districts:
		response = "You can't conduct the ritual here."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))



	name = None
	if cmd.tokens_count > 1:
		#value = ewutils.getIntToken(tokens = cmd.tokens, allow_all = True, negate = True)
		slimeoid = EwSlimeoid(member = cmd.message.author, sltype = ewcfg.sltype_nega)
		if slimeoid.life_state != ewcfg.slimeoid_state_none:
			response = "You already have an active negaslimeoid."
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		negaslimeoid_name = cmd.message.content[(len(cmd.tokens[0])):].strip()

		if len(negaslimeoid_name) > 32:
			response = "That name is too long. ({:,}/32)".format(len(negaslimeoid_name))
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		market_data = EwMarket(id_server = cmd.message.author.server.id)

		if market_data.negaslime >= 0:
			response = "The dead haven't amassed any negaslime yet."
		else:
			max_level = min(len(str(user_data.slimes)) - 1, len(str(market_data.negaslime)) - 1)
			level = random.randint(1, max_level)
			value = 10 ** (level - 1)
			#user_data.change_slimes(n = int(value/10))
			market_data.negaslime += value
			slimeoid.sltype = ewcfg.sltype_nega
			slimeoid.life_state = ewcfg.slimeoid_state_active
			slimeoid.level = level
			slimeoid.id_user = user_data.id_user
			slimeoid.id_server = user_data.id_server
			slimeoid.poi = user_data.poi
			slimeoid.name = negaslimeoid_name
			slimeoid.body = random.choice(ewcfg.body_names)
			slimeoid.head = random.choice(ewcfg.head_names)
			slimeoid.legs = random.choice(ewcfg.mobility_names)
			slimeoid.armor = random.choice(ewcfg.defense_names)
			slimeoid.weapon = random.choice(ewcfg.offense_names)
			slimeoid.special = random.choice(ewcfg.special_names)
			slimeoid.ai = random.choice(ewcfg.brain_names)
			for i in range(level):
				rand = random.randrange(3)
				if rand == 0:
					slimeoid.atk += 1
				elif rand == 1:
					slimeoid.defense += 1
				else:
					slimeoid.intel += 1



			user_data.persist()
			slimeoid.persist()
			market_data.persist()

			response = "You have summoned **{}**, a {}-foot-tall Negaslimeoid.".format(slimeoid.name, slimeoid.level)
			desc = ewslimeoid.slimeoid_describe(slimeoid)
			response += desc

	else:
		response = "To summon a negaslimeoid you must first know its name."
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

def generate_negaslimeoid_name():
	titles = ["Angel", "Emissary", "Gaping Maw", "Apostle", "Nemesis", "Harbinger", "Reaper", "Incarnation", "Wanderer", "Berserker", "Outcast", "Monarch", "Anomaly"]
	domains = ["Curses", "Doom", "Oblivion", "Darkness", "Madness", "the Void", "the Deep", "Nightmares", "Wrath", "Pestilence", "the End", "Terror", "Sorrow", "Pain", "Despair", "Souls", "Secrets", "Ruin", "Hatred", "Shadows", "the Night"]
	title = "{} of {}".format(random.choice(titles), random.choice(domains))
	name_length = random.randrange(5,min(10,30-len(title)))
	consonants = random.choice(["chlt","crwx","fhlt","bghl","brpq"])
	vowels = "aeuuooyy"
	num_vowels = random.randrange(int(name_length / 4), int(name_length/3)+1)
	name_list = []
	for i in range(name_length):
		if i < num_vowels:
			name_list.append(random.choice(vowels))
		else:
			name_list.append(random.choice(consonants))
	random.shuffle(name_list)
	apostrophe = random.randrange(1,name_length)
	name = ewutils.flattenTokenListToString(name_list[:apostrophe]) + "'" + ewutils.flattenTokenListToString(name_list[apostrophe:])
	name = name.capitalize()
	full_name = "{}, {}".format(name, title)
	return full_name


"""
	allows ghosts to leave the sewers
"""
async def manifest(cmd):
	user_data = EwUser(member = cmd.message.author)
	response = ""

	if user_data.life_state == ewcfg.life_state_corpse and user_data.busted:
		if user_data.poi == ewcfg.poi_id_thesewers:
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "You're busted, bitch. You can't leave the sewers until your restore your power by !haunting one of the living."))
		else:  # sometimes busted ghosts get stuck outside the sewers
			user_data.poi = ewcfg.poi_id_thesewers
			user_data.persist()
			await ewrolemgr.updateRoles(cmd.client, cmd.message.author)
			return

	if user_data.life_state != ewcfg.life_state_corpse:
		response = "You don't even know what that MEANS."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	
	if user_data.poi != ewcfg.poi_id_thesewers:
		response = "You've already manifested in the city."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.slimes > ewcfg.slimes_tomanifest:
		response = "You are too weak to manifest. You need to gather more negative slime."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	poi = ewcfg.id_to_poi.get(user_data.poi_death)

	response = "{}ing in {}.".format(cmd.tokens[0][1:].capitalize(), poi.str_name)

	# schedule tasks for concurrent execution
	message_task = asyncio.ensure_future(ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response)))
	wait_task = asyncio.ensure_future(asyncio.sleep(5))

	# Take control of the move for this player.
	ewmap.move_counter += 1
	move_current = ewutils.moves_active[cmd.message.author.id] = ewmap.move_counter
	await message_task
	await wait_task

		
	# check if the user entered another movement command while waiting for the current one to be completed
	if move_current != ewutils.moves_active[cmd.message.author.id]:
		return

	user_data = EwUser(member = cmd.message.author)
	user_data.poi = poi.id_poi
	user_data.persist()

	await ewrolemgr.updateRoles(cmd.client, cmd.message.author)
