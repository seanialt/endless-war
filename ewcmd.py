import random
import asyncio
import time

import ewcfg
import ewutils
import ewitem
import ewrolemgr
import ewstats
import ewstatuseffects
import ewmap
import ewslimeoid
from ew import EwUser
from ewmarket import EwMarket
from ewitem import EwItem
from ewslimeoid import EwSlimeoid
from ewhunting import find_enemy
from ewstatuseffects import EwStatusEffect

""" class to send general data about an interaction to a command """
class EwCmd:
	cmd = ""
	tokens = []
	tokens_count = 0
	message = None
	client = None
	mentions = []
	mentions_count = 0

	def __init__(
		self,
		tokens = [],
		message = None,
		client = None,
		mentions = []
	):
		self.tokens = tokens
		self.message = message
		self.client = client
		self.mentions = mentions
		self.mentions_count = len(mentions)

		if len(tokens) >= 1:
			self.tokens_count = len(tokens)
			self.cmd = tokens[0]

""" Send an initial message you intend to edit later while processing the command. Returns handle to the message. """
async def start(cmd = None, message = '...', channel = None, client = None):
	if cmd != None:
		channel = cmd.message.channel
		client = cmd.client

	if client != None and channel != None:
		return await ewutils.send_message(client, channel, message)

	return None

""" pure flavor command, howls """
async def cmd_howl(cmd):
	user_data = EwUser(member = cmd.message.author)
	slimeoid = EwSlimeoid(member = cmd.message.author)
	response = ewcfg.howls[random.randrange(len(ewcfg.howls))]

	if (slimeoid.life_state == ewcfg.slimeoid_state_active) and (user_data.life_state != ewcfg.life_state_corpse):
		response += "\n{} howls along with you! {}".format(str(slimeoid.name), ewcfg.howls[random.randrange(len(ewcfg.howls))])

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" returns true if it's night time and the casino is open, else false. """
def is_casino_open(t):
	if t < 18 and t >= 6:
		return False

	return True

def gen_score_text(
	id_user = None,
	id_server = None,
	display_name = None
):

	user_data = EwUser(
		id_user = id_user,
		id_server = id_server
	)

	items = ewitem.inventory(
		id_user = id_user,
		id_server = id_server,
		item_type_filter = ewcfg.it_item
	)

	poudrin_amount = ewitem.find_poudrin(id_user = id_user, id_server = id_server)

	if user_data.life_state == ewcfg.life_state_grandfoe:
		# Can't see a raid boss's slime score.
		response = "{}'s power is beyond your understanding.".format(display_name)
	else:
		# return somebody's score
		response = "{} currently has {:,} slime{}.".format(display_name, user_data.slimes, (" and {} slime poudrin{}".format(poudrin_amount, ("" if poudrin_amount == 1 else "s")) if poudrin_amount > 0 else ""))

	return response

""" show player's slime score """
async def score(cmd):
	user_data = None
	member = None

	if cmd.mentions_count == 0:
		user_data = EwUser(member = cmd.message.author)

		poudrin_amount = ewitem.find_poudrin(id_user = cmd.message.author.id, id_server = cmd.message.server.id)

		# return my score
		response = "You currently have {:,} slime{}.".format(user_data.slimes, (" and {} slime poudrin{}".format(poudrin_amount, ("" if poudrin_amount == 1 else "s")) if poudrin_amount > 0 else ""))

	else:
		member = cmd.mentions[0]
		response = gen_score_text(
			id_user = member.id,
			id_server = member.server.id,
			display_name = member.display_name
		)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
	if member != None:
		await ewrolemgr.updateRoles(client = cmd.client, member = member)

def gen_data_text(
	id_user = None,
	id_server = None,
	display_name = None
):
	response = ""
	user_data = EwUser(
		id_user = id_user,
		id_server = id_server
	)
	slimeoid = EwSlimeoid(id_user = id_user, id_server = id_server)
	
	mutations = user_data.get_mutations()

	cosmetics = ewitem.inventory(
		id_user = user_data.id_user,
		id_server = user_data.id_server,
		item_type_filter = ewcfg.it_cosmetic
	)
	adorned_cosmetics = []
	for cosmetic in cosmetics:
		cos = EwItem(id_item = cosmetic.get('id_item'))
		if cos.item_props['adorned'] == 'true':
			hue = ewcfg.hue_map.get(cos.item_props.get('hue'))
			adorned_cosmetics.append((hue.str_name + " colored " if hue != None else "") + cosmetic.get('name'))

	if user_data.life_state == ewcfg.life_state_grandfoe:
		poi = ewcfg.id_to_poi.get(user_data.poi)
		if poi != None:
			response = "{} is {} {}.".format(display_name, poi.str_in, poi.str_name)
		else:
			response = "You can't discern anything useful about {}.".format(display_name)
	else:

		# return somebody's score
		if user_data.life_state == ewcfg.life_state_corpse:
			response = "{} is a level {} deadboi.".format(display_name, user_data.slimelevel)
		else:
			response = "{} is a level {} slimeboi.".format(display_name, user_data.slimelevel)

		coinbounty = int(user_data.bounty / ewcfg.slimecoin_exchangerate)

		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))

		if weapon != None:
			response += " {} {}{}.".format(ewcfg.str_weapon_married if user_data.weaponmarried == True else ewcfg.str_weapon_wielding, ("" if len(weapon_item.item_props.get("weapon_name")) == 0 else "{}, ".format(weapon_item.item_props.get("weapon_name"))), weapon.str_weapon)
			if user_data.weaponskill >= 5:
				response += " {}".format(weapon.str_weaponmaster.format(rank = (user_data.weaponskill - 4)))

		trauma = ewcfg.weapon_map.get(user_data.trauma)
		# if trauma is not gathered from weapon_map, get it from attack_type_map
		if trauma == None:
			trauma = ewcfg.attack_type_map.get(user_data.trauma)

		if trauma != None:
			response += " {}".format(trauma.str_trauma)

		response_block = ""
		for mutation in mutations:
			mutation_flavor = ewcfg.mutations_map[mutation]
			response_block += "{} ".format(mutation_flavor.str_describe_other)

		if len(response_block) > 0:
			response += "\n\n" + response_block

		response_block = ""
		user_kills = ewstats.get_stat(user = user_data, metric = ewcfg.stat_kills)

		enemy_kills = ewstats.get_stat(user = user_data, metric = ewcfg.stat_pve_kills)

		if user_kills > 0 and enemy_kills > 0:
			response_block += "They have {:,} confirmed kills, and {:,} confirmed hunts. ".format(user_kills, enemy_kills)
		elif user_kills > 0:
			response_block += "They have {:,} confirmed kills. ".format(user_kills)
		elif enemy_kills > 0:
			response_block += "They have {:,} confirmed hunts. ".format(enemy_kills)


		if coinbounty != 0:
			response_block += "SlimeCorp offers a bounty of {:,} SlimeCoin for their death. ".format(coinbounty)

		if len(adorned_cosmetics) > 0:
			response_block += "They have a {} adorned. ".format(ewutils.formatNiceList(adorned_cosmetics, 'and'))

		statuses = user_data.getStatusEffects()
		
		for status in statuses:
			status_effect = EwStatusEffect(id_status=status, user_data=user_data)
			if status_effect.time_expire > time.time() or status_effect.time_expire == -1:
				status_flavor = ewcfg.status_effects_def_map.get(status)
				if status_flavor is not None:
					response_block += status_flavor.str_describe + " "

		if (slimeoid.life_state == ewcfg.slimeoid_state_active) and (user_data.life_state != ewcfg.life_state_corpse):
			response_block += "They are accompanied by {}, a {}-foot-tall Slimeoid.".format(slimeoid.name, str(slimeoid.level))
		if len(response_block) > 0:
			response += "\n\n" + response_block

	return response

""" show player information and description """
async def data(cmd):
	response = ""
	user_data = None
	member = None

	if len(cmd.tokens) > 1 and cmd.mentions_count == 0:
		user_data = EwUser(member = cmd.message.author)

		soughtenemy = " ".join(cmd.tokens[1:]).lower()
		enemy = find_enemy(soughtenemy, user_data)
		if enemy != None:
			if enemy.attacktype != ewcfg.enemy_attacktype_unarmed:
				response = "{} is a level {} enemy. They have {} slime, and attack with their {}.".format(enemy.display_name, enemy.level, enemy.slimes, enemy.attacktype)
			else:
				response = "{} is a level {} enemy. They have {} slime.".format(enemy.display_name, enemy.level, enemy.slimes)
		else:
			response = "ENDLESS WAR didn't understand that name."

	elif cmd.mentions_count == 0:

		user_data = EwUser(member = cmd.message.author)
		slimeoid = EwSlimeoid(member = cmd.message.author)
		mutations = user_data.get_mutations()

		cosmetics = ewitem.inventory(
			id_user = cmd.message.author.id,
			id_server = cmd.message.server.id,
			item_type_filter = ewcfg.it_cosmetic
		)
		adorned_cosmetics = []
		for cosmetic in cosmetics:
			cos = EwItem(id_item = cosmetic.get('id_item'))
			if cos.item_props['adorned'] == 'true':
				hue = ewcfg.hue_map.get(cos.item_props.get('hue'))
				adorned_cosmetics.append((hue.str_name + " colored " if hue != None else "") + cosmetic.get('name'))

		poi = ewcfg.id_to_poi.get(user_data.poi)
		if poi != None:
			response = "You find yourself {} {}. ".format(poi.str_in, poi.str_name)

		# return my data
		if user_data.life_state == ewcfg.life_state_corpse:
			response += "You are a level {} deadboi.".format(user_data.slimelevel)
		else:
			response += "You are a level {} slimeboi.".format(user_data.slimelevel)

		coinbounty = int(user_data.bounty / ewcfg.slimecoin_exchangerate)

		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))

		if weapon != None:
			response += " {} {}{}.".format(ewcfg.str_weapon_married_self if user_data.weaponmarried == True else ewcfg.str_weapon_wielding_self, ("" if len(weapon_item.item_props.get("weapon_name")) == 0 else "{}, ".format(weapon_item.item_props.get("weapon_name"))), weapon.str_weapon)
			if user_data.weaponskill >= 5:
				response += " {}".format(weapon.str_weaponmaster_self.format(rank = (user_data.weaponskill - 4)))

		trauma = ewcfg.weapon_map.get(user_data.trauma)
		# if trauma is not gathered from weapon_map, get it from attack_type_map
		if trauma == None:
			trauma = ewcfg.attack_type_map.get(user_data.trauma)

		if trauma != None:
			response += " {}".format(trauma.str_trauma_self)
		
		response_block = ""
		for mutation in mutations:
			mutation_flavor = ewcfg.mutations_map[mutation]
			response_block += "{} ".format(mutation_flavor.str_describe_self)

		if len(response_block) > 0:
			response += "\n\n" + response_block

		response_block = ""

		user_kills = ewstats.get_stat(user=user_data, metric=ewcfg.stat_kills)
		enemy_kills = ewstats.get_stat(user=user_data, metric=ewcfg.stat_pve_kills)

		if user_kills > 0 and enemy_kills > 0:
			response_block += "You have {:,} confirmed kills, and {:,} confirmed hunts. ".format(user_kills, enemy_kills)
		elif user_kills > 0:
			response_block += "You have {:,} confirmed kills. ".format(user_kills)
		elif enemy_kills > 0:
			response_block += "You have {:,} confirmed hunts. ".format(enemy_kills)


		if coinbounty != 0:
			response_block += "SlimeCorp offers a bounty of {:,} SlimeCoin for your death. ".format(coinbounty)

		if len(adorned_cosmetics) > 0:
			response_block += "You have a {} adorned. ".format(ewutils.formatNiceList(adorned_cosmetics, 'and'))

		if user_data.hunger > 0:
			response_block += "You are {}% hungry. ".format(
				round(user_data.hunger * 100.0 / user_data.get_hunger_max(), 1)
			)

		if user_data.busted and user_data.life_state == ewcfg.life_state_corpse:
			response_block += "You are busted and therefore cannot leave the sewers until your next !haunt. "

		statuses = user_data.getStatusEffects()
		
		for status in statuses:
			status_effect = EwStatusEffect(id_status=status, user_data=user_data)
			if status_effect.time_expire > time.time() or status_effect.time_expire == -1:
				status_flavor = ewcfg.status_effects_def_map.get(status)
				if status_flavor is not None:
					response_block += status_flavor.str_describe_self + " "

		if (slimeoid.life_state == ewcfg.slimeoid_state_active) and (user_data.life_state != ewcfg.life_state_corpse):
			response_block += "You are accompanied by {}, a {}-foot-tall Slimeoid. ".format(slimeoid.name, str(slimeoid.level))

		if len(response_block) > 0:
			response += "\n\n" + response_block


		response += "\n\nhttps://ew.krakissi.net/stats/player.html?pl={}".format(user_data.id_user)

	else:
		member = cmd.mentions[0]
		response = gen_data_text(
			id_user = member.id,
			id_server = member.server.id,
			display_name = member.display_name
		)

		response += "\n\nhttps://ew.krakissi.net/stats/player.html?pl={}".format(member.id)


	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
	if member != None:
		await ewrolemgr.updateRoles(client = cmd.client, member = member)

def weather_txt(id_server):
	response = ""
	market_data = EwMarket(id_server = id_server)
	time_current = market_data.clock
	displaytime = str(time_current)
	ampm = ''

	if time_current <= 12:
		ampm = 'AM'
	if time_current > 12:
		displaytime = str(time_current - 12)
		ampm = 'PM'

	if time_current == 0:
		displaytime = 'midnight'
		ampm = ''
	if time_current == 12:
		displaytime = 'high noon'
		ampm = ''

	flair = ''
	weather_data = ewcfg.weather_map.get(market_data.weather)
	if weather_data != None:
		if time_current >= 6 and time_current <= 7:
			flair = weather_data.str_sunrise
		if time_current >= 8 and time_current <= 17:
			flair = weather_data.str_day
		if time_current >= 18 and time_current <= 19:
			flair = weather_data.str_sunset
		if time_current >= 20 or time_current <= 5:
			flair = weather_data.str_night

	response += "It is currently {}{} in NLACakaNM.{}".format(displaytime, ampm, (' ' + flair))
	return response

""" time and weather information """
async def weather(cmd):
	response = weather_txt(cmd.message.server.id)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


"""
	Harvest is not and has never been a command.
"""
async def harvest(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, '**HARVEST IS NOT A COMMAND YOU FUCKING IDIOT**'))

"""
	Salute the NLACakaNM flag.
"""
async def salute(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'https://ew.krakissi.net/img/nlacakanm_flag.gif'))

"""
	Burn the NLACakaNM flag.
"""
async def unsalute(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'https://ew.krakissi.net/img/nlacakanm_flag_burning.gif'))
"""
	Burn the NLACakaNM flag.
"""
async def hurl(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'https://ew.krakissi.net/img/tfaaap-hurl.gif'))


"""
	Rowdys THRASH
"""
async def thrash(cmd):
	user_data = EwUser(member = cmd.message.author)

	if (user_data.life_state == ewcfg.life_state_enlisted or user_data.life_state == ewcfg.life_state_kingpin) and user_data.faction == ewcfg.faction_rowdys:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_slime3 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_slime1 + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_rf + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + '\n' + ewcfg.emote_rowdyfucker + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rowdyfucker + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime3 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_slime1 + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf + ewcfg.emote_rf))

"""
	Killers DAB
"""
async def dab(cmd):
	user_data = EwUser(member = cmd.message.author)

	if (user_data.life_state == ewcfg.life_state_enlisted or user_data.life_state == ewcfg.life_state_kingpin) and user_data.faction == ewcfg.faction_killers:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, '\n'  + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_slime3 + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_ck + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + '\n' + ewcfg.emote_copkiller  + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_slime1 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_copkiller + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_ck + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_ck + ewcfg.emote_slime3 + ewcfg.emote_slime1 + ewcfg.emote_slime1 + ewcfg.emote_slime3 + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_ck + ewcfg.emote_ck + ewcfg.emote_slime1 + ewcfg.emote_ck))

"""
	advertise patch notes
"""
async def patchnotes(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Look for the latest patchnotes on the news page: https://ew.krakissi.net/news/'))

"""
	advertise help services
"""
async def help(cmd):
	response = ""
	topic = None
	user_data = EwUser(member = cmd.message.author)

	# help only checks for districts while in game channels
	if ewmap.channel_name_is_poi(cmd.message.channel.name) == False:
		response = 'Check out the guide for help: https://ew.krakissi.net/guide/' + ' \n' + 'You can also visit N.L.A.C.U. (!goto uni) or Neo Milwaukee State (!goto nms) to get more in-depth descriptions about how various game mechanics work.'
	else:
		# checks if user is in a college
		if user_data.poi == ewcfg.poi_id_neomilwaukeestate or user_data.poi == ewcfg.poi_id_nlacu:
			if not len(cmd.tokens) > 1:
				# list off help topics to player at college
				response = 'What would you like to learn about? Topics include: \n' \
						   '**gangs**, **mining**, **food**, **capturing**, **transportation**, **death**, \n' \
						   '**dojo**, **scavenging**, **farming**, **slimeoids**, **ghosts**, **scouting**, \n' \
						   '**cosmetics**, **sparring**, **bleeding**, **stocks**, **casino**, and **offline**.'
			else:
				topic = ewutils.flattenTokenListToString(cmd.tokens[1:])
				if topic in ewcfg.help_responses:
					response = ewcfg.help_responses[topic]
				else:
					response = 'ENDLESS WAR questions your belief in the existence of such a topic. Try referring to the topics list again by using just !help.'
		else:
			# user not in college, check what help message would apply to the subzone they are in

			# poi variable assignment used for checking if player is in a vendor subzone or not
			poi = ewcfg.id_to_poi.get(user_data.poi)

			if user_data.poi in [ewcfg.poi_id_mine, ewcfg.poi_id_cv_mines, ewcfg.poi_id_tt_mines]:
				# mine help
				response = ewcfg.help_responses['mining']
			elif (len(poi.vendors) >= 1):
				# food help
				response = ewcfg.help_responses['food']
			elif user_data.poi in ewcfg.poi_id_dojo and not len(cmd.tokens) > 1:
				# dojo help
				response = "For general dojo information, do **'!help dojo'**. For information about the sparring and weapon rank systems, do **'!help sparring.'**"
			elif user_data.poi in ewcfg.poi_id_dojo and len(cmd.tokens) > 1:
				topic = ewutils.flattenTokenListToString(cmd.tokens[1:])
				if topic == 'dojo':
					response = ewcfg.help_responses['dojo']
				elif topic == 'sparring':
					response = ewcfg.help_responses['sparring']
				else:
					response = 'ENDLESS WAR questions your belief in the existence of such information regarding the dojo. Try referring to the topics list again by using just !help.'
			elif user_data.poi in [ewcfg.poi_id_jr_farms, ewcfg.poi_id_og_farms, ewcfg.poi_id_ab_farms]:
				# farming help
				response = ewcfg.help_responses['farming']
			elif user_data.poi in ewcfg.poi_id_slimeoidlab:
				# slimeoid help (somewhat redundant, but may help by pointing player towards !instructions)
				response = ewcfg.help_responses['slimeoids']
			elif user_data.poi in ewcfg.transport_stops:
				# transportation help
				response =  ewcfg.help_responses['transportation']
			elif user_data.poi in ewcfg.poi_id_stockexchange:
				# stock exchange help
				response = ewcfg.help_responses['stocks']
			elif user_data.poi in ewcfg.poi_id_thecasino:
				# casino help
				response = ewcfg.help_responses['casino']
			elif user_data.poi in ewcfg.poi_id_thesewers:
				# death help
				response = ewcfg.help_responses['death']
			else:
				# catch-all response for when user isn't in a sub-zone with a help response
				response = 'Check out the guide for help: https://ew.krakissi.net/guide/' + ' \n' + 'You can also visit N.L.A.C.U. (!goto uni) or Neo Milwaukee State (!goto nms) to get more in-depth descriptions about how various game mechanics work.'

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


"""
	Link to the world map.
"""
async def map(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Online world map: https://ew.krakissi.net/map/'))

"""
	Link to the RFCK wiki.
"""
async def wiki(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Rowdy Fuckers Cop Killers Wiki: https://rfck.miraheze.org/wiki/Main_Page'))

"""
	Link to the fan art booru.
"""
async def booru(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Rowdy Fuckers Cop Killers Booru: http://rfck.booru.org/'))

"""
	Link to the leaderboards on ew.krakissi.net.
"""
async def leaderboard(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Live leaderboards: https://ew.krakissi.net/stats/'))

""" Accept a russian roulette challenge """
async def accept(cmd):
	user = EwUser(member = cmd.message.author)
	if(user.rr_challenger != ""):
		challenger = EwUser(id_user = user.rr_challenger, id_server = user.id_server)
		if(user.rr_challenger != user.id_user and challenger.rr_challenger != user.id_user):
			challenger.rr_challenger = user.id_user
			challenger.persist()
			slimeoid_data = EwSlimeoid(member = cmd.message.author)
			if cmd.message.channel.name == ewcfg.channel_arena and ewslimeoid.active_slimeoidbattles.get(slimeoid_data.id_slimeoid):
				response = "You accept the challenge! Both of your Slimeoids ready themselves for combat!"
			elif cmd.message.channel.name == ewcfg.channel_casino:
				response = "You accept the challenge! Both of you head out back behind the casino and load a bullet into the gun."
			await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" Refuse a russian roulette challenge """
async def refuse(cmd):
	user = EwUser(member = cmd.message.author)

	if(user.rr_challenger != ""):
		challenger = EwUser(id_user = user.rr_challenger, id_server = user.id_server)

		user.rr_challenger = ""
		user.persist()

		if(user.rr_challenger != user.id_user and challenger.rr_challenger != user.id_user):
			response = "You refuse the challenge, but not before leaving a large puddle of urine beneath you."
			await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		else:
			challenger.rr_challenger = ""
			challenger.persist()

"""
	Ban a player from participating in the game
"""
async def arrest(cmd):

	author = cmd.message.author
	
	if not author.server_permissions.administrator:
		return
	
	if cmd.mentions_count == 1:
		member = cmd.mentions[0]
		user_data = EwUser(member = member)
		user_data.arrested = True
		user_data.poi = ewcfg.poi_id_juviesrow
		user_data.change_slimes(n = - user_data.slimes)
		user_data.persist()

		response = "{} is thrown into one of the Juvenile Detention Center's high security solitary confinement cells.".format(member.display_name)
		await ewrolemgr.updateRoles(client = cmd.client, member = member)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" !piss """
async def piss(cmd):
	user_data = EwUser(member = cmd.message.author)
	mutations = user_data.get_mutations()

	if ewcfg.mutation_id_enlargedbladder in mutations:
		response = "You unzip your dick and just start pissing all over the goddamn fucking floor. God, you’ve waited so long for this moment, and it’s just as perfect as you could have possibly imagined. You love pissing so much."

	else:
		response = "You lack the moral fiber necessary for urination."

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
