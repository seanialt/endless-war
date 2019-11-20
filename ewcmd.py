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
import ewdistrict
import ewslimeoid
import ewfaction
import ewapt

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
	display_name = None,
	channel_name = None
):
	resp_cont = ewutils.EwResponseContainer(id_server=id_server)
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
			adorned_cosmetics.append((hue.str_name + " " if hue != None else "") + cosmetic.get('name'))

	if user_data.life_state == ewcfg.life_state_grandfoe:
		poi = ewcfg.id_to_poi.get(user_data.poi)
		if poi != None:
			response = "{} is {} {}.".format(display_name, poi.str_in, poi.str_name)
		else:
			response = "You can't discern anything useful about {}.".format(display_name)

		resp_cont.add_channel_response(channel_name, response)
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

		resp_cont.add_channel_response(channel_name, response)

		response = ""
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
			response += "\n" + response_block

		response += "\n\nhttps://ew.krakissi.net/stats/player.html?pl={}".format(id_user)

		resp_cont.add_channel_response(channel_name, response)

	return resp_cont

""" show player information and description """
async def data(cmd):
	response = ""
	user_data = None
	member = None
	resp_cont = ewutils.EwResponseContainer(id_server=cmd.message.server.id)

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

		resp_cont.add_channel_response(cmd.message.channel.name, response)

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
				adorned_cosmetics.append((hue.str_name + " " if hue != None else "") + cosmetic.get('name'))

		poi = ewcfg.id_to_poi.get(user_data.poi)
		if poi != None:
			response = "You find yourself {} {}. ".format(poi.str_in, poi.str_name)

		# return my data
		if user_data.life_state == ewcfg.life_state_corpse:
			response += "You are a level {} deadboi.".format(user_data.slimelevel)
		else:
			response += "You are a level {} slimeboi.".format(user_data.slimelevel)

		if user_data.has_soul == 0:
			response += " You have no soul."

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

		resp_cont.add_channel_response(cmd.message.channel.name, response)

		response = ""
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
			response += "\n" + response_block


		response += "\n\nhttps://ew.krakissi.net/stats/player.html?pl={}".format(user_data.id_user)

		resp_cont.add_channel_response(cmd.message.channel.name, response)
	else:
		member = cmd.mentions[0]
		resp_cont = gen_data_text(
			id_user = member.id,
			id_server = member.server.id,
			display_name = member.display_name,
			channel_name = cmd.message.channel.name
		)
	
	# Send the response to the player.
	resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
	await resp_cont.post(channel=cmd.message.channel)

	await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
	if member != None:
		await ewrolemgr.updateRoles(client = cmd.client, member = member)


""" Check how hungry you are. """
async def hunger(cmd):
	user_data = EwUser(member=cmd.message.author)
	response = ""

	if user_data.hunger > 0:
		response = "You are {}% hungry. ".format(
			round(user_data.hunger * 100.0 / user_data.get_hunger_max(), 1)
		)
	else:
		response = "You aren't hungry at all."

	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


async def endlesswar(cmd):
	user_data = EwUser(member=cmd.message.author)
	id_server = user_data.id_server
	
	total = ewutils.execute_sql_query("SELECT SUM(slimes) FROM users WHERE slimes > 0 AND id_server = '{}'".format(id_server))
	totalslimes = total[0][0]

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "ENDLESS WAR has amassed {:,} slime.".format(totalslimes)))


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
	Ghosts BOO
"""
async def boo(cmd):
	user_data = EwUser(member = cmd.message.author)
	
	if user_data.life_state == ewcfg.life_state_corpse or user_data.life_state == ewcfg.life_state_grandfoe:
		resp_cont = ewutils.EwResponseContainer(id_server = user_data.id_server)
		
		response = ewutils.formatMessage(cmd.message.author, '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + '\n' + ewcfg.emote_ghost + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_ghost + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead)
		resp_cont.add_channel_response(cmd.message.channel.name, response)
		
		# if user_data.life_state == ewcfg.life_state_corpse or user_data.life_state == ewcfg.life_state_grandfoe:
		await resp_cont.post()
	#await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_blank + ewcfg.emote_blank + '\n' + ewcfg.emote_ghost + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_srs + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_ghost + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_blank + ewcfg.emote_blank + '\n' + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_negaslime + ewcfg.emote_srs + ewcfg.emote_negaslime + ewcfg.emote_staydead + ewcfg.emote_staydead + ewcfg.emote_blank + ewcfg.emote_blank + ewcfg.emote_blank))

async def spook(cmd):
	#user_data = EwUser(member=cmd.message.author)
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, '\n' "***SPOOKED YA!***" + '\n' + "https://www.youtube.com/watch?v=T-dtcIXZo4s"))

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

	# checks if user is in a college or if they have a game guide
	gameguide = ewitem.find_item(item_search="gameguide", id_user=cmd.message.author.id, id_server=cmd.message.server.id if cmd.message.server is not None else None)

	if user_data.poi == ewcfg.poi_id_neomilwaukeestate or user_data.poi == ewcfg.poi_id_nlacu or gameguide:
		if not len(cmd.tokens) > 1:
			topic_counter = 0
			topic_total = 0
			# list off help topics to player at college
			response = "(Use !help [topic] to learn about a topic. Example: '!help gangs')\n\nWhat would you like to learn about? Topics include: \n"
			
			# display the list of topics in order
			topics = ewcfg.help_responses_ordered_keys
			for topic in topics:
				topic_counter += 1
				topic_total += 1
				response += "**{}**".format(topic)
				if topic_total != len(topics):
					response += ", "
				
				if topic_counter == 5:
					topic_counter = 0
					response += "\n"
				
		else:
			topic = ewutils.flattenTokenListToString(cmd.tokens[1:])
			if topic in ewcfg.help_responses:
				response = ewcfg.help_responses[topic]
				if topic == 'mymutations':
					mutations = user_data.get_mutations()
					for mutation in mutations:
						response += "\n**{}**: {}".format(mutation, ewcfg.mutation_descriptions[mutation])
			else:
				response = 'ENDLESS WAR questions your belief in the existence of such a topic. Try referring to the topics list again by using just !help.'
	else:
		# user not in college, check what help message would apply to the subzone they are in

		# poi variable assignment used for checking if player is in a vendor subzone or not
		poi = ewcfg.id_to_poi.get(user_data.poi)

		dojo_topics = ["dojo", "sparring", "combat", "sap", ewcfg.weapon_id_revolver, ewcfg.weapon_id_dualpistols, ewcfg.weapon_id_shotgun, ewcfg.weapon_id_rifle, ewcfg.weapon_id_smg, ewcfg.weapon_id_minigun, ewcfg.weapon_id_bat, ewcfg.weapon_id_brassknuckles, ewcfg.weapon_id_katana, ewcfg.weapon_id_broadsword, ewcfg.weapon_id_nunchucks, ewcfg.weapon_id_scythe, ewcfg.weapon_id_yoyo, ewcfg.weapon_id_bass, ewcfg.weapon_id_umbrella, ewcfg.weapon_id_knives, ewcfg.weapon_id_molotov, ewcfg.weapon_id_grenades, ewcfg.weapon_id_garrote]

		if user_data.poi in [ewcfg.poi_id_mine, ewcfg.poi_id_cv_mines, ewcfg.poi_id_tt_mines]:
			# mine help
			response = ewcfg.help_responses['mining']
		elif (len(poi.vendors) >= 1) and not user_data.poi in ewcfg.poi_id_dojo:
			# food help
			response = ewcfg.help_responses['food']
		elif user_data.poi in ewcfg.poi_id_dojo and not len(cmd.tokens) > 1:
			# dojo help
			response = "For general dojo information, do **'!help dojo'**. For information about the sparring and weapon rank systems, do **'!help sparring.'**. For general information about combat, do **'!help combat'**. For information about the sap system, do **'!help sap'**. For information about a specific weapon, do **'!help [weapon]'**."
		elif user_data.poi in ewcfg.poi_id_dojo and len(cmd.tokens) > 1:
			topic = ewutils.flattenTokenListToString(cmd.tokens[1:])
			if topic in dojo_topics and topic in ewcfg.help_responses:
				response = ewcfg.help_responses[topic]
			else:
				response = 'ENDLESS WAR questions your belief in the existence of such information regarding the dojo. Try referring to the topics list again by using just !help.'
		elif user_data.poi in [ewcfg.poi_id_jr_farms, ewcfg.poi_id_og_farms, ewcfg.poi_id_ab_farms]:
			# farming help
			response = ewcfg.help_responses['farming']
		elif user_data.poi in ewcfg.poi_id_slimeoidlab and not len(cmd.tokens) > 1:
			# labs help
			response = "For information on slimeoids, do **'!help slimeoids'**. To learn about your current mutations, do **'!help mymutations'**"
		elif user_data.poi in ewcfg.poi_id_slimeoidlab and len(cmd.tokens) > 1:
			topic = ewutils.flattenTokenListToString(cmd.tokens[1:])
			if topic == 'slimeoids':
				response = ewcfg.help_responses['slimeoids']
			elif topic == 'mymutations':
				response = ewcfg.help_responses['mymutations']
				mutations = user_data.get_mutations()
				for mutation in mutations:
					response += "\n**{}**: {}".format(mutation, ewcfg.mutation_descriptions[mutation])
			else:
				response = 'ENDLESS WAR questions your belief in the existence of such information regarding the laboratory. Try referring to the topics list again by using just !help.'
		elif user_data.poi in ewcfg.transport_stops:
			# transportation help
			response = ewcfg.help_responses['transportation']
		elif user_data.poi in ewcfg.poi_id_stockexchange:
			# stock exchange help
			response = ewcfg.help_responses['stocks']
		elif user_data.poi in ewcfg.poi_id_thecasino:
			# casino help
			response = ewcfg.help_responses['casino']
		elif user_data.poi in ewcfg.poi_id_thesewers:
			# death help
			response = ewcfg.help_responses['death']

		elif user_data.poi in ewcfg.poi_id_realestate:
			#real estate help
			response = ewcfg.help_responses['realestate']
		elif user_data.poi in [
			ewcfg.poi_id_toxington_pier,
			ewcfg.poi_id_assaultflatsbeach_pier,
			ewcfg.poi_id_vagrantscorner_pier,
			ewcfg.poi_id_crookline_pier,
			ewcfg.poi_id_slimesend_pier,
			ewcfg.poi_id_jaywalkerplain_pier,
			ewcfg.poi_id_ferry
		]:
			# fishing help
			response = ewcfg.help_responses['fishing']
		elif user_data.poi in ewcfg.outskirts_districts:
			# hunting help
			response = ewcfg.help_responses['hunting']
		else:
			# catch-all response for when user isn't in a sub-zone with a help response
			response = ewcfg.generic_help_response
				
	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


"""
	Link to the world map.
"""
async def map(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Online world map: https://ew.krakissi.net/map/'))

"""
	Link to the subway map
"""
async def transportmap(cmd):
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Map of the subway: https://cdn.discordapp.com/attachments/431238867459375145/570392908780404746/t_system_final_stop_telling_me_its_wrong_magicks.png\nPlease note that the white line is currently non-operational, and that there also exists a **blimp** that goes between Dreadford and Assault Flats Beach, as well as a **ferry** that goes between Wreckington and Vagrant's Corner."))


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
			response = ""
			if cmd.message.channel.name == ewcfg.channel_arena and ewslimeoid.active_slimeoidbattles.get(slimeoid_data.id_slimeoid):
				response = "You accept the challenge! Both of your Slimeoids ready themselves for combat!"
			elif cmd.message.channel.name == ewcfg.channel_casino:
				response = "You accept the challenge! Both of you head out back behind the casino and load a bullet into the gun."

			if len(response) > 0:
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

"""
	Allow a player to participate in the game again
"""
async def release(cmd):

	author = cmd.message.author
	
	if not author.server_permissions.administrator:
		return
	
	if cmd.mentions_count == 1:
		member = cmd.mentions[0]
		user_data = EwUser(member = member)
		user_data.arrested = False
		user_data.persist()

		response = "{} is released. But beware, the cops will be keeping an eye on you.".format(member.display_name)
		await ewrolemgr.updateRoles(client = cmd.client, member = member)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

"""
	Grants executive status
"""
async def promote(cmd):

	author = cmd.message.author
	
	if not author.server_permissions.administrator:
		return
	
	if cmd.mentions_count == 1:
		member = cmd.mentions[0]
		user_data = EwUser(member = member)
		user_data.life_state = ewcfg.life_state_executive
		user_data.persist()

		await ewrolemgr.updateRoles(client = cmd.client, member = member)

""" !piss """
async def piss(cmd):
	user_data = EwUser(member = cmd.message.author)
	mutations = user_data.get_mutations()

	if ewcfg.mutation_id_enlargedbladder in mutations:
		response = "You unzip your dick and just start pissing all over the goddamn fucking floor. God, you’ve waited so long for this moment, and it’s just as perfect as you could have possibly imagined. You love pissing so much."

	else:
		response = "You lack the moral fiber necessary for urination."

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

"""find out how many days are left until the 31st"""
async def fursuit(cmd):
	user_data = EwUser(member=cmd.message.author)
	mutations = user_data.get_mutations()
	market_data = EwMarket(id_server=cmd.message.server.id)

	if ewcfg.mutation_id_organicfursuit in mutations:
		days_until = -market_data.day % 31
		
		if days_until == 0:
			response = "Hair is beginning to grow on the surface of your skin rapidly. Your canine instincts will take over soon!"
		else:
			response = "With a basic hairy palm reading, you determine that you'll be particularly powerful in {} day{}.".format(days_until, "s" if days_until is not 1 else "")

		if ewutils.check_fursuit_active(user_data.id_server):
			response = "The full moon shines above! Now's your chance to strike!"
			
	else:
		response = "You're about as hairless as an egg, my friend."

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

"""recycle your trash at the SlimeCorp Recycling plant"""
async def recycle(cmd):
	user_data = EwUser(member=cmd.message.author)
	response = ""

	if user_data.poi != ewcfg.poi_id_recyclingplant:
		response = "You can only {} your trash at the SlimeCorp Recycling Plant in Smogsburg.".format(cmd.tokens[0])
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])

	item_sought = ewitem.find_item(item_search = item_search, id_user = cmd.message.author.id, id_server = cmd.message.server.id if cmd.message.server is not None else None)
	
	if item_sought:
		item = EwItem(id_item = item_sought.get("id_item"))

		if not item.soulbound:
			if item.item_type == ewcfg.it_weapon and user_data.weapon >= 0 and item.id_item == user_data.weapon:
				if user_data.weaponmarried:
					weapon = ewcfg.weapon_map.get(item.item_props.get("weapon_type"))
					response = "Woah, wow, hold on there! Domestic violence is one thing, but how could you just throw your faithful {} into a glorified incinerator? Look, we all have bad days, but that's no way to treat a weapon. At least get a proper divorce first, you animal.".format(weapon.str_weapon)
					return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
				else:
					user_data.weapon = -1
					user_data.persist()
			
			ewitem.item_delete(id_item = item.id_item)

			pay = int(random.random() * 10 ** random.randrange(2,5))
			response = "You put your {} into the designated opening. **CRUSH! Splat!** *hiss...* and it's gone. \"Thanks for keeping the city clean.\" a robotic voice informs you.".format(item_sought.get("name"))
			if pay == 0:
				item_reward = random.choice(ewcfg.mine_results)

				item_props = ewitem.gen_item_props(item_reward)

				ewitem.item_create(
					item_type = item_reward.item_type,
					id_user = cmd.message.author.id,
					id_server = cmd.message.server.id,
					item_props = item_props
				)

				ewstats.change_stat(user = user_data, metric = ewcfg.stat_lifetime_poudrins, n = 1)

				response += "\n\nYou receive a {}!".format(item_reward.str_name)
			else:
				user_data.change_slimecoin(n=pay, coinsource = ewcfg.coinsource_recycle)
				user_data.persist()

				response += "\n\nYou receive {:,} SlimeCoin.".format(pay)

		else:
			response = "You can't {} soulbound items.".format(cmd.tokens[0])
	else:
		if item_search:
			response = "You don't have one"
		else:
			response = "{} which item? (check **!inventory**)".format(cmd.tokens[0])

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def store_item(cmd):
	user_data = EwUser(member = cmd.message.author)
	poi = ewcfg.id_to_poi.get(user_data.poi)

	if poi.community_chest != None:
		return await ewfaction.store(cmd)
	elif poi.is_apartment:
		response = "Try that in a DM to ENDLESS WAR."
	else:
		response = "There is no storage here, public or private."
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def remove_item(cmd):
	user_data = EwUser(member = cmd.message.author)
	poi = ewcfg.id_to_poi.get(user_data.poi)

	if poi.community_chest != None:
		return await ewfaction.take(cmd)
	elif poi.is_apartment:
		response = "Try that in a DM to ENDLESS WAR."
	else:
		response = "There is no storage here, public or private."
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def view_sap(cmd):
	user_data = EwUser(member = cmd.message.author)
	
	if cmd.mentions_count > 1:
		response = "One at a time."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	elif cmd.mentions_count == 1:
		member = cmd.mentions[0]
		target_data = EwUser(member = member)
		response = "{} has {} hardened sap and {} liquid sap.".format(member.display_name, target_data.hardened_sap, target_data.sap)
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		response = "You have {} hardened sap and {} liquid sap.".format(user_data.hardened_sap, user_data.sap)
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


async def push(cmd):
	user_data = EwUser(member=cmd.message.author)
	districtmodel = ewdistrict.EwDistrict(id_server=cmd.message.server.id, district=ewcfg.poi_id_slimesendcliffs)

	if cmd.mentions_count == 0:
		response = "You try to push a nearby building. Nope, still not strong enough to move it."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	elif cmd.mentions_count >= 2:
		response = "You can't push more than one person at a time."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	target = cmd.mentions[0]
	targetmodel = EwUser(member=target)
	target_mutations = targetmodel.get_mutations()
	user_mutations = user_data.get_mutations()

	server = cmd.message.server

	if targetmodel.poi != user_data.poi:
		response = "You can't {} them because they aren't here.".format(cmd.tokens[0])
		
	elif user_data.poi != ewcfg.poi_id_slimesendcliffs:
		response = random.choice(ewcfg.bully_responses)

		formatMap = {}
		formatMap["target_name"] = target.display_name

		slimeoid_model = EwSlimeoid(id_server=cmd.message.server.id, id_user=targetmodel.id_user)
		if slimeoid_model.name != "":
			slimeoid_model = slimeoid_model.name
		else:
			slimeoid_model = ""

		cosmetics = ewitem.inventory(id_user=targetmodel.id_user, id_server=targetmodel.id_server, item_type_filter=ewcfg.it_cosmetic)
		selected_cos = None
		for cosmetic in cosmetics:
			cosmetic_item = EwItem(id_item=cosmetic.get('id_item'))
			if cosmetic_item.item_props.get('adorned') == "true":
				selected_cos = cosmetic
				break

		if selected_cos == None:
			selected_cos = "PANTS"
		else:
			selected_cos = id_item = selected_cos.get('name')

		formatMap["cosmetic"] = selected_cos.upper()

		if "{slimeoid}" in response:
			if slimeoid_model != "":
				formatMap["slimeoid"] = slimeoid_model
			elif slimeoid_model == "":
				response = "You push {target_name} into a puddle of sludge, laughing at how hopelessly dirty they are."
			
		response = response.format_map(formatMap)

	elif user_data.life_state == ewcfg.life_state_corpse:
		response = "You attempt to push {} off the cliff, but your hand passes through them. If you're going to push someone, make sure you're corporeal.".format(target.display_name)

	elif targetmodel.life_state == ewcfg.life_state_corpse:
		response = "You try to give ol' {} a shove, but they're a bit too dead to be taking up physical space.".format(target.display_name)

	elif (ewcfg.mutation_id_bigbones in target_mutations or ewcfg.mutation_id_fatchance in target_mutations) and ewcfg.mutation_id_lightasafeather not in target_mutations:
		response = "You try to push {}, but they're way too heavy. It's always fat people, constantly trying to prevent your murderous schemes.".format(target.display_name)

	elif targetmodel.life_state == ewcfg.life_state_kingpin:
		response = "You sneak behind the kingpin and prepare to push. The crime you're about to commit is so heinous that you start snickering to yourself, and {} catches you in the act. Shit, mission failed.".format(target.display_name)

	elif ewcfg.mutation_id_lightasafeather in user_mutations:
		response = "You strain to push {} off the cliff, but your light frame gives you no lifting power.".format(target.display_name)

	else:
		response = "You push {} off the cliff and watch them scream in agony as they fall. Sea monsters frenzy on their body before they even land, gnawing them to jagged ribbons and gushing slime back to the clifftop.".format(target.display_name)

		if ewcfg.mutation_id_lightasafeather in target_mutations:
			response = "You pick {} up with your thumb and index finger, and gently toss them off the cliff. Wow. That was easy.".format(target.display_name)

		slimetotal = targetmodel.slimes * 0.75
		districtmodel.change_slimes(n=slimetotal)
		districtmodel.persist()

		deathreport = "You fell off a cliff. {}".format(ewcfg.emote_slimeskull)
		deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(target, deathreport)

		cliff_inventory = ewitem.inventory(id_server=cmd.message.server.id, id_user=targetmodel.id_user)
		for item in cliff_inventory:
			item_object = ewitem.EwItem(id_item=item.get('id_item'))
			if item.get('soulbound') == True:
				pass

			elif item_object.item_type == ewcfg.it_weapon:
				if item.get('id_item') == targetmodel.weapon:
					ewitem.give_item(id_item=item_object.id_item, id_user=ewcfg.poi_id_slimesea, id_server=cmd.message.server.id)

				else:
					item_off(id_item=item.get('id_item'), is_pushed_off=True, item_name=item.get('name'), id_server=cmd.message.server.id)


			elif item_object.item_props.get('adorned') == 'true':
				ewitem.give_item(id_item=item_object.id_item, id_user=ewcfg.poi_id_slimesea, id_server=cmd.message.server.id)

			else:
				item_off(id_item=item.get('id_item'), is_pushed_off=True, item_name=item.get('name'), id_server=cmd.message.server.id)



		targetmodel.die(cause = ewcfg.cause_cliff)
		targetmodel.persist()
		await ewrolemgr.updateRoles(client=cmd.client, member=target)
		if deathreport != "":
			sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
			await ewutils.send_message(cmd.client, sewerchannel, deathreport)

	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def jump(cmd):
	user_data = EwUser(member=cmd.message.author)

	if user_data.poi != ewcfg.poi_id_slimesendcliffs:
		response = "You jump. Nope. Still not good at parkour."
	elif user_data.life_state == ewcfg.life_state_corpse:
		response = "You're already dead. You'd just ghost hover above the cliff."
	elif user_data.life_state == ewcfg.life_state_kingpin:
		response = "You try to end things right here. Sadly, the gangster sycophants that kiss the ground you walk on grab your ankles in desperation and prevent you from suicide. Oh, the price of fame."
	else:
		response = "Hmm. The cliff looks safe enough. You imagine, with the proper diving posture, you'll be able to land in the slime unharmed. You steel yourself for the fall, run along the cliff, and swan dive off its steep edge. Of course, you forgot that the Slime Sea is highly corrosive, there are several krakens there, and you can't swim. Welp, time to die."
		deathreport = "You fell off a cliff. {}".format(ewcfg.emote_slimeskull)
		deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(cmd.message.author, deathreport)

		cliff_inventory = ewitem.inventory(id_server=cmd.message.server.id, id_user=user_data.id_user)
		for item in cliff_inventory:
			item_object = ewitem.EwItem(id_item=item.get('id_item'))
			if item.get('soulbound') == True:
				pass

			elif item_object.item_type == ewcfg.it_weapon:
				if item.get('id_item') == user_data.weapon:
					ewitem.give_item(id_item=item_object.id_item, id_user=ewcfg.poi_id_slimesea, id_server=cmd.message.server.id)

				else:
					item_off(id_item=item.get('id_item'), is_pushed_off=True, item_name=item.get('name'), id_server=cmd.message.server.id)


			elif item_object.item_props.get('adorned') == 'true':
				ewitem.give_item(id_item=item_object.id_item, id_user=ewcfg.poi_id_slimesea, id_server=cmd.message.server.id)

			else:
				item_off(id_item=item.get('id_item'), is_pushed_off=True, item_name=item.get('name'), id_server=cmd.message.server.id)

		user_data.die(cause = ewcfg.cause_cliff)
		user_data.persist()
		await ewrolemgr.updateRoles(client=cmd.client, member=cmd.message.author)
		if deathreport != "":
			sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
			await ewutils.send_message(cmd.client, sewerchannel, deathreport)
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


async def toss_off_cliff(cmd):
	user_data = EwUser(member=cmd.message.author)
	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
	item_sought = ewitem.find_item(item_search=item_search, id_user=cmd.message.author.id, id_server=user_data.id_server)

	if user_data.poi != ewcfg.poi_id_slimesendcliffs:
		return await ewitem.discard(cmd=cmd)

	elif item_sought:
		item_obj = EwItem(id_item=item_sought.get('id_item'))
		if item_obj.soulbound == True:
			response = "That's soulbound. You can't get rid of it just because you're in a more dramatic looking place."

		elif item_obj.item_type == ewcfg.it_weapon and user_data.weapon >= 0 and item_obj.id_item == user_data.weapon:
			if user_data.weaponmarried:
				weapon = ewcfg.weapon_map.get(item_obj.item_props.get("weapon_type"))
				response = "You decide not to chuck your betrothed off the cliff because you care about them very very much. See {}? I'm not going to hurt you. You don't have to call that social worker again.".format(weapon.str_weapon)
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

			else:
				response = item_off(item_sought.get('id_item'), user_data.id_server, item_sought.get('name'))
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		else:
			response = item_off(item_sought.get('id_item'), user_data.id_server, item_sought.get('name'))
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		response = "You don't have that item."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))




def item_off(id_item, id_server, item_name = "", is_pushed_off = False):
	item_obj = EwItem(id_item=id_item)
	districtmodel = ewdistrict.EwDistrict(id_server=id_server, district=ewcfg.poi_id_slimesendcliffs)
	slimetotal = 0

	if random.randrange(500) < 125 or item_obj.item_type == ewcfg.it_questitem or item_obj.item_type == ewcfg.it_medal or item_obj.item_props.get('rarity') == ewcfg.rarity_princeps or item_obj.item_props.get('id_cosmetic') == "soul" or item_obj.item_props.get('id_furniture') == "propstand":
		response = "You toss the {} off the cliff. It sinks into the ooze disappointingly.".format(item_name)
		ewitem.give_item(id_item=id_item, id_server=id_server, id_user=ewcfg.poi_id_slimesea)

	elif random.randrange(500) < 498:
		response = "You toss the {} off the cliff. A nearby kraken swoops in and chomps it down with the cephalapod's equivalent of a smile. Your new friend kicks up some sea slime for you. Sick!".format(item_name)
		slimetotal = 2000 + random.randrange(10000)
		ewitem.item_delete(id_item=id_item)

	else:
		response = "{} Oh fuck. FEEDING FRENZY!!! Sea monsters lurch down on the spoils like it's fucking christmas, and a ridiculous level of slime debris covers the ground. {}".format(ewcfg.emote_slime1, ewcfg.emote_slime1)
		slimetotal = 100000 + random.randrange(900000)

		ewitem.item_delete(id_item=id_item)

	districtmodel.change_slimes(n=slimetotal)
	districtmodel.persist()
	return response


async def confirm(cmd):
	return

async def cancel(cmd):
	return


