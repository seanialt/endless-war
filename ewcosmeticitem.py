import math
import random

import ewcfg
import ewitem
import ewutils
import asyncio

from ew import EwUser
from ewitem import EwItem

"""
	Cosmetic item model object
"""
class EwCosmeticItem:
	item_type = "cosmetic"

	# The proper name of the cosmetic item
	id_cosmetic = ""

	# The string name of the cosmetic item
	str_name = ""

	# The text displayed when you look at it
	str_desc = ""

	# How rare the item is, can be "Plebeian", "Patrician", or "Princeps"
	rarity = ""

	# The ingredients necessary to make this item via it's acquisition method
	ingredients = ""

	# Cost in SlimeCoin to buy this item.
	price = 0

	# Names of the vendors selling this item.
	vendors = []

	def __init__(
		self,
		id_cosmetic = "",
		str_name = "",
		str_desc = "",
		rarity = "",
		ingredients = "",
		acquisition = "",
		price = 0,
		vendors = [],

	):
		self.item_type = ewcfg.it_cosmetic

		self.id_cosmetic = id_cosmetic
		self.str_name = str_name
		self.str_desc = str_desc
		self.rarity = rarity
		self.ingredients = ingredients
		self.acquisition = acquisition
		self.price = price
		self.vendors = vendors

async def adorn(cmd):
	item_id = ewutils.flattenTokenListToString(cmd.tokens[1:])

	try:
		item_id_int = int(item_id)
	except:
		item_id_int = None

	if item_id != None and len(item_id) > 0:
		response = "You don't have one."

		items = ewitem.inventory(
			id_user = cmd.message.author.id,
			id_server = cmd.message.server.id,
			item_type_filter = ewcfg.it_cosmetic
		)

		item_sought = None
		item_from_slimeoid = None
		already_adorned = False
		for item in items:
			if item.get('id_item') == item_id_int or item_id in ewutils.flattenTokenListToString(item.get('name')):
				i = EwItem(item.get('id_item'))
				if item_from_slimeoid == None and i.item_props.get("slimeoid") == 'true':
					item_from_slimeoid = i
					continue

				if i.item_props.get("adorned") == 'true':
					already_adorned = True
				else:
					item_sought = i
					break

		if item_sought == None:
			item_sought = item_from_slimeoid

		if item_sought != None:
			adorned_items = 0
			for it in items:
				i = EwItem(it.get('id_item'))
				if i.item_props['adorned'] == 'true':
					adorned_items += 1

			user_data = EwUser(member = cmd.message.author)

			if adorned_items >= ewutils.max_adorn_bylevel(user_data.slimelevel):
				response = "You can't adorn anymore cosmetics."
			else:
				item_sought.item_props['adorned'] = 'true'

				if item_sought.item_props.get('slimeoid') == 'true':
					item_sought.item_props['slimeoid'] = 'false'
					response = "You take your {} from your slimeoid and successfully adorn it.".format(
						item_sought.item_props.get('cosmetic_name'))

				else:
					response = "You successfully adorn your " + item_sought.item_props['cosmetic_name'] + "."

				item_sought.persist()

		elif already_adorned:
			response = "You already have it adorned."

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	else:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Adorn which cosmetic? Check your **!inventory**.'))

async def dedorn(cmd):
	item_id = ewutils.flattenTokenListToString(cmd.tokens[1:])

	try:
		item_id_int = int(item_id)
	except:
		item_id_int = None

	if item_id != None and len(item_id) > 0:
		response = "You don't have one."

		items = ewitem.inventory(
			id_user = cmd.message.author.id,
			id_server = cmd.message.server.id,
			item_type_filter = ewcfg.it_cosmetic
		)

		item_sought = None
		for item in items:
			if item.get('id_item') == item_id_int or item_id in ewutils.flattenTokenListToString(item.get('name')):
				i = EwItem(item.get('id_item'))
				if i.item_props.get("adorned") == 'true':
					item_sought = i
					break

		if item_sought != None:
			item_sought.item_props['adorned'] = 'false'

			response = "You successfully dedorn your " + item_sought.item_props['cosmetic_name'] + "."

			item_sought.persist()

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	else:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'Dedorn which cosmetic? Check your **!inventory**.'))


async def dye(cmd):
	first_id = ewutils.flattenTokenListToString(cmd.tokens[1:2])
	second_id = ewutils.flattenTokenListToString(cmd.tokens[2:])

	try:
		first_id_int = int(first_id)
		second_id_int = int(second_id)
	except:
		first_id_int = None
		second_id_int = None

	if first_id != None and len(first_id) > 0 and second_id != None and len(second_id) > 0:
		response = "You don't have one."

		items = ewitem.inventory(
			id_user = cmd.message.author.id,
			id_server = cmd.message.server.id,
		)

		cosmetic = None
		dye = None
		for item in items:
			if item.get('id_item') in [first_id_int, second_id_int] or first_id in ewutils.flattenTokenListToString(item.get('name')) or second_id in ewutils.flattenTokenListToString(item.get('name')):
				if item.get('item_type') == ewcfg.it_cosmetic and cosmetic is None:
					cosmetic = item

				if item.get('item_type') == ewcfg.it_item and item.get('name') in ewcfg.dye_map and dye is None:
					dye = item	

				if cosmetic != None and dye != None:
					break

		if cosmetic != None:
			if dye != None:
				user_data = EwUser(member = cmd.message.author)

				cosmetic_item = EwItem(id_item=cosmetic.get("id_item"))
				dye_item = EwItem(id_item=dye.get("id_item"))

				hue = ewcfg.hue_map.get(dye_item.item_props.get('id_item'))

				response = "You dye your {} in {} paint!".format(cosmetic_item.item_props.get('cosmetic_name'), hue.str_name)
				cosmetic_item.item_props['hue'] = hue.id_hue

				cosmetic_item.persist()
				ewitem.item_delete(id_item=dye.get('id_item'))
			else:
				response = 'Use which dye? Check your **!inventory**.'
		else:
			response = 'Dye which cosmetic? Check your **!inventory**.'
		
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	else:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, 'You need to specify which cosmetic you want to paint and which dye you want to use! Check your **!inventory**.'))

async def smoke(cmd):
	usermodel = EwUser(member=cmd.message.author)
	#item_sought = ewitem.find_item(item_search="cigarette", id_user=cmd.message.author.id, id_server=usermodel.id_server)
	item_sought = None
	item_stash = ewitem.inventory(id_user=cmd.message.author.id, id_server=usermodel.id_server)
	for item_piece in item_stash:
		item = EwItem(id_item=item_piece.get('id_item'))
		if item_piece.get('item_type') == ewcfg.it_cosmetic and item.item_props.get('id_cosmetic') == "cigarette" and "lit" not in item.item_props.get('cosmetic_desc'):
			item_sought = item_piece

	if item_sought:
		item = EwItem(id_item=item_sought.get('id_item'))
		if item_sought.get('item_type') == ewcfg.it_cosmetic and item.item_props.get('id_cosmetic') == "cigarette":
			response = "You light a cig and bring it to your mouth. So relaxing. So *cool*. All those naysayers and PSAs in Health class can go fuck themselves."
			item.item_props['cosmetic_desc'] = "A single lit cigarette sticking out of your mouth. You huff these things down in seconds but you’re never seen without one. Everyone thinks you’re really, really cool."
			item.item_props['adorned'] = "true"
			item.persist()
			await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
			await asyncio.sleep(60)
			item = EwItem(id_item=item_sought.get('id_item'))

			response = "The cigarette fizzled out."

			item.item_props['cosmetic_desc'] = "It's a cigarette butt. What kind of hoarder holds on to these?"
			item.item_props['adorned'] = "false"
			item.item_props['id_cosmetic'] = "cigarettebutt"
			item.item_props['cosmetic_name'] = "cigarette butt"
			item.persist()
		else:
			response = "There aren't any usable cigarettes in your inventory."
	else:
		response = "There aren't any usable cigarettes in your inventory."
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
