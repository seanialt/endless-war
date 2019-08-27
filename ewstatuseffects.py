import time
import math

import ewcfg
import ewutils

class EwStatusEffectDef:
	id_status = ""
	# Time until expiration, negative values have specific expiration conditions
	time_expire = -1
    
	str_acquire = ""
	str_describe = ""
	str_describe_self = ""
	dmg_mod_self = 0
	miss_mod_self = 0
	crit_mod_self = 0
	dmg_mod = 0
	miss_mod = 0
	crit_mod = 0

	def __init__(
        self,
        id_status = "",
        time_expire = -1,
        str_acquire = "",
        str_describe = "",
        str_describe_self = "",
		dmg_mod_self = 0,
		miss_mod_self = 0,
		crit_mod_self = 0,
		dmg_mod = 0,
		miss_mod = 0,
		crit_mod = 0
    ):
		self.id_status = id_status
		self.time_expire = time_expire
		self.str_acquire = str_acquire
		self.str_describe = str_describe
		self.str_describe_self = str_describe_self
		self.dmg_mod_self = dmg_mod_self
		self.miss_mod_self = miss_mod_self
		self.crit_mod_self = crit_mod_self
		self.dmg_mod = dmg_mod
		self.miss_mod = miss_mod
		self.crit_mod = crit_mod

class EwStatusEffect:
	id_server = ""
	id_user = ""
	id_status = ""
	
	time_expire = -1
	value = 0
	source = ""

	def __init__(
		self,
		id_status = None,
        user_data = None,
		time_expire = 0,
		value = 0,
		source = ""
	):
		if id_status != None and user_data != None:
			self.id_server = user_data.id_server
			self.id_user = user_data.id_user
			self.id_status = id_status
			self.time_expire = time_expire
			self.value = value
			self.source = source
			time_now = int(time.time())

			try:
				conn_info = ewutils.databaseConnect()
				conn = conn_info.get('conn')
				cursor = conn.cursor()

				# Retrieve object
				cursor.execute("SELECT {time_expire}, {value}, {source} FROM status_effects WHERE {id_status} = %s and {id_server} = %s and {id_user} = %s".format(
                    time_expire = ewcfg.col_time_expir,
                    id_status = ewcfg.col_id_status,
                    id_server = ewcfg.col_id_server,
                    id_user = ewcfg.col_id_user,
					value = ewcfg.col_value,
					source = ewcfg.col_source
				), (
					self.id_status,
                    self.id_server,
                    self.id_user
				))
				result = cursor.fetchone()

				if result != None:
					self.time_expire = result[0]
					self.value = result[1]
					self.source = result[2]

				else:
					# Save the object.
					cursor.execute("REPLACE INTO status_effects({}, {}, {}, {}, {}, {}) VALUES(%s, %s, %s, %s, %s, %s)".format(
						ewcfg.col_id_server,
						ewcfg.col_id_user,
						ewcfg.col_id_status,
						ewcfg.col_time_expir,
						ewcfg.col_value,
						ewcfg.col_source
					), (
						self.id_server,
						self.id_user,
						self.id_status,
						(self.time_expire + time_now) if self.time_expire > 0 else self.time_expire,
						self.value,
						self.source
					))

					self.time_expire = (self.time_expire + time_now) if self.time_expire > 0 else self.time_expire

					conn.commit()

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
			cursor.execute("REPLACE INTO status_effects({}, {}, {}, {}, {}, {}) VALUES(%s, %s, %s, %s, %s, %s)".format(
				ewcfg.col_id_server,
				ewcfg.col_id_user,
				ewcfg.col_id_status,
				ewcfg.col_time_expir,
				ewcfg.col_value,
				ewcfg.col_source
			), (
				self.id_server,
				self.id_user,
                self.id_status,
				self.time_expire,
				self.value,
				self.source
			))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			ewutils.databaseClose(conn_info)
