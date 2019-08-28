import time
import random
import math
import asyncio

import ewcfg
import ewutils
import ewitem
import ewrolemgr
import ewstats

from ew import EwUser
from ewitem import EwItem
from ewmarket import EwMarket
from ewplayer import EwPlayer
from ewdistrict import EwDistrict
from ewslimeoid import EwSlimeoid
#from ewstatuseffects import EwEnemyStatusEffect

""" Enemy data model for database persistence """

class EwEnemy:
    id_enemy = 0
    id_server = ""

    # The amount of slime an enemy has
    slimes = 0

    # The total amount of damage an enemy has sustained throughout its lifetime
    totaldamage = 0

    # The type of AI the enemy uses to select which players to attack
    ai = ""

    # The name of enemy shown in responses
    display_name = ""

    # Used to help identify enemies of the same type in a district
    identifier = ""

    # An enemy's level, which determines how much damage it does
    level = 0

    # An enemy's location
    poi = ""

    # Life state 0 = Dead, pending for deletion when it tries its next attack / action
    # Life state 1 = Alive / Activated raid boss
    # Life state 2 = Raid boss pending activation
    life_state = 0

    # Used to determine how much slime an enemy gets, what AI it uses, as well as what weapon it uses.
    enemytype = ""

    # The 'weapon' of an enemy
    attacktype = ""

    # An enemy's bleed storage
    bleed_storage = 0

    # Used for determining when a raid boss should be able to move between districts
    time_lastenter = 0

    # Used to determine how much slime an enemy started out with to create a 'health bar' ( current slime / initial slime )
    initialslimes = 0

    # Enemies despawn when this number reaches 10800 (3 hours)
    lifetime = 0

    # Used by the 'defender' AI to determine who it should retaliate against
    id_target = ""

    # Used by raid bosses to determine when they should activate
    raidtimer = 0
    
    # Determines if an enemy should use its rare variant or not
    rare_status = 0

    """ Load the enemy data from the database. """

    def __init__(self, id_enemy=None, id_server=None, enemytype=None):
        query_suffix = ""

        if id_enemy != None:
            query_suffix = " WHERE id_enemy = '{}'".format(id_enemy)
        else:

            if id_server != None:
                query_suffix = " WHERE id_server = '{}'".format(id_server)
                if enemytype != None:
                    query_suffix += " AND enemytype = '{}'".format(enemytype)

        if query_suffix != "":
            try:
                conn_info = ewutils.databaseConnect()
                conn = conn_info.get('conn')
                cursor = conn.cursor();

                # Retrieve object
                cursor.execute(
                    "SELECT {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {} FROM enemies{}".format(
                        ewcfg.col_id_enemy,
                        ewcfg.col_id_server,
                        ewcfg.col_enemy_slimes,
                        ewcfg.col_enemy_totaldamage,
                        ewcfg.col_enemy_ai,
                        ewcfg.col_enemy_type,
                        ewcfg.col_enemy_attacktype,
                        ewcfg.col_enemy_display_name,
                        ewcfg.col_enemy_identifier,
                        ewcfg.col_enemy_level,
                        ewcfg.col_enemy_poi,
                        ewcfg.col_enemy_life_state,
                        ewcfg.col_enemy_bleed_storage,
                        ewcfg.col_enemy_time_lastenter,
                        ewcfg.col_enemy_initialslimes,
                        ewcfg.col_enemy_lifetime,
                        ewcfg.col_enemy_id_target,
                        ewcfg.col_enemy_raidtimer,
                        ewcfg.col_enemy_rare_status,
                        query_suffix
                    ))
                result = cursor.fetchone();

                if result != None:
                    # Record found: apply the data to this object.
                    self.id_enemy = result[0]
                    self.id_server = result[1]
                    self.slimes = result[2]
                    self.totaldamage = result[3]
                    self.ai = result[4]
                    self.enemytype = result[5]
                    self.attacktype = result[6]
                    self.display_name = result[7]
                    self.identifier = result[8]
                    self.level = result[9]
                    self.poi = result[10]
                    self.life_state = result[11]
                    self.bleed_storage = result[12]
                    self.time_lastenter = result[13]
                    self.initialslimes = result[14]
                    self.lifetime = result[15]
                    self.id_target = result[16]
                    self.raidtimer = result[17]
                    self.rare_status = result[18]

            finally:
                # Clean up the database handles.
                cursor.close()
                ewutils.databaseClose(conn_info)

    """ Save enemy data object to the database. """

    def persist(self):
        try:
            conn_info = ewutils.databaseConnect()
            conn = conn_info.get('conn')
            cursor = conn.cursor();

            # Save the object.
            cursor.execute(
                "REPLACE INTO enemies({}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}, {}) VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)".format(
                    ewcfg.col_id_enemy,
                    ewcfg.col_id_server,
                    ewcfg.col_enemy_slimes,
                    ewcfg.col_enemy_totaldamage,
                    ewcfg.col_enemy_ai,
                    ewcfg.col_enemy_type,
                    ewcfg.col_enemy_attacktype,
                    ewcfg.col_enemy_display_name,
                    ewcfg.col_enemy_identifier,
                    ewcfg.col_enemy_level,
                    ewcfg.col_enemy_poi,
                    ewcfg.col_enemy_life_state,
                    ewcfg.col_enemy_bleed_storage,
                    ewcfg.col_enemy_time_lastenter,
                    ewcfg.col_enemy_initialslimes,
                    ewcfg.col_enemy_lifetime,
                    ewcfg.col_enemy_id_target,
                    ewcfg.col_enemy_raidtimer,
                    ewcfg.col_enemy_rare_status,
                ), (
                    self.id_enemy,
                    self.id_server,
                    self.slimes,
                    self.totaldamage,
                    self.ai,
                    self.enemytype,
                    self.attacktype,
                    self.display_name,
                    self.identifier,
                    self.level,
                    self.poi,
                    self.life_state,
                    self.bleed_storage,
                    self.time_lastenter,
                    self.initialslimes,
                    self.lifetime,
                    self.id_target,
                    self.raidtimer,
                    self.rare_status,
                ))

            conn.commit()
        finally:
            # Clean up the database handles.
            cursor.close()
            ewutils.databaseClose(conn_info)

    # Function that enemies use to attack or otherwise interact with players.
    async def kill(self):

        client = ewutils.get_client()

        last_messages = []
        should_post_resp_cont = True

        enemy_data = self

        time_now = int(time.time())
        resp_cont = ewutils.EwResponseContainer(id_server=enemy_data.id_server)
        district_data = EwDistrict(district=enemy_data.poi, id_server=enemy_data.id_server)
        market_data = EwMarket(id_server=enemy_data.id_server)
        ch_name = ewcfg.id_to_poi.get(enemy_data.poi).channel

        target_data = None
        target_player = None
        target_slimeoid = None

        used_attacktype = None

        if enemy_data.attacktype != ewcfg.enemy_attacktype_unarmed:
            used_attacktype = ewcfg.attack_type_map.get(enemy_data.attacktype)
        else:
            used_attacktype = ewcfg.enemy_attacktype_unarmed

        # Get target's info based on its AI.

        if enemy_data.ai == ewcfg.enemy_ai_coward:
            users = ewutils.execute_sql_query(
                "SELECT {id_user}, {life_state} FROM users WHERE {poi} = %s AND {id_server} = %s AND NOT {life_state} = {life_state_corpse}".format(
                    id_user=ewcfg.col_id_user,
                    life_state=ewcfg.col_life_state,
                    poi=ewcfg.col_poi,
                    id_server=ewcfg.col_id_server,
                    life_state_corpse=ewcfg.life_state_corpse
                ), (
                    enemy_data.poi,
                    enemy_data.id_server
                ))
            if len(users) > 0:
                if random.randrange(100) > 92:
                    response = random.choice(ewcfg.coward_responses)
                    response = response.format(enemy_data.display_name, enemy_data.display_name)
                    resp_cont.add_channel_response(ch_name, response)
        else:
            target_data = get_target_by_ai(enemy_data)

        if check_raidboss_countdown(enemy_data) and enemy_data.life_state == ewcfg.enemy_lifestate_unactivated:
            # Raid boss has activated!
            response = "*The ground quakes beneath your feet as slime begins to pool into one hulking, solidified mass...*" \
                       "\n{} **{} has arrvied! It's level {} and has {} slime!** {}\n".format(
                ewcfg.emote_megaslime,
                enemy_data.display_name,
                enemy_data.level,
                enemy_data.slimes,
                ewcfg.emote_megaslime
            )
            resp_cont.add_channel_response(ch_name, response)

            enemy_data.life_state = ewcfg.enemy_lifestate_alive
            enemy_data.time_lastenter = time_now
            enemy_data.persist()

            target_data = None

        elif check_raidboss_countdown(enemy_data) and enemy_data.life_state == ewcfg.enemy_lifestate_alive:
            # Raid boss attacks.
            pass

        # If a raid boss is currently counting down, delete the previous countdown message to reduce visual clutter.
        elif check_raidboss_countdown(enemy_data) == False:

            target_data = None

            while check_raidboss_countdown(enemy_data) == False:
                timer = (enemy_data.raidtimer - (int(time.time())) + ewcfg.time_raidcountdown)

                if timer < ewcfg.enemy_attack_tick_length and timer != 0:
                    timer = ewcfg.enemy_attack_tick_length

                countdown_response = "A sinister presence is lurking. Time remaining: {} seconds...".format(timer)
                resp_cont.add_channel_response(ch_name, countdown_response)

                try:
                    await asyncio.sleep(ewcfg.enemy_attack_tick_length)
                    await client.delete_message(last_messages[len(last_messages)-1])
                except:
                    pass

                last_messages = await resp_cont.post()

            # Once it exits the loop, delete the final countdown message
            try:
                await asyncio.sleep(ewcfg.enemy_attack_tick_length)
                await client.delete_message(last_messages[len(last_messages) - 1])
            except:
                pass

            # Don't make an attempt to post resp_cont, since it should be emptied out after the loop exit
            should_post_resp_cont = False


        if target_data != None:

            target_player = EwPlayer(id_user=target_data.id_user)
            target_slimeoid = EwSlimeoid(id_user=target_data.id_user)

            server = client.get_server(target_data.id_server)
            # server = discord.Server(id=target_data.id_server)
            # print(target_data.id_server)
            # channel = discord.utils.get(server.channels, name=ch_name)

            # print(server)

            # member = discord.utils.get(channel.server.members, name=target_player.display_name)
            # print(member)
					

            target_mutations = target_data.get_mutations()

            miss = False
            crit = False
            backfire = False
            strikes = 0

            # maybe enemies COULD have weapon skills? could punishes players who die to the same enemy without mining up beforehand
            # slimes_damage = int((slimes_spent * 4) * (100 + (user_data.weaponskill * 10)) / 100.0)

            # since enemies dont use up slime or hunger, this is only used for damage calculation
            slimes_spent = int(ewutils.slime_bylevel(enemy_data.level) / 20 * ewcfg.enemy_attack_tick_length / 2)

            slimes_damage = int(slimes_spent * 4)

            if used_attacktype == ewcfg.enemy_attacktype_unarmed:
                slimes_damage /= 2  # specific to juvies
            if enemy_data.enemytype == ewcfg.enemy_type_microslime:
                slimes_damage *= 20  # specific to microslime

            # Organic Fursuit
            if ewcfg.mutation_id_organicfursuit in target_mutations and (
                    (market_data.day % 31 == 0 and market_data.clock >= 20)
                    or (market_data.day % 31 == 1 and market_data.clock < 6)
            ):
                slimes_damage *= 0.1

            # Fat chance
            if ewcfg.mutation_id_fatchance in target_mutations and target_data.hunger / target_data.get_hunger_max() > 0.5:
                slimes_damage *= 0.75

            slimes_dropped = target_data.totaldamage + target_data.slimes

            target_iskillers = target_data.life_state == ewcfg.life_state_enlisted and target_data.faction == ewcfg.faction_killers
            target_isrowdys = target_data.life_state == ewcfg.life_state_enlisted and target_data.faction == ewcfg.faction_rowdys
            target_isslimecorp = target_data.life_state in [ewcfg.life_state_lucky, ewcfg.life_state_executive]
            target_isjuvie = target_data.life_state == ewcfg.life_state_juvenile
            target_isnotdead = target_data.life_state != ewcfg.life_state_corpse

            if target_data.life_state == ewcfg.life_state_kingpin:
                # Disallow killing generals.
                response = "The {} tries to attack the kingpin, but is taken aback by the sheer girth of their slime.".format(enemy_data.display_name)
                resp_cont.add_channel_response(ch_name, response)

            elif (time_now - target_data.time_lastrevive) < ewcfg.invuln_onrevive:
                # User is currently invulnerable.
                response = "The {} tries to attack {}, but they have died too recently and are immune.".format(
                    enemy_data.display_name,
                    target_player.display_name)
                resp_cont.add_channel_response(ch_name, response)

            # enemies dont fuck with ghosts, ghosts dont fuck with enemies.
            elif (target_iskillers or target_isrowdys or target_isjuvie or target_isslimecorp) and (target_isnotdead):
                was_killed = False
                was_hurt = False

                if target_data.life_state in [ewcfg.life_state_enlisted, ewcfg.life_state_juvenile, ewcfg.life_state_lucky, ewcfg.life_state_executive]:

                    # If a target is being attacked by an enemy with the defender ai, check to make sure it can be hit.
                    if (enemy_data.ai == ewcfg.enemy_ai_defender) and (ewutils.check_defender_targets(target_data, enemy_data) == False):
                        return
                    else:
                        # Target can be hurt by enemies.
                        was_hurt = True

                if was_hurt:
                    # Weaponized flavor text.
                    randombodypart = ewcfg.hitzone_list[random.randrange(len(ewcfg.hitzone_list))]

                    # Attacking-type-specific adjustments
                    if used_attacktype != ewcfg.enemy_attacktype_unarmed and used_attacktype.fn_effect != None:
                        # Build effect container
                        ctn = EwEnemyEffectContainer(
                            miss=miss,
                            backfire=backfire,
                            crit=crit,
                            slimes_damage=slimes_damage,
                            enemy_data=enemy_data,
                            target_data=target_data
                        )

                        # Make adjustments
                        used_attacktype.fn_effect(ctn)

                        # Apply effects for non-reference values
                        miss = ctn.miss
                        backfire = ctn.backfire
                        crit = ctn.crit
                        slimes_damage = ctn.slimes_damage
                        strikes = ctn.strikes

                    # can't hit lucky lucy
                    if target_data.life_state == ewcfg.life_state_lucky:
                        miss = True

                    if miss:
                        slimes_damage = 0

                    enemy_data.persist()
                    target_data = EwUser(id_user = target_data.id_user, id_server = target_data.id_server)


                    if slimes_damage >= target_data.slimes - target_data.bleed_storage:
                        was_killed = True
                        slimes_damage = max(target_data.slimes - target_data.bleed_storage, 0)

                    sewer_data = EwDistrict(district=ewcfg.poi_id_thesewers, id_server=enemy_data.id_server)

                    # move around slime as a result of the shot
                    if target_isjuvie:
                        slimes_drained = int(3 * slimes_damage / 4)  # 3/4
                    else:
                        slimes_drained = 0

                    damage = str(slimes_damage)

                    slimes_tobleed = int((slimes_damage - slimes_drained) / 2)
                    if ewcfg.mutation_id_bleedingheart in target_mutations:
                        slimes_tobleed *= 2

                    slimes_directdamage = slimes_damage - slimes_tobleed
                    slimes_splatter = slimes_damage - slimes_tobleed - slimes_drained

                    district_data.change_slimes(n=slimes_splatter, source=ewcfg.source_killing)
                    target_data.bleed_storage += slimes_tobleed
                    target_data.change_slimes(n=- slimes_directdamage, source=ewcfg.source_damage)
                    sewer_data.change_slimes(n=slimes_drained)

                    if was_killed:

                        # Dedorn player cosmetics
                        ewitem.item_dedorn_cosmetics(id_server=target_data.id_server, id_user=target_data.id_user)
                        # Drop all items into district
                        ewitem.item_dropall(id_server=target_data.id_server, id_user=target_data.id_user)

                        # Give a bonus to the player's weapon skill for killing a stronger player.
                        # if target_data.slimelevel >= user_data.slimelevel and weapon is not None:
                        # enemy_data.add_weaponskill(n = 1, weapon_type = weapon.id_weapon)

                        explode_damage = ewutils.slime_bylevel(target_data.slimelevel) / 5
                        # explode, damaging everyone in the district

                        # release bleed storage
                        slimes_todistrict = target_data.slimes

                        district_data.change_slimes(n=slimes_todistrict, source=ewcfg.source_killing)

                        # Player was killed. Remove its id from enemies with defender ai.
                        enemy_data.id_target = ""
                        target_data.id_killer = enemy_data.id_enemy
                        target_data.die(cause=ewcfg.cause_enemy_killing)
                        #target_data.change_slimes(n=-slimes_dropped / 10, source=ewcfg.source_ghostification)

                        kill_descriptor = "beaten to death"
                        if used_attacktype != ewcfg.enemy_attacktype_unarmed:
                            response = used_attacktype.str_damage.format(
                                name_enemy=enemy_data.display_name,
                                name_target=target_player.display_name,
                                hitzone=randombodypart,
                                strikes=strikes
                            )
                            kill_descriptor = used_attacktype.str_killdescriptor
                            if crit:
                                response += " {}".format(used_attacktype.str_crit.format(
                                    name_enemy=enemy_data.display_name,
                                    name_target=target_player.display_name
                                ))

                            response += "\n\n{}".format(used_attacktype.str_kill.format(
                                name_enemy=enemy_data.display_name,
                                name_target=target_player.display_name,
                                emote_skull=ewcfg.emote_slimeskull
                            ))
                            target_data.trauma = used_attacktype.id_type

                        else:
                            response = "{name_target} is hit!!\n\n{name_target} has died.".format(
                                name_target=target_player.display_name)

                            target_data.trauma = ""

                        if target_slimeoid.life_state == ewcfg.slimeoid_state_active:
                            brain = ewcfg.brain_map.get(target_slimeoid.ai)
                            response += "\n\n" + brain.str_death.format(slimeoid_name=target_slimeoid.name)

                        deathreport = "You were {} by {}. {}".format(kill_descriptor, enemy_data.display_name,
                                                                     ewcfg.emote_slimeskull)
                        deathreport = "{} ".format(ewcfg.emote_slimeskull) + ewutils.formatMessage(target_player, deathreport)

                        target_data.persist()
                        enemy_data.persist()
                        resp_cont.add_channel_response(ewcfg.channel_sewers, deathreport)
                        resp_cont.add_channel_response(ch_name, response)
                        if ewcfg.mutation_id_spontaneouscombustion in target_mutations:
                            import ewwep
                            explode_resp = "\n{} spontaneously combusts, horribly dying in a fiery explosion of slime and shrapnel!! Oh, the humanity!".format(
                                target_player.display_name)
                            resp_cont.add_channel_response(ch_name, explode_resp)
                            explosion = await ewutils.explode(damage=explode_damage, district_data=district_data)
                            resp_cont.add_response_container(explosion)

                        # don't recreate enemy data if enemy was killed in explosion
                        if check_death(enemy_data) == False:
                            enemy_data = EwEnemy(id_enemy=self.id_enemy)

                        target_data = EwUser(id_user = target_data.id_user, id_server = target_data.id_server)
                    else:
                        # A non-lethal blow!

                        if used_attacktype != ewcfg.enemy_attacktype_unarmed:
                            if miss:
                                response = "{}".format(used_attacktype.str_miss.format(
                                    name_enemy=enemy_data.display_name,
                                    name_target=target_player.display_name
                                ))
                            elif backfire:
                                response = "{}".format(used_attacktype.str_backfire.format(
                                    name_enemy = enemy_data.display_name,
                                    name_target = target_player.display_name
                                ))
                            else:
                                response = used_attacktype.str_damage.format(
                                    name_enemy=enemy_data.display_name,
                                    name_target=target_player.display_name,
                                    hitzone=randombodypart,
                                    strikes=strikes
                                )
                                if crit:
                                    response += " {}".format(used_attacktype.str_crit.format(
                                        name_enemy=enemy_data.display_name,
                                        name_target=target_player.display_name
                                    ))
                                response += " {target_name} loses {damage} slime!".format(
                                    target_name=target_player.display_name,
                                    damage=damage
                                )
                        else:
                            if miss:
                                response = "{target_name} dodges the {enemy_name}'s strike.".format(
                                    target_name=target_player.display_name, enemy_name=enemy_data.display_name)
                            else:
                                response = "{target_name} is hit!! {target_name} loses {damage} slime!".format(
                                    target_name=target_player.display_name,
                                    damage=damage
                                )
                        resp_cont.add_channel_response(ch_name, response)
                else:
                    response = '{} is unable to attack {}.'.format(enemy_data.display_name, target_player.display_name)
                    resp_cont.add_channel_response(ch_name, response)

                # Persist user and enemy data.
                if enemy_data.life_state == ewcfg.enemy_lifestate_alive or enemy_data.life_state == ewcfg.enemy_lifestate_unactivated:
                    enemy_data.persist()
                target_data.persist()

                district_data.persist()

                # Assign the corpse role to the newly dead player.
                if was_killed:
                    member = server.get_member(target_data.id_user)
                    await ewrolemgr.updateRoles(client=client, member=member)
                    # announce death in kill feed channel
                    # killfeed_channel = ewutils.get_channel(enemy_data.id_server, ewcfg.channel_killfeed)
                    # killfeed_resp = resp_cont.channel_responses[ch_name]
                    # for r in killfeed_resp:
                    #     resp_cont.add_channel_response(ewcfg.channel_killfeed, r)
                    # resp_cont.format_channel_response(ewcfg.channel_killfeed, enemy_data)
                    # resp_cont.add_channel_response(ewcfg.channel_killfeed, "`-------------------------`")
                # await ewutils.send_message(client, killfeed_channel, ewutils.formatMessage(enemy_data.display_name, killfeed_resp))

        # Send the response to the player.
        resp_cont.format_channel_response(ch_name, enemy_data)
        if should_post_resp_cont:
            await resp_cont.post()

    def move(self):
        resp_cont = ewutils.EwResponseContainer(id_server=self.id_server)

        old_district_response = ""
        new_district_response = ""
        gang_base_response = ""

        try:
            # Raid bosses can only move into the city (capturable districts), never back into the outskirts.
            destinations = ewcfg.poi_neighbors.get(self.poi).intersection(set(ewcfg.capturable_districts))
            if len(destinations) > 0:
                old_poi = self.poi
                new_poi = random.choice(list(destinations))
                self.poi = new_poi
                self.time_lastenter = int(time.time())
                self.id_target = ""

                # print("DEBUG - {} MOVED FROM {} TO {}".format(self.display_name, old_poi, new_poi))

                #new_district = EwDistrict(district=new_poi, id_server=self.id_server)
                #if len(new_district.get_enemies_in_district() > 0:

                # When a raid boss enters a new district, give it a new identifier
                self.identifier = set_identifier(new_poi, self.id_server)

                new_poi_def = ewcfg.id_to_poi.get(new_poi)
                new_ch_name = new_poi_def.channel
                new_district_response = "*A low roar booms throughout the district, as slime on the ground begins to slosh all around.*\n {} **{} has arrived!** {}".format(
                    ewcfg.emote_megaslime,
                    self.display_name,
                    ewcfg.emote_megaslime
                )
                resp_cont.add_channel_response(new_ch_name, new_district_response)

                old_district_response = "{} has moved to {}!".format(self.display_name, new_poi_def.str_name)
                old_poi_def = ewcfg.id_to_poi.get(old_poi)
                old_ch_name = old_poi_def.channel
                resp_cont.add_channel_response(old_ch_name, old_district_response)

                gang_base_response = "There are reports of a powerful enemy roaming around {}.".format(new_poi_def.str_name)
                resp_cont.add_channel_response(ewcfg.channel_rowdyroughhouse, gang_base_response)
                resp_cont.add_channel_response(ewcfg.channel_copkilltown, gang_base_response)
        finally:
            self.persist()
            return resp_cont

    def change_slimes(self, n=0, source=None):
        change = int(n)
        self.slimes += change

        if n < 0:
            change *= -1  # convert to positive number
            if source == ewcfg.source_damage or source == ewcfg.source_bleeding or source == ewcfg.source_self_damage:
                self.totaldamage += change

        self.persist()

# Reskinned version of effect container from ewwep.
class EwEnemyEffectContainer:
    miss = False
    backfire = False
    crit = False
    strikes = 0
    slimes_damage = 0
    enemy_data = None
    target_data = None

    # Debug method to dump out the members of this object.
    def dump(self):
        print(
            "effect:\nmiss: {miss}\ncrit: {crit}\nbackfire: {backfire}\nstrikes: {strikes}\nslimes_damage: {slimes_damage}\nslimes_spent: {slimes_spent}".format(
                miss=self.miss,
                backfire=self.backfire,
                crit=self.crit,
                strikes=self.strikes,
                slimes_damage=self.slimes_damage,
                slimes_spent=self.slimes_spent
            ))

    def __init__(
            self,
            miss=False,
            backfire=False,
            crit=False,
            strikes=0,
            slimes_damage=0,
            slimes_spent=0,
            enemy_data=None,
            target_data=None
    ):
        self.miss = miss
        self.backfire = backfire
        self.crit = crit
        self.strikes = strikes
        self.slimes_damage = slimes_damage
        self.slimes_spent = slimes_spent
        self.enemy_data = enemy_data
        self.target_data = target_data

# Debug command. Could be used for events, perhaps?
async def summon_enemy(cmd):
    author = cmd.message.author

    if not author.server_permissions.administrator:
        return

    time_now = int(time.time())
    response = ""
    user_data = EwUser(member=cmd.message.author)

    enemytype = None
    enemy_location = None
    poi = None
    enemy_slimes = None
    enemy_displayname = None
    enemy_level = None

    if len(cmd.tokens) >= 3:
        enemytype = cmd.tokens[1]
        enemy_location = cmd.tokens[2]
        if len(cmd.tokens) >= 6:
            enemy_slimes = cmd.tokens[3]
            enemy_level = cmd.tokens[4]
            enemy_displayname = " ".join(cmd.tokens[5:])
    
        poi = ewcfg.id_to_poi.get(enemy_location)

    if enemytype != None and poi != None:

        enemy = get_enemy_data(enemytype)

        # Assign enemy attributes that weren't assigned in get_enemy_data
        enemy.id_server = user_data.id_server
        enemy.poi = poi.id_poi
        enemy.level = level_byslime(enemy.slimes)
        enemy.lifetime = time_now
        enemy.identifier = set_identifier(poi.id_poi, user_data.id_server)
        
        # Re-assign rare_status to 0 so custom names don't confuse the dict in ewcfg
        enemy.rare_status = 0
        
        if enemy_slimes != None and enemy_displayname != None and enemy_level != None:
            enemy.initialslimes = enemy_slimes
            enemy.slimes = enemy_slimes
            enemy.display_name = enemy_displayname
            enemy.level = enemy_level

        enemy.persist()

        response = "**DEBUG**: You have summoned **{}**, a level {} enemy of type **{}**. It has {} slime. It spawned in {}.".format(
            enemy.display_name,
            enemy.level,
            enemy.enemytype,
            enemy.slimes,
            enemy.poi
        )
        
    else:
        response = "**DEBUG**: PLEASE RE-SUMMON WITH APPLICABLE TYPING / LOCATION. ADDITIONAL OPTIONS ARE SLIME / LEVEL / DISPLAYNAME"

    await ewutils.send_message(cmd.client, cmd.message.channel, ewutils.formatMessage(cmd.message.author, response))

# Gathers all enemies from the database and has them perform an action
async def enemy_perform_action(id_server):
    enemydata = ewutils.execute_sql_query("SELECT {id_enemy} FROM enemies WHERE id_server = %s".format(
	id_enemy = ewcfg.col_id_enemy
    ), (
	id_server,
    ))
    for row in enemydata:
        enemy = EwEnemy(id_enemy=row[0], id_server=id_server)

        # If an enemy is marked for death or has been alive too long, delete it
        if enemy.life_state == ewcfg.enemy_lifestate_dead or (enemy.lifetime < (int(time.time()) - ewcfg.time_despawn)):
            delete_enemy(enemy)
        else:
            # If an enemy is an activated raid boss, it has a 1/10 chance to move between districts.
            if enemy.enemytype in ewcfg.raid_bosses and enemy.life_state == ewcfg.enemy_lifestate_alive and check_raidboss_movecooldown(enemy):
                if random.randrange(20) == 0:
                    resp_cont = enemy.move()
                    if resp_cont != None:
                        await resp_cont.post()

            # If an enemy is alive, make it peform the kill function.
            resp_cont = await enemy.kill()
            if resp_cont != None:
                await resp_cont.post()

# Spawns an enemy in a randomized outskirt district. If a district is full, it will try again, up to 5 times.
async def spawn_enemy(id_server):
    time_now = int(time.time())
    response = ""
    ch_name = ""
    chosen_poi = ""

    enemies_count = ewcfg.max_enemies
    try_count = 0

    rarity_choice = random.randrange(10000)

    if rarity_choice <= 5000:
        # common enemies
        enemytype = random.choice(ewcfg.common_enemies)
    elif rarity_choice <= 7500:
        # uncommon enemies
        enemytype = random.choice(ewcfg.uncommon_enemies)
    elif rarity_choice <= 9500:
        # rare enemies
        enemytype = random.choice(ewcfg.rare_enemies)
    else:
        # raid bosses
        enemytype = random.choice(ewcfg.raid_bosses)

    # debug manual reassignment
    # enemytype = 'juvie'

    while enemies_count >= ewcfg.max_enemies and try_count < 5:

        potential_chosen_poi = random.choice(ewcfg.outskirts_districts)
        # potential_chosen_poi = 'cratersvilleoutskirts'
        potential_chosen_district = EwDistrict(district=potential_chosen_poi, id_server=id_server)
        enemies_list = potential_chosen_district.get_enemies_in_district()
        enemies_count = len(enemies_list)

        if enemies_count < ewcfg.max_enemies:
            chosen_poi = potential_chosen_poi
            try_count = 5
        else:
            # Enemy couldn't spawn in that district, try again
            try_count += 1

    if enemytype != None and chosen_poi != "":
        enemy = get_enemy_data(enemytype)

        # Assign enemy attributes that weren't assigned in get_enemy_data
        enemy.id_server = id_server
        enemy.level = level_byslime(enemy.slimes)
        enemy.lifetime = time_now
        enemy.initialslimes = enemy.slimes
        enemy.poi = chosen_poi
        enemy.identifier = set_identifier(chosen_poi, id_server)

        enemy.persist()

        if enemytype not in ewcfg.raid_bosses:
            response = "**An enemy draws near!!** It's a level {} {}, and has {} slime.".format(enemy.level, enemy.display_name, enemy.slimes)
        ch_name = ewcfg.id_to_poi.get(enemy.poi).channel

    return response, ch_name

# Finds an enemy based on its regular/shorthand name, or its ID.
def find_enemy(enemy_search=None, user_data=None):
    enemy_found = None
    enemy_search_alias = None
    

    if enemy_search != None:

        for enemy_type in ewcfg.enemy_aliases:
            if enemy_search.lower() in ewcfg.enemy_aliases[enemy_type]:
                enemy_search_alias = enemy_type
                continue

        enemy_search_tokens = enemy_search.split(' ')

        if enemy_search_tokens[len(enemy_search_tokens) - 1].upper() in ewcfg.identifier_letters:
            # user passed in an identifier for a district specific enemy

            searched_identifier = enemy_search_tokens[len(enemy_search_tokens) - 1]

            enemydata = ewutils.execute_sql_query(
                "SELECT {id_enemy} FROM enemies WHERE {poi} = %s AND {identifier} = %s AND {life_state} = 1".format(
                    id_enemy=ewcfg.col_id_enemy,
                    poi=ewcfg.col_enemy_poi,
                    identifier=ewcfg.col_enemy_identifier,
                    life_state=ewcfg.col_enemy_life_state
                ), (
                    user_data.poi,
                    searched_identifier,
                ))

            for row in enemydata:
                enemy = EwEnemy(id_enemy=row[0], id_server=user_data.id_server)
                enemy_found = enemy
                break
        else:
            # last token was a string, identify enemy by name

            enemydata = ewutils.execute_sql_query("SELECT {id_enemy} FROM enemies WHERE {poi} = %s AND {life_state} = 1".format(
                id_enemy=ewcfg.col_id_enemy,
                poi=ewcfg.col_enemy_poi,
                life_state=ewcfg.col_enemy_life_state
            ), (
                user_data.poi,
            ))

            # find the first (i.e. the oldest) item that matches the search
            for row in enemydata:
                enemy = EwEnemy(id_enemy=row[0], id_server=user_data.id_server)
                
                if (enemy.display_name.lower() == enemy_search) or (enemy.enemytype == enemy_search_alias):
                    enemy_found = enemy
                    break

    return enemy_found

# Deletes an enemy the database.
def delete_enemy(enemy_data):
    # print("DEBUG - {} - {} DELETED".format(enemy_data.id_enemy, enemy_data.display_name))
    ewutils.execute_sql_query("DELETE FROM enemies WHERE {id_enemy} = %s".format(
        id_enemy=ewcfg.col_id_enemy
    ), (
        enemy_data.id_enemy,
    ))

# Drops items into the district when an enemy dies.
def drop_enemy_loot(enemy_data, district_data):
    response = ""

    item_counter = 0
    loot_multiplier = 1

    poudrin_dropped = False
    poudrin_amount = 0

    pleb_dropped = False
    pleb_amount = 0

    patrician_dropped = False
    patrician_amount = 0

    crop_dropped = False
    crop_amount = 0

    meat_dropped = False
    meat_amount = 0

    card_dropped = False
    card_amount = 0
    
    drop_chance = None
    drop_min = None
    drop_max = None
    drop_range = None
    
    poudrin_values = None
    pleb_values = None
    patrician_values = None
    crop_values = None
    meat_values = None
    card_values = None
    
    drop_table = ewcfg.enemy_drop_tables[enemy_data.enemytype]
    
    # Go through all the possible drops in the drop table and catch exceptions when necessary
    for item in drop_table:
        try:
            if item["poudrin"]:
                poudrin_values = item["poudrin"]
        except:
            pass
        try:
            if item["pleb"]:
                pleb_values = item["pleb"]
        except:
            pass
        try:
            if item["patrician"]:
                patrician_values = item["patrician"]
        except:
            pass
        try:
            if item["crop"]:
                crop_values = item["crop"]
        except:
            pass
        try:
            if item["meat"]:
                meat_values = item["meat"]
        except:
            pass
        try:
            if item["card"]:
                card_values = item["card"]
        except:
            pass
        
    if poudrin_values != None:
        drop_chance = poudrin_values[0]
        drop_min = poudrin_values[1]
        drop_max = poudrin_values[2]
        
        poudrin_dropped = random.randrange(101) < drop_chance
        
        if poudrin_dropped:
            drop_range = list(range(drop_min, drop_max+1))
            poudrin_amount = random.choice(drop_range)
            
    if pleb_values != None:
        drop_chance = pleb_values[0]
        drop_min = pleb_values[1]
        drop_max = pleb_values[2]
        
        pleb_dropped = random.randrange(101) < drop_chance
        
        if pleb_dropped:
            drop_range = list(range(drop_min, drop_max + 1))
            pleb_amount = random.choice(drop_range)

    if patrician_values != None:
        drop_chance = patrician_values[0]
        drop_min = patrician_values[1]
        drop_max = patrician_values[2]

        patrician_dropped = random.randrange(101) < drop_chance

        if patrician_dropped:
            drop_range = list(range(drop_min, drop_max + 1))
            patrician_amount = random.choice(drop_range)

    if crop_values != None:
        drop_chance = crop_values[0]
        drop_min = crop_values[1]
        drop_max = crop_values[2]

        crop_dropped = random.randrange(101) < drop_chance

        if crop_dropped:
            drop_range = list(range(drop_min, drop_max + 1))
            crop_amount = random.choice(drop_range)

    if meat_values != None:
        drop_chance = meat_values[0]
        drop_min = meat_values[1]
        drop_max = meat_values[2]

        meat_dropped = random.randrange(101) < drop_chance

        if meat_dropped:
            drop_range = list(range(drop_min, drop_max + 1))
            meat_amount = random.choice(drop_range)

    if card_values != None:
        drop_chance = card_values[0]
        drop_min = card_values[1]
        drop_max = card_values[2]

        card_dropped = random.randrange(101) < drop_chance

        if card_dropped:
            drop_range = list(range(drop_min, drop_max + 1))
            card_amount = random.choice(drop_range)

    if pleb_dropped or patrician_dropped:
        cosmetics_list = []

        for result in ewcfg.cosmetic_items_list:
            if result.ingredients == "":
                cosmetics_list.append(result)
            else:
                pass
            
    # Multiply the amount of loot if an enemy is its rare variant
    # Loot is also multiplied for the UFO raid boss, since it's a special case with the increased variety of slime it can have.
    if enemy_data.rare_status == 1:
        loot_multiplier *= 1.5
        
    if enemy_data.enemytype == ewcfg.enemy_type_unnervingfightingoperator:
        if enemy_data.slimes >= 1500000:
            loot_multiplier *= 5
        elif enemy_data.slimes >= 1000000:
            loot_multiplier *= 4
        else:
            loot_multiplier *= 3
        
    poudrin_amount = math.ceil(poudrin_amount * loot_multiplier)
    pleb_amount = math.ceil(pleb_amount * loot_multiplier)
    patrician_amount = math.ceil(patrician_amount * loot_multiplier)
    crop_amount = math.ceil(crop_amount * loot_multiplier)
    meat_amount = math.ceil(meat_amount * loot_multiplier)
    card_amount = math.ceil(card_amount * loot_multiplier)

    # Drops items one-by-one
    if poudrin_dropped:
        item_counter = 0

        while item_counter < poudrin_amount:
            for item in ewcfg.item_list:
                if item.context == "poudrin":
                    ewitem.item_create(
                        item_type=ewcfg.it_item,
                        id_user=district_data.name,
                        id_server=district_data.id_server,
                        item_props={
                            'id_item': item.id_item,
                            'context': item.context,
                            'item_name': item.str_name,
                            'item_desc': item.str_desc,
                        }
                    ),
                    item = EwItem(id_item=item.id_item)
                    item.persist()
            response += "They dropped a slime poudrin!\n"

            item_counter += 1

    if pleb_dropped:
        item_counter = 0

        while item_counter < pleb_amount:
            items = []

            for cosmetic in cosmetics_list:
                if cosmetic.rarity == ewcfg.rarity_plebeian:
                    items.append(cosmetic)

            item = items[random.randint(0, len(items) - 1)]

            ewitem.item_create(
                item_type=ewcfg.it_cosmetic,
                id_user=district_data.name,
                id_server=district_data.id_server,
                item_props={
                    'id_cosmetic': item.id_cosmetic,
                    'cosmetic_name': item.str_name,
                    'cosmetic_desc': item.str_desc,
                    'rarity': item.rarity,
                    'adorned': 'false'
                }
            )
            response += "They dropped a {item_name}!\n".format(item_name=item.str_name)

            item_counter += 1

    if patrician_dropped:
        item_counter = 0

        while item_counter < patrician_amount:
            items = []

            for cosmetic in cosmetics_list:
                if cosmetic.rarity == ewcfg.rarity_patrician:
                    items.append(cosmetic)

            item = items[random.randint(0, len(items) - 1)]

            ewitem.item_create(
                item_type=ewcfg.it_cosmetic,
                id_user=district_data.name,
                id_server=district_data.id_server,
                item_props={
                    'id_cosmetic': item.id_cosmetic,
                    'cosmetic_name': item.str_name,
                    'cosmetic_desc': item.str_desc,
                    'rarity': item.rarity,
                    'adorned': 'false'
                }
            )
            response += "They dropped a {item_name}!\n".format(item_name=item.str_name)

            item_counter += 1

    if crop_dropped:
        item_counter = 0

        while item_counter < crop_amount:

            vegetable = random.choice(ewcfg.vegetable_list)

            ewitem.item_create(
                id_user=district_data.name,
                id_server=district_data.id_server,
                item_type=ewcfg.it_food,
                item_props={
                    'id_food': vegetable.id_food,
                    'food_name': vegetable.str_name,
                    'food_desc': vegetable.str_desc,
                    'recover_hunger': vegetable.recover_hunger,
                    'str_eat': vegetable.str_eat,
                    'time_expir': time.time() + ewcfg.farm_food_expir
                }
            )
            response += "They dropped a bushel of {vegetable_name}!\n".format(vegetable_name=vegetable.str_name)

            item_counter += 1

    # Drop dinoslime meat
    if meat_dropped:
        meat = None
        item_counter = 0

        for food in ewcfg.food_list:
            if food.id_food == ewcfg.item_id_dinoslimemeat:
                meat = food
                
        while item_counter < meat_amount:  
            ewitem.item_create(
                id_user=district_data.name,
                id_server=district_data.id_server,
                item_type=ewcfg.it_food,
                item_props={
                    'id_food': meat.id_food,
                    'food_name': meat.str_name,
                    'food_desc': meat.str_desc,
                    'recover_hunger': meat.recover_hunger,
                    'str_eat': meat.str_eat,
                    'time_expir': time.time() + ewcfg.std_food_expir
                }
            )
            response += "They dropped a piece of meat!\n"
            
            item_counter += 1
    
    # Drop trading cards
    if card_dropped:
        cards = None
        item_counter = 0
        
        for item in ewcfg.item_list:
            if item.id_item == ewcfg.item_id_tradingcardpack:
                cards = item

        while item_counter < card_amount:
            ewitem.item_create(
                id_user=district_data.name,
                id_server=district_data.id_server,
                item_type=ewcfg.it_item,
                item_props={
                    'id_item': cards.id_item,
                    'context': cards.context,
                    'item_name': cards.str_name,
                    'item_desc': cards.str_desc,
                }
            )
            response += "They dropped a pack of trading cards!\n"
            
            item_counter += 1

    if not poudrin_dropped and not pleb_dropped and not patrician_dropped and not crop_dropped and not meat_dropped and not card_dropped:
        response = "They didn't drop anything...\n"

    return response

# Determines what level an enemy is based on their slime count.
def level_byslime(slime):
    return int(abs(slime) ** 0.25)

# Reskinned version of weapon class from ewwep.
class EwAttackType:

    # An name used to identify the attacking type
    id_type = ""

    # Displayed when this weapon is used for a !kill
    str_kill = ""

    # Displayed to the dead victim in the sewers. Brief phrase such as "gunned down" etc.
    str_killdescriptor = ""

    # Displayed when viewing the !trauma of another player.
    str_trauma = ""

    # Displayed when viewing the !trauma of yourself.
    str_trauma_self = ""

    # Displayed when a non-lethal hit occurs.
    str_damage = ""

    # Displayed when an attack backfires
    str_backfire = ""

    # Function that applies the special effect for this weapon.
    fn_effect = None

    # Displayed when a weapon effect causes a critical hit.
    str_crit = ""

    # Displayed when a weapon effect causes a miss.
    str_miss = ""

    def __init__(
            self,
            id_type="",
            str_kill="",
            str_killdescriptor="",
            str_trauma="",
            str_trauma_self="",
            str_damage="",
            fn_effect=None,
            str_crit="",
            str_miss="",
            str_backfire = "",
    ):
        self.id_type = id_type
        self.str_kill = str_kill
        self.str_killdescriptor = str_killdescriptor
        self.str_trauma = str_trauma
        self.str_trauma_self = str_trauma_self
        self.str_damage = str_damage
        self.str_backfire = str_backfire
        self.fn_effect = fn_effect
        self.str_crit = str_crit
        self.str_miss = str_miss
        

# Check if an enemy is dead. Implemented to prevent enemy data from being recreated when not necessary.
def check_death(enemy_data):
    if enemy_data.slimes <= 0 or enemy_data.life_state == ewcfg.enemy_lifestate_dead:
        # delete_enemy(enemy_data)
        return True
    else:
        return False

# Assigns enemies most of their necessary attributes based on their type.
def get_enemy_data(enemy_type):
    enemy = EwEnemy()
    
    rare_status = 0
    if random.randrange(10) == 0:
       rare_status = 1

    enemy.id_server = ""
    enemy.slimes = get_enemy_slime(enemy_type)
    enemy.totaldamage = 0
    enemy.level = 0
    enemy.life_state = ewcfg.enemy_lifestate_alive
    enemy.enemytype = enemy_type
    enemy.bleed_storage = 0
    enemy.time_lastenter = 0
    enemy.initialslimes = 0
    enemy.id_target = ""
    enemy.raidtimer = 0
    enemy.rare_status = rare_status

    # Normal enemies
    if enemy_type == ewcfg.enemy_type_juvie:
        enemy.ai = ewcfg.enemy_ai_coward
        enemy.display_name = ewcfg.enemy_displayname_juvie
        enemy.attacktype = ewcfg.enemy_attacktype_unarmed

    elif enemy_type == ewcfg.enemy_type_microslime:
        enemy.ai = ewcfg.enemy_ai_defender
        enemy.display_name = ewcfg.enemy_displayname_microslime
        enemy.attacktype = ewcfg.enemy_attacktype_unarmed

    elif enemy_type == ewcfg.enemy_type_dinoslime:
        enemy.ai = ewcfg.enemy_ai_attacker_a
        enemy.display_name = ewcfg.enemy_displayname_dinoslime
        enemy.attacktype = ewcfg.enemy_attacktype_fangs

    elif enemy_type == ewcfg.enemy_type_slimeadactyl:
        enemy.ai = ewcfg.enemy_ai_attacker_b
        enemy.display_name = ewcfg.enemy_displayname_slimeadactyl
        enemy.attacktype = ewcfg.enemy_attacktype_talons

    elif enemy_type == ewcfg.enemy_type_desertraider:
        enemy.ai = ewcfg.enemy_ai_attacker_b
        enemy.display_name = ewcfg.enemy_displayname_desertraider
        enemy.attacktype = ewcfg.enemy_attacktype_raiderscythe

    elif enemy_type == ewcfg.enemy_type_mammoslime:
        enemy.ai = ewcfg.enemy_ai_defender
        enemy.display_name = ewcfg.enemy_displayname_mammoslime
        enemy.attacktype = ewcfg.enemy_attacktype_tusks

    # Raid bosses
    elif enemy_type == ewcfg.enemy_type_megaslime:
        enemy.ai = ewcfg.enemy_ai_attacker_a
        enemy.display_name = ewcfg.enemy_displayname_megaslime
        enemy.attacktype = ewcfg.enemy_attacktype_gunkshot

    elif enemy_type == ewcfg.enemy_type_slimeasaurusrex:
        enemy.ai = ewcfg.enemy_ai_attacker_b
        enemy.display_name = ewcfg.enemy_displayname_slimeasaurusrex
        enemy.attacktype = ewcfg.enemy_attacktype_fangs
        
    elif enemy_type == ewcfg.enemy_type_greeneyesslimedragon:
        enemy.ai = ewcfg.enemy_ai_attacker_a
        enemy.display_name = ewcfg.enemy_displayname_greeneyesslimedragon
        enemy.attacktype = ewcfg.enemy_attacktype_molotovbreath
        
    elif enemy_type == ewcfg.enemy_type_unnervingfightingoperator:
        enemy.ai = ewcfg.enemy_ai_attacker_b
        enemy.display_name = ewcfg.enemy_displayname_unnervingfightingoperator
        enemy.attacktype = ewcfg.enemy_attacktype_raiderrifle
        
    if enemy_type in ewcfg.raid_bosses:
        enemy.life_state = ewcfg.enemy_lifestate_unactivated
        enemy.raidtimer = int(time.time())
        
    if rare_status == 1:
        enemy.display_name = ewcfg.rare_display_names[enemy.display_name]
        enemy.slimes *= 2

    return enemy

# Returns a randomized amount of slime based on enemy type
def get_enemy_slime(enemy_type):
    slime = 0
    if enemy_type == ewcfg.enemy_type_juvie:
        slime = ((random.randrange(40000) + 10000) + 1)
    elif enemy_type == ewcfg.enemy_type_microslime:
        slime = 10000
    elif enemy_type == ewcfg.enemy_type_dinoslime:
        slime = ((random.randrange(250000) + 250000) + 1)
    elif enemy_type == ewcfg.enemy_type_slimeadactyl:
        slime = ((random.randrange(250000) + 500000) + 1)
    elif enemy_type == ewcfg.enemy_type_desertraider:
        slime = ((random.randrange(500000) + 250000) + 1)
    elif enemy_type == ewcfg.enemy_type_mammoslime:
        slime = ((random.randrange(300000) + 600000) + 1)
    elif enemy_type == ewcfg.enemy_type_megaslime:
        slime = 1000000
    elif enemy_type == ewcfg.enemy_type_slimeasaurusrex:
        slime = ((random.randrange(500000) + 1000000) + 1)
    elif enemy_type == ewcfg.enemy_type_greeneyesslimedragon:
        slime = ((random.randrange(500000) + 1250000) + 1)
    elif enemy_type ==  ewcfg.enemy_type_unnervingfightingoperator:
        slime = ((random.randrange(1500000) + 500000) + 1)
    return slime

# Selects which non-ghost user to attack based on certain parameters.
def get_target_by_ai(enemy_data):

    target_data = None

    time_now = int(time.time())

    # If a player's time_lastenter is less than this value, it can be attacked.
    targettimer = time_now - ewcfg.time_enemyaggro

    if enemy_data.ai == ewcfg.enemy_ai_defender:
        if enemy_data.id_target != "":
            target_data = EwUser(id_user=enemy_data.id_target, id_server=enemy_data.id_server)

    elif enemy_data.ai == ewcfg.enemy_ai_attacker_a:
        users = ewutils.execute_sql_query(
            "SELECT {id_user}, {life_state}, {time_lastenter} FROM users WHERE {poi} = %s AND {id_server} = %s AND {time_lastenter} < {targettimer} AND NOT {life_state} = {life_state_corpse} ORDER BY {time_lastenter} ASC".format(
                id_user=ewcfg.col_id_user,
                life_state=ewcfg.col_life_state,
                time_lastenter=ewcfg.col_time_lastenter,
                poi=ewcfg.col_poi,
                id_server=ewcfg.col_id_server,
                targettimer=targettimer,
                life_state_corpse=ewcfg.life_state_corpse
            ), (
                enemy_data.poi,
                enemy_data.id_server
            ))
        if len(users) > 0:
            target_data = EwUser(id_user=users[0][0], id_server=enemy_data.id_server)

    elif enemy_data.ai == ewcfg.enemy_ai_attacker_b:
        users = ewutils.execute_sql_query(
            "SELECT {id_user}, {life_state}, {slimes} FROM users WHERE {poi} = %s AND {id_server} = %s AND {time_lastenter} < {targettimer} AND NOT {life_state} = {life_state_corpse} ORDER BY {slimes} DESC".format(
                id_user=ewcfg.col_id_user,
                life_state=ewcfg.col_life_state,
                slimes=ewcfg.col_slimes,
                poi=ewcfg.col_poi,
                id_server=ewcfg.col_id_server,
                time_lastenter=ewcfg.col_time_lastenter,
                targettimer=targettimer,
                life_state_corpse=ewcfg.life_state_corpse
            ), (
                enemy_data.poi,
                enemy_data.id_server
            ))
        if len(users) > 0:
            target_data = EwUser(id_user=users[0][0], id_server=enemy_data.id_server)

    return target_data

# Check if raidboss is ready to attack / be attacked
def check_raidboss_countdown(enemy_data):
    time_now = int(time.time())

    # Wait for raid bosses
    if enemy_data.enemytype in ewcfg.raid_bosses and enemy_data.raidtimer <= time_now - ewcfg.time_raidcountdown:
        # Raid boss has activated!
        return True
    elif enemy_data.enemytype in ewcfg.raid_bosses and enemy_data.raidtimer > time_now - ewcfg.time_raidcountdown:
        # Raid boss hasn't activated.
        return False

def check_raidboss_movecooldown(enemy_data):
    time_now = int(time.time())

    if enemy_data.enemytype in ewcfg.raid_bosses and enemy_data.time_lastenter <= time_now - ewcfg.time_raidboss_movecooldown:
        # Raid boss can move
        return True
    elif enemy_data.enemytype in ewcfg.raid_bosses and enemy_data.time_lastenter > time_now - ewcfg.time_raidboss_movecooldown:
        # Raid boss can't move yet
        return False

# Gives enemy an identifier so it's easier to pick out in a crowd of enemies
def set_identifier(poi, id_server):
    district = EwDistrict(district=poi, id_server=id_server)
    enemies_list = district.get_enemies_in_district()

    # A list of identifiers from enemies in a district
    enemy_identifiers = []

    new_identifier = ewcfg.identifier_letters[0]

    if len(enemies_list) > 0:
        for enemy_id in enemies_list:
            enemy = EwEnemy(id_enemy=enemy_id)
            enemy_identifiers.append(enemy.identifier)

        # Sort the list of identifiers alphabetically
        enemy_identifiers.sort()

        for checked_enemy_identifier in enemy_identifiers:
            # If the new identifier matches one from the list of enemy identifiers, give it the next applicable letter
            # Repeat until a unique identifier is given
            if new_identifier == checked_enemy_identifier:
                next_letter = (ewcfg.identifier_letters.index(checked_enemy_identifier) + 1)
                new_identifier = ewcfg.identifier_letters[next_letter]
            else:
                continue

    return new_identifier


