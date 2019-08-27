import asyncio
import time
import random
import math

import ewcfg
import ewutils
import ewitem
import ewmap
import ewrolemgr
import ewstats
import ewstatuseffects
import ewhunting

from ew import EwUser
from ewitem import EwItem
from ewmarket import EwMarket
from ewslimeoid import EwSlimeoid
from ewdistrict import EwDistrict
from ewplayer import EwPlayer
from ewhunting import EwEnemy

""" A weapon object which adds flavor text to kill/shoot. """
class EwWeapon:

	item_type = "weapon"

	# A unique name for the weapon. This is used in the database and typed by
	# users, so it should be one word, all lowercase letters.
	id_weapon = ""

	# An array of names that might be used to identify this weapon by the player.
	alias = []

	# Displayed when !equip-ping this weapon
	str_equip = ""

	# Displayed when this weapon is used for a !kill
	str_kill = ""

	# Displayed to the dead victim in the sewers. Brief phrase such as "gunned down" etc.
	str_killdescriptor = ""

	# Displayed when viewing the !trauma of another player.
	str_trauma = ""

	# Displayed when viewing the !trauma of yourself.
	str_trauma_self = ""
	
	# Displayed when viewing the !weapon of another player.
	str_weapon = ""

	# Displayed when viewing the !weapon of yourself.
	str_weapon_self = ""

	# Same as weapon and weapon_self, but used when the player's weapon skill is max.
	str_weaponmaster = ""
	str_weaponmaster_self = ""

	# Displayed when a non-lethal hit occurs.
	str_damage = ""

	# Displayed when a weapon backfires
	str_backfire = ""

	# Displayed when a weapon jams
	str_jammed = ""

	# Displayed when two players wielding the same weapon !spar with each other.
	str_duel = ""

	# Function that applies the special effect for this weapon.
	fn_effect = None

	# Displayed when a weapon effect causes a critical hit.
	str_crit = ""

	# Displayed when a weapon effect causes a miss.
	str_miss = ""

	# Displayed when !inspect-ing
	str_description = ""

	# Displayed when reloading
	str_reload = ""

	# Displayed when the weapon used it's last ammo
	str_reload_warning = ""

	# Displayed when the weapon is unjammed
	str_unjam = ""

	# Clip size
	clip_size = 0

	# Cost
	price = 0

	# Hard Cooldown 
	cooldown = 0

	# Vendor
	vendors = []

	# Classes the weapon belongs to
	classes = []

	acquisition = "dojo"

	# Statistics metric
	stat = ""
	
	def __init__(
		self,
		id_weapon = "",
		alias = [],
		str_equip = "",
		str_kill = "",
		str_killdescriptor = "",
		str_trauma = "",
		str_trauma_self = "",
		str_weapon = "",
		str_weapon_self = "",
		str_damage = "",
		str_backfire = "",
		str_duel = "",
		str_weaponmaster = "",
		str_weaponmaster_self = "",
		fn_effect = None,
		str_crit = "",
		str_miss = "",
		str_jammed = "",
		str_description = "",
		str_reload = "",
		str_reload_warning = "",
		str_unjam = "",
		clip_size = 0,
		price = 0,
		cooldown = 0,
		vendors = [],
		classes = [],
		acquisition = "dojo",
		stat = ""
	):
		self.item_type = ewcfg.it_weapon

		self.id_weapon = id_weapon
		self.alias = alias
		self.str_equip = str_equip
		self.str_kill = str_kill
		self.str_killdescriptor = str_killdescriptor
		self.str_trauma = str_trauma
		self.str_trauma_self = str_trauma_self
		self.str_weapon = str_weapon
		self.str_weapon_self = str_weapon_self
		self.str_damage = str_damage
		self.str_backfire = str_backfire
		self.str_duel = str_duel
		self.str_weaponmaster = str_weaponmaster
		self.str_weaponmaster_self = str_weaponmaster_self
		self.fn_effect = fn_effect
		self.str_crit = str_crit
		self.str_miss = str_miss
		self.str_jammed = str_jammed
		self.str_description = str_description
		self.str_reload = str_reload
		self.str_reload_warning = str_reload_warning
		self.str_unjam = str_unjam
		self.clip_size = clip_size
		self.price = price
		self.cooldown = cooldown
		self.vendors = vendors
		self.classes = classes
		self.acquisition = acquisition
		self.stat = stat

		self.str_name = self.str_weapon


""" A data-moving class which holds references to objects we want to modify with weapon effects. """
class EwEffectContainer:
	miss = False
	crit = False
	backfire = False
	jammed = False
	strikes = 0
	slimes_damage = 0
	slimes_spent = 0
	user_data = None
	shootee_data = None
	weapon_item = None
	time_now = 0
	bystander_damage = 0
	miss_mod = 0
	crit_mod = 0

	# Debug method to dump out the members of this object.
	def dump(self):
		print("effect:\nmiss: {miss}\nbackfire: {backfire}\ncrit: {crit}\nstrikes: {strikes}\nslimes_damage: {slimes_damage}\nslimes_spent: {slimes_spent}\nexplosion_dmg: {bystander_damage}".format(
			miss = self.miss,
			backfire = self.backfire,
			crit = self.crit,
			strikes = self.strikes,
			slimes_damage = self.slimes_damage,
			slimes_spent = self.slimes_spent,
			bystander_damage = self.bystander_damage
		))

	def __init__(
		self,
		miss = False,
		crit = False,
		backfire = False,
		jammed = False,
		strikes = 0,
		slimes_damage = 0,
		slimes_spent = 0,
		user_data = None,
		shootee_data = None,
		weapon_item = None,
		time_now = 0,
		bystander_damage = 0,
		miss_mod = 0,
		crit_mod = 0
	):
		self.miss = miss
		self.crit = crit
		self.backfire = backfire
		self.jammes = jammed
		self.strikes = strikes
		self.slimes_damage = slimes_damage
		self.slimes_spent = slimes_spent
		self.user_data = user_data
		self.shootee_data = shootee_data
		self.weapon_item = weapon_item
		self.time_now = time_now
		self.bystander_damage = bystander_damage
		self.miss_mod = miss_mod
		self.crit_mod = crit_mod

def canAttack(cmd):
	response = ""
	time_now = int(time.time())
	user_data = EwUser(member = cmd.message.author)
	weapon_item = None
	weapon = None
	if user_data.weapon >= 0:
		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
	statuses = user_data.getStatusEffects()

	if ewmap.channel_name_is_poi(cmd.message.channel.name) == False:
		response = "You can't commit violence from here."
	elif ewmap.poi_is_pvp(user_data.poi) == False:
		response = "You must go elsewhere to commit gang violence."
	elif cmd.mentions_count > 1:
		response = "One shot at a time!"
	elif user_data.hunger >= ewutils.hunger_max_bylevel(user_data.slimelevel):
		response = "You are too exhausted for gang violence right now. Go get some grub!"
	elif weapon != None and ewcfg.weapon_class_ammo in weapon.classes and int(weapon_item.item_props.get('ammo')) == 0:
		response = "You've run out of ammo and need to {}!".format(ewcfg.cmd_reload)
	elif weapon != None and ewcfg.weapon_class_thrown in weapon.classes and weapon_item.stack_size == 0:
		response = "You're out of {}! Go buy more at the {}".format(weapon.str_weapon, ewutils.formatNiceList(names = weapon.vendors, conjunction="or" ))
	elif weapon != None and weapon.cooldown + (int(weapon_item.item_props.get("time_lastattack")) if weapon_item.item_props.get("time_lastattack") != None else 0) > time_now:
		response = "Your {weapon_name} isn't ready for another attack yet!".format(weapon_name = weapon.id_weapon)
	elif weapon != None and weapon_item.item_props.get("jammed") == "True":
		response = "Your {weapon_name} is jammed, you will need to {unjam} it before shooting again".format(weapon_name = weapon.id_weapon, unjam = ewcfg.cmd_unjam)
	elif cmd.mentions_count <= 0:
		slimes_spent = int(ewutils.slime_bylevel(user_data.slimelevel) / 24)
		# user is going after enemies rather than players

		# Get target's info.
		# converts ['THE', 'Lost', 'juvie'] into 'the lost juvie'
		huntedenemy = " ".join(cmd.tokens[1:]).lower()

		enemy_data = ewhunting.find_enemy(huntedenemy, user_data)

		user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
		user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
		user_isslimecorp = user_data.life_state == ewcfg.life_state_lucky
		
		if enemy_data == None and (user_data.life_state == ewcfg.life_state_corpse):
			slimes_spent = int(ewutils.slime_bylevel(user_data.slimelevel) / 20)
			response = "You don't have enough slime to attack. ({:,}/{:,})".format(user_data.slimes, slimes_spent)

		elif (slimes_spent > user_data.slimes):
			# Not enough slime to shoot.
			response = "You don't have enough slime to attack. ({:,}/{:,})".format(user_data.slimes, slimes_spent)

		elif (time_now - user_data.time_lastkill) < ewcfg.cd_kill:
			# disallow kill if the player has killed recently
			response = "Take a moment to appreciate your last slaughter."

		elif user_iskillers == False and user_isrowdys == False and user_isslimecorp == False:
			# Only killers, rowdys, the cop killer, and rowdy fucker can shoot people.
			if user_data.life_state == ewcfg.life_state_juvenile:
				response = "Juveniles lack the moral fiber necessary for violence."
			else:
				response = "You lack the moral fiber necessary for violence."
				
		elif enemy_data != None:
			# enemy found, redirect variables to code in ewhunting
			response = ewcfg.enemy_targeted_string
			
		else:
			# no enemy is found within that district
			response = "Your bloodlust is appreciated, but ENDLESS WAR couldn't find what you were trying to kill."

	elif cmd.mentions_count == 1:
		slimes_spent = int(ewutils.slime_bylevel(user_data.slimelevel) / 24)

		# Get target's info.
		member = cmd.mentions[0]
		shootee_data = EwUser(member = member)

		user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
		user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
		user_isslimecorp = user_data.life_state == ewcfg.life_state_lucky

		if shootee_data.life_state == ewcfg.life_state_kingpin:
			# Disallow killing generals.
			response = "He is hiding in his ivory tower and playing video games like a retard."

		elif (slimes_spent > user_data.slimes):
			# Not enough slime to shoot.
			response = "You don't have enough slime to attack. ({:,}/{:,})".format(user_data.slimes, slimes_spent)

		elif (time_now - user_data.time_lastkill) < ewcfg.cd_kill:
			# disallow kill if the player has killed recently
			response = "Take a moment to appreciate your last slaughter."

		elif shootee_data.poi != user_data.poi:
			response = "You can't reach them from where you are."

		elif ewmap.poi_is_pvp(shootee_data.poi) == False:
			response = "{} is not mired in the ENDLESS WAR right now.".format(member.display_name)

		elif user_iskillers == False and user_isrowdys == False and user_isslimecorp == False:
			# Only killers, rowdys, the cop killer, and rowdy fucker can shoot people.
			if user_data.life_state == ewcfg.life_state_juvenile:
				response = "Juveniles lack the moral fiber necessary for violence."
			else:
				response = "You lack the moral fiber necessary for violence."

		elif (time_now - shootee_data.time_lastrevive) < ewcfg.invuln_onrevive:
			# User is currently invulnerable.
			response = "{} has died too recently and is immune.".format(member.display_name)

		elif shootee_data.life_state == ewcfg.life_state_corpse and shootee_data.busted == True:
			# Target is already dead and not a ghost.
			response = "{} is already dead.".format(member.display_name)
		
		elif shootee_data.life_state == ewcfg.life_state_corpse and ewcfg.status_ghostbust_id not in statuses:
			# Target is a ghost but user is not able to bust 
			response = "You don't know how to fight a ghost."

	return response

""" Player deals damage to another player. """
async def attack(cmd):
	time_now = int(time.time())
	response = ""
	deathreport = ""
	levelup_response = ""
	coinbounty = 0
	resp_cont = ewutils.EwResponseContainer(id_server = cmd.message.server.id)
	market_data = EwMarket(id_server = cmd.message.server.id)

	user_data = EwUser(member = cmd.message.author)
	slimeoid = EwSlimeoid(member = cmd.message.author)
	weapon = None
	weapon_item = None
	if user_data.weapon >= 0:
		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))

	response = canAttack(cmd)

	if response == "":
		# Get shooting player's info
		if user_data.slimelevel <= 0: 
			user_data.slimelevel = 1
			user_data.persist()

		# Get target's info.
		member = cmd.mentions[0]
		if member.id == cmd.message.author.id:
			response = "Try {}.".format(ewcfg.cmd_suicide)
			resp_cont.add_channel_response(cmd.message.channel.name, response)
			return await resp_cont.post()
		else:
			shootee_data = EwUser(member = member)
		shootee_slimeoid = EwSlimeoid(member = member)

		user_mutations = user_data.get_mutations()
		shootee_mutations = shootee_data.get_mutations()

		district_data = EwDistrict(district = user_data.poi, id_server = cmd.message.server.id)

		miss = False
		crit = False
		backfire = False
		jammed = False
		strikes = 0
		bystander_damage = 0
		miss_mod = 0
		crit_mod = 0
		dmg_mod = 0

		miss_mod += round(apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_miss, target = ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_miss, target = ewcfg.status_effect_target_other), 2)
		crit_mod += round(apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_crit, target = ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_crit, target = ewcfg.status_effect_target_other), 2)
		dmg_mod += round(apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_damage, target = ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type = ewcfg.status_effect_type_damage, target = ewcfg.status_effect_target_other), 2)

		slimes_spent = int(ewutils.slime_bylevel(user_data.slimelevel) / 24)
		slimes_damage = int((slimes_spent * 4) * (100 + (user_data.weaponskill * 10)) / 100.0)

		if weapon is None:
			slimes_damage /= 2  # penalty for not using a weapon, otherwise fists would be on par with other weapons
		slimes_dropped = shootee_data.totaldamage + shootee_data.slimes

		slimes_damage += int(slimes_damage * dmg_mod)

		user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
		user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
		user_isslimecorp = user_data.life_state in [ewcfg.life_state_lucky, ewcfg.life_state_executive]

		if shootee_data.life_state == ewcfg.life_state_corpse:
			# Attack a ghostly target
			coinbounty = int(shootee_data.bounty / ewcfg.slimecoin_exchangerate)
			user_data.change_slimecoin(n = coinbounty, coinsource = ewcfg.coinsource_bounty)

			ewstats.track_maximum(user = user_data, metric = ewcfg.stat_biggest_bust_level, value = shootee_data.slimelevel)

			# Steal items
			ewitem.item_loot(member = member, id_user_target = cmd.message.author.id)

			shootee_data.die(cause = ewcfg.cause_busted)

			response = "{name_target}\'s ghost has been **BUSTED**!!".format(name_target = member.display_name)

			deathreport = "Your ghost has been busted by {}. {}".format(cmd.message.author.display_name, ewcfg.emote_bustin)
			deathreport = "{} ".format(ewcfg.emote_bustin) + ewutils.formatMessage(member, deathreport)
			
			if coinbounty > 0:
				response += "\n\n SlimeCorp transfers {} SlimeCoin to {}\'s account.".format(str(coinbounty), cmd.message.author.display_name)

			#adjust busts
			ewstats.increment_stat(user = user_data, metric = ewcfg.stat_ghostbusts)

			# Persist every users' data.
			user_data.persist()
			shootee_data.persist()
			resp_cont.add_channel_response(cmd.message.channel.name, response)
			if deathreport != "":
				resp_cont.add_channel_response(ewcfg.channel_sewers, deathreport)

			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.server.get_member(shootee_data.id_user))

		else:
			#hunger drain
			user_data.hunger += ewcfg.hunger_pershot * ewutils.hunger_cost_mod(user_data.slimelevel)
			
			# Weaponized flavor text.
			randombodypart = ewcfg.hitzone_list[random.randrange(len(ewcfg.hitzone_list))]

			# Weapon-specific adjustments
			if weapon != None and weapon.fn_effect != None:
				# Build effect container
				ctn = EwEffectContainer(
					miss = miss,
					backfire=backfire,
					crit = crit,
					jammed=jammed,
					slimes_damage = slimes_damage,
					slimes_spent = slimes_spent,
					user_data = user_data,
					weapon_item = weapon_item,
					shootee_data = shootee_data,
					time_now = time_now,
					bystander_damage = bystander_damage,
					miss_mod = miss_mod,
					crit_mod = crit_mod
				)

				# Make adjustments
				weapon.fn_effect(ctn)

				# Apply effects for non-reference values
				miss = ctn.miss
				backfire = ctn.backfire
				crit = ctn.crit
				jammed = ctn.jammed
				slimes_damage = ctn.slimes_damage
				slimes_spent = ctn.slimes_spent
				strikes = ctn.strikes
				bystander_damage = ctn.bystander_damage
				# user_data and shootee_data should be passed by reference, so there's no need to assign them back from the effect container.

				weapon_item.item_props['time_lastattack'] = time_now
				weapon_item.persist()

				# Spend slimes, to a minimum of zero
				user_data.change_slimes(n = (-user_data.slimes if slimes_spent >= user_data.slimes else -slimes_spent), source = ewcfg.source_spending)

				if weapon.id_weapon == ewcfg.weapon_id_garrote:
					user_data.persist()
					shootee_data.persist()
					response = "You wrap your wire around {}'s neck...".format(member.display_name)
					resp_cont.add_channel_response(cmd.message.channel.name, response)
					resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
					await resp_cont.post()
					msg = await cmd.client.wait_for_message(timeout = 5, author = member)

					user_data = EwUser(member = cmd.message.author)
					shootee_data = EwUser(member = member)

					# One of the players died in the meantime
					if user_data.life_state == ewcfg.life_state_corpse or shootee_data.life_state == ewcfg.life_state_corpse:
						return
					# A user left the district or strangling was broken
					elif msg != None or user_data.poi != shootee_data.poi:
						return
					else:
						shootee_data.clear_status(ewcfg.status_strangled_id)
						#shootee_data.persist()
					
				if weapon.id_weapon == ewcfg.weapon_id_minigun:
					user_data.persist()
					shootee_data.persist()
					response = "You begin revving up your minigun..."
					resp_cont.add_channel_response(cmd.message.channel.name, response)
					resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
					await resp_cont.post()
					await asyncio.sleep(5)
					user_data = EwUser(member = cmd.message.author)
					shootee_data = EwUser(member = member)

					# One of the players died in the meantime
					if user_data.life_state == ewcfg.life_state_corpse or shootee_data.life_state == ewcfg.life_state_corpse:
						return
					# A user left the district
					if user_data.poi != shootee_data.poi:
						miss = True

				# Remove a bullet from the weapon
				if ewcfg.weapon_class_ammo in weapon.classes:
					weapon_item.item_props['ammo'] = int(weapon_item.item_props.get("ammo")) - 1

				# Remove one item from stack
				if ewcfg.weapon_class_thrown in weapon.classes:
					weapon_item.stack_size -= 1

				if ewcfg.weapon_class_exploding in weapon.classes:
					user_data.persist()
					shootee_data.persist()

					if not miss:
						life_states = [ewcfg.life_state_juvenile, ewcfg.life_state_enlisted]
						factions = ["", user_data.faction if backfire else shootee_data.faction]
						# Burn players in district
						if weapon.id_weapon == ewcfg.weapon_id_molotov:
							bystander_users = district_data.get_players_in_district(life_states=life_states, factions=factions)
							for bystander in bystander_users:
								#print(bystander)
								bystander_user_data = EwUser(id_user = bystander, id_server = user_data.id_server)
								bystander_player_data = EwPlayer(id_user = bystander, id_server = user_data.id_server)
								resp = bystander_user_data.applyStatus(id_status=ewcfg.status_burning_id, value=bystander_damage, source=user_data.id_user).format(name_player = bystander_player_data.display_name)
								resp_cont.add_channel_response(cmd.message.channel.name, resp)
						#Damage players/enemies in district
						else:
							resp = await weapon_explosion(user_data=user_data, shootee_data=shootee_data, district_data=district_data, life_states=life_states, factions=factions, slimes_damage=bystander_damage, backfire=backfire, time_now=time_now, target_enemy=False)
							resp_cont.add_response_container(resp)

					user_data = EwUser(member = cmd.message.author)
					shootee_data = EwUser(member = member)

			# can't hit lucky lucy
			if shootee_data.life_state == ewcfg.life_state_lucky:
				miss = True

			if miss or backfire or jammed:
				slimes_damage = 0
				weapon_item.item_props["consecutive_hits"] = 0

			# Remove !revive invulnerability.
			user_data.time_lastrevive = 0

			# Lone wolf
			if ewcfg.mutation_id_lonewolf in user_mutations:
				allies_in_district = district_data.get_players_in_district(
					min_level = math.ceil((1/10) ** 0.25 * user_data.slimelevel),
					life_states = [ewcfg.life_state_enlisted],
					factions = [user_data.faction]
				)
				if user_data.id_user in allies_in_district:
					allies_in_district.remove(user_data.id_user)

				if len(allies_in_district) == 0:
					slimes_damage *= 1.5
			
			# Organic fursuit
			if ewcfg.mutation_id_organicfursuit in user_mutations and (
				(market_data.day % 31 == 0 and market_data.clock >= 20)
				or (market_data.day % 31 == 1 and market_data.clock < 6)
			):
				slimes_damage *= 2
			if ewcfg.mutation_id_organicfursuit in shootee_mutations and (
				(market_data.day % 31 == 0 and market_data.clock >= 20)
				or (market_data.day % 31 == 1 and market_data.clock < 6)
			):
				slimes_damage *= 0.1

			# Fat chance
			if ewcfg.mutation_id_fatchance in shootee_mutations and shootee_data.hunger / shootee_data.get_hunger_max() > 0.5:
				slimes_damage *= 0.75
			
			# Social animal
			if ewcfg.mutation_id_socialanimal in user_mutations:
				allies_in_district = district_data.get_players_in_district(
					min_level = math.ceil((1/10) ** 0.25 * user_data.slimelevel),
					life_states = [ewcfg.life_state_enlisted],
					factions = [user_data.faction]
				)
				if user_data.id_user in allies_in_district:
					allies_in_district.remove(user_data.id_user)

				slimes_damage *= 1 + 0.1 * len(allies_in_district)
				
			# Dressed to kill
			if ewcfg.mutation_id_dressedtokill in user_mutations:
				items = ewitem.inventory(
					id_user = cmd.message.author.id,
					id_server = cmd.message.server.id,
					item_type_filter = ewcfg.it_cosmetic
				)

				adorned_items = 0
				for it in items:
					i = EwItem(it.get('id_item'))
					if i.item_props['adorned'] == 'true':
						adorned_items += 1

				if adorned_items >= ewutils.max_adorn_bylevel(user_data.slimelevel):
					slimes_damage *= 1.5

			# Damage stats
			ewstats.track_maximum(user = user_data, metric = ewcfg.stat_max_hitdealt, value = slimes_damage)
			ewstats.change_stat(user = user_data, metric = ewcfg.stat_lifetime_damagedealt, n = slimes_damage)

			# Slimes from this shot might be awarded to the boss.
			role_boss = (ewcfg.role_copkiller if user_iskillers else ewcfg.role_rowdyfucker)
			boss_slimes = 0
			user_inital_level = user_data.slimelevel

			was_juvenile = False
			was_killed = False
			was_shot = False

			if shootee_data.life_state in [ewcfg.life_state_enlisted, ewcfg.life_state_juvenile, ewcfg.life_state_lucky, ewcfg.life_state_executive]:
				# User can be shot.
				if shootee_data.life_state == ewcfg.life_state_juvenile:
					was_juvenile = True

				was_shot = True

			if was_shot:

				if slimes_damage >= shootee_data.slimes - shootee_data.bleed_storage:
					was_killed = True
					if ewcfg.mutation_id_thickerthanblood in user_mutations:
						slimes_damage = 0
					else:
						slimes_damage = max(shootee_data.slimes - shootee_data.bleed_storage, 0)

				sewer_data = EwDistrict(district = ewcfg.poi_id_thesewers, id_server = cmd.message.server.id)
				# move around slime as a result of the shot
				if was_juvenile or user_data.faction == shootee_data.faction:
					slimes_drained = int(3 * slimes_damage / 4) # 3/4
					slimes_toboss = 0
				else:
					slimes_drained = 0
					slimes_toboss = int(slimes_damage / 2)

				damage = str(slimes_damage)

				slimes_tobleed = int((slimes_damage - slimes_toboss - slimes_drained) / 2)
				if ewcfg.mutation_id_nosferatu in user_mutations and (market_data.clock < 6 or market_data.clock >= 20):
					slimes_tobleed = 0
				if ewcfg.mutation_id_bleedingheart in shootee_mutations:
					slimes_tobleed *= 2

				slimes_directdamage = slimes_damage - slimes_tobleed
				slimes_splatter = slimes_damage - slimes_toboss - slimes_tobleed - slimes_drained

				boss_slimes += slimes_toboss
				district_data.change_slimes(n = slimes_splatter, source = ewcfg.source_killing)
				shootee_data.bleed_storage += slimes_tobleed
				shootee_data.change_slimes(n = - slimes_directdamage, source = ewcfg.source_damage)
				sewer_data.change_slimes(n = slimes_drained)
				sewer_data.persist()

				if was_killed:
					#adjust statistics
					ewstats.increment_stat(user = user_data, metric = ewcfg.stat_kills)
					ewstats.track_maximum(user = user_data, metric = ewcfg.stat_biggest_kill, value = int(slimes_dropped))
					if user_data.slimelevel > shootee_data.slimelevel:
						ewstats.increment_stat(user = user_data, metric = ewcfg.stat_lifetime_ganks)
					elif user_data.slimelevel < shootee_data.slimelevel:
						ewstats.increment_stat(user = user_data, metric = ewcfg.stat_lifetime_takedowns)

					if weapon != None:
						weapon_item.item_props["kills"] = (int(weapon_item.item_props.get("kills")) if weapon_item.item_props.get("kills") != None else 0) + 1
						weapon_item.item_props["totalkills"] = (int(weapon_item.item_props.get("totalkills"))  if weapon_item.item_props.get("totalkills") != None else 0) + 1
						ewstats.increment_stat(user = user_data, metric = weapon.stat)
						
					# Collect bounty
					coinbounty = int(shootee_data.bounty / ewcfg.slimecoin_exchangerate)  # 100 slime per coin
					
					if shootee_data.slimes >= 0:
						user_data.change_slimecoin(n = coinbounty, coinsource = ewcfg.coinsource_bounty)

					# Steal items
					ewitem.item_loot(member = member, id_user_target = cmd.message.author.id)

					#add bounty
					user_data.add_bounty(n = (shootee_data.bounty / 2) + (slimes_dropped / 4))

					# Give a bonus to the player's weapon skill for killing a stronger player.
					if shootee_data.slimelevel >= user_data.slimelevel and weapon is not None:
						user_data.add_weaponskill(n = 1, weapon_type = weapon.id_weapon)
					
					explode_damage = ewutils.slime_bylevel(shootee_data.slimelevel) / 5

					# release bleed storage
					if ewcfg.mutation_id_thickerthanblood in user_mutations:
						slimes_todistrict = 0
						slimes_tokiller = shootee_data.slimes
					else:
						slimes_todistrict = shootee_data.slimes / 2
						slimes_tokiller = shootee_data.slimes / 2
					district_data.change_slimes(n = slimes_todistrict, source = ewcfg.source_killing)
					levelup_response = user_data.change_slimes(n = slimes_tokiller, source = ewcfg.source_killing)
					if ewcfg.mutation_id_fungalfeaster in user_mutations:
						user_data.hunger = 0

					# Player was killed.
					shootee_data.id_killer = user_data.id_user
					shootee_data.die(cause = ewcfg.cause_killing)
					shootee_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)

					kill_descriptor = "beaten to death"
					if weapon != None:
						response = weapon.str_damage.format(
							name_player = cmd.message.author.display_name,
							name_target = member.display_name,
							hitzone = randombodypart,
							strikes = strikes
						)
						kill_descriptor = weapon.str_killdescriptor
						if crit:
							response += " {}".format(weapon.str_crit.format(
								name_player = cmd.message.author.display_name,
								name_target = member.display_name,
								hitzone = randombodypart,
							))

						response += "\n\n{}".format(weapon.str_kill.format(
							name_player = cmd.message.author.display_name,
							name_target = member.display_name,
							emote_skull = ewcfg.emote_slimeskull
						))

						if ewcfg.weapon_class_ammo in weapon.classes and weapon_item.item_props.get("ammo") == 0:
							response += "\n" + weapon.str_reload_warning.format(name_player = cmd.message.author.display_name)

						shootee_data.trauma = weapon.id_weapon

					else:
						response = "{name_target} is hit!!\n\n{name_target} has died.".format(name_target = member.display_name)

						shootee_data.trauma = ""

					if slimeoid.life_state == ewcfg.slimeoid_state_active:
						brain = ewcfg.brain_map.get(slimeoid.ai)
						response += "\n\n" + brain.str_kill.format(slimeoid_name = slimeoid.name)

					if shootee_slimeoid.life_state == ewcfg.slimeoid_state_active:
						brain = ewcfg.brain_map.get(shootee_slimeoid.ai)
						response += "\n\n" + brain.str_death.format(slimeoid_name = shootee_slimeoid.name)

					deathreport = "You were {} by {}. {}".format(kill_descriptor, cmd.message.author.display_name, ewcfg.emote_slimeskull)
					deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(member, deathreport)
					
					if coinbounty > 0:
						response += "\n\n SlimeCorp transfers {} SlimeCoin to {}\'s account.".format(str(coinbounty), cmd.message.author.display_name)

					shootee_data.persist()
					user_data.persist()
					resp_cont.add_channel_response(ewcfg.channel_sewers, deathreport)
					resp_cont.add_channel_response(cmd.message.channel.name, response)
					if ewcfg.mutation_id_spontaneouscombustion in shootee_mutations:
						explode_resp = "\n{} spontaneously combusts, horribly dying in a fiery explosion of slime and shrapnel!! Oh, the humanity!".format(member.display_name)
						resp_cont.add_channel_response(cmd.message.channel.name, explode_resp)
						explosion = await ewutils.explode(damage = explode_damage, district_data = district_data)
						resp_cont.add_response_container(explosion)
					user_data = EwUser(member = cmd.message.author)
					shootee_data = EwUser(member = member)
				else:
					# A non-lethal blow!

					if weapon != None:
						if miss:
							response = "{}".format(weapon.str_miss.format(
								name_player = cmd.message.author.display_name,
								name_target = member.display_name
							))
						elif backfire:
							response = "{}".format(weapon.str_backfire.format(
								name_player = cmd.message.author.display_name,
								name_target = member.display_name
							))
						elif jammed:
							response = "{}".format(weapon.str_jammed.format(
								name_player = cmd.message.author.display_name,
								name_target = member.display_name
							))
						else:
							response = weapon.str_damage.format(
								name_player = cmd.message.author.display_name,
								name_target = member.display_name,
								hitzone = randombodypart,
								strikes = strikes
							)
							if crit:
								response += " {}".format(weapon.str_crit.format(
									name_player = cmd.message.author.display_name,
									name_target = member.display_name
								))
							response += " {target_name} loses {damage} slime!".format(
								target_name = member.display_name,
								damage = damage
							)
						
						if ewcfg.weapon_class_ammo in weapon.classes and weapon_item.item_props.get("ammo") == 0:
							response += "\n"+weapon.str_reload_warning.format(name_player = cmd.message.author.display_name)

					else:
						if miss:
							response = "{target_name} dodges your strike.".format(target_name = member.display_name)
						else:
							response = "{target_name} is hit!! {target_name} loses {damage} slime!".format(
								target_name = member.display_name,
								damage = damage
							)

					resp_cont.add_channel_response(cmd.message.channel.name, response)
			else:
				response = 'You are unable to attack {}.'.format(member.display_name)
				resp_cont.add_channel_response(cmd.message.channel.name, response)

			# Add level up text to response if appropriate
			if user_inital_level < user_data.slimelevel:
				resp_cont.add_channel_response(cmd.message.channel.name, "\n" + levelup_response)
			# Team kills don't award slime to the kingpin.
			if user_data.faction != shootee_data.faction:
				# Give slimes to the boss if possible.
				kingpin = ewutils.find_kingpin(id_server = cmd.message.server.id, kingpin_role = role_boss)

				if kingpin:
					kingpin.change_slimes(n = boss_slimes)
					kingpin.persist()

			# Persist every users' data.
			user_data.persist()
			if user_data.weapon > 0:
				weapon_item.persist()

			shootee_data.persist()
			if shootee_data.weapon > 0:
				shootee_weapon = EwItem(id_item = shootee_data.weapon)
				shootee_weapon.item_props["consecutive_hits"] = 0
				shootee_weapon.persist()

			district_data.persist()

			# Assign the corpse role to the newly dead player.
			if was_killed:
				await ewrolemgr.updateRoles(client = cmd.client, member = member)
				# announce death in kill feed channel
				#killfeed_channel = ewutils.get_channel(cmd.message.server, ewcfg.channel_killfeed)
				killfeed_resp = resp_cont.channel_responses[cmd.message.channel.name]
				for r in killfeed_resp:
					resp_cont.add_channel_response(ewcfg.channel_killfeed, r)
				resp_cont.format_channel_response(ewcfg.channel_killfeed, cmd.message.author)
				resp_cont.add_channel_response(ewcfg.channel_killfeed, "`-------------------------`")
				#await ewutils.send_message(cmd.client, killfeed_channel, ewutils.formatMessage(cmd.message.author, killfeed_resp))

			# Send the response to the player.
			resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
		await resp_cont.post()
		
	elif response == ewcfg.enemy_targeted_string:
		#TODO - Move this to it's own function in ewhunting or merge it into the previous code block somehow
		
		# Enemy has been targeted rather than a player
		await attackEnemy(cmd, user_data, weapon, resp_cont, weapon_item, slimeoid, market_data, time_now)
		
	else:
		resp_cont.add_channel_response(cmd.message.channel.name, response)
		resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
		
		await resp_cont.post()

""" player kills themself """
async def suicide(cmd):
	response = ""
	deathreport = ""

	# Only allowed in the combat zone.
	if ewmap.channel_name_is_poi(cmd.message.channel.name) == False:
		response = "You must go into the city to commit {}.".format(cmd.tokens[0][1:])
	else:
		# Get the user data.
		user_data = EwUser(member = cmd.message.author)

		user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
		user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
		user_isgeneral = user_data.life_state == ewcfg.life_state_kingpin
		user_isjuvenile = user_data.life_state == ewcfg.life_state_juvenile
		user_isdead = user_data.life_state == ewcfg.life_state_corpse
		user_isexecutive = user_data.life_state == ewcfg.life_state_executive
		user_islucky = user_data.life_state == ewcfg.life_state_lucky

		if user_isdead:
			response = "Too late for that."
		elif user_isjuvenile:
			response = "Juveniles are too cowardly for suicide."
		elif user_isgeneral:
			response = "\*click* Alas, your gun has jammed."
		elif user_iskillers or user_isrowdys or user_isexecutive or user_islucky:
			#Give slime to challenger if player suicides mid russian roulette
			if user_data.rr_challenger != "":
				response = "You can't do that now"
				return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response)) 
				
			district_data = EwDistrict(district = user_data.poi, id_server = cmd.message.server.id)
			district_data.change_slimes(n = user_data.slimes + user_data.bleed_storage, source = ewcfg.source_killing)
			district_data.persist()

			# Set the id_killer to the player himself, remove his slime and slime poudrins.
			user_data.id_killer = cmd.message.author.id
			user_data.die(cause = ewcfg.cause_suicide)
			user_data.persist()

			# Assign the corpse role to the player. He dead.
			await ewrolemgr.updateRoles(client = cmd.client, member = cmd.message.author)

			response = '{} has willingly returned to the slime. {}'.format(cmd.message.author.display_name, ewcfg.emote_slimeskull)
			deathreport = "You arrive among the dead by your own volition. {}".format(ewcfg.emote_slimeskull)
			deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(cmd.message.author, deathreport)
		else:
			# This should never happen. We handled all the role cases. Just in case.
			response = "\*click* Alas, your gun has jammed."

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	if deathreport != "":
		sewerchannel = ewutils.get_channel(cmd.message.server, ewcfg.channel_sewers)
		await ewutils.send_message(cmd.client, sewerchannel, deathreport)

""" Damage all players in a district; Exploding weapon's effect """
async def weapon_explosion(user_data = None, shootee_data = None, district_data = None, life_states = None, factions = None, slimes_damage = 0, backfire = None, time_now = 0, target_enemy = None):
	if user_data != None and shootee_data != None and district_data != None:
		user_player = EwPlayer(id_user=user_data.id_user, id_server=user_data.id_server)
		if target_enemy == False:
			shootee_player = EwPlayer(id_user=shootee_data.id_user, id_server=shootee_data.id_server)
		else:
			enemy_data = shootee_data
			
			# This makes it so that a display name can still be accessed regardless if a player or enemy is the target of the attack
			shootee_player = shootee_data

		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))

		client = ewutils.get_client()
		server = client.get_server(user_data.id_server)
		
		channel = ewcfg.id_to_poi.get(user_data.poi).channel

		resp_cont = ewutils.EwResponseContainer(id_server=user_data.id_server)

		bystander_users = district_data.get_players_in_district(life_states=life_states, factions=factions)
		bystander_enemies = district_data.get_enemies_in_district()

		for bystander in bystander_users:
			# Don't damage the shooter or the shootee a second time
			
			# If an enemy is being targeted, check id_enemy instead of id_user when going through bystander_users
			checked_id = None
			if target_enemy:
				checked_id = shootee_data.id_enemy
			else:
				checked_id = shootee_data.id_user
			
			if bystander != user_data.id_user and bystander != checked_id:
				response = ""

				target_data = EwUser(id_user=bystander, id_server=user_data.id_server)
				target_player = EwPlayer(id_user=bystander, id_server=user_data.id_server)

				target_iskillers = target_data.life_state == ewcfg.life_state_enlisted and target_data.faction == ewcfg.faction_killers
				target_isrowdys = target_data.life_state == ewcfg.life_state_enlisted and target_data.faction == ewcfg.faction_rowdys
				target_isjuvenile = target_data.life_state == ewcfg.life_state_juvenile	

				role_boss = (ewcfg.role_copkiller if user_data.faction == ewcfg.faction_killers else ewcfg.role_rowdyfucker)
				boss_slimes = 0

				slimes_dropped = target_data.totaldamage + target_data.slimes

				was_killed = False

				if slimes_damage >= shootee_data.slimes - shootee_data.bleed_storage:
					was_killed = True
					
				sewer_data = EwDistrict(district=ewcfg.poi_id_thesewers, id_server=user_data.id_server)

				# move around slime as a result of the shot
				if target_isjuvenile or user_data.faction == target_data.faction:
					slimes_drained = int(3 * slimes_damage / 4) # 3/4
					slimes_toboss = 0
				else:
					slimes_drained = 0
					slimes_toboss = int(slimes_damage / 2)

				damage = str(slimes_damage)
				

				slimes_tobleed = int((slimes_damage - slimes_toboss - slimes_drained) / 2)

				slimes_directdamage = slimes_damage - slimes_tobleed
				slimes_splatter = slimes_damage - slimes_toboss - slimes_tobleed - slimes_drained

				boss_slimes += slimes_toboss
				district_data.change_slimes(n = slimes_splatter, source = ewcfg.source_killing)
				target_data.bleed_storage += slimes_tobleed
				target_data.change_slimes(n = - slimes_directdamage, source = ewcfg.source_damage)
				sewer_data.change_slimes(n = slimes_drained)
				sewer_data.persist()

				if was_killed:
					#adjust statistics
					ewstats.increment_stat(user = user_data, metric = ewcfg.stat_kills)
					ewstats.track_maximum(user = user_data, metric = ewcfg.stat_biggest_kill, value = int(slimes_dropped))
					if user_data.slimelevel > target_data.slimelevel:
						ewstats.increment_stat(user = user_data, metric = ewcfg.stat_lifetime_ganks)
					elif user_data.slimelevel < target_data.slimelevel:
						ewstats.increment_stat(user = user_data, metric = ewcfg.stat_lifetime_takedowns)

					# Collect bounty
					coinbounty = int(target_data.bounty / ewcfg.slimecoin_exchangerate)

					#add bounty
					user_data.add_bounty(n = (target_data.bounty / 2) + (slimes_dropped / 4))

					user_data.change_slimecoin(n = coinbounty, coinsource = ewcfg.coinsource_bounty)

					# Give a bonus to the player's weapon skill for killing a stronger player.
					if target_data.slimelevel >= user_data.slimelevel:
						user_data.add_weaponskill(n = 1, weapon_type = weapon.id_weapon)

					district_data.change_slimes(n = target_data.slimes/2, source = ewcfg.source_killing)
					levelup_resp = user_data.change_slimes(n = target_data.slimes/2, source = ewcfg.source_killing)

					target_data.id_killer = user_data.id_user
					target_data.die(cause = ewcfg.cause_killing)
					target_data.change_slimes(n = -slimes_dropped / 10, source = ewcfg.source_ghostification)
					target_data.persist()

					response += "{} was killed by an explosion during your fight with {}!".format(target_player.display_name, shootee_player.display_name)
					if coinbounty > 0:
						response += "\n\n SlimeCorp transfers {} SlimeCoin to {}\'s account.".format(str(coinbounty), user_player.display_name)

					resp_cont.add_channel_response(channel, response)

					if ewcfg.mutation_id_spontaneouscombustion in target_data.get_mutations():
						
						explode_damage = ewutils.slime_bylevel(target_data.slimelevel) / 5
						
						explode_resp = "\n{} spontaneously combusts, horribly dying in a fiery explosion of slime and shrapnel!! Oh, the humanity!".format(user_player.display_name)
						resp_cont.add_channel_response(channel, explode_resp)
						explosion = await ewutils.explode(damage = explode_damage, district_data = district_data)
						resp_cont.add_response_container(explosion)

					await ewrolemgr.updateRoles(client = client, member = server.get_member(target_data.id_user))
				#Survived the explosion
				else:
					response += "{} was caught in an explosion during your fight with {} and lost {} slime".format(target_player.display_name, shootee_player.display_name, damage)
					resp_cont.add_channel_response(channel, response)
					target_data.persist()

		for bystander in bystander_enemies:
			# Don't damage the shooter or the enemy a second time
			
			if bystander != user_data.id_user and bystander != enemy_data.id_enemy:
				response = ""

				target_enemy_data = EwEnemy(id_enemy=bystander, id_server=user_data.id_server)

				slimes_dropped = target_enemy_data.totaldamage + target_enemy_data.slimes

				was_killed = False

				if slimes_damage >= shootee_data.slimes - shootee_data.bleed_storage:
					was_killed = True

				sewer_data = EwDistrict(district=ewcfg.poi_id_thesewers, id_server=user_data.id_server)

				# move around slime as a result of the shot
				slimes_drained = int(3 * slimes_damage / 4)  # 3/4

				damage = str(slimes_damage)

				slimes_tobleed = int((slimes_damage - slimes_drained) / 2)

				slimes_directdamage = slimes_damage - slimes_tobleed
				slimes_splatter = slimes_damage - slimes_tobleed - slimes_drained

				district_data.change_slimes(n=slimes_splatter, source=ewcfg.source_killing)
				target_enemy_data.bleed_storage += slimes_tobleed
				target_enemy_data.change_slimes(n=- slimes_directdamage, source=ewcfg.source_damage)
				sewer_data.change_slimes(n=slimes_drained)
				sewer_data.persist()

				if was_killed:
					# adjust statistics
					ewstats.increment_stat(user=user_data, metric=ewcfg.stat_kills)
					ewstats.track_maximum(user=user_data, metric=ewcfg.stat_biggest_kill, value=int(slimes_dropped))
					if user_data.slimelevel > target_enemy_data.level:
						ewstats.increment_stat(user=user_data, metric=ewcfg.stat_lifetime_ganks)
					elif user_data.slimelevel < target_enemy_data.level:
						ewstats.increment_stat(user=user_data, metric=ewcfg.stat_lifetime_takedowns)


					# Give a bonus to the player's weapon skill for killing a stronger player.
					if target_enemy_data.level >= user_data.slimelevel:
						user_data.add_weaponskill(n=1, weapon_type=weapon.id_weapon)

					district_data.change_slimes(n=target_enemy_data.slimes / 2, source=ewcfg.source_killing)
					levelup_resp = user_data.change_slimes(n=target_enemy_data.slimes / 2, source=ewcfg.source_killing)

					ewhunting.delete_enemy(target_enemy_data)

					response += "{} was killed by an explosion during your fight with {}!".format(target_enemy_data.display_name, shootee_player.display_name)
					response += "\n\n" + ewhunting.drop_enemy_loot(enemy_data, district_data)
					
					resp_cont.add_channel_response(channel, response)

				# Survived the explosion
				else:
					response += "{} was caught in an explosion during your fight with {} and lost {} slime".format(target_enemy_data.display_name, shootee_player.display_name, damage)
					resp_cont.add_channel_response(channel, response)
					target_enemy_data.persist()

		return resp_cont

""" Player spars with a friendly player to gain slime. """
async def spar(cmd):
	time_now = int(time.time())
	response = ""

	if cmd.message.channel.name != ewcfg.channel_dojo:
		response = "You must go to the dojo to spar."

	elif cmd.mentions_count > 1:
		response = "One sparring partner at a time!"
		
	elif cmd.mentions_count == 1:
		member = cmd.mentions[0]

		if(member.id == cmd.message.author.id):
			response = "How do you expect to spar with yourself?"
		else:
			# Get killing player's info.
			user_data = EwUser(member = cmd.message.author)
			weapon_item = EwItem(id_item = user_data.weapon)

			# Get target's info.
			sparred_data = EwUser(member = member)
			sparred_weapon_item = EwItem(id_item = sparred_data.weapon)

			user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
			user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
			user_isdead = user_data.life_state == ewcfg.life_state_corpse

			if user_data.hunger >= ewutils.hunger_max_bylevel(user_data.slimelevel):
				response = "You are too exhausted to train right now. Go get some grub!"
			elif user_data.poi != ewcfg.poi_id_dojo or sparred_data.poi != ewcfg.poi_id_dojo:
				response = "Both players need to be in the dojo to spar."
			elif sparred_data.hunger >= ewutils.hunger_max_bylevel(sparred_data.slimelevel):
				response = "{} is too exhausted to train right now. They need a snack!".format(member.display_name)
			elif user_isdead == True:
				response = "The dead think they're too cool for conventional combat. Pricks."
			elif user_iskillers == False and user_isrowdys == False:
				# Only killers, rowdys, the cop killer, and the rowdy fucker can spar
				response = "Juveniles lack the backbone necessary for combat."
			else:
				was_juvenile = False
				was_sparred = False
				was_dead = False
				was_player_tired = False
				was_target_tired = False
				was_enemy = False
				duel = False

				#Determine if the !spar is a duel:
				weapon = None
				if user_data.weapon >= 0 and sparred_data.weapon >= 0 and weapon_item.item_props.get("weapon_type") == sparred_weapon_item.item_props.get("weapon_type"):
					weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
					duel = True

				if sparred_data.life_state == ewcfg.life_state_corpse:
					# Target is already dead.
					was_dead = True
				elif (user_data.time_lastspar + ewcfg.cd_spar) > time_now:
					# player sparred too recently
					was_player_tired = True
				elif (sparred_data.time_lastspar + ewcfg.cd_spar) > time_now:
					# taret sparred too recently
					was_target_tired = True
				elif sparred_data.life_state == ewcfg.life_state_juvenile:
					# Target is a juvenile.
					was_juvenile = True

				elif (user_iskillers and (sparred_data.life_state == ewcfg.life_state_enlisted and sparred_data.faction == ewcfg.faction_killers)) or (user_isrowdys and (sparred_data.life_state == ewcfg.life_state_enlisted and sparred_data.faction == ewcfg.faction_rowdys)):
					# User can be sparred.
					was_sparred = True
				elif (user_iskillers and (sparred_data.life_state == ewcfg.life_state_enlisted and sparred_data.faction == ewcfg.faction_rowdys)) or (user_isrowdys and (sparred_data.life_state == ewcfg.life_state_enlisted and sparred_data.faction == ewcfg.faction_killers)):
					# Target is a member of the opposing faction.
					was_enemy = True


				#if the duel is successful
				if was_sparred:
					weaker_player = sparred_data if sparred_data.slimes < user_data.slimes else user_data
					stronger_player = sparred_data if user_data is weaker_player else user_data

					# Weaker player gains slime based on the slime of the stronger player.
					possiblegain = int(ewcfg.slimes_perspar_base * (2.2 ** weaker_player.slimelevel))
					slimegain = min(possiblegain, stronger_player.slimes / 20)
					weaker_player.change_slimes(n = slimegain)
					
					#hunger drain for both players
					user_data.hunger += ewcfg.hunger_perspar * ewutils.hunger_cost_mod(user_data.slimelevel)
					sparred_data.hunger += ewcfg.hunger_perspar * ewutils.hunger_cost_mod(sparred_data.slimelevel)

					# Bonus 50% slime to both players in a duel.
					if duel:
						weaker_player.change_slimes(n = slimegain / 2)
						stronger_player.change_slimes(n = slimegain / 2)

						if weaker_player.weaponskill < 5 or (weaker_player.weaponskill + 1) < stronger_player.weaponskill:
							weaker_player.add_weaponskill(n = 1, weapon_type = weapon.id_weapon)

						if stronger_player.weaponskill < 5 or (stronger_player.weaponskill + 1) < weaker_player.weaponskill:
							stronger_player.add_weaponskill(n = 1, weapon_type = weapon.id_weapon)

					weaker_player.time_lastspar = time_now

					user_data.persist()
					sparred_data.persist()

					# player was sparred with
					if duel and weapon != None:
						response = weapon.str_duel.format(name_player = cmd.message.author.display_name, name_target = member.display_name)
					else:
						response = '{} parries the attack. :knife: {}'.format(member.display_name, ewcfg.emote_slime5)

					#Notify if max skill is reached	
					if weapon != None:
						if user_data.weaponskill >= 5:
							response += ' {} is a master of the {}.'.format(cmd.message.author.display_name, weapon.id_weapon)
						if sparred_data.weaponskill >= 5:
							response += ' {} is a master of the {}.'.format(member.display_name, weapon.id_weapon)

				else:
					if was_dead:
						# target is already dead
						response = '{} is already dead.'.format(member.display_name)
					elif was_target_tired:
						# target has sparred too recently
						response = '{} is too tired to spar right now.'.format(member.display_name)
					elif was_player_tired:
						# player has sparred too recently
						response = 'You are too tired to spar right now.'
					elif was_enemy:
						# target and player are different factions
						response = "You cannot spar with your enemies."
					else:
						#otherwise unkillable
						response = '{} cannot spar now.'.format(member.display_name)
	else:
		response = 'Your fighting spirit is appreciated, but ENDLESS WAR didn\'t understand that name.'

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" equip a weapon """
async def equip(cmd):
	user_data = EwUser(member = cmd.message.author)
	response = ""

	item_search = ewutils.flattenTokenListToString(cmd.tokens[1:])

	item_sought = ewitem.find_item(item_search = item_search, id_user = cmd.message.author.id, id_server = cmd.message.server.id if cmd.message.server is not None else None)

	if item_sought:
		item = EwItem(id_item = item_sought.get("id_item"))

		if item.item_type == ewcfg.it_weapon:
			response = user_data.equip(item)
			user_data.persist()
		else:
			response = "Not a weapon you ignorant juvenile"
	else:
		response = "You don't have one"

	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

""" name a weapon using a slime poudrin """
async def annoint(cmd):
	response = ""

	if cmd.tokens_count < 2:
		response = "Specify a name for your weapon!"
	else:
		annoint_name = cmd.message.content[(len(ewcfg.cmd_annoint)):].strip()

		if len(annoint_name) > 32:
			response = "That name is too long. ({:,}/32)".format(len(annoint_name))
		else:
			user_data = EwUser(member = cmd.message.author)

			poudrin = ewitem.find_item(item_search = "slimepoudrin", id_user = cmd.message.author.id, id_server = cmd.message.server.id if cmd.message.server is not None else None)

			all_weapons = ewitem.inventory(
				id_server = cmd.message.server.id,
				item_type_filter = ewcfg.it_weapon
			)
			for weapon in all_weapons:
				if weapon.get("name") == annoint_name and weapon.get("id_item") != user_data.weapon:
					response = "**ORIGINAL WEAPON NAME DO NOT STEAL.**"
					return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


			if poudrin is None:
				response = "You need a slime poudrin."
			elif user_data.slimes < 100:
				response = "You need more slime."
			elif user_data.weapon < 0:
				response = "Equip a weapon first."
			else:
				# Perform the ceremony.
				user_data.change_slimes(n = -100, source = ewcfg.source_spending)
				weapon_item = EwItem(id_item = user_data.weapon)
				weapon_item.item_props["weapon_name"] = annoint_name
				weapon_item.persist()

				if user_data.weaponskill < 10:
					user_data.add_weaponskill(n = 1, weapon_type = weapon_item.item_props.get("weapon_type"))

				# delete a slime poudrin from the player's inventory
				ewitem.item_delete(id_item = poudrin.get('id_item'))

				user_data.persist()

				response = "You place your weapon atop the poudrin and annoint it with slime. It is now known as {}!\n\nThe name draws you closer to your weapon. The poudrin was destroyed in the process.".format(annoint_name)

	# Send the response to the player.
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))


async def marry(cmd):
	user_data = EwUser(member = cmd.message.author)
	weapon_item = EwItem(id_item = user_data.weapon)
	weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
	display_name = cmd.message.author.display_name
	if weapon != None:
		weapon_name = weapon_item.item_props.get("weapon_name") if len(weapon_item.item_props.get("weapon_name")) > 0 else weapon.str_weapon

	#Checks to make sure you're in the dojo.
	if user_data.poi != ewcfg.poi_id_dojo:
		response = "Do you really expect to just get married on the side of the street in this war torn concrete jungle? No way, you need to see a specialist for this type of thing, someone who can empathize with a man’s love for his arsenal. Maybe someone in the Dojo can help, *hint hint*."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	#Informs you that you cannot be a fucking faggot.
	elif cmd.mentions_count > 0:
		response = "Ewww, gross! You can’t marry another juvenile! That’s just degeneracy, pure and simple. What happened to the old days, where you could put a bullet in someone’s brain for receiving a hug? You people have gone soft on me, I tells ya."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	#Makes sure you have a weapon to marry.
	elif weapon is None:
		response = "How do you plan to get married to your weapon if you aren’t holding any weapon? Goddamn, think these things through, I have to spell out everything for you."
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	#Makes sure you have a displayed rank 6 or higher weapon.
	elif user_data.weaponskill < 10:
		response = "Slow down, Casanova. You do not nearly have a close enough bond with your {} to engage in holy matrimony with it. You’ll need to reach rank 8 mastery or higher to get married.".format(weapon_name)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	#Makes sure you aren't trying to farm the extra weapon mastery ranks by marrying over and over again.
	elif user_data.weaponmarried == True:
		response = "Ah, to recapture the magic of the first nights together… Sadly, those days are far behind you now. You’ve already had your special day, now it’s time to have the same boring days forever. Aren’t you glad you got married??"
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))
	else:
		#Preform the ceremony 2: literally this time
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"You decide it’s finally time to take your relationship with your {} to the next level. You approach the Dojo Master with your plight, requesting his help to circumvent the legal issues of marrying your weapon. He takes a moment to unfurl his brow before letting out a raspy chuckle. He hasn’t been asked to do something like this for a long time, or so he says. You scroll up to the last instance of this flavor text and conclude he must have Alzheimer's or something. Regardless, he agrees.".format(weapon.str_weapon)
		))
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"Departing from the main floor of the Dojo, he rounds a corner and disappears for a few minutes before returning with illegally doctor marriage paperwork and cartoonish blotches of ink on his face and hands to visually communicate the hard work he’s put into the forgeries. You see, this is a form of visual shorthand that artists utilize so they don’t have to explain every beat of their narrative explicitly, but I digress."
		))
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"You express your desire to get things done as soon as possible so that you can stop reading this boring wall of text and return to your busy agenda of murder, and so he prepares to officiate immediately. You stand next to your darling {}, the only object of your affection in this godforsaken city. You shiver with anticipation for the most anticipated in-game event of your ENDLESS WAR career. A crowd of enemy and allied gangsters alike forms around you three as the Dojo Master begins the ceremony...".format(weapon_name)
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"”We are gathered here today to witness the combined union of {} and {}.".format(display_name, weapon_name)
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"Two of the greatest threats in the current metagame. No greater partners, no worse adversaries."
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"Through thick and thin, these two have stood together, fought together, and gained experience points--otherwise known as “EXP”--together."
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"It was not through hours mining or stock exchanges that this union was forged, but through iron and slime."
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"Without the weapon, the wielder would be defenseless, and without the wielder, the weapon would have no purpose."
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"It is this union that we are here today to officially-illegally affirm.”"
		))
		await asyncio.sleep(6)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"He takes a pregnant pause to increase the drama, and allow for onlookers to press 1 in preparation."
		))
		await asyncio.sleep(6)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"“I now pronounce you juvenile and armament!! You may anoint the {}”".format(weapon.str_weapon)
		))
		await asyncio.sleep(3)
		await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(
			cmd.message.author,
			"You begin to tear up, fondly regarding your last kill with your {} that you love so much. You lean down and kiss your new spouse on the handle, anointing an extra two mastery ranks with pure love. It remains completely motionless, because it is an inanimate object. The Dojo Master does a karate chop midair to bookend the entire experience. Sick, you’re married now!".format(weapon_name)
		))

		#Sets their weaponmarried table to true, so that "you are married to" appears instead of "you are wielding" intheir !data, you get an extra two mastery levels, and you can't change your weapon.
		user_data = EwUser(member = cmd.message.author)
		user_data.weaponmarried = True
		user_data.add_weaponskill(n = 2, weapon_type = weapon.id_weapon)
		user_data.persist()
		weapon_item.item_props["married"] = user_data.id_user
		weapon_item.persist()
		return


async def divorce(cmd):
	user_data = EwUser(member = cmd.message.author)
	weapon_item = EwItem(id_item = user_data.weapon)
	weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
	if weapon != None:
		weapon_name = weapon_item.item_props.get("weapon_name") if len(weapon_item.item_props.get("weapon_name")) > 0 else weapon.str_weapon

	#Makes sure you have a partner to divorce.
	if user_data.weaponmarried == False:
		response = "I appreciate your forward thinking attitude, but how do you expect to get a divorce when you haven’t even gotten married yet? Throw your life away first, then we can talk."
	# Checks to make sure you're in the dojo.
	elif user_data.poi != ewcfg.poi_id_dojo:
		response = "As much as it would be satisfying to just chuck your {} down an alley and be done with it, here in civilization we deal with things *maturely.* You’ll have to speak to the guy that got you into this mess in the first place, or at least the guy that allowed you to make the retarded decision in the first place. Luckily for you, they’re the same person, and he’s at the Dojo.".format(weapon.str_weapon)
	else:
		#Unpreform the ceremony
		response = "You decide it’s finally time to end the frankly obviously retarded farce that is your marriage with your {}. Things were good at first, you both wanted the same things out of life. But, that was then and this is now. You reflect briefly on your myriad of woes; the constant bickering, the mundanity of your everyday routine, the total lack of communication. You’re a slave. But, a slave you will be no longer! You know what you must do." \
				"\nYou approach the Dojo Master yet again, and explain to him your troubles. He solemnly nods along to every beat of your explanation. Luckily, he has a quick solution. He rips apart the marriage paperwork he forged last flavor text, and just like that you’re divorced from {}. It receives half of your SlimeCoin in the settlement, a small price to pay for your freedom. You hand over what used to be your most beloved possession and partner to the old man, probably to be pawned off to whatever bumfuck juvie waddles into the Dojo next. You don’t care, you just don’t want it in your data. " \
				"So, yeah. You’re divorced. Damn, that sucks.".format(weapon.str_weapon, weapon_name)

		#You divorce your weapon, discard it, lose it's rank, and loose half your SlimeCoin in the aftermath.
		user_data.weaponmarried = False
		user_data.weapon = -1
		ewutils.weaponskills_set(member = cmd.message.author, weapon = weapon_item.item_props.get("weapon_type"), weaponskill = 0)

		fee = (user_data.slimecoin / 2)
		user_data.change_slimecoin(n = -fee, coinsource = ewcfg.coinsource_revival)

		user_data.persist()

		#delete weapon item
		ewitem.item_delete(id_item = weapon_item.id_item)
	
	await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def reload(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.weapon > 0:
		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
		if ewcfg.weapon_class_ammo in weapon.classes:
			weapon_item.item_props["ammo"] = weapon.clip_size
			weapon_item.persist()
			response = weapon.str_reload
		else:
			response = "What do you think you're going to be reloading with that?"
	else:
		response = "What are you expecting to reload, dumbass? {} a weapon first!".format(ewcfg.cmd_equip)
	
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

async def unjam(cmd):
	user_data = EwUser(member = cmd.message.author)

	if user_data.weapon > 0:
		weapon_item = EwItem(id_item = user_data.weapon)
		weapon = ewcfg.weapon_map.get(weapon_item.item_props.get("weapon_type"))
		if ewcfg.weapon_class_jammable in weapon.classes:
			if weapon_item.item_props.get("jammed") == "True":
				weapon_item.item_props["jammed"] = "False"
				weapon_item.persist()
				response = weapon.str_unjam.format(name_player = cmd.message.author.display_name)
			else:
				response = "Let’s not get ahead of ourselves, there’s nothing clogging with your {weapon} (yet)!!".format(weapon = weapon.id_weapon)
		else:
			response = "What are you trying to do, exactly? Your weapon can’t jam!!"
	else:
		response = "What are you expecting to do, dumbass? {} a weapon first!".format(ewcfg.cmd_equip)
	
	return await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

# Returns the total modifier of all statuses of a certain type and target of a given player
def apply_combat_mods(user_data = None, desired_type = None, target = None):
	if user_data != None and desired_type != None and target != None:

		modifier = 0

		# Get the user's status effects
		user_statuses = user_data.getStatusEffects()
		for status in user_statuses:
			status_flavor = ewcfg.status_effects_def_map.get(status)

			if status_flavor is not None:
				if target == ewcfg.status_effect_target_self:
					if desired_type == ewcfg.status_effect_type_miss:
						modifier += status_flavor.miss_mod_self
					elif desired_type == ewcfg.status_effect_type_crit:
						modifier += status_flavor.crit_mod_self
					elif desired_type == ewcfg.status_effect_type_damage:
						modifier += status_flavor.dmg_mod_self
					
				elif target == ewcfg.status_effect_target_other:
					if desired_type == ewcfg.status_effect_type_miss:
						modifier += status_flavor.miss_mod
					elif desired_type == ewcfg.status_effect_type_crit:
						modifier += status_flavor.crit_mod
					elif desired_type == ewcfg.status_effect_type_damage:
						modifier += status_flavor.dmg_mod

		return modifier
	
async def attackEnemy(cmd, user_data, weapon, resp_cont, weapon_item, slimeoid, market_data, time_now):
	# Get shooting player's info
	if user_data.slimelevel <= 0:
		user_data.slimelevel = 1
		user_data.persist()

	# Get target's info.
	huntedenemy = " ".join(cmd.tokens[1:]).lower()
	enemy_data = ewhunting.find_enemy(huntedenemy, user_data)

	user_mutations = user_data.get_mutations()

	district_data = EwDistrict(district=user_data.poi, id_server=cmd.message.server.id)

	miss = False
	crit = False
	backfire = False
	jammed = False
	strikes = 0
	bystander_damage = 0
	miss_mod = 0
	crit_mod = 0
	dmg_mod = 0

	miss_mod += round(apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_miss, target=ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_miss, target=ewcfg.status_effect_target_other), 2)
	crit_mod += round(apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_crit, target=ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_crit, target=ewcfg.status_effect_target_other), 2)
	dmg_mod += round(apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_damage, target=ewcfg.status_effect_target_self) + apply_combat_mods(user_data=user_data, desired_type=ewcfg.status_effect_type_damage, target=ewcfg.status_effect_target_other), 2)

	slimes_spent = int(ewutils.slime_bylevel(user_data.slimelevel) / 24)
	slimes_damage = int((slimes_spent * 4) * (100 + (user_data.weaponskill * 10)) / 100.0)

	if weapon is None:
		slimes_damage /= 2  # penalty for not using a weapon, otherwise fists would be on par with other weapons
	slimes_dropped = enemy_data.totaldamage + enemy_data.slimes

	slimes_damage += int(slimes_damage * dmg_mod)

	user_iskillers = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_killers
	user_isrowdys = user_data.life_state == ewcfg.life_state_enlisted and user_data.faction == ewcfg.faction_rowdys
	user_isslimecorp = user_data.life_state in [ewcfg.life_state_lucky, ewcfg.life_state_executive]

	# hunger drain
	user_data.hunger += ewcfg.hunger_pershot * ewutils.hunger_cost_mod(user_data.slimelevel)

	# Weaponized flavor text.
	randombodypart = ewcfg.hitzone_list[random.randrange(len(ewcfg.hitzone_list))]

	# Weapon-specific adjustments
	if weapon != None and weapon.fn_effect != None:
		# Build effect container
		ctn = EwEffectContainer(
			miss=miss,
			backfire=backfire,
			crit=crit,
			jammed=jammed,
			slimes_damage=slimes_damage,
			slimes_spent=slimes_spent,
			user_data=user_data,
			weapon_item=weapon_item,
			shootee_data=enemy_data,
			time_now=time_now,
			bystander_damage=bystander_damage,
			miss_mod=miss_mod,
			crit_mod=crit_mod
		)

		# Make adjustments
		if weapon.id_weapon != ewcfg.weapon_id_garrote:
			weapon.fn_effect(ctn)

		# Apply effects for non-reference values
		miss = ctn.miss
		backfire = ctn.backfire
		crit = ctn.crit
		jammed = ctn.jammed
		slimes_damage = ctn.slimes_damage
		slimes_spent = ctn.slimes_spent
		strikes = ctn.strikes
		bystander_damage = ctn.bystander_damage
		# user_data and enemy_data should be passed by reference, so there's no need to assign them back from the effect container.

		weapon_item.item_props['time_lastattack'] = time_now
		weapon_item.persist()

		# Spend slimes, to a minimum of zero
		user_data.change_slimes(n=(-user_data.slimes if slimes_spent >= user_data.slimes else -slimes_spent),
								source=ewcfg.source_spending)

		if weapon.id_weapon == ewcfg.weapon_id_garrote:
			user_data.persist()
			enemy_data.persist()
			response = "You wrap your wire around {}'s neck...\n**...to no avail! {} breaks free with ease!**".format(
				enemy_data.display_name, enemy_data.display_name)
			resp_cont.add_channel_response(cmd.message.channel.name, response)
			resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
			await resp_cont.post()

			user_data = EwUser(member=cmd.message.author)

			# TODO - Make enemies able to be strangled
			# One of the players/enemies died in the meantime
			if user_data.life_state == ewcfg.life_state_corpse or enemy_data.life_state == ewcfg.life_state_corpse:
				return
			else:
				return
		# else:
		# pass
		# enemy_data.persist()

		if weapon.id_weapon == ewcfg.weapon_id_minigun:
			user_data.persist()
			enemy_data.persist()
			response = "You begin revving up your minigun..."
			resp_cont.add_channel_response(cmd.message.channel.name, response)
			resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
			await resp_cont.post()
			await asyncio.sleep(5)
			user_data = EwUser(member=cmd.message.author)

			# One of the users/enemies died in the meantime
			if user_data.life_state == ewcfg.life_state_corpse or enemy_data.life_state == ewcfg.enemy_lifestate_dead:
				return
			# A user/enemy left the district
			if user_data.poi != enemy_data.poi:
				miss = True

		# Remove a bullet from the weapon
		if ewcfg.weapon_class_ammo in weapon.classes:
			weapon_item.item_props['ammo'] = int(weapon_item.item_props.get("ammo")) - 1

		# Remove one item from stack
		if ewcfg.weapon_class_thrown in weapon.classes:
			weapon_item.stack_size -= 1

		if ewcfg.weapon_class_exploding in weapon.classes:
			user_data.persist()
			enemy_data.persist()

			if not miss:
				life_states = [ewcfg.life_state_juvenile, ewcfg.life_state_enlisted]
				bystander_faction = ""
				if user_data.faction == "rowdys":
					bystander_faction = "killers"
				elif user_data.faction == "killers":
					bystander_faction = "rowdys"
				factions = ["", user_data.faction if backfire else bystander_faction]
				# Burn players in district
				if weapon.id_weapon == ewcfg.weapon_id_molotov:
					bystander_users = district_data.get_players_in_district(life_states=life_states, factions=factions)
					# TODO - Make enemies work with molotovs the same way players do.
					for bystander in bystander_users:
						# print(bystander)
						bystander_user_data = EwUser(id_user=bystander, id_server=user_data.id_server)
						bystander_player_data = EwPlayer(id_user=bystander, id_server=user_data.id_server)
						resp = bystander_user_data.applyStatus(id_status=ewcfg.status_burning_id,
															   value=bystander_damage, source=user_data.id_user).format(
							name_player=bystander_player_data.display_name)
						resp_cont.add_channel_response(cmd.message.channel.name, resp)
				# Damage players/enemies in district
				else:
					resp = await weapon_explosion(user_data=user_data, shootee_data=enemy_data,
												  district_data=district_data, life_states=life_states,
												  factions=factions, slimes_damage=bystander_damage, backfire=backfire,
												  time_now=time_now, target_enemy=True)
					resp_cont.add_response_container(resp)

			user_data = EwUser(member=cmd.message.author)

	if miss or backfire or jammed:
		slimes_damage = 0
		weapon_item.item_props["consecutive_hits"] = 0

	# Remove !revive invulnerability.
	user_data.time_lastrevive = 0

	# Lone wolf
	if ewcfg.mutation_id_lonewolf in user_mutations:
		allies_in_district = district_data.get_players_in_district(
			min_level=math.ceil((1 / 10) ** 0.25 * user_data.slimelevel),
			life_states=[ewcfg.life_state_enlisted],
			factions=[user_data.faction]
		)
		if user_data.id_user in allies_in_district:
			allies_in_district.remove(user_data.id_user)

		if len(allies_in_district) == 0:
			slimes_damage *= 1.5

	# Organic fursuit
	if ewcfg.mutation_id_organicfursuit in user_mutations and (
			(market_data.day % 31 == 0 and market_data.clock >= 20)
			or (market_data.day % 31 == 1 and market_data.clock < 6)
	):
		slimes_damage *= 2

	# Social animal
	if ewcfg.mutation_id_socialanimal in user_mutations:
		allies_in_district = district_data.get_players_in_district(
			min_level=math.ceil((1 / 10) ** 0.25 * user_data.slimelevel),
			life_states=[ewcfg.life_state_enlisted],
			factions=[user_data.faction]
		)
		if user_data.id_user in allies_in_district:
			allies_in_district.remove(user_data.id_user)

		slimes_damage *= 1 + 0.1 * len(allies_in_district)

	# Dressed to kill
	if ewcfg.mutation_id_dressedtokill in user_mutations:
		items = ewitem.inventory(
			id_user=cmd.message.author.id,
			id_server=cmd.message.server.id,
			item_type_filter=ewcfg.it_cosmetic
		)

		adorned_items = 0
		for it in items:
			i = EwItem(it.get('id_item'))
			if i.item_props['adorned'] == 'true':
				adorned_items += 1

		if adorned_items >= ewutils.max_adorn_bylevel(user_data.slimelevel):
			slimes_damage *= 2

	# Damage stats
	ewstats.track_maximum(user=user_data, metric=ewcfg.stat_max_hitdealt, value=slimes_damage)
	ewstats.change_stat(user=user_data, metric=ewcfg.stat_lifetime_damagedealt, n=slimes_damage)

	user_inital_level = user_data.slimelevel

	was_killed = False

	if slimes_damage >= enemy_data.slimes - enemy_data.bleed_storage:
		was_killed = True
		if ewcfg.mutation_id_thickerthanblood in user_mutations:
			slimes_damage = 0
		else:
			slimes_damage = max(enemy_data.slimes - enemy_data.bleed_storage, 0)

	sewer_data = EwDistrict(district=ewcfg.poi_id_thesewers, id_server=cmd.message.server.id)
	# move around slime as a result of the shot
	slimes_drained = int(3 * slimes_damage / 4)  # 3/4

	damage = str(slimes_damage)

	slimes_tobleed = int((slimes_damage - slimes_drained) / 2)
	if ewcfg.mutation_id_nosferatu in user_mutations and (market_data.clock < 6 or market_data.clock >= 20):
		slimes_tobleed = 0

	slimes_directdamage = slimes_damage - slimes_tobleed
	slimes_splatter = slimes_damage - slimes_tobleed - slimes_drained

	district_data.change_slimes(n=slimes_splatter, source=ewcfg.source_killing)
	enemy_data.bleed_storage += slimes_tobleed
	enemy_data.change_slimes(n=- slimes_directdamage, source=ewcfg.source_damage)
	sewer_data.change_slimes(n=slimes_drained)
	sewer_data.persist()

	if was_killed:
		# adjust statistics
		ewstats.increment_stat(user=user_data, metric=ewcfg.stat_pve_kills)
		ewstats.track_maximum(user=user_data, metric=ewcfg.stat_biggest_kill, value=int(slimes_dropped))
		if user_data.slimelevel > enemy_data.level:
			ewstats.increment_stat(user=user_data, metric=ewcfg.stat_lifetime_pve_ganks)
		elif user_data.slimelevel < enemy_data.level:
			ewstats.increment_stat(user=user_data, metric=ewcfg.stat_lifetime_pve_takedowns)

		if weapon != None:
			weapon_item.item_props["kills"] = (int(weapon_item.item_props.get("kills")) if weapon_item.item_props.get(
				"kills") != None else 0) + 1
			weapon_item.item_props["totalkills"] = (int(
				weapon_item.item_props.get("totalkills")) if weapon_item.item_props.get(
				"totalkills") != None else 0) + 1
			ewstats.increment_stat(user=user_data, metric=weapon.stat)

		# Give a bonus to the player's weapon skill for killing a stronger enemy.
		if enemy_data.level >= user_data.slimelevel and weapon is not None:
			user_data.add_weaponskill(n=1, weapon_type=weapon.id_weapon)

		# release bleed storage
		if ewcfg.mutation_id_thickerthanblood in user_mutations:
			slimes_todistrict = 0
			slimes_tokiller = enemy_data.slimes
		else:
			slimes_todistrict = enemy_data.slimes / 2
			slimes_tokiller = enemy_data.slimes / 2
		district_data.change_slimes(n=slimes_todistrict, source=ewcfg.source_killing)
		levelup_response = user_data.change_slimes(n=slimes_tokiller, source=ewcfg.source_killing)
		if ewcfg.mutation_id_fungalfeaster in user_mutations:
			user_data.hunger = 0

		# Enemy was killed.
		ewhunting.delete_enemy(enemy_data)

		kill_descriptor = "beaten to death"
		if weapon != None:
			response = weapon.str_damage.format(
				name_player=cmd.message.author.display_name,
				name_target=enemy_data.display_name,
				hitzone=randombodypart,
				strikes=strikes
			)
			kill_descriptor = weapon.str_killdescriptor
			if crit:
				response += " {}".format(weapon.str_crit.format(
					name_player=cmd.message.author.display_name,
					name_target=enemy_data.display_name
				))

			response += "\n\n{}".format(weapon.str_kill.format(
				name_player=cmd.message.author.display_name,
				name_target=enemy_data.display_name,
				emote_skull=ewcfg.emote_slimeskull
			))

			if ewcfg.weapon_class_ammo in weapon.classes and weapon_item.item_props.get("ammo") == 0:
				response += "\n" + weapon.str_reload_warning.format(
					name_player=cmd.message.author.display_name)

		else:
			response = "{name_target} is hit!!\n\n{name_target} has died.".format(
				name_target=enemy_data.display_name)

		# When a raid boss dies, use this response instead so its drops aren't shown in the killfeed
		old_response = response

		# give player item for defeating an enemy
		response += "\n\n" + ewhunting.drop_enemy_loot(enemy_data, district_data)

		if slimeoid.life_state == ewcfg.slimeoid_state_active:
			brain = ewcfg.brain_map.get(slimeoid.ai)
			response += "\n" + brain.str_kill.format(slimeoid_name=slimeoid.name)

		user_data.persist()
		resp_cont.add_channel_response(cmd.message.channel.name, response)
		user_data = EwUser(member=cmd.message.author)
	else:
		# A non-lethal blow!

		if weapon != None:
			if miss:
				response = "{}".format(weapon.str_miss.format(
					name_player=cmd.message.author.display_name,
					name_target=enemy_data.display_name
				))
			elif backfire:
				response = "{}".format(weapon.str_backfire.format(
					name_player=cmd.message.author.display_name,
					name_target=enemy_data.display_name
				))
			elif jammed:
				response = "{}".format(weapon.str_jammed.format(
					name_player=cmd.message.author.display_name,
					name_target=enemy_data.display_name
				))
			else:
				response = weapon.str_damage.format(
					name_player=cmd.message.author.display_name,
					name_target=enemy_data.display_name,
					hitzone=randombodypart,
					strikes=strikes
				)
				if crit:
					response += " {}".format(weapon.str_crit.format(
						name_player=cmd.message.author.display_name,
						name_target=enemy_data.display_name
					))
				response += " {target_name} loses {damage} slime!".format(
					target_name=enemy_data.display_name,
					damage=damage
				)

			if ewcfg.weapon_class_ammo in weapon.classes and weapon_item.item_props.get("ammo") == 0:
				response += "\n" + weapon.str_reload_warning.format(
					name_player=cmd.message.author.display_name)

		else:
			if miss:
				response = "{target_name} dodges your strike.".format(target_name=enemy_data.display_name)
			else:
				response = "{target_name} is hit!! {target_name} loses {damage} slime!".format(
					target_name=enemy_data.display_name,
					damage=damage
				)

		resp_cont.add_channel_response(cmd.message.channel.name, response)

	# Add level up text to response if appropriate
	if user_inital_level < user_data.slimelevel:
		resp_cont.add_channel_response(cmd.message.channel.name, "\n" + levelup_response)
	# Enemy kills don't award slime to the kingpin.

	# Persist user data.
	user_data.persist()
	if user_data.weapon > 0:
		weapon_item.persist()

	district_data.persist()

	# If an enemy is a raidboss, announce that kill in the killfeed
	if was_killed and enemy_data.enemytype in ewcfg.raid_bosses:
		# announce raid boss kill in kill feed channel

		killfeed_resp = "*{}*: {}\n\n".format(cmd.message.author.display_name, old_response)
		killfeed_resp += "`-------------------------`"

		killfeed_resp_cont = ewutils.EwResponseContainer(id_server=cmd.message.server.id)
		killfeed_resp_cont.add_channel_response(ewcfg.channel_killfeed, killfeed_resp)
		await killfeed_resp_cont.post()

		# Send the response to the player.
		resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
		await resp_cont.post()

	else:
		resp_cont.format_channel_response(cmd.message.channel.name, cmd.message.author)
	
		await resp_cont.post()