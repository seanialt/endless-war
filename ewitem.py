import math
import time
import random
import asyncio

import ewutils
import ewcfg
import ewstats
import ewdistrict
import ewrolemgr
import ewsmelting
from ew import EwUser
from ewplayer import EwPlayer
import re

"""
	EwItemDef is a class used to model base items. These are NOT the items
	owned by players, but rather the description of what those items are.
"""
class EwItemDef:
	# This is the unique reference name for this item.
	item_type = ""

	# If this is true, the item can not be traded or stolen.
	soulbound = False

	# If this value is positive, the item may actually be a pile of the same type of item, up to the specified size.
	stack_max = -1

	# If this value is greater than one, creating this item will actually give the user that many of them.
	stack_size = 1

	# Nice display name for this item.
	str_name = ""

	# The long description of this item's appearance.
	str_desc = ""

	# A map of default additional properties.
	item_props = None

	def __init__(
		self,
		item_type = "",
		str_name = "",
		str_desc = "",
		soulbound = False,
		stack_max = -1,
		stack_size = 1,
		item_props = None
	):
		self.item_type = item_type
		self.str_name = str_name
		self.str_desc = str_desc
		self.soulbound = soulbound
		self.stack_max = stack_max
		self.stack_size = stack_size
		self.item_props = item_props

"""
	EwItem is the instance of an item (described by EwItemDef, linked by
	item_type) which is possessed by a player and stored in the database.
"""
class EwItem:
	id_item = -1
	id_server = ""
	id_owner = ""
	item_type = ""
	time_expir = -1

	stack_max = -1
	stack_size = 0
	soulbound = False

	item_props = None

	def __init__(
		self,
		id_item = None
	):
		if(id_item != None):
			self.id_item = id_item

			self.item_props = {}
			# the item props don't reset themselves automatically which is why the items_prop table had tons of extraneous rows (like food items having medal_names)
			#self.item_props.clear()

			try:
				conn_info = ewutils.databaseConnect()
				conn = conn_info.get('conn')
				cursor = conn.cursor()

				# Retrieve object
				cursor.execute("SELECT {}, {}, {}, {}, {}, {}, {} FROM items WHERE id_item = %s".format(
					ewcfg.col_id_server,
					ewcfg.col_id_user,
					ewcfg.col_item_type,
					ewcfg.col_time_expir,
					ewcfg.col_stack_max,
					ewcfg.col_stack_size,
					ewcfg.col_soulbound
				), (
					self.id_item,
				))
				result = cursor.fetchone();

				if result != None:
					# Record found: apply the data to this object.
					self.id_server = result[0]
					self.id_owner = result[1]
					self.item_type = result[2]
					self.time_expir = result[3]
					self.stack_max = result[4]
					self.stack_size = result[5]
					self.soulbound = (result[6] != 0)

					# Retrieve additional properties
					cursor.execute("SELECT {}, {} FROM items_prop WHERE id_item = %s".format(
						ewcfg.col_name,
						ewcfg.col_value
					), (
						self.id_item,
					))

					for row in cursor:
						# this try catch is only necessary as long as extraneous props exist in the table
						try:
							self.item_props[row[0]] = row[1]
						except:
							ewutils.logMsg("extraneous item_prop row detected.")

				else:
					# Item not found.
					self.id_item = -1

			finally:
				# Clean up the database handles.
				cursor.close()
				ewutils.databaseClose(conn_info)

	""" Save item data object to the database. """
	def persist(self):
		try:
			conn_info = ewutils.databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor()

			# Save the object.
			cursor.execute("REPLACE INTO items({}, {}, {}, {}, {}, {}, {}, {}) VALUES(%s, %s, %s, %s, %s, %s, %s, %s)".format(
				ewcfg.col_id_item,
				ewcfg.col_id_server,
				ewcfg.col_id_user,
				ewcfg.col_item_type,
				ewcfg.col_time_expir,
				ewcfg.col_stack_max,
				ewcfg.col_stack_size,
				ewcfg.col_soulbound
			), (
				self.id_item,
				self.id_server,
				self.id_owner,
				self.item_type,
				self.time_expir if self.time_expir is not None else self.item_props['time_expir'] if 'time_expir' in self.item_props.keys() else 0,
				self.stack_max,
				self.stack_size,
				(1 if self.soulbound else 0)
			))

			# Remove all existing property rows.
			cursor.execute("DELETE FROM items_prop WHERE {} = %s".format(
				ewcfg.col_id_item
			), (
				self.id_item,
			))

			# Write out all current property rows.
			for name in self.item_props:
				cursor.execute("INSERT INTO items_prop({}, {}, {}) VALUES(%s, %s, %s)".format(
					ewcfg.col_id_item,
					ewcfg.col_name,
					ewcfg.col_value
				), (
					self.id_item,
					name,
					self.item_props[name]
				))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			ewutils.databaseClose(conn_info)

"""
	These are unassuming, tangible, multi-faceted, customizable items that you can actually interact with in-game.
"""
class EwGeneralItem:
	item_type = "item"
	id_item = " "
	alias = []
	context = ""
	str_name = ""
	str_desc = ""
	ingredients = ""
	acquisition = ""
	price = 0
	vendors = []

	def __init__(
		self,
		id_item = " ",
		alias = [],
		context = "",
		str_name = "",
		str_desc = "",
		ingredients = "",
		acquisition = "",
		price = 0,
		vendors = [],
	):
		self.item_type = ewcfg.it_item
		self.id_item = id_item
		self.alias = alias
		self.context = context
		self.str_name = str_name
		self.str_desc = str_desc
		self.ingredients = ingredients
		self.acquisition = acquisition
		self.price = price
		self.vendors = vendors


"""
	Delete the specified item by ID. Also deletes all items_prop values.
"""
def item_delete(
	id_item = None
):
	try:
		conn_info = ewutils.databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()

		# Create the item in the database.
		cursor.execute("DELETE FROM items WHERE {} = %s".format(
			ewcfg.col_id_item
		), (
			id_item,
		))

		conn.commit()
	finally:
		# Clean up the database handles.
		cursor.close()
		ewutils.databaseClose(conn_info)
	
	remove_from_trades(id_item)


"""
	Drop item into current district.
"""
def item_drop(
	id_item = None
):
	try:
		item_data = EwItem(id_item = id_item)
		user_data = EwUser(id_user = item_data.id_owner, id_server = item_data.id_server)
		if item_data.item_type == ewcfg.it_cosmetic:
			item_data.item_props["adorned"] = "false"
		item_data.persist()
		give_item(id_user = user_data.poi, id_server = item_data.id_server, id_item = item_data.id_item)
	except:
		ewutils.logMsg("Failed to drop item {}.".format(id_item))

"""
	Create a new item and give it to a player.

	Returns the unique database ID of the newly created item.
"""
def item_create(
	item_type = None,
	id_user = None,
	id_server = None,
	stack_max = -1,
	stack_size = 0,
	item_props = None
):
	item_def = ewcfg.item_def_map.get(item_type)

	if item_def == None:
		ewutils.logMsg('Tried to create invalid item_type: {}'.format(item_type))
		return

	try:
		# Get database handles if they weren't passed.
		conn_info = ewutils.databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()

		# Create the item in the database.

		cursor.execute("INSERT INTO items({}, {}, {}, {}, {}, {}) VALUES(%s, %s, %s, %s, %s, %s)".format(
			ewcfg.col_item_type,
			ewcfg.col_id_user,
			ewcfg.col_id_server,
			ewcfg.col_soulbound,
			ewcfg.col_stack_max,
			ewcfg.col_stack_size
		), (
			item_type,
			id_user,
			id_server,
			(1 if item_def.soulbound else 0),
			stack_max,
			stack_size
		))

		item_id = cursor.lastrowid
		conn.commit()

		if item_id > 0:
			# If additional properties are specified in the item definition or in this create call, create and persist them.
			if item_props != None or item_def.item_props != None:
				item_inst = EwItem(id_item = item_id)

				if item_def.item_props != None:
					item_inst.item_props.update(item_def.item_props)

				if item_props != None:
					item_inst.item_props.update(item_props)

				item_inst.persist()

			conn.commit()
	finally:
		# Clean up the database handles.
		cursor.close()
		ewutils.databaseClose(conn_info)


	return item_id

"""
	Drop all of a player's non-soulbound items into their district
"""
def item_dropall(
	id_server = None,
	id_user = None
):
	
	try:
		user_data = EwUser(id_server = id_server, id_user = id_user)
		
		ewutils.execute_sql_query(
			"UPDATE items SET id_user = %s WHERE id_user = %s AND id_server = %s AND soulbound = 0",(
				user_data.poi,
				id_user,
				id_server
			))

	except:
		ewutils.logMsg('Failed to drop items for user with id {}'.format(id_user))

"""
	Drop some of a player's non-soulbound items into their district.
"""
def item_dropsome(id_server = None, id_user = None, item_type_filter = None, fraction = None):
	#try:
	user_data = EwUser(id_server = id_server, id_user = id_user)
	items = inventory(id_user = id_user, id_server = id_server, item_type_filter = item_type_filter)

	drop_candidates = []
	#safe_items = [ewcfg.item_id_gameguide]

	# Filter out Soulbound items.
	for item in items:
		if item.get('soulbound') == False:
			drop_candidates.append(item)

	filtered_items = []

	if item_type_filter == ewcfg.it_item or item_type_filter == ewcfg.it_food:
		filtered_items = drop_candidates
	if item_type_filter == ewcfg.it_cosmetic:
		for item in drop_candidates:
			cosmetic_id = item.get('id_item')
			cosmetic_item = EwItem(id_item = cosmetic_id)
			if cosmetic_item.item_props.get('adorned') != "true" and cosmetic_item.item_props.get('slimeoid') != "true":
				filtered_items.append(item)

	if item_type_filter == ewcfg.it_weapon:
		for item in drop_candidates:
			if item.get('id_item') != user_data.weapon:
				filtered_items.append(item)
			else:
				pass

	number_of_filtered_items = len(filtered_items)

	number_of_items_to_drop = int(number_of_filtered_items / fraction)

	if number_of_items_to_drop >= 2:
		random.shuffle(filtered_items)
		for drop in range(number_of_items_to_drop):
			for item in filtered_items:
				id_item = item.get('id_item')
				give_item(id_user = user_data.poi, id_server = id_server, id_item = id_item)
				filtered_items.pop(0)
				break
	#except:
	#	ewutils.logMsg('Failed to drop items for user with id {}'.format(id_user))

"""
	Dedorn all of a player's cosmetics
"""
def item_dedorn_cosmetics(
	id_server = None,
	id_user = None
):
	try:
		
		ewutils.execute_sql_query(
			"UPDATE items_prop SET value = 'false' WHERE (name = 'adorned') AND {id_item} IN (\
				SELECT {id_item} FROM items WHERE {id_user} = %s AND {id_server} = %s\
			)".format(
				id_item = ewcfg.col_id_item,
				id_user = ewcfg.col_id_user,
				id_server = ewcfg.col_id_server
			),(
				id_user,
				id_server
			))

	except:
		ewutils.logMsg('Failed to dedorn cosmetics for user with id {}'.format(id_user))


def item_lootspecific(id_server = None, id_user = None, item_search = None):
	response = ""
	if id_server is not None and id_user is not None:
		user_data = EwUser(id_user = id_user, id_server = id_server)
		item_sought = find_item(
			item_search = item_search, 
			id_server = user_data.id_server, 
			id_user = user_data.poi
		)
		if item_sought is not None:
			item_type = item_sought.get("item_type")
			response += "You found a {}!".format(item_sought.get("name"))
			can_loot = check_inv_capacity(id_server = id_server, id_user = id_user, item_type = item_type)
			if can_loot:
				give_item(
					id_item = item_sought.get("id_item"),
					id_user = user_data.id_user,
					id_server = user_data.id_server
				)
			else:
				response += " But you couldn't carry any more {} items, so you tossed it back.".format(item_type)
	return response


"""
	Transfer a random item from district inventory to player inventory
"""
def item_lootrandom(id_server = None, id_user = None):
	response = ""

	try:
		user_data = EwUser(id_server = id_server, id_user = id_user)

		items_in_poi = ewutils.execute_sql_query("SELECT {id_item} FROM items WHERE {id_owner} = %s AND {id_server} = %s".format(
				id_item = ewcfg.col_id_item,
				id_owner = ewcfg.col_id_user,
				id_server = ewcfg.col_id_server
			),(
				user_data.poi,
				id_server
			))

		if len(items_in_poi) > 0:
			id_item = random.choice(items_in_poi)[0]

			item_sought = find_item(item_search = str(id_item), id_user = user_data.poi, id_server = id_server)

			response += "You found a {}!".format(item_sought.get('name'))

			if item_sought.get('item_type') == ewcfg.it_food:
				food_items = inventory(
					id_user = id_user,
					id_server = id_server,
					item_type_filter = ewcfg.it_food
				)

				if len(food_items) >= user_data.get_food_capacity():
					response += " But you couldn't carry any more food items, so you tossed it back."
				else:
					give_item(id_user = id_user, id_server = id_server, id_item = id_item)
			elif item_sought.get('item_type') == ewcfg.it_weapon:
				weapons_held = inventory(
					id_user = id_user,
					id_server = id_server,
					item_type_filter = ewcfg.it_weapon
				)

				if len(weapons_held) >= user_data.get_weapon_capacity():
					response += " But you couldn't carry any more weapons, so you tossed it back."
				else:
					give_item(id_user = id_user, id_server = id_server, id_item = id_item)

			else:
				if item_sought.get('name') == "Slime Poudrin":
					ewstats.change_stat(
						id_server = user_data.id_server,
						id_user = user_data.id_user,
						metric = ewcfg.stat_poudrins_looted,
						n = 1
					)
				give_item(id_user = id_user, id_server = id_server, id_item = id_item)

		else:
			response += "You found a... oh, nevermind, it's just a piece of trash."

	except:
		ewutils.logMsg("Failed to loot random item")

	finally:
		return response

"""
	Destroy all of a player's non-soulbound items.
"""
def item_destroyall(id_server = None, id_user = None, member = None):
	if member != None:
		id_server = member.server.id
		id_user = member.id

	if id_server != None and id_user != None:
		try:
			# Get database handles if they weren't passed.
			conn_info = ewutils.databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor()

			cursor.execute("DELETE FROM items WHERE {id_server} = %s AND {id_user} = %s AND {soulbound} = 0".format(
				id_user = ewcfg.col_id_user,
				id_server = ewcfg.col_id_server,
				soulbound = ewcfg.col_soulbound,
			), (
				id_server,
				id_user
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			ewutils.databaseClose(conn_info)


"""
	Loot all non-soulbound items from a player upon killing them, reassinging to id_user_target.
"""
def item_loot(
	member = None,
	id_user_target = ""
):
	if member == None or len(id_user_target) == 0:
		return

	try:
		target_data = EwUser(id_user = id_user_target, id_server = member.server.id)
		source_data = EwUser(member = member)

		# Transfer adorned cosmetics
		data = ewutils.execute_sql_query(
			"SELECT id_item FROM items " +
			"WHERE id_user = %s AND id_server = %s AND soulbound = 0 AND item_type = %s AND id_item IN (" +
				"SELECT id_item FROM items_prop " +
				"WHERE name = 'adorned' AND value = 'true' " +
			")"
		,(
			member.id,
			member.server.id,
			ewcfg.it_cosmetic
		))

		for row in data:
			item_data = EwItem(id_item = row[0])
			item_data.item_props["adorned"] = 'false'
			item_data.id_owner = id_user_target
			item_data.persist()
				

		ewutils.logMsg('Transferred {} cosmetic items.'.format(len(data)))

		if source_data.weapon >= 0:
			weapons_held = inventory(
				id_user = target_data.id_user,
				id_server = target_data.id_server,
				item_type_filter = ewcfg.it_weapon
			)

			if len(weapons_held) <= target_data.get_weapon_capacity():
				give_item(id_user = target_data.id_user, id_server = target_data.id_server, id_item = source_data.weapon)

	except:
		ewutils.logMsg("Failed to loot items from user {}".format(member.id))
			

def check_inv_capacity(id_user = None, id_server = None, item_type = None):
	if id_user is not None and id_server is not None and item_type is not None:
		user_data = EwUser(id_user = id_user, id_server = id_server)
		if item_type == ewcfg.it_food:
			food_items = inventory(
				id_user = id_user,
				id_server = id_server,
				item_type_filter = ewcfg.it_food
			)

			if len(food_items) >= user_data.get_food_capacity():
				return False
			else:
				return True
		elif item_type == ewcfg.it_weapon:
			weapons_held = inventory(
				id_user = id_user,
				id_server = id_server,
				item_type_filter = ewcfg.it_weapon
			)

			if len(weapons_held) >= user_data.get_weapon_capacity():
				return False
			else:
				return True
		else:
			return True
		
	else:
		return False

"""
	Check how many items are in a given district or player's inventory
"""
def get_inventory_size(owner = None, id_server = None):
	if owner != None and id_server != None:
		try:
			items_in_poi = ewutils.execute_sql_query("SELECT {id_item} FROM items WHERE {id_owner} = %s AND {id_server} = %s".format(
					id_item = ewcfg.col_id_item,
					id_owner = ewcfg.col_id_user,
					id_server = ewcfg.col_id_server
				),(
					owner,
					id_server
				))

			return len(items_in_poi)

		except:
			return 0
	else:
		return 0
	

"""
	Returns true if the command string is !inv or equivalent.
"""
def cmd_is_inventory(cmd):
	return (cmd == ewcfg.cmd_inventory or cmd == ewcfg.cmd_inventory_alt1 or cmd == ewcfg.cmd_inventory_alt2 or cmd == ewcfg.cmd_inventory_alt3)

"""
	Get a list of items for the specified player.

	Specify an item_type_filter to get only those items. Be careful: This is
	inserted into SQL without validation/sanitation.
"""
def inventory(
	id_user = None,
	id_server = None,
	item_type_filter = None,
	item_sorting_method = None,
):
	items = []

	try:

		conn_info = ewutils.databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()

		sql = "SELECT {}, {}, {}, {}, {} FROM items WHERE {} = %s"
		if id_user != None:
			sql += " AND {} = '{}'".format(ewcfg.col_id_user, str(id_user))
		if item_type_filter != None:
			sql += " AND {} = '{}'".format(ewcfg.col_item_type, item_type_filter)
		if item_sorting_method != None:
			if item_sorting_method == 'type':
				sql += " ORDER BY {}".format(ewcfg.col_item_type)
			if item_sorting_method == 'id':
				sql += " ORDER BY {}".format(ewcfg.col_id_item)

		if id_server != None:
			cursor.execute(sql.format(
				ewcfg.col_id_item,
				ewcfg.col_item_type,
				ewcfg.col_soulbound,
				ewcfg.col_stack_max,
				ewcfg.col_stack_size,

				ewcfg.col_id_server
			), [
				id_server
			])

			for row in cursor:
				id_item = row[0]
				item_type = row[1]
				soulbound = (row[2] == 1)
				stack_max = row[3]
				stack_size = row[4]

				if item_type == 'slimepoudrin':
					item_data = EwItem(id_item = id_item)
					item_type = ewcfg.it_item
					item_data.item_type = item_type
					for item in ewcfg.item_list:
						if item.context == "poudrin":
							item_props = {
								'id_item': item.id_item,
								'context': item.context,
								'item_name': item.str_name,
								'item_desc': item.str_desc
							}
					item_def = ewcfg.item_def_map.get(item_type)
					item_data.item_props.update(item_def.item_props)
					item_data.item_props.update(item_props)
					item_data.persist()

					ewutils.logMsg('Updated poudrin to new format: {}'.format(id_item))
					    
				item_def = ewcfg.item_def_map.get(item_type)

				if(item_def != None):
					items.append({
						'id_item': id_item,
						'item_type': item_type,
						'soulbound': soulbound,
						'stack_max': stack_max,
						'stack_size': stack_size,

						'item_def': item_def
					})

			for item in items:
				item_def = item.get('item_def')
				id_item = item.get('id_item')
				name = item_def.str_name

				quantity = 1
				if item.get('stack_max') > 0:
					quantity = item.get('stack_size')

				item['quantity'] = quantity

				# Name requires variable substitution. Look up the item properties.
				if name.find('{') >= 0:
					item_inst = EwItem(id_item = id_item)

					if item_inst != None and item_inst.id_item >= 0:
						name = name.format_map(item_inst.item_props)

						if name.find('{') >= 0:
							name = name.format_map(item_inst.item_props)

				#if a weapon has no name show its type instead
				if name == "" and item_inst.item_type == ewcfg.it_weapon:
					name = item_inst.item_props.get("weapon_type")

				item['name'] = name
	finally:
		# Clean up the database handles.
		cursor.close()
		ewutils.databaseClose(conn_info)

	return items


"""
	Dump out a player's inventory.
"""
async def inventory_print(cmd):
	
	community_chest = False
	can_message_user = True
	inventory_source = cmd.message.author.id

	player = EwPlayer(id_user = cmd.message.author.id)

	user_data = EwUser(id_user = cmd.message.author.id, id_server = player.id_server)
	poi = ewcfg.id_to_poi.get(user_data.poi)
	if cmd.tokens[0].lower() == ewcfg.cmd_communitychest:
		if poi.community_chest == None:
			response = "There is no community chest here."
			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		community_chest = True
		can_message_user = False
		inventory_source = poi.community_chest

	sort_by_type = False
	sort_by_name = False
	sort_by_id = False
	
	stacking = False
	stacked_message_list = []
	stacked_item_map = {}

	if cmd.tokens_count > 1:
		token_list = cmd.tokens[1:]
		lower_token_list = []
		for token in token_list:
			token = token.lower()
			lower_token_list.append(token)

		if 'type' in lower_token_list:
			sort_by_type = True
		elif 'name' in lower_token_list:
			sort_by_name = True
		elif 'id' in lower_token_list:
			sort_by_id = True
			
		if 'stack' in lower_token_list:
			stacking = True

	if sort_by_id:
		items = inventory(
			id_user = inventory_source,
			id_server = player.id_server,
			item_sorting_method='id'
		)
	elif sort_by_type:
		items = inventory(
			id_user=inventory_source,
			id_server=player.id_server,
			item_sorting_method='type'
		)
	else:
		items = inventory(
			id_user=inventory_source,
			id_server=player.id_server,
		)

	if community_chest:
		if len(items) == 0:
			response = "The community chest is empty."
		else:
			response = "The community chest contains:"
	else:
		if len(items) == 0:
			response = "You don't have anything."
		else:
			response = "You are holding:"

	msg_handle = None
	try:
		if can_message_user:
			msg_handle = await ewutils.send_message(cmd.client, cmd.message.author, response)
	except:
		can_message_user = False

	if msg_handle is None:
		can_message_user = False

	if not can_message_user:
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if sort_by_name:
		items = sorted(items, key=lambda item: item.get('name').lower())

	if len(items) > 0:
		
		response = ""

		for item in items:
			id_item = item.get('id_item')
			quantity = item.get('quantity')

			if not stacking:
				response_part = "\n{id_item}: {soulbound_style}{name}{soulbound_style}{quantity}".format(
					id_item = item.get('id_item'),
					name = item.get('name'),
					soulbound_style = ("**" if item.get('soulbound') else ""),
					quantity = (" x{:,}".format(quantity) if (quantity > 1) else "")
				)
			else:

				item_name = item.get('name')
				if item_name in stacked_item_map:
					stacked_item = stacked_item_map.get(item_name)
					stacked_item['quantity'] += item.get('quantity')
				else:
					stacked_item_map[item_name] = item
				
			if not stacking and len(response) + len(response_part) > 1492:
				if can_message_user:
					await ewutils.send_message(cmd.client, cmd.message.author, response)
				else:
					await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

				response = ""
				
			if not stacking:
				response += response_part

		if stacking:
			item_names = stacked_item_map.keys()
			if sort_by_name:
				item_names = sorted(item_names)
			for item_name in item_names:
				item = stacked_item_map.get(item_name)
				quantity = item.get('quantity')
				response_part = "\n{soulbound_style}{name}{soulbound_style}{quantity}".format(
					name=item.get('name'),
					soulbound_style=("**" if item.get('soulbound') else ""),
					quantity=(" **x{:,}**".format(quantity) if (quantity > 0) else "")
				)
				
				if len(response) + len(response_part) > 1492:
					if can_message_user:
						await ewutils.send_message(cmd.client, cmd.message.author, response)
					else:
						await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	
					response = ""
				response += response_part

		if can_message_user:
			await ewutils.send_message(cmd.client, cmd.message.author, response)
		else:
			await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


"""
	Dump out the visual description of an item.
"""
async def item_look(cmd):
	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
	author = cmd.message.author
	player = EwPlayer(id_user=cmd.message.author.id)
	server = player.id_server
	user_data = EwUser(id_user=cmd.message.author.id, id_server=server)
	poi = ewcfg.id_to_poi.get(user_data.poi)
	mutations = user_data.get_mutations()

	if user_data.visiting != ewcfg.location_id_empty:
		user_data = EwUser(id_user=user_data.visiting, id_server=server)

	item_dest = []

	item_sought_inv = find_item(item_search=item_search, id_user=author.id, id_server=server)
	item_dest.append(item_sought_inv)

	iterate = 0
	response = ""

	if poi.is_apartment:
		item_sought_closet = find_item(item_search=item_search, id_user=user_data.id_user + ewcfg.compartment_id_closet, id_server=server)
		item_sought_fridge = find_item(item_search=item_search, id_user=user_data.id_user + ewcfg.compartment_id_fridge, id_server=server)
		item_sought_decorate = find_item(item_search=item_search, id_user=user_data.id_user + ewcfg.compartment_id_decorate, id_server=server)

		item_dest.append(item_sought_closet)
		item_dest.append(item_sought_fridge)
		item_dest.append(item_sought_decorate)

	for item_sought in item_dest:
		iterate+=1
		if item_sought:
			item = EwItem(id_item = item_sought.get('id_item'))

			id_item = item.id_item
			name = item_sought.get('name')
			response = item_sought.get('item_def').str_desc

			# Replace up to two levels of variable substitutions.
			if response.find('{') >= 0:
				response = response.format_map(item.item_props)

				if response.find('{') >= 0:
					response = response.format_map(item.item_props)


			if item.item_type == ewcfg.it_food:
				if float(item.item_props.get('time_expir') if not None else 0) < time.time() and item.id_owner[-6:] != ewcfg.compartment_id_fridge:
					response += " This food item is rotten"
					if ewcfg.mutation_id_spoiledappetite in mutations:
						response += ". Yummy!"
					else:
						response += ", so you decide to throw it away."
						item_drop(id_item)

			if item.item_type == ewcfg.it_weapon:
				response += "\n\n"

				if item.item_props.get("married") != "":
					previous_partner = EwPlayer(id_user = item.item_props.get("married"), id_server = server)

					if item.item_props.get("married") != user_data.id_user or item.id_item != user_data.weapon:
						response += "There's a barely legible engraving on the weapon that reads *{} :heart: {}*.\n\n".format(previous_partner.display_name, name)
					else:
						response += "Your beloved partner. You can't help but give it a little kiss on the handle.\n"

				weapon = ewcfg.weapon_map.get(item.item_props.get("weapon_type"))

				if ewcfg.weapon_class_ammo in weapon.classes:
					response += "Ammo: {}/{}".format(item.item_props.get("ammo"), weapon.clip_size) + "\n"

				if ewcfg.weapon_class_captcha in weapon.classes:
					captcha = item.item_props.get("captcha")
					if captcha not in [None, ""]:
						response += "Security Code: **{}**".format(captcha) + "\n"

				totalkills = int(item.item_props.get("totalkills")) if item.item_props.get("totalkills") != None else 0

				if totalkills < 10:
					response += "It looks brand new" + (".\n" if totalkills == 0 else ", having only killed {} people.\n".format(totalkills))
				elif totalkills < 100:
					response += "There's some noticeable wear and tear on it. It has killed {} people.\n".format(totalkills)
				else:
					response += "A true legend in the battlefield, it has killed {} people.\n".format(totalkills)

				response += "You have killed {} people with it.".format(item.item_props.get("kills") if item.item_props.get("kills") != None else 0)

			if item.item_type == ewcfg.it_cosmetic:
				hue = ewcfg.hue_map.get(item.item_props.get('hue'))
				if hue != None:
					response += " It's been dyed in {} paint.".format(hue.str_name)

			response = name + (" x{:,}".format(item.stack_size) if (item.stack_size >= 1) else "") + "\n\n" + response

			return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		else:
			if iterate == len(item_dest) and response == "":
				if item_search:  # if they didnt forget to specify an item and it just wasn't found
					response = "You don't have one."
				else:
					response = "Inspect which item? (check **!inventory**)"

				await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

# this is basically just the item_look command with some other stuff at the bottom
async def item_use(cmd):
	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
	author = cmd.message.author
	server = cmd.message.server

	item_sought = find_item(item_search = item_search, id_user = author.id, id_server = server.id)

	if item_sought:		
		# Load the user before the item so that the right item props are used
		user_data = EwUser(member = author)

		item = EwItem(id_item = item_sought.get('id_item'))

		response = "The item doesn't have !use functionality"  # if it's not overwritten

		if item.item_type == ewcfg.it_food:
			response = user_data.eat(item)
			user_data.persist()
			asyncio.ensure_future(ewutils.decrease_food_multiplier(user_data.id_user))

		if item.item_type == ewcfg.it_weapon:
			response = user_data.equip(item)
			user_data.persist()

		if item.item_type == ewcfg.it_item:
			name = item_sought.get('name')
			context = item.item_props.get('context')
			if name == "Trading Cards":
				response = ewsmelting.unwrap(id_user = author, id_server = server, item = item)
			elif (context == 'repel' or context == 'superrepel' or context == 'maxrepel'):
				statuses = user_data.getStatusEffects()
				if ewcfg.status_repelaftereffects_id in statuses:
					response = "You need to wait a bit longer before applying more body spray."
				else:
					if context == 'repel':
						response = user_data.applyStatus(ewcfg.status_repelled_id)
					elif context == 'superrepel':
						response = user_data.applyStatus(ewcfg.status_repelled_id, multiplier=2)
					elif context == 'maxrepel':
						response = user_data.applyStatus(ewcfg.status_repelled_id, multiplier=4)
					item_delete(item.id_item)

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

	else:
		if item_search:  # if they didnt forget to specify an item and it just wasn't found
			response = "You don't have one."
		else:
			response = "Use which item? (check **!inventory**)"

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

"""
	Assign an existing item to a player
"""
def give_item(
	member = None,
	id_item = None,
	id_user = None,
	id_server = None
):

	if id_user is None and id_server is None and member is not None:
		id_server = member.server.id
		id_user = member.id

	if id_server is not None and id_user is not None and id_item is not None:
		ewutils.execute_sql_query(
			"UPDATE items SET id_user = %s WHERE id_server = %s AND {id_item} = %s".format(
				id_item = ewcfg.col_id_item
			), (
				id_user,
				id_server,
				id_item
			)
		)

		remove_from_trades(id_item)

		item = EwItem(id_item = id_item)
		# Reset the weapon's damage modifying stats
		if item.item_type == ewcfg.it_weapon:
			item.item_props["kills"] = 0
			item.item_props["consecutive_hits"] = 0
			item.item_props["time_lastattack"] = 0
			item.persist()

	return


def soulbind(id_item):
	item = EwItem(id_item = id_item)
	item.soulbound = True
	item.persist()

"""
	Find a single item in the player's inventory (returns either a (non-EwItem) item or None)
"""
def find_item(item_search = None, id_user = None, id_server = None):
	item_sought = None

	# search for an ID instead of a name
	try:
		item_search_int = int(item_search)
	except:
		item_search_int = None

	if item_search:
		items = inventory(id_user = id_user, id_server = id_server)
		item_sought = None

		# find the first (i.e. the oldest) item that matches the search
		for item in items:
			if item.get('id_item') == item_search_int or item_search in ewutils.flattenTokenListToString(item.get('name')):
				item_sought = item
				break

	return item_sought



"""
	Find every item matching the search in the player's inventory (returns a list of (non-EwItem) item)
"""
def find_item_all(item_search = None, id_user = None, id_server = None, item_type_filter = None):
	items_sought = []
	props_to_search = [
		'weapon_type',
		'id_item',
		'id_food',
		'id_cosmetic',
		'id_furniture'
	]


	if item_search:
		items = inventory(id_user = id_user, id_server = id_server, item_type_filter = item_type_filter)

		# find the first (i.e. the oldest) item that matches the search
		for item in items:
			item_data = EwItem(id_item = item.get('id_item'))
			for prop in props_to_search:
				if prop in item_data.item_props and \
				ewutils.flattenTokenListToString(item_data.item_props.get(prop)) == item_search:
					items_sought.append(item)
					break

	return items_sought

"""
	Finds the amount of Slime Poudrins inside your inventory.
"""
def find_poudrin(id_user = None, id_server = None):

	items = inventory(
		id_user = id_user,
		id_server = id_server,
		item_type_filter = ewcfg.it_item
	)

	poudrins = []

	for poudrin in items:
		name = poudrin.get('name')
		if name != "Slime Poudrin":
			pass
		else:
			poudrins.append(poudrin)

	poudrins_amount = len(poudrins)

	return poudrins_amount

"""
	Command that lets players !give others items
"""
async def give(cmd):
	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])
	author = cmd.message.author
	server = cmd.message.server

	if cmd.mentions:  # if they're not empty
		recipient = cmd.mentions[0]
	else:
		response = "You have to specify the recipient of the item."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	user_data = EwUser(member = author)
	recipient_data = EwUser(member = recipient)

	if user_data.poi != recipient_data.poi:
		response = "You must be in the same location as the person you want to gift your item to, bitch."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	item_sought = find_item(item_search = item_search, id_user = author.id, id_server = server.id)

	if item_sought:  # if an item was found

		# don't let people give others food when they shouldn't be able to carry more food items
		if item_sought.get('item_type') == ewcfg.it_food:
			food_items = inventory(
				id_user = recipient.id,
				id_server = server.id,
				item_type_filter = ewcfg.it_food
			)

			if len(food_items) >= recipient_data.get_food_capacity():
				response = "They can't carry any more food items."
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		if item_sought.get('item_type') == ewcfg.it_weapon:
			weapons_held = inventory(
				id_user = recipient.id,
				id_server = server.id,
				item_type_filter = ewcfg.it_weapon
			)

			if user_data.weaponmarried and user_data.weapon == item_sought.get('id_item'):
				response = "Your cuckoldry is appreciated, but your {} will always remain faithful to you.".format(item_sought.get('name'))
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
			elif recipient_data.life_state == ewcfg.life_state_corpse:
				response = "Ghosts can't hold weapons."
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
			elif len(weapons_held) >= recipient_data.get_weapon_capacity():
				response  = "They can't carry any more weapons."
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

		if item_sought.get('item_type') == ewcfg.it_cosmetic:
			item_data = EwItem(id_item = item_sought.get('id_item'))
			item_data.item_props["adorned"] = 'false'
			item_data.persist()


		if item_sought.get('soulbound'):
			response = "You can't just give away soulbound items."
		else:
			give_item(
				member = recipient,
				id_item = item_sought.get('id_item')
			)

			response = "You gave {recipient} a {item}".format(
				recipient = recipient.display_name,
				item = item_sought.get('name')
			)

			if item_sought.get('id_item') == user_data.weapon:
				user_data.weapon = -1
				user_data.persist()
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		if item_search:  # if they didnt forget to specify an item and it just wasn't found
			response = "You don't have one."
		else:
			response = "Give which item? (check **!inventory**)"

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

"""
	Throw away an item
"""
async def discard(cmd):
	user_data = EwUser(member = cmd.message.author)
	response = ""

	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])

	item_sought = find_item(item_search = item_search, id_user = cmd.message.author.id, id_server = cmd.message.server.id if cmd.message.server is not None else None)

	if item_sought:
		item = EwItem(id_item = item_sought.get("id_item"))

		if not item.soulbound:
			if item.item_type == ewcfg.it_weapon and user_data.weapon >= 0 and item.id_item == user_data.weapon:
				if user_data.weaponmarried:
					weapon = ewcfg.weapon_map.get(item.item_props.get("weapon_type"))
					response = "As much as it would be satisfying to just chuck your {} down an alley and be done with it, here in civilization we deal with things *maturely.* You’ll have to speak to the guy that got you into this mess in the first place, or at least the guy that allowed you to make the retarded decision in the first place. Luckily for you, they’re the same person, and he’s at the Dojo.".format(weapon.str_weapon)
					return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
				else:
					user_data.weapon = -1
					user_data.persist()
				
			response = "You throw away your " + item_sought.get("name")
			item_drop(id_item = item.id_item)

		else:
			response = "You can't throw away soulbound items."
	else:
		if item_search:
			response = "You don't have one"
		else:
			response = "Discard which item? (check **!inventory**)"

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

def gen_item_props(item):
	item_props = {}
	if not hasattr(item, "item_type"):
		return item_props
	if item.item_type == ewcfg.it_food:
		
		item_props = {
			'id_food': item.id_food,
			'food_name': item.str_name,
			'food_desc': item.str_desc,
			'recover_hunger': item.recover_hunger,
			'inebriation': item.inebriation,
			'str_eat': item.str_eat,
			'time_expir': int(time.time()) + item.time_expir,
			'time_fridged': item.time_fridged,
		}
	elif item.item_type == ewcfg.it_item:
		item_props = {
			'id_item': item.id_item,
			'context': item.context,
			'item_name': item.str_name,
			'item_desc': item.str_desc,
			'ingredients': item.ingredients,
			'acquisition': item.acquisition,
		}
	elif item.item_type == ewcfg.it_weapon:
		captcha = ""
		if ewcfg.weapon_class_captcha in item.classes:
			captcha = ewutils.generate_captcha(n = item.captcha_length)

		item_props = {
			"weapon_type": item.id_weapon,
			"weapon_name": "",
			"weapon_desc": item.str_description,
			"married": "",
			"ammo": item.clip_size,
			"captcha": captcha
		}

	elif item.item_type == ewcfg.it_cosmetic:
		item_props = {
			'id_cosmetic': item.id_cosmetic,
			'cosmetic_name': item.str_name,
			'cosmetic_desc': item.str_desc,
			'rarity': item.rarity,
			'adorned': 'false'
		}
	elif item.item_type == ewcfg.it_furniture:
		item_props = {
			'id_furniture': item.id_furniture,
			'furniture_name': item.str_name,
			'furniture_desc': item.str_desc,
			'rarity': item.rarity,
			'furniture_place_desc': item.furniture_place_desc,
			'furniture_look_desc': item.furniture_look_desc,
			'acquisition': item.acquisition
		}

	return item_props


async def soulextract(cmd):
	usermodel = EwUser(member=cmd.message.author)
	playermodel = EwPlayer(id_user=cmd.message.author.id, id_server=cmd.message.server.id)
	if usermodel.has_soul == 1:
		item_create(
			id_user=cmd.message.author.id,
			id_server=cmd.message.server.id,
			item_type=ewcfg.it_cosmetic,
			item_props = {
				'id_cosmetic': "soul",
				'cosmetic_name': "{}'s soul".format(playermodel.display_name),
				'cosmetic_desc': "The immortal soul of {}. It dances with a vivacious energy inside its jar.\n If you listen to it closely you can hear it whispering numbers: {}.".format(playermodel.display_name, cmd.message.author.id),
				'rarity': ewcfg.rarity_patrician,
				'adorned': 'false',
				'user_id': usermodel.id_user
			}
		)
		usermodel.has_soul = 0
		usermodel.persist()
		response = "You tremble at the thought of trying this. Nothing ventured, nothing gained, you suppose. With all your mental fortitude you jam your hand deep into your chest and begin to pull out the very essence of your being. Your spirit, aspirations, everything that made you who you are begins to slowly drain from your mortal effigy until you feel absolutely nothing. Your soul flickers about, taunting you from outside your body. You capture it in a jar, almost reflexively.\n\nWow. Your personality must suck now."
	else:
		response = "There's nothing left in you to extract. You already spent the soul you had."
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		
async def returnsoul(cmd):
	usermodel = EwUser(member=cmd.message.author)
	#soul = find_item(item_search="soul", id_user=cmd.message.author.id, id_server=cmd.message.server.id)
	user_inv = inventory(id_user=cmd.message.author.id, id_server=cmd.message.server.id, item_type_filter=ewcfg.it_cosmetic)
	soul_item = None
	soul = None
	for inv_object in user_inv:
		soul = inv_object
		soul_item = EwItem(id_item=soul.get('id_item'))
		if soul_item.item_props.get('user_id') == cmd.message.author.id:
			break

	if usermodel.has_soul == 1:
		response = "Your current soul is a little upset you tried to give it a roommate. Only one fits in your body at a time."
	elif soul:

		if soul.get('item_type') == ewcfg.it_cosmetic and soul_item.item_props.get('id_cosmetic') == "soul":
			if soul_item.item_props.get('user_id') != cmd.message.author.id:
				response = "That's not your soul. Nice try, though."
			else:
				response = "You open the soul jar and hold the opening to your chest. The soul begins to crawl in, and a warmth returns to your body. Not exactly the warmth you had before, but it's too wonderful to pass up. You feel invigorated and ready to take on the world."
				item_delete(id_item=soul.get('id_item'))
				usermodel.has_soul = 1
				usermodel.persist()
		else:
			response = "Nice try, but your mortal coil recognizes a fake soul when it sees it."
	else:
		response = "You don't have a soul to absorb. Hopelessness is no fun, but don't get all delusional on us now."
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def squeeze(cmd):
	usermodel = EwUser(member=cmd.message.author)
	soul_inv = inventory(id_user=cmd.message.author.id, id_server=cmd.message.server.id, item_type_filter=ewcfg.it_cosmetic)
	
	if cmd.mentions_count <= 0:
		response = "Specify a soul you want to squeeze the life out of."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	
	target = cmd.mentions[0]
	targetmodel = EwUser(member=target)
	if cmd.mentions_count > 1:
		response = "One dehumanizing soul-clutch at a time, please."
	elif targetmodel.life_state == ewcfg.life_state_corpse:
		response = "Enough already. They're dead."
	else:

		playermodel = EwPlayer(id_user=targetmodel.id_user)
		receivingreport = "" #the receiver of the squeeze gets this in their channel

		squeezetext = re.sub("<.+>", "", cmd.message.content[(len(cmd.tokens[0])):]).strip()
		if len(squeezetext) > 500:
			haunt_message_content = squeezetext[:-500]



		poi = None
		target_item = None
		for soul in soul_inv:
			soul_item = EwItem(id_item=soul.get('id_item'))
			if soul_item.item_props.get('user_id') == targetmodel.id_user:
				target_item = soul

		if targetmodel.has_soul == 1:
			response = "They look pretty soulful right now. You can't do anything to them."
		elif target_item == None:
			response = "You don't have their soul."
		elif (int(time.time()) - usermodel.time_lasthaunt) < ewcfg.cd_squeeze:
			timeleft = ewcfg.cd_squeeze - (int(time.time()) - usermodel.time_lasthaunt)
			response = "It's still all rubbery and deflated from the last time you squeezed it. Give it {} seconds.".format(timeleft)
		else:
			if squeezetext != "":
				receivingreport = "A voice in your head screams: \"{}\"\nSuddenly, you feel searing palpitations in your chest, and vomit slime all over the floor. Dammit, {} must be fucking around with your soul.".format(squeezetext, cmd.message.author.display_name)
			else:
				receivingreport = "You feel searing palpitations in your chest, and vomit slime all over the floor. Dammit, {} must be fucking with your soul.".format(cmd.message.author.display_name)

			poi = ewcfg.id_to_poi.get(targetmodel.poi)

			usermodel.time_lasthaunt = int(time.time())
			usermodel.persist()

			server = ewcfg.server_list[targetmodel.id_server]
			member_object = server.get_member(targetmodel.id_user)

			penalty = (targetmodel.slimes* -0.25)
			targetmodel.change_slimes(n=penalty, source=ewcfg.source_haunted)
			targetmodel.persist()

			district_data = ewdistrict.EwDistrict(district=targetmodel.poi, id_server=cmd.message.server.id)
			district_data.change_slimes(n= -penalty, source=ewcfg.source_squeeze)
			district_data.persist()

			if receivingreport != "":
				loc_channel = ewutils.get_channel(cmd.message.server, poi.channel)
				await ewutils.send_message(cmd.client, loc_channel, ewutils.formatMessage(member_object, receivingreport))

			response = "You tightly squeeze {}'s soul in your hand, jeering into it as you do so. This thing was worth every penny.".format(playermodel.display_name)

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))



	
# search and remove the given item from an ongoing trade
def remove_from_trades(id_item):
	for trader in ewutils.trading_offers:
		for item in ewutils.trading_offers.get(trader):
			if id_item == item.get("id_item"):
				ewutils.trading_offers.get(trader).remove(item)

				ewutils.active_trades.get(trader)["state"] = ewcfg.trade_state_ongoing 
				ewutils.active_trades.get(ewutils.active_trades.get(trader).get("trader"))["state"] = ewcfg.trade_state_ongoing
				return


async def makecostume(cmd):
	costumekit = find_item(item_search="costumekit", id_user=cmd.message.author.id, id_server=cmd.message.server.id if cmd.message.server is not None else None)

	user_data = EwUser(member=cmd.message.author)
	
	id_user = user_data.id_user
	id_server = user_data.id_server
	
	if not costumekit:
		response = "You don't know how to make one, bitch."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	
	if len(cmd.tokens) != 3:
		response = 'Usage: !makecostume "[name]" "[description]".\nExample: !makecostume "Ghost Costume" "A bedsheet with holes for eyes."'
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	item_delete(id_item=costumekit.get('id_item'))

	item_name = cmd.tokens[1]
	item_desc = cmd.tokens[2]

	item_props = {
		"cosmetic_name": item_name,
		"cosmetic_desc": item_desc,
		"adorned": "false",
		"rarity": "Plebeian",
		"context": "costume",
	}

	new_item_id = item_create(
		id_server = id_server,
		id_user = id_user,
		item_type = ewcfg.it_cosmetic,
		item_props = item_props
	)
	
	response = "You fashion your **{}** Double Halloween costume using the creation kit.".format(item_name)
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
