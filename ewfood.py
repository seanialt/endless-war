import math
import time
import asyncio

import ewcfg
import ewitem
import ewutils
import random
import ewrolemgr
import ewstatuseffects
from ew import EwUser
from ewmarket import EwMarket, EwCompany, EwStock
from ewitem import EwItem
from ewdistrict import EwDistrict

""" Food model object """
class EwFood:
	item_type = "food"

	# The main name of this food.
	id_food = ""

	# A list of alternative names.
	alias = []

	# Hunger reduced by eating this food.
	recover_hunger = 0

	# Cost in SlimeCoin to eat this food.
	price = 0

	# A nice string name describing this food.
	str_name = ""

	# Names of the vendors selling this food in the food court.
	vendors = []

	# Flavor text displayed when you eat this food.
	str_eat = ""

	# Alcoholic effect
	inebriation = 0

	# Flavor text displayed when you inspect this food.
	str_desc = ""

	# Expiration time (can be left blank for standard expiration time)
	time_expir = 0

	# The ingredients necessary to make this item via it's acquisition method
	ingredients = ""

	# The way that you can acquire this item. If blank, it's not relevant.
	acquisition = ""

	#Timestamp when an item was fridged.

	time_fridged = 0

	def __init__(
		self,
		id_food = "",
		alias = [],
		recover_hunger = 0,
		price = 0,
		str_name = "",
		vendors = [],
		str_eat = "",
		inebriation = 0,
		str_desc = "",
		time_expir = 0,
		time_fridged =0,
		ingredients = "",
		acquisition = "",
	):
		self.item_type = ewcfg.it_food

		self.id_food = id_food
		self.alias = alias
		self.recover_hunger = recover_hunger
		self.price = price
		self.str_name = str_name
		self.vendors = vendors
		self.str_eat = str_eat
		self.inebriation = inebriation
		self.str_desc = str_desc
		self.time_expir = time_expir if time_expir > 0 else ewcfg.std_food_expir
		self.time_fridged = time_fridged
		self.ingredients = ingredients
		self.acquisition = acquisition


""" show all available food items """
async def menu(cmd):
	user_data = EwUser(member = cmd.message.author)
	poi = ewcfg.id_to_poi.get(user_data.poi)
	market_data = EwMarket(id_server = cmd.message.server.id)

	if poi == None or len(poi.vendors) == 0:
		# Only allowed in the food court.
		response = "There’s nothing to buy here. If you want to purchase some items, go to a sub-zone with a vendor in it, like the food court, the speakeasy, or the bazaar."
	else:
		if poi.is_subzone:
			district_data = EwDistrict(district = poi.mother_district, id_server = cmd.message.server.id)
		else:
			district_data = EwDistrict(district = poi.id_poi, id_server = cmd.message.server.id)

		response = "{} Menu:\n\n".format(poi.str_name)

		for vendor in poi.vendors:
			items = []
			# If the vendor is the bazaar get the current rotation of items from the market_data
			vendor_inv = ewcfg.vendor_inv[vendor] if vendor != ewcfg.vendor_bazaar else market_data.bazaar_wares.values()
			for item_name in vendor_inv:
				item_item = ewcfg.item_map.get(item_name)
				food_item = ewcfg.food_map.get(item_name)
				cosmetic_item = ewcfg.cosmetic_map.get(item_name)
				furniture_item = ewcfg.furniture_map.get(item_name)
				weapon_item = ewcfg.weapon_map.get(item_name)


				# increase profits for the stock market
				stock_data = None
				if vendor in ewcfg.vendor_stock_map:
					stock = ewcfg.vendor_stock_map.get(vendor)
					stock_data = EwStock(id_server = user_data.id_server, stock = stock)

				value = 0

				if item_item:
					value = item_item.price

				if food_item:
					value = food_item.price

				if cosmetic_item:
					value = cosmetic_item.price

				if furniture_item:
					value = furniture_item.price

				if weapon_item:
					value = weapon_item.price

				if stock_data != None:
					value *= (stock_data.exchange_rate / ewcfg.default_stock_exchange_rate) ** 0.2


				if district_data.controlling_faction != "":
					# prices are halved for the controlling gang
					if district_data.controlling_faction == user_data.faction:
						value /= 2

					# and 4 times as much for enemy gangsters
					elif user_data.faction != "":
						value *= 4

				value = int(value)

				if value != 0:
					items.append('{name} ({price})'.format(name = item_name, price = value))
				else:
					items.append(item_name)

			response += "**{}**: *{}*\n".format(vendor, ewutils.formatNiceList(names = items))
			if user_data.has_soul == 0:
				if vendor == ewcfg.vendor_dojo:
					response += "\n\nThe Dojo master looks at your soulless form with pity."
				elif vendor == ewcfg.vendor_bar:
					response += "\n\nThe bartender, sensing your misery, asks if you're okay."
				elif vendor == ewcfg.vendor_diner:
					response += "\n\nThe cook gives you a concerned look as he throws down another helping of flapjacks."
				elif vendor == ewcfg.vendor_seafood:
					response += "\n\nThe waiter sneers at how soulless and unkempt you look. You try to ignore him."
				elif vendor == ewcfg.vendor_bazaar:
					response += "\n\nAll the shops seem so lively. You wish you had a soul so you could be like them."
				elif vendor == ewcfg.vendor_beachresort or vendor == ewcfg.vendor_countryclub:
					response += "\n\nEverything looks so fancy here, but it doesn't really appeal to you since you don't have a soul."


	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

# Buy items.
async def order(cmd):
	user_data = EwUser(member = cmd.message.author)
	poi = ewcfg.id_to_poi.get(user_data.poi)
	market_data = EwMarket(id_server = cmd.message.server.id)

	if poi == None or len(poi.vendors) == 0:
		# Only allowed in the food court.
		response = "There’s nothing to buy here. If you want to purchase some items, go to a sub-zone with a vendor in it, like the food court, the speakeasy, or the bazaar."
	else:
		value = ewutils.flattenTokenListToString(cmd.tokens[1:])
		#if cmd.tokens_count > 1:
		#	value = cmd.tokens[1]
		#	value = value.lower()

		# Finds the item if it's an EwGeneralItem.

		item = ewcfg.item_map.get(value)
		item_type = ewcfg.it_item
		if item != None:
			item_id = item.id_item
			name = item.str_name

		# Finds the item if it's an EwFood item.
		if item == None:
			item = ewcfg.food_map.get(value)
			item_type = ewcfg.it_food
			if item != None:
				item_id = item.id_food
				name = item.str_name

		# Finds the item if it's an EwCosmeticItem.
		if item == None:
			item = ewcfg.cosmetic_map.get(value)
			item_type = ewcfg.it_cosmetic
			if item != None:
				item_id = item.id_cosmetic
				name = item.str_name

		if item == None:
			item = ewcfg.furniture_map.get(value)
			item_type = ewcfg.it_furniture
			if item != None:
				item_id = item.id_furniture
				name = item.str_name

		if item == None:
			item = ewcfg.weapon_map.get(value)
			item_type = ewcfg.it_weapon
			if item != None: 
				item_id = item.id_weapon
				name = item.str_weapon


		if item != None:
			item_type = item.item_type
			# Gets a vendor that the item is available and the player currently located in
			try:
				current_vendor = (set(item.vendors).intersection(set(poi.vendors))).pop()
			except:
				current_vendor = None

			# Check if the item is available in the current bazaar item rotation
			if current_vendor == ewcfg.vendor_bazaar:
				if item_id not in market_data.bazaar_wares.values():
					current_vendor = None

			if current_vendor is None or len(current_vendor) < 1:
				response = "Check the {} for a list of items you can {}.".format(ewcfg.cmd_menu, ewcfg.cmd_order)

			else:
				response = ""

				value = item.price

				stock_data = None
				company_data = None
				# factor in the current stocks
				for vendor in item.vendors:
					if vendor in ewcfg.vendor_stock_map:
						stock = ewcfg.vendor_stock_map.get(vendor)
						company_data = EwCompany(id_server = user_data.id_server, stock = stock)
						stock_data = EwStock(id_server = user_data.id_server, stock = stock)

				if stock_data is not None:
					value *= (stock_data.exchange_rate / ewcfg.default_stock_exchange_rate) ** 0.2

				if poi.is_subzone:
					district_data = EwDistrict(district = poi.mother_district, id_server = cmd.message.server.id)
				else:
					district_data = EwDistrict(district = poi.id_poi, id_server = cmd.message.server.id)


				if district_data.controlling_faction != "":
					# prices are halved for the controlling gang
					if district_data.controlling_faction == user_data.faction:
						value /= 2

					# and 4 times as much for enemy gangsters
					elif user_data.faction != "":
						value *= 4

				value = int(value)

				# Kingpins eat free.
				if user_data.life_state == ewcfg.life_state_kingpin or user_data.life_state == ewcfg.life_state_grandfoe:
					value = 0

				if value > user_data.slimes:
					# Not enough money.
					response = "A {} costs {:,} slime, and you only have {:,}.".format(name, value, user_data.slimes)
				else:
					if item_type == ewcfg.it_food:
						food_items = ewitem.inventory(
							id_user = cmd.message.author.id,
							id_server = cmd.message.server.id,
							item_type_filter = ewcfg.it_food
						)

						if len(food_items) >= user_data.get_food_capacity():
							# user_data never got persisted so the player won't lose money unnecessarily
							response = "You can't carry any more food than that."
							return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

					elif item_type == ewcfg.it_weapon:
						weapons_held = ewitem.inventory(
							id_user = user_data.id_user,
							id_server = cmd.message.server.id,
							item_type_filter = ewcfg.it_weapon
						)

						has_weapon = False

						# Thrown weapons are stackable
						if ewcfg.weapon_class_thrown in item.classes:
							# Check the player's inventory for the weapon and add amount to stack size. Create a new item the max stack size has been reached
							for wep in weapons_held:
								weapon = EwItem(id_item=wep.get("id_item"))
								if weapon.item_props.get("weapon_type") == item.id_weapon and weapon.stack_size < weapon.stack_max:
									has_weapon = True
									weapon.stack_size += 1
									weapon.persist()
									response = "You slam {:,} slime down on the counter at {} for {}.".format(value, current_vendor, item.str_weapon)
									user_data.change_slimes(n=-value, source=ewcfg.source_spending)
									user_data.persist()
									return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

						if has_weapon == False:
							if len(weapons_held) >= user_data.get_weapon_capacity():
								response = "You can't carry any more weapons."
								return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


							elif user_data.life_state == ewcfg.life_state_corpse:
								response = "Ghosts can't hold weapons."
								return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

					user_data.change_slimes(n = -value, source = ewcfg.source_spending)

					if company_data is not None:
						company_data.recent_profits += value
						company_data.persist()

					item_props = ewitem.gen_item_props(item)

					if item.str_name == "arcade cabinet":
						item_props['furniture_desc'] = random.choice(ewcfg.cabinets_list)


					ewitem.item_create(
						item_type = item_type,
						id_user = cmd.message.author.id,
						id_server = cmd.message.server.id,
						stack_max = 20 if item_type == ewcfg.it_weapon and ewcfg.weapon_class_thrown in item.classes else -1,
						stack_size = 1 if item_type == ewcfg.it_weapon and ewcfg.weapon_class_thrown in item.classes else 0,
						item_props = item_props
					)

					response = "You slam {:,} slime down on the counter at {} for {}.".format(value, current_vendor, item.str_name)
					user_data.persist()

		else:
			response = "Check the {} for a list of items you can {}.".format(ewcfg.cmd_menu, ewcfg.cmd_order)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
