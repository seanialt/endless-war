import time
import random
import math

# import ewcmd
import ewitem
import ewrolemgr
import ewutils
import ewcfg
import ewstats
from ew import EwUser
from ewplayer import EwPlayer

class EwMarket:
	id_server = ""

	clock = 0
	weather = 'sunny'
	day = 0

	slimes_casino = 0
	slimes_revivefee = 0

	market_rate = 1000
	exchange_rate = 1000000
	boombust = 0
	time_lasttick = 0
	negaslime = 0
	decayed_slimes = 0
	donated_slimes = 0
	donated_poudrins = 0
	caught_fish = 0

	# Dict of bazaar items available for purchase
	bazaar_wares = None

	""" Load the market data for this server from the database. """
	def __init__(self, id_server = None):
		if(id_server != None):
			self.id_server = id_server
			self.bazaar_wares = {}

			try:
				conn_info = ewutils.databaseConnect()
				conn = conn_info.get('conn')
				cursor = conn.cursor();

				# Retrieve object
				cursor.execute("SELECT {time_lasttick}, {slimes_revivefee}, {negaslime}, {clock}, {weather}, {day}, {decayed_slimes}, {donated_slimes}, {donated_poudrins}, {caught_fish} FROM markets WHERE id_server = %s".format(
					time_lasttick = ewcfg.col_time_lasttick,
					slimes_revivefee = ewcfg.col_slimes_revivefee,
					negaslime = ewcfg.col_negaslime,
					clock = ewcfg.col_clock,
					weather = ewcfg.col_weather,
					day = ewcfg.col_day,
					decayed_slimes = ewcfg.col_decayed_slimes,
					donated_slimes = ewcfg.col_donated_slimes,
					donated_poudrins = ewcfg.col_donated_poudrins,
					caught_fish = ewcfg.col_caught_fish,
				), (self.id_server, ))
				result = cursor.fetchone();

				if result != None:
					# Record found: apply the data to this object.
					self.time_lasttick = result[0]
					self.slimes_revivefee = result[1]
					self.negaslime = result[2]
					self.clock = result[3]
					self.weather = result[4]
					self.day = result[5]
					self.decayed_slimes = result[6]
					self.donated_slimes = result[7]
					self.donated_poudrins = result[8]
					self.caught_fish = result[9]

					cursor.execute("SELECT {}, {} FROM bazaar_wares WHERE {} = %s".format(
						ewcfg.col_name,
						ewcfg.col_value,
						ewcfg.col_id_server,
					), (
						self.id_server,
					))

					for row in cursor:
						# this try catch is only necessary as long as extraneous props exist in the table
						try:
							self.bazaar_wares[row[0]] = row[1]
						except:
							ewutils.logMsg("extraneous bazaar item row detected.")

				else:
					# Create a new database entry if the object is missing.
					cursor.execute("REPLACE INTO markets(id_server) VALUES(%s)", (id_server, ))

					conn.commit()
			finally:
				# Clean up the database handles.
				cursor.close()
				ewutils.databaseClose(conn_info)

	""" Save market data object to the database. """
	def persist(self):
		try:
			conn_info = ewutils.databaseConnect()
			conn = conn_info.get('conn')
			cursor = conn.cursor();

			# Save the object.
			cursor.execute("REPLACE INTO markets ({id_server}, {time_lasttick}, {slimes_revivefee}, {negaslime}, {clock}, {weather}, {day}, {decayed_slimes}, {donated_slimes}, {donated_poudrins}, {caught_fish}) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
				id_server = ewcfg.col_id_server,
				time_lasttick = ewcfg.col_time_lasttick,
				slimes_revivefee = ewcfg.col_slimes_revivefee,
				negaslime = ewcfg.col_negaslime,
				clock = ewcfg.col_clock,
				weather = ewcfg.col_weather,
				day = ewcfg.col_day,
				decayed_slimes = ewcfg.col_decayed_slimes,
				donated_slimes = ewcfg.col_donated_slimes,
				donated_poudrins = ewcfg.col_donated_poudrins,
				caught_fish = ewcfg.col_caught_fish,
			), (
				self.id_server,
				self.time_lasttick,
				self.slimes_revivefee,
				self.negaslime,
				self.clock,
				self.weather,
				self.day,
				self.decayed_slimes,
				self.donated_slimes,
				self.donated_poudrins,
				self.caught_fish,
			))

			cursor.execute("DELETE FROM bazaar_wares WHERE {} = %s".format(
				ewcfg.col_id_server,
			), (
				self.id_server,
			))

			# Write out all current item rows.
			for name in self.bazaar_wares:
				cursor.execute("INSERT INTO bazaar_wares({}, {}, {}) VALUES(%s, %s, %s)".format(
					ewcfg.col_id_server,
					ewcfg.col_name,
					ewcfg.col_value,
				), (
					self.id_server,
					name,
					self.bazaar_wares[name],
				))

			conn.commit()
		finally:
			# Clean up the database handles.
			cursor.close()
			ewutils.databaseClose(conn_info)

class EwStock:
	id_server = ""

	# The stock's identifying string
	id_stock = ""

	market_rate = 1000

	exchange_rate = 1000000

	boombust = 0

	total_shares = 0

	timestamp = 0

	previous_entry = 0

	def __init__(self, id_server = None, stock = None, timestamp = None):
		if id_server is not None and stock is not None:
			self.id_server = id_server
			self.id_stock = stock

			# get stock data at specified timestamp
			if timestamp is not None:
				data = ewutils.execute_sql_query("SELECT {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp} FROM stocks WHERE id_server = %s AND {stock} = %s AND {timestamp} = %s".format(
					stock = ewcfg.col_stock,
					market_rate = ewcfg.col_market_rate,
					exchange_rate = ewcfg.col_exchange_rate,
					boombust = ewcfg.col_boombust,
					total_shares = ewcfg.col_total_shares,
					timestamp = ewcfg.col_timestamp
				), (
					id_server,
					stock,
					timestamp
				))
			# otherwise get most recent data
			else:

				data = ewutils.execute_sql_query("SELECT {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp} FROM stocks WHERE id_server = %s AND {stock} = %s ORDER BY {timestamp} DESC".format(
					stock = ewcfg.col_stock,
					market_rate = ewcfg.col_market_rate,
					exchange_rate = ewcfg.col_exchange_rate,
					boombust = ewcfg.col_boombust,
					total_shares = ewcfg.col_total_shares,
					timestamp = ewcfg.col_timestamp,
				), (
					id_server,
					stock
				))

			# slimecoin_total = ewutils.execute_sql_query()

			if len(data) > 0:  # if data is not empty, i.e. it found an entry
				# data is always a two-dimensional array and if we only fetch one row, we have to type data[0][x]
				self.id_stock = data[0][0]
				self.market_rate = data[0][1]
				self.exchange_rate = data[0][2]
				self.boombust = data[0][3]
				self.total_shares = data[0][4]
				self.timestamp = data[0][5]
				self.previous_entry = data[1] if len(data) > 1 else 0 #gets the previous stock
			else:  # create new entry
				self.timestamp = time.time()
				self.market_rate = ewcfg.default_stock_market_rate
				self.exchange_rate = ewcfg.default_stock_exchange_rate
				self.persist()

	def persist(self):
		ewutils.execute_sql_query("INSERT INTO stocks ({id_server}, {stock}, {market_rate}, {exchange_rate}, {boombust}, {total_shares}, {timestamp}) VALUES(%s, %s, %s, %s, %s, %s, %s)".format(
			id_server = ewcfg.col_id_server,
			stock = ewcfg.col_stock,
			market_rate = ewcfg.col_market_rate,
			exchange_rate = ewcfg.col_exchange_rate,
			boombust = ewcfg.col_boombust,
			total_shares = ewcfg.col_total_shares,
			timestamp = ewcfg.col_timestamp
		), (
			self.id_server,
			self.id_stock,
			self.market_rate,
			self.exchange_rate,
			self.boombust,
			self.total_shares,
			self.timestamp
		))

class EwCompany:
	id_server = ""

	id_stock = ""

	recent_profits = 0

	total_profits = 0

	""" Load the Company data from the database. """
	def __init__(self, id_server = None, stock = None):
		if id_server is not None and stock is not None:
			self.id_server = id_server
			self.id_stock = stock

			try:
				# Retrieve object
				result = ewutils.execute_sql_query("SELECT {recent_profits}, {total_profits} FROM companies WHERE {id_server} = %s AND {stock} = %s".format(
					recent_profits = ewcfg.col_recent_profits,
					total_profits = ewcfg.col_total_profits,
					id_server = ewcfg.col_id_server,
					stock = ewcfg.col_stock
				), (self.id_server, self.id_stock))

				if len(result) > 0:
					# Record found: apply the data to this object.
					self.recent_profits = result[0][0]
					self.total_profits = result[0][1]
				else:
					# Create a new database entry if the object is missing.
					self.persist()
			except:
				ewutils.logMsg("Failed to retrieve company {} from database.".format(self.id_stock))


	""" Save company data object to the database. """
	def persist(self):
		try:
			ewutils.execute_sql_query("REPLACE INTO companies({recent_profits}, {total_profits}, {id_server}, {stock}) VALUES(%s,%s,%s,%s)".format(
				recent_profits = ewcfg.col_recent_profits,
				total_profits = ewcfg.col_total_profits,
				id_server = ewcfg.col_id_server,
				stock = ewcfg.col_stock
			    ), (self.recent_profits, self.total_profits, self.id_server, self.id_stock ))
		except:
			ewutils.logMsg("Failed to save company {} to the database.".format(self.id_stock))

""" player invests slimecoin in the market """
async def invest(cmd):
	user_data = EwUser(member = cmd.message.author)
	time_now = round(time.time())
	market_data = EwMarket(id_server = cmd.message.author.server.id)

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "invest")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
		
	if market_data.clock < 6 or market_data.clock >= 20:
		response = ewcfg.str_exchange_closed
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.time_lastinvest + ewcfg.cd_invest > time_now:
		# Limit frequency of investments.
		response = ewcfg.str_exchange_busy.format(action = "invest")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.life_state == ewcfg.life_state_corpse:
		# Disallow invests from ghosts.
		response = "Your slimebroker can't confirm your identity while you're dead."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	roles_map_user = ewutils.getRoleMap(cmd.message.author.roles)
	if ewcfg.role_rowdyfucker in roles_map_user or ewcfg.role_copkiller in roles_map_user:
		# Disallow investments by RF and CK kingpins.
		response = "You need that money to buy more videogames."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		value = None
		stock = None

		if cmd.tokens_count > 1:
			value = ewutils.getIntToken(cmd.tokens, allow_all = True)
			
			for token in cmd.tokens[1:]:
				if token.lower() in ewcfg.stocks:
					stock = token.lower()
					break


		if value != None:
			if value < 0:
				value = user_data.slimecoin
			if value <= 0:
				value = None

		if value != None:
			if stock != None:

				stock = EwStock(id_server = cmd.message.server.id, stock = stock)
				# basic exchange rate / 1000 = 1 share
				exchange_rate = (stock.exchange_rate / 1000.0)

				cost_total = round(value * 1.05)

				# gets the highest value possible where the player can still pay the fee
				if value == user_data.slimecoin:
					while cost_total > user_data.slimecoin:
						value -= cost_total - value
						cost_total = round(value * 1.05)

				# The user can only buy a whole number of shares, so adjust their cost based on the actual number of shares purchased.
				net_shares = round(value / exchange_rate)

				if user_data.slimecoin < cost_total:
					response = "You don't have enough SlimeCoin. ({:,}/{:,})".format(user_data.slimecoin, cost_total)

				elif value > user_data.slimecoin:
					response = "You don't have that much SlimeCoin to invest."

				elif net_shares == 0:
					response = "You don't have enough SlimeCoin to buy a share in {stock}".format(stock = ewcfg.stock_names.get(stock.id_stock))

				else:
					user_data.change_slimecoin(n = -cost_total, coinsource = ewcfg.coinsource_invest)
					shares = getUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user)
					shares += net_shares
					updateUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user, shares = shares)
					user_data.time_lastinvest = time_now

					stock.total_shares += net_shares
					response = "You invest {coin:,} SlimeCoin and receive {shares:,} shares in {stock}. Your slimebroker takes his nominal fee of {fee:,} SlimeCoin.".format(coin = value, shares = net_shares, stock = ewcfg.stock_names.get(stock.id_stock), fee = (cost_total - value))

					user_data.persist()
					stock.timestamp = round(time.time())
					stock.persist()

			else:
				response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(names = ewcfg.stocks))

		else:
			response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "invest")

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" player withdraws slimecoin from the market """
async def withdraw(cmd):
	user_data = EwUser(member = cmd.message.author)
	time_now = round(time.time())
	market_data = EwMarket(id_server = cmd.message.author.server.id)

	if market_data.clock < 6 or market_data.clock >= 20:
		response = ewcfg.str_exchange_closed
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "withdraw")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.life_state == ewcfg.life_state_corpse:
		# Disallow withdraws from ghosts.
		response = "Your slimebroker can't confirm your identity while you're dead."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		value = None
		stock = None

		if cmd.tokens_count > 1:
			value = ewutils.getIntToken(cmd.tokens[1:], allow_all = True)

			for token in cmd.tokens[1:]:
				if token.lower() in ewcfg.stocks:
					stock = token.lower()
					break


		if stock != None:
			stock = EwStock(id_server = cmd.message.server.id, stock = stock)

			total_shares = getUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user)

			if value != None:
				if value < 0:
					value = total_shares 
				if value <= 0:
					value = None

			if value != None:

				if value <= total_shares:
					exchange_rate = (stock.exchange_rate / 1000.0)

					shares = value
					slimecoin = round(value * exchange_rate)

					if user_data.time_lastinvest + ewcfg.cd_invest > time_now:
						# Limit frequency of withdrawals
						response = ewcfg.str_exchange_busy.format(action = "withdraw")
					else:
						user_data.change_slimecoin(n = slimecoin, coinsource = ewcfg.coinsource_withdraw)
						total_shares -= shares
						user_data.time_lastinvest = time_now
						stock.total_shares -= shares

						response = "You exchange {shares:,} shares in {stock} for {coins:,} SlimeCoin.".format(coins = slimecoin, shares = shares, stock = ewcfg.stock_names.get(stock.id_stock))
						user_data.persist()
						stock.timestamp = round(time.time())
						stock.persist()
						updateUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user, shares = total_shares)
				else:
					response = "You don't have that many shares in {stock} to exchange.".format(stock = ewcfg.stock_names.get(stock.id_stock))
			else:
				response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "withdraw")
		else:
			response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(names = ewcfg.stocks))


	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" donate slime to slimecorp in exchange for slimecoin """
async def donate(cmd):
	user_data = EwUser(member = cmd.message.author)
	market_data = EwMarket(id_server = user_data.id_server)

	time_now = round(time.time())

	if user_data.poi == ewcfg.poi_id_slimecorphq:
		value = None
		if cmd.tokens_count > 1:
			value = ewutils.getIntToken(tokens = cmd.tokens, allow_all = True)

		if value != None:
			if value < 0:
				value = user_data.slimes
			if value <= 0:
				value = None

		if value != None and value < ewcfg.slimecoin_exchangerate:
			response = "You must volunteer to donate at least %d slime to receive compensation." % ewcfg.slimecoin_exchangerate

		elif value != None:
			# Amount of slime invested.
			cost_total = round(value)
			coin_total = round(value / ewcfg.slimecoin_exchangerate)

			if user_data.slimes < cost_total:
				response = "Acid-green flashes of light and bloodcurdling screams emanate from small window of SlimeCorp HQ. Unfortunately, you did not survive the procedure. Your body is dumped down a disposal chute to the sewers."
				market_data.donated_slimes += user_data.slimes
				market_data.persist()
				user_data.die(cause = ewcfg.cause_donation)
				user_data.persist()
				# Assign the corpse role to the player. He dead.
				await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
				sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
				await ewutils.send_message(cmd.client, sewerchannel, "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(cmd.message.author, "You have died in a medical mishap. {}".format(ewcfg.emote_slimeskull)))
			else:
				# Do the transfer if the player can afford it.
				market_data.donated_slimes += cost_total
				market_data.persist()
				user_data.change_slimes(n = -cost_total, source = ewcfg.source_spending)
				user_data.change_slimecoin(n = coin_total, coinsource = ewcfg.coinsource_donation)
				user_data.slime_donations += cost_total

				# Persist changes
				user_data.persist()

				response = "You stumble out of a Slimecorp HQ vault room in a stupor. You don't remember what happened in there, but your body hurts and you've got {slimecoin:,} shiny new SlimeCoin in your pocket.".format(slimecoin = coin_total)

		else:
			response = ewcfg.str_exchange_specify.format(currency = "slime", action = "donate")

	elif user_data.poi == ewcfg.poi_id_slimeoidlab:
		poudrins = ewitem.find_item(item_search = "slimepoudrin", id_user = cmd.message.author.id, id_server = cmd.message.server.id if cmd.message.server is not None else None)

		if poudrins == None:
			response = "You have to own a poudrin in order to donate a poudrin. Duh."

		else:
			ewitem.item_delete(id_item = poudrins.get('id_item'))  # Remove Poudrins
			market_data.donated_poudrins += 1
			market_data.persist()
			user_data.poudrin_donations += 1
			user_data.persist()

			response = "You hand off one of your hard-earned poudrins to the front desk receptionist, who is all too happy to collect it. Pretty uneventful, but at the very least you’re glad donating isn’t physically painful anymore."

	else:
		response = "To donate slime, go to the SlimeCorp HQ in Downtown. To donate poudrins, go to the SlimeCorp Lab in Brawlden."

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" transfer slimecoin between players """
async def xfer(cmd):
	time_now = round(time.time())
	user_data = EwUser(member = cmd.message.author)

	if cmd.message.channel.name != ewcfg.channel_stockexchange:
		# Only allowed in the stock exchange.
		response = ewcfg.str_exchange_channelreq.format(currency = "SlimeCoin", action = "transfer")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if cmd.mentions_count != 1:
		# Must have exactly one target to send to.
		response = "Mention the player you want to send SlimeCoin to."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.time_lastinvest + ewcfg.cd_invest > time_now:
		# Limit frequency of transfers
		response = ewcfg.str_exchange_busy.format(action = "transfer slimecoin")
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	if user_data.life_state == ewcfg.life_state_corpse:
		# Disallow transfers from ghosts.
		response = "Your slimebroker can't confirm your identity while you're dead."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	member = cmd.mentions[0]
	target_data = EwUser(member = member)

	if target_data.life_state == ewcfg.life_state_kingpin:
		# Disallow transfers to RF and CK kingpins.
		response = "You can't transfer SlimeCoin to a known criminal warlord."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	market_data = EwMarket(id_server = cmd.message.author.server.id)

	if cmd.message.author.id == member.id:
		user_data.id_killer = cmd.message.author.id
		user_data.die(cause = ewcfg.cause_suicide)
		user_data.persist()

		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, "Gaming the slimeconomy is punishable by death. SlimeCorp soldiers execute you immediately."))
		await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)
		return

	# Parse the slime value to send.
	value = None
	if cmd.tokens_count > 1:
		value = ewutils.getIntToken(tokens = cmd.tokens)

	if value != None:
		if value < 0:
			value = user_data.slimes
		if value <= 0:
			value = None

	if value != None:
		# Cost including the 5% transfer fee.
		cost_total = round(value * 1.05)

		if user_data.slimecoin < cost_total:
			response = "You don't have enough SlimeCoin. ({:,}/{:,})".format(user_data.slimecoin, cost_total)
		else:
			# Do the transfer if the player can afford it.
			target_data.change_slimecoin(n = value, coinsource = ewcfg.coinsource_transfer)
			user_data.change_slimecoin(n = -cost_total, coinsource = ewcfg.coinsource_transfer)
			user_data.time_lastinvest = time_now

			# Persist changes
			response = "You transfer {slime:,} SlimeCoin to {target_name}. Your slimebroker takes his nominal fee of {fee:,} SlimeCoin.".format(slime = value, target_name = member.display_name, fee = (cost_total - value))

			target_data.persist()
			user_data.persist()
	else:
		response = ewcfg.str_exchange_specify.format(currency = "SlimeCoin", action = "transfer")

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


""" show the current market exchange rate """
async def rate(cmd):
	user_data = EwUser(member = cmd.message.author)
	response = ""

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = "You must go to the Slime Stock Exchange to check the current stock exchange rates ."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
		stock = ""

		if cmd.tokens_count > 0:
			stock = ewutils.flattenTokenListToString(cmd.tokens[1:])

		if stock in ewcfg.stocks:
			stock = EwStock(id_server = cmd.message.server.id, stock = stock)
			response = "The current value of {stock} stocks is {cred:,} SlimeCoin per 1000 Shares.".format(stock = ewcfg.stock_names.get(stock.id_stock), cred = stock.exchange_rate)
		elif stock == "":
			for stock in ewcfg.stocks:
				stock = EwStock(id_server = cmd.message.server.id, stock = stock)
				response += "\nThe current value of {stock} stocks is {cred:,} SlimeCoin per 1000 Shares.".format(stock = ewcfg.stock_names.get(stock.id_stock), cred = stock.exchange_rate)

		else:
			response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(ewcfg.stocks))

		# Send the response to the player.
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show player's shares in a stock """
async def shares(cmd):
	user_data = EwUser(member = cmd.message.author)
	stock = ""
	response = ""

	if cmd.tokens_count > 0:
		stock = ewutils.flattenTokenListToString(cmd.tokens[1:])

	if stock in ewcfg.stocks:
		response = get_user_shares_str(id_server = user_data.id_server, id_user = user_data.id_user, stock = stock)

	elif stock == "":
		for stock in ewcfg.stocks:
			response += "\n"
			response += get_user_shares_str(id_server = user_data.id_server, id_user = user_data.id_user, stock = stock)

	else:
		response = "That's not a valid stock name, please use a proper one, you cunt: {}".format(ewutils.formatNiceList(ewcfg.stocks))

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show all interactable stocks in the market """
async def stocks(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.poi != ewcfg.poi_id_stockexchange:
		# Only allowed in the stock exchange.
		response = "You must go to the Slime Stock Exchange to check the currently available stocks."
		return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

	else:
			response = "Here are the currently available stocks: {}".format(ewutils.formatNiceList(ewcfg.stocks))

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" show player's slimecoin balance """
async def slimecoin(cmd):
	if cmd.mentions_count == 0:
		coins = EwUser(member = cmd.message.author).slimecoin
		response = "You have {:,} SlimeCoin.".format(coins)
	else:
		member = cmd.mentions[0]
		coins = EwUser(member = member).slimecoin
		response = "{} has {:,} SlimeCoin.".format(member.display_name, coins)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" update stock values according to market activity """
def market_tick(stock_data, id_server):
	market_data = EwMarket(id_server = id_server)
	company_data = EwCompany(id_server = id_server, stock = stock_data.id_stock)

	# Nudge the value back to stability.
	market_rate = stock_data.market_rate
	if market_rate >= 1030:
		market_rate -= 10
	elif market_rate <= 970:
		market_rate += 10


	# Invest/Withdraw effects
	coin_rate = 0
	stock_at_last_tick = EwStock(id_server = id_server, stock = stock_data.id_stock, timestamp = market_data.time_lasttick)
	latest_stock = EwStock(id_server = id_server, stock = stock_data.id_stock)
	total_shares = [latest_stock.total_shares, stock_at_last_tick.total_shares]

	# Add profit bonus.
	profits = company_data.recent_profits
	profit_bonus = profits / 100 #- 1 * ((latest_stock.exchange_rate / ewcfg.default_stock_exchange_rate) ** 0.2)
	profit_bonus = min(50, max(profit_bonus, -50))
	market_rate += (profit_bonus / 2)

	if total_shares[0] != total_shares[1]:
		# Positive if net investment, negative if net withdrawal.
		coin_change = (total_shares[0] - total_shares[1])
		coin_rate = ((coin_change * 1.0) / total_shares[1] if total_shares[1] != 0 else 1)

		if coin_rate > 1.0:
			coin_rate = 1.0
		elif coin_rate < -0.5:
			coin_rate = -0.5

		coin_rate = round((coin_rate * ewcfg.max_iw_swing) if coin_rate > 0 else (
					coin_rate * 2 * ewcfg.max_iw_swing))

	market_rate += coin_rate

	# Tick down the boombust cooldown.
	if stock_data.boombust < 0:
		stock_data.boombust += 1
	elif stock_data.boombust > 0:
		stock_data.boombust -= 1

	# Adjust the market rate.
	fluctuation = 0  # (random.randrange(5) - 2) * 100
	noise = (random.randrange(19) - 9) * 2
	subnoise = (random.randrange(13) - 6)

	# Some extra excitement!
	if noise == 0 and subnoise == 0:
		boombust = (random.randrange(3) - 1) * 200

		# If a boombust occurs shortly after a previous boombust, make sure it's the opposite effect. (Boom follows bust, bust follows boom.)
		if (stock_data.boombust > 0 and boombust > 0) or (stock_data.boombust < 0 and boombust < 0):
			boombust *= -1

		if boombust != 0:
			stock_data.boombust = ewcfg.cd_boombust

			if boombust < 0:
				stock_data.boombust *= -1
	else:
		boombust = 0

	market_rate += fluctuation + noise + subnoise + boombust
	if market_rate < 300:
		market_rate = (300 + noise + subnoise)

	#percentage = ((market_rate / 10) - 100)
	#percentage_abs = percentage * -1


	exchange_rate_increase = round((market_rate - ewcfg.default_stock_market_rate) * min(stock_data.exchange_rate, ewcfg.default_stock_exchange_rate) / ewcfg.default_stock_market_rate)

	percentage = exchange_rate_increase / stock_data.exchange_rate
	percentage_abs = percentage * -1


	# negative exchange rate causes problems, duh
	#exchange_rate_increase = max(exchange_rate_increase, -stock_data.exchange_rate + 1000)

	points = abs(exchange_rate_increase / 1000.0)

	stock_data.exchange_rate += exchange_rate_increase
	stock_data.market_rate = market_rate


	# Give some indication of how the market is doing to the users.
	response = ewcfg.stock_emotes.get(stock_data.id_stock) + ' ' + ewcfg.stock_names.get(stock_data.id_stock) + ' '

	if stock_data.exchange_rate < 1000:
		response += 'has gone bankrupt!'
		if stock_data.total_shares > 0:
			majority_shareholder = get_majority_shareholder(stock = stock_data.id_stock, id_server = id_server)
			player_data = EwPlayer(id_user = majority_shareholder)
			shares = getUserTotalShares(stock = stock_data.id_stock, id_user = majority_shareholder, id_server = stock_data.id_server)
			shares_lost = int(shares * 0.9)
			stock_data.total_shares -= shares_lost
			updateUserTotalShares(stock = stock_data.id_stock, id_user = majority_shareholder, id_server = stock_data.id_server, shares = shares - shares_lost)
			response += ' The majority shareholder {} is held responsible. SlimeCorp seizes 90% of their shares in the company to pay for the damages.'.format(player_data.display_name)
			stock_data.exchange_rate = 10000
		else:
			response += ' SlimeCorp pumps several billion slimecoin into bailing the company out and a new image campaign.'
			stock_data.exchange_rate = ewcfg.default_stock_exchange_rate
			stock_data.market_rate = ewcfg.default_stock_market_rate
	else:
		# Market is up ...
		if market_rate > 1200:
			response += 'is skyrocketing!!! Slime stock is up {p:.3g} points!!!'.format(p = points)
		elif market_rate > 1100:
			response += 'is booming! Slime stock is up {p:.3g} points!'.format(p = points)
		elif market_rate > 1000:
			response += 'is doing well. Slime stock is up {p:.3g} points.'.format(p = points)
		# Market is down ...
		elif market_rate < 800:
			response += 'is plummeting!!! Slime stock is down {p:.3g} points!!!'.format(p = points)
		elif market_rate < 900:
			response += 'is stagnating! Slime stock is down {p:.3g} points!'.format(p = points)
		elif market_rate < 1000:
			response += 'is a bit sluggish. Slime stock is down {p:.3g} points.'.format(p = points)
		# Perfectly balanced
		else:
			response += 'is holding steady. No change in slime stock value.'

	response += ' ' + ewcfg.stock_emotes.get(stock_data.id_stock)

	stock_data.persist()

	company_data.total_profits += company_data.recent_profits
	company_data.recent_profits = 0
	company_data.persist()


	# Send the announcement.
	return response

""" Returns an array of the most recent counts of all invested slime coin, from newest at 0 to oldest. """
def getRecentTotalShares(id_server=None, stock=None, count=2):
	if id_server != None and stock != None:

		values = []

		try:

			count = round(count)
			data = ewutils.execute_sql_query("SELECT {total_shares} FROM stocks WHERE {id_server} = %s AND {stock} = %s ORDER BY {timestamp} DESC LIMIT %s".format(
				stock = ewcfg.col_stock,
				total_shares = ewcfg.col_total_shares,
				id_server = ewcfg.col_id_server,
				timestamp = ewcfg.col_timestamp,
			), (
				id_server,
				stock,
				(count if (count > 0) else 2)
			))

			for row in data:
				values.append(row[0])

			# Make sure we return at least one value.
			if len(values) == 0:
				values.append(0)

			# If we don't have enough data, pad out to count with the last value in the array.
			value_last = values[-1]
			while len(values) < count:
				values.append(value_last)
		except:
			pass
		finally:
			return values

"""" returns the total number of shares a player has in a certain stock """
def getUserTotalShares(id_server=None, stock=None, id_user=None):
	if id_server != None and stock != None and id_user != None:

		values = 0

		try:

			data = ewutils.execute_sql_query("SELECT {shares} FROM shares WHERE {id_server} = %s AND {id_user} = %s AND {stock} = %s".format(
				stock = ewcfg.col_stock,
				shares = ewcfg.col_shares,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				id_user,
				stock,
			))

			for row in data:
				values = row[0]

		except:
			pass
		finally:
			return values

"""" updates the total number of shares a player has in a certain stock """
def updateUserTotalShares(id_server=None, stock=None, id_user=None, shares=0):
	if id_server != None and stock != None and id_user != None:

		try:

			ewutils.execute_sql_query("REPLACE INTO shares({id_server}, {id_user}, {stock}, {shares}) VALUES(%s, %s, %s, %s)".format(
				stock = ewcfg.col_stock,
				shares = ewcfg.col_shares,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				id_user,
				stock,
				shares,
			))
		except:
			pass

""" used for !shares """
def get_user_shares_str(id_server = None, stock = None, id_user = None):
	response = ""
	if id_server != None and stock != None and id_user != None:
		user_data = EwUser(id_server = id_server, id_user = id_user)
		stock = EwStock(id_server = id_server, stock = stock)
		shares = getUserTotalShares(id_server = user_data.id_server, stock = stock.id_stock, id_user = user_data.id_user)
		shares_value = round(shares * (stock.exchange_rate / 1000.0))

		response = "You have {shares:,} shares in {stock}".format(shares = shares, stock = ewcfg.stock_names.get(stock.id_stock))
		if user_data.poi == ewcfg.poi_id_stockexchange:
			response += ", currently valued at {coin:,} SlimeCoin.".format(coin = shares_value)
		else:
			response += "."
		
	return response

""" get user ID of player with most shares in a stock """
def get_majority_shareholder(id_server = None, stock = None):
	result = None
	if id_server is not None and stock is not None:
		try:

			data = ewutils.execute_sql_query("SELECT {id_user}, {shares} FROM shares WHERE {id_server} = %s AND {stock} = %s ORDER BY {shares} DESC LIMIT 1".format(
				stock = ewcfg.col_stock,
				shares = ewcfg.col_shares,
				id_server = ewcfg.col_id_server,
				id_user = ewcfg.col_id_user
			), (
				id_server,
				stock,
			))

			if len(data) > 0:
				if data[0][1] > 0:
					result = data[0][0]

		except:
			pass
		finally:
			return result

async def quarterlyreport(cmd):
	progress = 0
	objective = 1000
	goal = "POUDRINS DONATED"
	completion = False

	try:
		conn_info = ewutils.databaseConnect()
		conn = conn_info.get('conn')
		cursor = conn.cursor()

		# Display the progress towards the current Quarterly Goal, whatever that may be.
		cursor.execute("SELECT {metric} FROM markets WHERE id_server = %s".format(
			metric = ewcfg.col_donated_poudrins
		), (cmd.message.server.id, ))

		result = cursor.fetchone();

		if result != None:
			progress = result[0]

			if progress == None:
				progress = 0

			if progress >= objective:
				progress = objective
				completion = True

	finally:
		cursor.close()
		ewutils.databaseClose(conn_info)

	response = "{:,} / {:,} {}.".format(progress, objective, goal)

	if completion == True:
		response += " THE QUARTERLY GOAL HAS BEEN REACHED. STAY TUNED FOR FURTHER ANNOUNCEMENTS."

	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
