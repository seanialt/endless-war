import sys
import traceback

import MySQLdb
import datetime
import time
import re
import random
import asyncio
import math

import ewstats
import ewitem
import ewhunting
import ewrolemgr

import discord

import ewcfg
import ewwep
from ew import EwUser
from ewdistrict import EwDistrict
from ewplayer import EwPlayer
from ewhunting import EwEnemy
from ewmarket import EwMarket
from ewstatuseffects import EwStatusEffect

TERMINATE = False

db_pool = {}
db_pool_id = 0

# Map of user IDs to their course ID.
moves_active = {}

food_multiplier = {}

# Contains who players are trading with and the state of the trades
active_trades = {}
# Contains the items being offered by players
trading_offers = {}

class Message:
	# Send the message to this exact channel by name.
	channel = None

	# Send the message to the channel associated with this point of interest.
	id_poi = None

	# Should this message echo to adjacent points of interest?
	reverb = None
	message = ""

	def __init__(
		self,
		channel = None,
		reverb = False,
		message = "",
		id_poi = None
	):
		self.channel = channel
		self.reverb = reverb
		self.message = message
		self.id_poi = id_poi

"""
	Class for storing, passing, editing and posting channel responses and topics
"""
class EwResponseContainer:
	client = None
	id_server = ""
	channel_responses = {}
	channel_topics = {}
	members_to_update = []

	def __init__(self, client = None, id_server = None):
		self.client = client
		self.id_server = id_server
		self.channel_responses = {}
		self.channel_topics = {}
		self.members_to_update = []

	def add_channel_response(self, channel, response):
		if channel in self.channel_responses:
			self.channel_responses[channel].append(response)
		else:
			self.channel_responses[channel] = [response]

	def add_channel_topic(self, channel, topic):
		self.channel_topics[channel] = topic

	def add_member_to_update(self, member):
		for update_member in self.members_to_update:
			if update_member.id == member.id:
				return

		self.members_to_update.append(member)

	def add_response_container(self, resp_cont):
		for ch in resp_cont.channel_responses:
			responses = resp_cont.channel_responses[ch]
			for r in responses:
				self.add_channel_response(ch, r)

		for ch in resp_cont.channel_topics:
			self.add_channel_topic(ch, resp_cont.channel_topics[ch])

		for member in resp_cont.members_to_update:
			self.add_member_to_update(member)

	def format_channel_response(self, channel, member):
		if channel in self.channel_responses:
			for i in range(len(self.channel_responses[channel])):
				self.channel_responses[channel][i] = formatMessage(member, self.channel_responses[channel][i])

	async def post(self, channel=None):
		self.client = get_client()
		messages = []

		if self.client == None:
			logMsg("Couldn't find client")
			return messages
			
		server = self.client.get_server(self.id_server)
		if server == None:
			logMsg("Couldn't find server with id {}".format(self.id_server))
			return messages

		for member in self.members_to_update:
			await ewrolemgr.updateRoles(client = self.client, member = member)

		for ch in self.channel_responses:
			if channel == None:
				current_channel = get_channel(server = server, channel_name = ch)
			else:
				current_channel = channel
			try:
				response = ""
				while len(self.channel_responses[ch]) > 0:
					if len(response) == 0 or len("{}\n{}".format(response, self.channel_responses[ch][0])) < ewcfg.discord_message_length_limit:
						response += "\n" + self.channel_responses[ch].pop(0)
					else:
						message = await send_message(self.client, current_channel, response)
						messages.append(message)
						response = ""
				message = await send_message(self.client, current_channel, response)
				messages.append(message)
			except:
				logMsg('Failed to send message to channel {}: {}'.format(ch, self.channel_responses[ch]))
				

		for ch in self.channel_topics:
			channel = get_channel(server = server, channel_name = ch)
			try:
				await self.client.edit_channel(channel = channel, topic = self.channel_topics[ch])
			except:
				logMsg('Failed to set channel topic for {} to {}'.format(ch, self.channel_topics[ch]))

		return messages


def readMessage(fname):
	msg = Message()

	try:
		f = open(fname, "r")
		f_lines = f.readlines()

		count = 0
		for line in f_lines:
			line = line.rstrip()
			count += 1
			if len(line) == 0:
				break

			args = line.split('=')
			if len(args) == 2:
				field = args[0].strip().lower()
				value = args[1].strip()

				if field == "channel":
					msg.channel = value.lower()
				elif field == "poi":
					msg.poi = value.lower()
				elif field == "reverb":
					msg.reverb = True if (value.lower() == "true") else False
			else:
				count -= 1
				break

		for line in f_lines[count:]:
			msg.message += (line.rstrip() + "\n")
	except:
		logMsg('failed to parse message.')
		traceback.print_exc(file = sys.stdout)
	finally:
		f.close()

	return msg

""" Write the string to stdout with a timestamp. """
def logMsg(string):
	print("[{}] {}".format(datetime.datetime.now(), string))

	return string

""" read a file named fname and return its contents as a string """
def getValueFromFileContents(fname):
	token = ""

	try:
		f_token = open(fname, "r")
		f_token_lines = f_token.readlines()

		for line in f_token_lines:
			line = line.rstrip()
			if len(line) > 0:
				token = line
	except IOError:
		token = ""
		print("Could not read {} file.".format(fname))
	finally:
		f_token.close()

	return token

""" get the Discord API token from the config file on disk """
def getToken():
	return getValueFromFileContents("token")

""" get the Twitch client ID from the config file on disk """
def getTwitchClientId():
	return getValueFromFileContents("twitch_client_id")

""" print a list of strings with nice comma-and grammar """
def formatNiceList(names = [], conjunction = "and"):
	l = len(names)

	if l == 0:
		return ''

	if l == 1:
		return names[0]
	
	return ', '.join(names[0:-1]) + '{comma} {conj} '.format(comma = (',' if l > 2 else ''), conj = conjunction) + names[-1]

""" turn a list of Users into a list of their respective names """
def userListToNameString(list_user):
	names = []

	for user in list_user:
		names.append(user.display_name)

	return formatNiceList(names)

""" turn a list of Roles into a map of name = >Role """
def getRoleMap(roles):
	roles_map = {}

	for role in roles:
		roles_map[mapRoleName(role.name)] = role

	return roles_map

""" turn a list of Roles into a map of id = >Role """
def getRoleIdMap(roles):
	roles_map = {}

	for role in roles:
		roles_map[mapRoleName(role.id)] = role

	return roles_map

""" canonical lowercase no space name for a role """
def mapRoleName(roleName):
	return roleName.replace(" ", "").lower()

""" connect to the database """
def databaseConnect():
	conn_info = None

	conn_id_todelete = []

	global db_pool
	global db_pool_id

	# Iterate through open connections and find the currently active one.
	for pool_id in db_pool:
		conn_info_iter = db_pool.get(pool_id)

		if conn_info_iter['closed'] == True:
			if conn_info_iter['count'] <= 0:
				conn_id_todelete.append(pool_id)
		else:
			conn_info = conn_info_iter

	# Close and remove dead connections.
	if len(conn_id_todelete) > 0:
		for pool_id in conn_id_todelete:
			conn_info_iter = db_pool[pool_id]
			conn_info_iter['conn'].close()

			del db_pool[pool_id]

	# Create a new connection.
	if conn_info == None:
		db_pool_id += 1
		conn_info = {
			'conn': MySQLdb.connect(host = "localhost", user = "rfck-bot", passwd = "rfck" , db = "rfck", charset = "utf8"),
			'created': int(time.time()),
			'count': 1,
			'closed': False
		}
		db_pool[db_pool_id] = conn_info
	else:
		conn_info['count'] += 1

	return conn_info

""" close (maybe) the active database connection """
def databaseClose(conn_info):
	conn_info['count'] -= 1

	# Expire old database connections.
	if (conn_info['created'] + 60) < int(time.time()):
		conn_info['closed'] = True

""" format responses with the username: """
def formatMessage(user_target, message):
	# If the display name belongs to an unactivated raid boss, hide its name while it's counting down.
	try:
		if user_target.display_name in ewcfg.raid_boss_names and user_target.life_state == ewcfg.enemy_lifestate_unactivated:
			return "{}".format(message)
		else:
			# Send messages normally if the raid boss is activated or if user_target is a player
			return "*{}*: {}".format(user_target.display_name, message).replace("@", "\{at\}")
	# If the user has the name of a raid boss, catch the exception and format the message correctly
	except:
		return "*{}*: {}".format(user_target.display_name, message).replace("@", "\{at\}")

""" Decay slime totals for all users """
def decaySlimes(id_server = None):
	if id_server != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			cursor.execute("SELECT id_user FROM users WHERE id_server = %s AND {slimes} > 1".format(
				slimes = ewcfg.col_slimes
			), (
				id_server,
			))

			users = cursor.fetchall()
			total_decayed = 0

			for user in users:
				user_data = EwUser(id_user = user[0], id_server = id_server)
				slimes_to_decay = user_data.slimes - (user_data.slimes * (.5 ** (ewcfg.update_market / ewcfg.slime_half_life)))

				#round up or down, randomly weighted
				remainder = slimes_to_decay - int(slimes_to_decay)
				if random.random() < remainder: 
					slimes_to_decay += 1 
				slimes_to_decay = int(slimes_to_decay)

				if slimes_to_decay >= 1:
					user_data.change_slimes(n = -slimes_to_decay, source = ewcfg.source_decay)
					user_data.persist()
					total_decayed += slimes_to_decay

			cursor.execute("SELECT district FROM districts WHERE id_server = %s AND {slimes} > 1".format(
				slimes = ewcfg.col_district_slimes
			), (
				id_server,
			))

			districts = cursor.fetchall()

			for district in districts:
				district_data = EwDistrict(district = district[0], id_server = id_server)
				slimes_to_decay = district_data.slimes - (district_data.slimes * (.5 ** (ewcfg.update_market / ewcfg.slime_half_life)))

				#round up or down, randomly weighted
				remainder = slimes_to_decay - int(slimes_to_decay)
				if random.random() < remainder: 
					slimes_to_decay += 1 
				slimes_to_decay = int(slimes_to_decay)

				if slimes_to_decay >= 1:
					district_data.change_slimes(n = -slimes_to_decay, source = ewcfg.source_decay)
					district_data.persist()
					total_decayed += slimes_to_decay

			cursor.execute("UPDATE markets SET {decayed} = ({decayed} + %s) WHERE {server} = %s".format(
				decayed = ewcfg.col_decayed_slimes,
				server = ewcfg.col_id_server
			), (
				total_decayed,
				id_server
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)	
			
"""
	Coroutine that continually calls bleedSlimes; is called once per server, and not just once globally
"""
async def bleed_tick_loop(id_server):
	interval = ewcfg.bleed_tick_length
	# causes a capture tick to happen exactly every 10 seconds (the "elapsed" thing might be unnecessary, depending on how long capture_tick ends up taking on average)
	while not TERMINATE:
		await bleedSlimes(id_server = id_server)
		await enemyBleedSlimes(id_server = id_server)
		# ewutils.logMsg("Capture tick happened on server %s." % id_server + " Timestamp: %d" % int(time.time()))

		await asyncio.sleep(interval)

""" Bleed slime for all users """
async def bleedSlimes(id_server = None):
	if id_server != None:
		try:
			client = get_client()
			server = client.get_server(id_server)
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			cursor.execute("SELECT id_user FROM users WHERE id_server = %s AND {bleed_storage} > 1".format(
				bleed_storage = ewcfg.col_bleed_storage
			), (
				id_server,
			))

			users = cursor.fetchall()
			total_bled = 0
			deathreport = ""
			resp_cont = EwResponseContainer(id_server = id_server)
			for user in users:
				user_data = EwUser(id_user = user[0], id_server = id_server)
				slimes_to_bleed = user_data.bleed_storage * (1 - .5 ** (ewcfg.bleed_tick_length / ewcfg.bleed_half_life))
				slimes_to_bleed = max(slimes_to_bleed, ewcfg.bleed_tick_length * 1000)
				slimes_to_bleed = min(slimes_to_bleed, user_data.bleed_storage)
				slimes_dropped = user_data.totaldamage + user_data.slimes

				district_data = EwDistrict(id_server = id_server, district = user_data.poi)

				#round up or down, randomly weighted
				remainder = slimes_to_bleed - int(slimes_to_bleed)
				if random.random() < remainder: 
					slimes_to_bleed += 1 
				slimes_to_bleed = int(slimes_to_bleed)

				if slimes_to_bleed >= 1:
					user_data.bleed_storage -= slimes_to_bleed
					user_data.change_slimes(n = - slimes_to_bleed, source = ewcfg.source_bleeding)
					if user_data.slimes < 0:
						user_data.die(cause = ewcfg.cause_bleeding)
						#user_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)
						player_data = EwPlayer(id_server = user_data.id_server, id_user = user_data.id_user)
						deathreport = "{skull} *{uname}*: You have succumbed to your wounds. {skull}".format(skull = ewcfg.emote_slimeskull, uname = player_data.display_name)
						resp_cont.add_channel_response(ewcfg.channel_sewers, deathreport)
					user_data.persist()

					district_data.change_slimes(n = slimes_to_bleed, source = ewcfg.source_bleeding)
					district_data.persist()
					total_bled += slimes_to_bleed

				await ewrolemgr.updateRoles(client = client, member = server.get_member(user_data.id_user))

			await resp_cont.post()

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)		

""" Bleed slime for all enemies """
async def enemyBleedSlimes(id_server = None):
	if id_server != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			cursor.execute("SELECT id_enemy FROM enemies WHERE id_server = %s AND {bleed_storage} > 1".format(
				bleed_storage = ewcfg.col_enemy_bleed_storage
			), (
				id_server,
			))

			enemies = cursor.fetchall()
			total_bled = 0
			resp_cont = EwResponseContainer(id_server = id_server)
			for enemy in enemies:
				enemy_data = EwEnemy(id_enemy = enemy[0], id_server = id_server)
				slimes_to_bleed = enemy_data.bleed_storage * (1 - .5 ** (ewcfg.bleed_tick_length / ewcfg.bleed_half_life))
				slimes_to_bleed = max(slimes_to_bleed, ewcfg.bleed_tick_length * 1000)
				slimes_to_bleed = min(slimes_to_bleed, enemy_data.bleed_storage)

				district_data = EwDistrict(id_server = id_server, district = enemy_data.poi)

				#round up or down, randomly weighted
				remainder = slimes_to_bleed - int(slimes_to_bleed)
				if random.random() < remainder:
					slimes_to_bleed += 1
				slimes_to_bleed = int(slimes_to_bleed)

				if slimes_to_bleed >= 1:
					enemy_data.bleed_storage -= slimes_to_bleed
					enemy_data.change_slimes(n = - slimes_to_bleed, source = ewcfg.source_bleeding)
					enemy_data.persist()
					district_data.change_slimes(n = slimes_to_bleed, source = ewcfg.source_bleeding)
					district_data.persist()
					total_bled += slimes_to_bleed

					if enemy_data.slimes <= 0:
						ewhunting.delete_enemy(enemy_data)

			await resp_cont.post()
			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

""" Increase hunger for every player in the server. """
def pushupServerHunger(id_server = None):
	if id_server != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			# Save data
			cursor.execute("UPDATE users SET {hunger} = {hunger} + {tick} WHERE life_state > 0 AND id_server = %s AND hunger < {limit}".format(
				hunger = ewcfg.col_hunger,
				tick = ewcfg.hunger_pertick,
				# this function returns the bigger of two values; there is no simple way to do this in sql and we can't calculate it within this python script
				limit = "0.5 * (({val1} + {val2}) + ABS({val1} - {val2}))".format(
					val1 = ewcfg.min_stamina,
					val2 = "POWER(" + ewcfg.col_slimelevel + ", 2)"
				)
			), (
				id_server,
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

""" Reduce inebriation for every player in the server. """
def pushdownServerInebriation(id_server = None):
	if id_server != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			# Save data
			cursor.execute("UPDATE users SET {inebriation} = {inebriation} - {tick} WHERE id_server = %s AND {inebriation} > {limit}".format(
				inebriation = ewcfg.col_inebriation,
				tick = ewcfg.inebriation_pertick,
				limit = 0
			), (
				id_server,
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

"""
	Coroutine that continually calls burnSlimes; is called once per server, and not just once globally
"""
async def burn_tick_loop(id_server):
	interval = ewcfg.burn_tick_length
	while not TERMINATE:
		await burnSlimes(id_server = id_server)
		await asyncio.sleep(interval)

""" Burn slime for all users """
async def burnSlimes(id_server = None):
	if id_server != None:
		time_now = int(time.time())
		client = get_client()
		server = client.get_server(id_server)

		results = {}

		# Get users with burning effect
		data = execute_sql_query("SELECT {id_user}, {value}, {source} from status_effects WHERE {id_status} = %s and {id_server} = %s".format(
			id_user = ewcfg.col_id_user,
			value = ewcfg.col_value,
			id_status = ewcfg.col_id_status,
			id_server = ewcfg.col_id_server,
			source = ewcfg.col_source
		), (
			ewcfg.status_burning_id,
			id_server
		))

		deathreport = ""
		resp_cont = EwResponseContainer(id_server = id_server)
		for result in data:
			user_data = EwUser(id_user = result[0], id_server = id_server)

			slimes_dropped = user_data.totaldamage + user_data.slimes

			# Deal 10% of total slime to burn every second
			slimes_to_burn = math.ceil(int(float(result[1])) * ewcfg.burn_tick_length / ewcfg.time_expire_burn)

			killer_data = EwUser(id_server = id_server, id_user=result[2])

			# Damage stats
			ewstats.change_stat(user = killer_data, metric = ewcfg.stat_lifetime_damagedealt, n = slimes_to_burn)

			# Player died
			if user_data.slimes - slimes_to_burn < 0:	
				weapon = ewcfg.weapon_map.get(ewcfg.weapon_id_molotov)

				player_data = EwPlayer(id_server = user_data.id_server, id_user = user_data.id_user)
				killer = EwPlayer(id_server = id_server, id_user=killer_data.id_user)

				# Kill stats
				ewstats.increment_stat(user = killer_data, metric = ewcfg.stat_kills)
				ewstats.track_maximum(user = killer_data, metric = ewcfg.stat_biggest_kill, value = int(slimes_dropped))

				if killer_data.slimelevel > user_data.slimelevel:
					ewstats.increment_stat(user = killer_data, metric = ewcfg.stat_lifetime_ganks)
				elif killer_data.slimelevel < user_data.slimelevel:
					ewstats.increment_stat(user = killer_data, metric = ewcfg.stat_lifetime_takedowns)

				# Collect bounty
				coinbounty = int(user_data.bounty / ewcfg.slimecoin_exchangerate)  # 100 slime per coin
				
				if user_data.slimes >= 0:
					killer_data.change_slimecoin(n = coinbounty, coinsource = ewcfg.coinsource_bounty)

				# Kill player
				user_data.id_killer = killer_data.id_user
				user_data.die(cause = ewcfg.cause_burning)
				#user_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)
			
				deathreport = "You were {} by {}. {}".format(weapon.str_killdescriptor, killer.display_name, ewcfg.emote_slimeskull)
				deathreport = "{} ".format(ewcfg.emote_slimeskull) + formatMessage(server.get_member(user_data.id_user), deathreport)
				resp_cont.add_channel_response(ewcfg.channel_sewers, deathreport)

				user_data.trauma = weapon.id_weapon

				user_data.persist()
				await ewrolemgr.updateRoles(client = client, member = server.get_member(user_data.id_user))
			else:
				user_data.change_slimes(n = -slimes_to_burn, source = ewcfg.source_damage)
				user_data.persist()
				

		await resp_cont.post()	

async def remove_status_loop(id_server):
	interval = ewcfg.removestatus_tick_length
	while not TERMINATE:
		removeExpiredStatuses(id_server = id_server)
		await asyncio.sleep(interval)

""" Decay slime totals for all users """
def removeExpiredStatuses(id_server = None):
	if id_server != None:
		time_now = int(time.time())

		#client = get_client()
		#server = client.get_server(id_server)

		statuses = execute_sql_query("SELECT {id_status},{id_user} FROM status_effects WHERE id_server = %s AND {time_expire} < %s".format(
			id_status = ewcfg.col_id_status,
			id_user = ewcfg.col_id_user,
			time_expire = ewcfg.col_time_expir
		), (
			id_server,
			time_now
		))

		for row in statuses:
			status = row[0]
			id_user = row[1]
			user_data = EwUser(id_user = id_user, id_server = id_server)
			status_def = ewcfg.status_effects_def_map.get(status)
			status_effect = EwStatusEffect(id_status=status, user_data = user_data)
	
			if status_def.time_expire > 0:
				if status_effect.time_expire < time_now:
					user_data.clear_status(id_status=status)

			# Status that expire under special conditions
			else:
				if status == ewcfg.status_stunned_id:
					if int(status_effect.value) < time_now:
						user_data.clear_status(id_status=status)

""" Parse a list of tokens and return an integer value. If allow_all, return -1 if the word 'all' is present. """
def getIntToken(tokens = [], allow_all = False, negate = False):
	value = None

	for token in tokens[1:]:
		try:
			value = int(token.replace(",", ""))
			if value < 0 and not negate:
				value = None
			elif value > 0 and negate:
				value = None
			elif negate:
				value = -value
			break
		except:
			if allow_all and ("{}".format(token)).lower() == 'all':
				return -1
			else:
				value = None

	return value

""" Get the map of weapon skills for the specified player. """
def weaponskills_get(id_server = None, id_user = None, member = None):
	weaponskills = {}

	if member != None:
		id_server = member.server.id
		id_user = member.id

	if id_server != None and id_user != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			cursor.execute("SELECT {weapon}, {weaponskill} FROM weaponskills WHERE {id_server} = %s AND {id_user} = %s".format(
				weapon = ewcfg.col_weapon,
				weaponskill = ewcfg.col_weaponskill,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				id_user
			))

			data = cursor.fetchall()
			if data != None:
				for row in data:
					weaponskills[row[0]] = {
						'skill': row[1]
					}
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

	return weaponskills

""" Set an individual weapon skill value for a player. """
def weaponskills_set(id_server = None, id_user = None, member = None, weapon = None, weaponskill = 0):
	if member != None:
		id_server = member.server.id
		id_user = member.id

	if id_server != None and id_user != None and weapon != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			cursor.execute("REPLACE INTO weaponskills({id_server}, {id_user}, {weapon}, {weaponskill}) VALUES(%s, %s, %s, %s)".format(
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user,
				weapon = ewcfg.col_weapon,
				weaponskill = ewcfg.col_weaponskill
			), (
				id_server,
				id_user,
				weapon,
				weaponskill
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

""" Clear all weapon skills for a player (probably called on death). """
def weaponskills_clear(id_server = None, id_user = None, member = None, weaponskill = None):
	if member != None:
		id_server = member.server.id
		id_user = member.id

	if id_server != None and id_user != None:
		try:
			conn_info = databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			# Clear any records that might exist.
			cursor.execute("UPDATE weaponskills SET {weaponskill} = %s WHERE {weaponskill} > %s AND {id_server} = %s AND {id_user} = %s".format(
				weaponskill = ewcfg.col_weaponskill,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				weaponskill,
				weaponskill,
				id_server,
				id_user
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			databaseClose(conn_info)

re_flattener = re.compile("[ '\"!@#$%^&*().,/?{}\[\];:]")

"""
	Turn an array of tokens into a single word (no spaces or punctuation) with all lowercase letters.
"""
def flattenTokenListToString(tokens):
	global re_flattener
	target_name = ""

	if type(tokens) == list:
		for token in tokens:
			if token.startswith('<@') == False:
				target_name += re_flattener.sub("", token.lower())
	elif tokens.startswith('<@') == False:
		target_name = re_flattener.sub("", tokens.lower())

	return target_name


"""
	Execute a given sql_query. (the purpose of this function is to minimize repeated code and keep functions readable)
"""
def execute_sql_query(sql_query = None, sql_replacements = None):
	data = None

	try:
		conn_info = databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()
		cursor.execute(sql_query, sql_replacements)
		if sql_query.lower().startswith("select"):
			data = cursor.fetchall()
		conn.commit()
	finally:
		# Clean up the database handles.
		cursor.close()
		databaseClose(conn_info)

	return data


"""
	Send a message to multiple chat channels at once. "channels" can be either a list of discord channel objects or strings
"""
async def post_in_channels(id_server, message, channels = None):
	client = get_client()
	server = client.get_server(id = id_server)

	if channels is None and server is not None:
		channels = server.channels

	for channel in channels:
		if type(channel) is str:  # if the channels are passed as strings instead of discord channel objects
			channel = get_channel(server, channel)
		if channel is not None and channel.type == discord.ChannelType.text:
			await send_message(client, channel, message)
	return

"""
	Find a chat channel by name in a server.
"""
def get_channel(server = None, channel_name = ""):
	channel = None

	for chan in server.channels:
		if chan.name == channel_name:
			channel = chan

	return channel

"""
	Return the role name of a user's faction. Takes user data object or life_state and faction tag
"""
def get_faction(user_data = None, life_state = 0, faction = ""):
	life_state = life_state
	faction = faction
	if user_data != None:
		life_state = user_data.life_state
		faction = user_data.faction

	faction_role = ewcfg.role_corpse

	if life_state == ewcfg.life_state_juvenile:
		faction_role = ewcfg.role_juvenile

	elif life_state == ewcfg.life_state_enlisted:
		if faction == ewcfg.faction_killers:
			faction_role = ewcfg.role_copkillers

		elif faction == ewcfg.faction_rowdys:
			faction_role = ewcfg.role_rowdyfuckers

		else:
			faction_role = ewcfg.role_juvenile

	elif life_state == ewcfg.life_state_kingpin:
		faction_role = ewcfg.role_kingpin

	elif life_state == ewcfg.life_state_grandfoe:
		faction_role = ewcfg.role_grandfoe

	elif life_state == ewcfg.life_state_executive:
		faction_role = ewcfg.role_slimecorp

	elif life_state == ewcfg.life_state_lucky:
		faction_role = ewcfg.role_slimecorp

	return faction_role

def get_faction_symbol(faction = "", faction_raw = ""):
	result = None

	if faction == ewcfg.role_kingpin:
		if faction_raw == ewcfg.faction_rowdys:
			result = ewcfg.emote_rowdyfucker
		elif faction_raw == ewcfg.faction_killers:
			result = ewcfg.emote_copkiller

	if result == None:
		if faction == ewcfg.role_corpse:
			result = ewcfg.emote_ghost
		elif faction == ewcfg.role_juvenile:
			result = ewcfg.emote_slime3
		elif faction == ewcfg.role_copkillers:
			result = ewcfg.emote_ck
		elif faction == ewcfg.role_rowdyfuckers:
			result = ewcfg.emote_rf
		else:
			result = ewcfg.emote_blank

	return result


"""
	Calculate the slime amount needed to reach a certain level
"""
def slime_bylevel(slimelevel):
	return int(slimelevel ** 4)


"""
	Calculate what level the player should be at, given their slime amount
"""
def level_byslime(slime):
	return int(abs(slime) ** 0.25)


"""
	Calculate the maximum hunger level at the player's slimelevel
"""
def hunger_max_bylevel(slimelevel):
	# note that when you change this formula, you'll also have to adjust its sql equivalent in pushupServerHunger
	return max(ewcfg.min_stamina, slimelevel ** 2)


"""
	Calculate how much more stamina activities should cost
"""
def hunger_cost_mod(slimelevel):
	return hunger_max_bylevel(slimelevel) / 200


"""
	Calculate how much food the player can carry
"""
def food_carry_capacity_bylevel(slimelevel):
	return math.ceil(slimelevel / ewcfg.max_food_in_inv_mod)
        
"""
	Calculate how many weapons the player can carry
"""
def weapon_carry_capacity_bylevel(slimelevel):
	return math.floor(slimelevel / ewcfg.max_weapon_mod) + 1

def max_adorn_bylevel(slimelevel):
        return math.ceil(slimelevel / ewcfg.max_adorn_mod)
"""
	Returns an EwUser object of the selected kingpin
"""
def find_kingpin(id_server, kingpin_role):
	data = execute_sql_query("SELECT id_user FROM users WHERE id_server = %s AND {life_state} = %s AND {faction} = %s".format(
		life_state = ewcfg.col_life_state,
		faction = ewcfg.col_faction
	), (
		id_server,
		ewcfg.life_state_kingpin,
		ewcfg.faction_rowdys if kingpin_role == ewcfg.role_rowdyfucker else ewcfg.faction_killers
	))

	kingpin = None

	if len(data) > 0:
		id_kingpin = data[0][0]
		kingpin = EwUser(id_server = id_server, id_user = id_kingpin)

	return kingpin


"""
	Posts a message both in CK and RR.
"""
async def post_in_hideouts(id_server, message):
	await post_in_channels(
		id_server = id_server,
		message = message,
		channels = [ewcfg.channel_copkilltown, ewcfg.channel_rowdyroughhouse]
	)

"""
	gets the discord client the bot is running on
"""
def get_client():
	return ewcfg.get_client()


"""
	Proxy to discord.py Client.send_message with exception handling.
"""
async def send_message(client, channel, text):
	try:
		return await client.send_message(channel, text)
	except:
		logMsg('Failed to send message to channel: {}\n{}'.format(channel, text))

"""
	Proxy to discord.py Client.edit_message with exception handling.
"""
async def edit_message(client, message, text):
	try:
		return await client.edit_message(message, text)
	except:
		logMsg('Failed to edit message. Updated text would have been:\n{}'.format(text))

"""
	Returns a list of slimeoid ids in the district
"""
def get_slimeoids_in_poi(id_server = None, poi = None, sltype = None):
	slimeoids = []
	if id_server is None:
		return slimeoids

	query = "SELECT {id_slimeoid} FROM slimeoids WHERE {id_server} = %s".format(
		id_slimeoid = ewcfg.col_id_slimeoid,
		id_server = ewcfg.col_id_server
	)

	if sltype is not None:
		query += " AND {} = '{}'".format(ewcfg.col_type, sltype)

	if poi is not None:
		query += " AND {} = '{}'".format(ewcfg.col_poi, poi)

	data = execute_sql_query(query,(
		id_server,
	))

	for row in data:
		slimeoids.append(row[0])

	return slimeoids

async def decrease_food_multiplier(id_user):
	await asyncio.sleep(5)
	if id_user in food_multiplier:
		food_multiplier[id_user] = max(0, food_multiplier.get(id_user) - 1)

async def spawn_enemies(id_server = None):
	if random.randrange(3) == 0:
		resp_cont = ewhunting.spawn_enemy(id_server)

		await resp_cont.post()

async def spawn_enemies_tick_loop(id_server):
	interval = ewcfg.enemy_spawn_tick_length
	# Causes the possibility of an enemy spawning every 10 seconds
	while not TERMINATE:
		await asyncio.sleep(interval)
		await spawn_enemies(id_server = id_server)


async def enemy_action_tick_loop(id_server):
	interval = ewcfg.enemy_attack_tick_length
	# Causes hostile enemies to attack every tick.
	while not TERMINATE:
		await asyncio.sleep(interval)
		# resp_cont = EwResponseContainer(id_server=id_server)
		await ewhunting.enemy_perform_action(id_server)


# Clears out id_target in enemies with defender ai. Primarily used for when players die or leave districts the defender is in.
def check_defender_targets(user_data, enemy_data):
	defending_enemy = EwEnemy(id_enemy=enemy_data.id_enemy)
	searched_user = EwUser(id_user=user_data.id_user, id_server=user_data.id_server)

	if (defending_enemy.poi != searched_user.poi) or (searched_user.life_state == ewcfg.life_state_corpse):
		defending_enemy.id_target = ""
		defending_enemy.persist()
		return False
	else:
		return True

def get_move_speed(user_data):
	time_now = int(time.time())
	mutations = user_data.get_mutations()
	market_data = EwMarket(id_server = user_data.id_server)
	move_speed = 1

	if ewcfg.mutation_id_organicfursuit in mutations and (
		(market_data.day % 31 == 0 and market_data.clock >= 20)
		or (market_data.day % 31 == 1 and market_data.clock < 6)
	):
		move_speed *= 2
	if ewcfg.mutation_id_lightasafeather in mutations and market_data.weather == "windy":
		move_speed *= 2
	if ewcfg.mutation_id_fastmetabolism in mutations and user_data.hunger / user_data.get_hunger_max() < 0.4:
		move_speed *= 1.33

	if user_data.time_expirpvp >= time_now:
		move_speed = 0.5 # Reduces movement speed to half standard movement speed, even if you have mutations that speed it up.
		
	# TODO: Remove after Double Halloween
	if user_data.life_state == ewcfg.life_state_corpse:
		move_speed *= 2

	return move_speed

""" Damage all players in a district """
def explode(damage = 0, district_data = None):
	id_server = district_data.id_server
	poi = district_data.name

	client = get_client()
	server = client.get_server(id_server)

	resp_cont = EwResponseContainer(id_server = id_server)
	response = ""
	channel = ewcfg.id_to_poi.get(poi).channel

	life_states = [ewcfg.life_state_juvenile, ewcfg.life_state_enlisted, ewcfg.life_state_executive]
	users = district_data.get_players_in_district(life_states = life_states)

	enemies = district_data.get_enemies_in_district()

	# damage players
	for user in users:
		user_data = EwUser(id_user = user, id_server = id_server)
		mutations = user_data.get_mutations()

		if True:
			player_data = EwPlayer(id_user = user_data.id_user)
			response = "{} is blown back by the explosion’s sheer force! They lose {} slime!!".format(player_data.display_name, damage)
			resp_cont.add_channel_response(channel, response)
			slimes_damage = damage
			if user_data.slimes < slimes_damage + user_data.bleed_storage:
				# die in the explosion
				district_data.change_slimes(n = user_data.slimes, source = ewcfg.source_killing)
				district_data.persist()
				slimes_dropped = user_data.totaldamage + user_data.slimes
				explode_damage = slime_bylevel(user_data.slimelevel)

				user_data.die(cause = ewcfg.cause_killing)
				#user_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)
				user_data.persist()

				response = "Alas, {} was caught too close to the blast. They are consumed by the flames, and die in the explosion.".format(player_data.display_name)
				resp_cont.add_channel_response(channel, response)

				if ewcfg.mutation_id_spontaneouscombustion in mutations:
					sub_explosion = explode(explode_damage, district_data)
					resp_cont.add_response_container(sub_explosion)

				resp_cont.add_member_to_update(server.get_member(user_data.id_user))
			else:
				# survive
				slime_splatter = 0.5 * slimes_damage
				district_data.change_slimes(n = slime_splatter, source = ewcfg.source_killing)
				district_data.persist()
				slimes_damage -= slime_splatter
				user_data.bleed_storage += slimes_damage
				user_data.change_slimes(n = -slime_splatter, source = ewcfg.source_killing)
				user_data.persist()

	# damage enemies
	for enemy in enemies:
		enemy_data = EwEnemy(id_enemy = enemy, id_server = id_server)

		if True:
			response = "{} is blown back by the explosion’s sheer force! They lose {} slime!!".format(enemy_data.display_name, damage)
			resp_cont.add_channel_response(channel, response)
			slimes_damage = damage
			if enemy_data.slimes < slimes_damage + enemy_data.bleed_storage:
				# die in the explosion
				district_data.change_slimes(n = enemy_data.slimes, source = ewcfg.source_killing)
				district_data.persist()
				# slimes_dropped = enemy_data.totaldamage + enemy_data.slimes
				# explode_damage = ewutils.slime_bylevel(enemy_data.level)

				response = "Alas, {} was caught too close to the blast. They are consumed by the flames, and die in the explosion.".format(enemy_data.display_name)
				resp_cont.add_response_container(ewhunting.drop_enemy_loot(enemy_data, district_data))
				resp_cont.add_channel_response(channel, response)

				enemy_data.life_state = ewcfg.enemy_lifestate_dead
				enemy_data.persist()

			else:
				# survive
				slime_splatter = 0.5 * slimes_damage
				district_data.change_slimes(n = slime_splatter, source = ewcfg.source_killing)
				district_data.persist()
				slimes_damage -= slime_splatter
				enemy_data.bleed_storage += slimes_damage
				enemy_data.change_slimes(n = -slime_splatter, source = ewcfg.source_killing)
				enemy_data.persist()
	return resp_cont

def is_otp(user_data):
	poi = ewcfg.id_to_poi.get(user_data.poi)
	return user_data.poi not in [ewcfg.poi_id_thesewers, ewcfg.poi_id_juviesrow, ewcfg.poi_id_copkilltown, ewcfg.poi_id_rowdyroughhouse] and (not poi.is_apartment)


async def delete_last_message(client, last_messages, tick_length):
	if len(last_messages) == 0:
		return
	await asyncio.sleep(tick_length)
	try:
		await client.delete_message(last_messages[-1])
	except:
		logMsg("failed to delete last message")

def check_accept_or_refuse(string):
	if string.content.lower() == ewcfg.cmd_accept or string.content.lower() == ewcfg.cmd_refuse:
		return True

def check_confirm_or_cancel(string):
	if string.content.lower() == ewcfg.cmd_confirm or string.content.lower() == ewcfg.cmd_cancel:
		return True
	
# TODO: Remove after Double Halloween
def check_trick_or_treat(string):
	if string.content.lower() == ewcfg.cmd_treat or string.content.lower() == ewcfg.cmd_trick:
		return True
	
def end_trade(id_user):
	# Cancel an ongoing trade
	if active_trades.get(id_user) != None and len(active_trades.get(id_user)) > 0:
		trader = active_trades.get(id_user).get("trader")
		
		active_trades[id_user] = {}
		active_trades[trader] = {}
		
		trading_offers[trader] = []
		trading_offers[id_user] = []

def generate_captcha(n = 4):
	captcha = ""
	for i in range(n):
		captcha += random.choice(ewcfg.alphabet)
	return captcha.upper()

