import asyncio
import time

import ewcfg
import ewutils

from ew import EwUser

class EwRole:
	id_server = ""
	id_role = ""
	name = ""

	def __init__(self, id_server = None, name = None, id_role = None):
		if id_server is not None and name is not None:
			self.id_server = id_server
			self.name = name


			data = ewutils.execute_sql_query("SELECT {id_role} FROM roles WHERE id_server = %s AND {name} = %s".format(
				id_role = ewcfg.col_id_role,
				name = ewcfg.col_role_name
			), (
				id_server,
				name
			))

			if len(data) > 0:  # if data is not empty, i.e. it found an entry
				# data is always a two-dimensional array and if we only fetch one row, we have to type data[0][x]
				self.id_role = data[0][0]
			else:  # create new entry
				ewutils.execute_sql_query("REPLACE INTO roles ({id_server}, {name}) VALUES (%s, %s)".format(
					id_server = ewcfg.col_id_server,
					name = ewcfg.col_role_name
				), (
					id_server,
					name
				))
		elif id_server is not None and id_role is not None:
			self.id_server = id_server
			self.id_role = id_role


			data = ewutils.execute_sql_query("SELECT {name} FROM roles WHERE id_server = %s AND {id_role} = %s".format(
				id_role = ewcfg.col_id_role,
				name = ewcfg.col_role_name
			), (
				id_server,
				id_role
			))

			if len(data) > 0:  # if data is not empty, i.e. it found an entry
				# data is always a two-dimensional array and if we only fetch one row, we have to type data[0][x]
				self.name = data[0][0]

	def persist(self):
		ewutils.execute_sql_query("REPLACE INTO roles (id_server, {id_role}, {name}) VALUES(%s, %s, %s)".format(
			id_role = ewcfg.col_id_role,
			name = ewcfg.col_role_name
		), (
			self.id_server,
			self.id_role,
			self.name
		))
			

"""
	Find relevant roles and save them to the database.
"""
def setupRoles(client = None, id_server = ""):
	
	roles_map = ewutils.getRoleMap(client.get_server(id_server).roles)
	for poi in ewcfg.poi_list:
		if poi.role in roles_map:
			try:
				role_data = EwRole(id_server = id_server, name = poi.role)
				role_data.id_role = roles_map[poi.role].id
				role_data.persist()
			except:
				ewutils.logMsg('Failed to set up role {}'.format(poi.role))

	for faction_role in ewcfg.faction_roles:
		if faction_role in roles_map:
			try:
				role_data = EwRole(id_server = id_server, name = faction_role)
				role_data.id_role = roles_map[faction_role].id
				role_data.persist()
			except:
				ewutils.logMsg('Failed to set up role {}'.format(faction_role))

"""
	Hide the names of poi roles behind a uniform alias
"""
async def hideRoleNames(client = None, id_server = ""):
	
	server = client.get_server(id_server)
	roles_map = ewutils.getRoleMap(server.roles)
	for poi in ewcfg.poi_list:
		try:
			if poi.role in roles_map:
				role = roles_map[poi.role]
				await client.edit_role(server = server, role = role, name = ewcfg.generic_role_name)
		except:
			ewutils.logMsg('Failed to hide role name for {}'.format(poi.role))

"""
	Restore poi roles to their original names
"""
async def restoreRoleNames(cmd):

	member = cmd.message.author
	
	if not member.server_permissions.administrator:
		return
	
	client = cmd.client
	server = member.server
	for poi in ewcfg.poi_list:
		try:
			role_data = EwRole(id_server = server.id, name = poi.role)
			for role in server.roles:
				if role.id == role_data.id_role:
					await client.edit_role(server = server, role = role, name = role_data.name)
		except:
			ewutils.logMsg('Failed to restore role name for {}'.format(poi.role))

"""
	Fix the Discord roles assigned to this member.
"""
async def updateRoles(
	client = None,
	member = None,
	server_default = None
):
	time_now = int(time.time())

	if server_default != None:
		user_data = EwUser(id_user=member.id, id_server = server_default)
	else:
		user_data = EwUser(member=member)

	id_server = user_data.id_server
	
	if member == None:
		return ewutils.logMsg("error: member was not supplied for updateRoles")

	#roles_map = ewutils.getRoleMap(member.server.roles)
	roles_map_user = ewutils.getRoleIdMap(member.roles)

	if user_data.life_state != ewcfg.life_state_kingpin and ewcfg.role_kingpin in roles_map_user:
		# Fix the life_state of kingpins, if somehow it wasn't set.
		user_data.life_state = ewcfg.life_state_kingpin
		user_data.persist()

	elif user_data.life_state != ewcfg.life_state_grandfoe and ewcfg.role_grandfoe in roles_map_user:
		# Fix the life_state of a grand foe.
		user_data.life_state = ewcfg.life_state_grandfoe
		user_data.persist()

	faction_roles_remove = [
		ewcfg.role_juvenile,
		ewcfg.role_juvenile_active,
		ewcfg.role_juvenile_pvp,
		ewcfg.role_rowdyfuckers,
		ewcfg.role_rowdyfuckers_pvp,
		ewcfg.role_rowdyfuckers_active,
		ewcfg.role_copkillers,
		ewcfg.role_copkillers_pvp,
		ewcfg.role_copkillers_active,
		ewcfg.role_corpse,
		ewcfg.role_corpse_pvp,
		ewcfg.role_corpse_active,
		ewcfg.role_kingpin,
		ewcfg.role_grandfoe,
		ewcfg.role_slimecorp,
		ewcfg.role_tutorial,
	]

	# Manage faction roles.
	faction_role = ewutils.get_faction(user_data = user_data)

	faction_roles_remove.remove(faction_role)

	pvp_role = None
	active_role = None
	if faction_role in ewcfg.role_to_pvp_role:

		if user_data.time_expirpvp >= time_now:
			pvp_role = ewcfg.role_to_pvp_role.get(faction_role)
			faction_roles_remove.remove(pvp_role)

		if ewutils.is_otp(user_data):
			active_role = ewcfg.role_to_active_role.get(faction_role)
			faction_roles_remove.remove(active_role)

	tutorial_role = None
	if user_data.poi in ewcfg.tutorial_pois:
		tutorial_role = ewcfg.role_tutorial
		faction_roles_remove.remove(tutorial_role)

	# Manage location roles.
	poi = ewcfg.id_to_poi.get(user_data.poi)
	if poi != None:
		poi_role = poi.role
	else:
		poi_role = None

	poi_roles_remove = []
	for poi in ewcfg.poi_list:
		if poi.role != None and poi.role != poi_role:
			poi_roles_remove.append(poi.role)


	role_ids = []
	for role_id in roles_map_user:

		try:
			role_data = EwRole(id_server = id_server, id_role = role_id)
			roleName = role_data.name
			if roleName != None and roleName not in faction_roles_remove and roleName not in poi_roles_remove:
				role_ids.append(role_data.id_role)
		except:
			ewutils.logMsg('error: couldn\'t find role with id {}'.format(role_id))

	
	try:
		role_data = EwRole(id_server = id_server, name = faction_role)
		if not role_data.id_role in role_ids:
			role_ids.append(role_data.id_role)
			#ewutils.logMsg('found role {} with id {}'.format(role_data.name, role_data.id_role))
	except:
		ewutils.logMsg('error: couldn\'t find role {}'.format(faction_role))

	try:
		role_data = EwRole(id_server = id_server, name = pvp_role)
		if not role_data.id_role in role_ids:
			role_ids.append(role_data.id_role)
			#ewutils.logMsg('found role {} with id {}'.format(role_data.name, role_data.id_role))
	except:
		ewutils.logMsg('error: couldn\'t find role {}'.format(pvp_role))

	try:
		role_data = EwRole(id_server = id_server, name = active_role)
		if not role_data.id_role in role_ids:
			role_ids.append(role_data.id_role)
			#ewutils.logMsg('found role {} with id {}'.format(role_data.name, role_data.id_role))
	except:
		ewutils.logMsg('error: couldn\'t find role {}'.format(active_role))

	try:
		role_data = EwRole(id_server = id_server, name = tutorial_role)
		if not role_data.id_role in role_ids:
			role_ids.append(role_data.id_role)
			#ewutils.logMsg('found role {} with id {}'.format(role_data.name, role_data.id_role))
	except:
		ewutils.logMsg('error: couldn\'t find role {}'.format(tutorial_role))

	try:
		role_data = EwRole(id_server = id_server, name = poi_role)
		if not role_data.id_role in role_ids:
			role_ids.append(role_data.id_role)
			#ewutils.logMsg('found role {} with id {}'.format(role_data.name, role_data.id_role))
	except:
		ewutils.logMsg('error: couldn\'t find role {}'.format(poi_role))

	#if faction_role not in role_names:
	#	role_names.append(faction_role)
	#if poi_role != None and poi_role not in role_names:
	#	role_names.append(poi_role)

	#replacement_roles = []
	#for name in role_names:
	#	role = roles_map.get(name)

	#	if role != None:
	#		replacement_roles.append(role)
	#	else:
	#		ewutils.logMsg("error: role missing \"{}\"".format(name))

	#ewutils.logMsg('looking for {} roles to replace'.format(len(role_ids)))
	replacement_roles = []

	for role in member.server.roles:
		if role.id in role_ids:
			#ewutils.logMsg('found role {} with id {}'.format(role.name, role.id))
			replacement_roles.append(role)

	#ewutils.logMsg('found {} roles to replace'.format(len(replacement_roles)))


	try:
		await client.replace_roles(member, *replacement_roles)
	except:
		ewutils.logMsg('error: failed to replace roles for {}'.format(member.display_name))

	#try:
	#	await client.replace_roles(member, *replacement_roles)
	#except:
	#	ewutils.logMsg('error: failed to replace roles for {}'.format(member.display_name))
