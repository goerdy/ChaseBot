import asyncio
from logger import logger_newLog
from database import db_getUsers, db_getGamesWithStatus, db_Game_getStartTime, db_Game_getDuration, db_Game_setStatus, db_getHunters, db_getRunners, db_Game_getField
from datetime import datetime, timedelta
from config import conf_getMaxLocationAgeMinutes
from time import time

async def game_updateLocations():
    """Prüft die Standorte aller Spieler in der Datenbank"""
    logger_newLog("debug", "game_updateLocations", "Standort-Update gestartet")
    
    # Hole alle aktiven User aus der Datenbank
    users = db_getUsers()
    
    for user in users:
        user_id, username, first_name, lat, lon, timestamp, role, team, game_id = user
        
        if lat is not None and lon is not None:
            logger_newLog("debug", "game_updateLocations", f"User {username} ({user_id}) hat Standort: {lat}, {lon} (Timestamp: {timestamp})")
            
            # Speichere Standort in locations Tabelle, wenn das Spiel läuft
            if game_id is not None:
                from database import db_Game_getStatus, db_Locations_add
                game_status = db_Game_getStatus(game_id)
                
                # Nur speichern wenn das Spiel läuft (headstart oder running)
                if game_status in ['headstart', 'running']:
                    if db_Locations_add(user_id, game_id, lat, lon):
                        logger_newLog("debug", "game_updateLocations", f"Standort für User {username} ({user_id}) in Spiel {game_id} gespeichert")
                    else:
                        logger_newLog("error", "game_updateLocations", f"Fehler beim Speichern des Standorts für User {username} ({user_id})")
            
            # TODO: Spiellogik basierend auf Standorten
        else:
            logger_newLog("debug", "game_updateLocations", f"User {username} ({user_id}) hat keinen Standort freigegeben")

async def check_player_locations(game_id):
    from database import db_getRunners, db_getHunters, db_Game_getField
    from telegram_bot import TelegramBot
    from datetime import datetime, timedelta
    bot = TelegramBot()
    max_age_min = conf_getMaxLocationAgeMinutes()
    now = datetime.now()
    runners = db_getRunners(game_id)
    hunters = db_getHunters(game_id)
    game = db_Game_getField(game_id)
    gamemaster_id = game[2] if game else None
    outdated_players = []
    for player in list(runners) + list(hunters):
        name = player[1] or f"User_{player[0]}"
        ts = player[5]
        ok = False
        if ts:
            try:
                ts_dt = datetime.fromisoformat(ts)
                if now - ts_dt < timedelta(minutes=max_age_min):
                    ok = True
            except Exception:
                pass
        if not ok:
            outdated_players.append(name)
            try:
                await bot.send_message(player[0], f"❌ Dein Standort ist älter als {max_age_min} Minuten. Bitte aktiviere/aktualisiere deinen Live-Standort!")
            except Exception as e:
                logger_newLog("error", "check_player_locations", f"Fehler beim Senden an {name}: {str(e)}")
    if outdated_players and gamemaster_id:
        try:
            await bot.send_message(gamemaster_id, "⚠️ Folgende Spieler haben keinen aktuellen Standort (<{max_age_min} Minuten):\n" + "\n".join(outdated_players))
        except Exception as e:
            logger_newLog("error", "check_player_locations", f"Fehler beim Senden an Gamemaster: {str(e)}")

async def game_Scheduler():
    last_location_check = 0
    while True:
        logger_newLog("debug", "game_Scheduler", "Scheduler läuft")
        
        # Führe Standort-Updates aus
        await game_updateLocations()

        # --- NEU: Laufende Spiele prüfen ---
        # Prüfe Spiele mit Status 'headstart' oder 'running'
        now_ts = time()
        do_location_check = False
        if now_ts - last_location_check > 60:
            do_location_check = True
            last_location_check = now_ts
        headstart_games = db_getGamesWithStatus("headstart")
        running_games = db_getGamesWithStatus("running")
        # Headstart-Logik
        for game in headstart_games:
            game_id = game[0]
            if do_location_check:
                await check_player_locations(game_id)
            start_time_str = db_Game_getStartTime(game_id)
            headstart_minutes = game[6]  # runner_headstart_minutes
            if start_time_str and headstart_minutes is not None:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    now = datetime.now()
                    if (now - start_time).total_seconds() >= headstart_minutes * 60:
                        db_Game_setStatus(game_id, "running")
                        logger_newLog("info", "game_Scheduler", f"Spiel {game_id}: Headstart vorbei, Status auf 'running' gesetzt.")
                        # Sende Startsignal an Hunter und Runner
                        from database import db_getHunters, db_getRunners
                        from telegram_bot import TelegramBot
                        bot = TelegramBot()
                        hunters = db_getHunters(game_id)
                        runners = db_getRunners(game_id)
                        for hunter in hunters:
                            try:
                                await bot.send_message(hunter[0], "🦊 Du darfst jetzt loslegen! Die Jagd beginnt!")
                            except Exception as e:
                                logger_newLog("error", "game_Scheduler", f"Fehler beim Senden des Hunter-Startsignals an {hunter[0]}: {str(e)}")
                        for runner in runners:
                            try:
                                await bot.send_message(runner[0], "⚠️ Die Hunter sind jetzt unterwegs! Die Jagd beginnt!")
                            except Exception as e:
                                logger_newLog("error", "game_Scheduler", f"Fehler beim Senden des Runner-Startsignals an {runner[0]}: {str(e)}")
                except Exception as e:
                    logger_newLog("error", "game_Scheduler", f"Fehler beim Headstart-Check für Spiel {game_id}: {str(e)}")
        # Running-Logik
        for game in running_games:
            game_id = game[0]
            if do_location_check:
                await check_player_locations(game_id)
            start_time_str = db_Game_getStartTime(game_id)
            duration_minutes = db_Game_getDuration(game_id)
            gamemaster_id = game[2]
            if start_time_str and duration_minutes:
                try:
                    start_time = datetime.fromisoformat(start_time_str)
                    end_time = start_time + timedelta(minutes=duration_minutes)
                    if datetime.now() > end_time:
                        db_Game_setStatus(game_id, "ended")
                        logger_newLog("info", "game_Scheduler", f"Spiel {game_id} ist abgelaufen und wurde auf 'ended' gesetzt.")
                        # Sende Endnachricht an alle Runner, Hunter und Gamemaster
                        from database import db_getHunters, db_getRunners
                        from telegram_bot import TelegramBot
                        bot = TelegramBot()
                        runners = db_getRunners(game_id)
                        hunters = db_getHunters(game_id)
                        end_msg = "🏁 Das Spiel ist beendet! Die Zeit ist abgelaufen."
                        for runner in runners:
                            try:
                                await bot.send_message(runner[0], end_msg)
                            except Exception as e:
                                logger_newLog("error", "game_Scheduler", f"Fehler beim Senden der Endnachricht an Runner {runner[0]}: {str(e)}")
                        for hunter in hunters:
                            try:
                                await bot.send_message(hunter[0], end_msg)
                            except Exception as e:
                                logger_newLog("error", "game_Scheduler", f"Fehler beim Senden der Endnachricht an Hunter {hunter[0]}: {str(e)}")
                        try:
                            await bot.send_message(gamemaster_id, "🏁 Das Spiel ist beendet! Die Zeit ist abgelaufen.\nBitte führe jetzt die Auswertung und ggf. Siegerehrung durch.")
                        except Exception as e:
                            logger_newLog("error", "game_Scheduler", f"Fehler beim Senden der Endnachricht an Gamemaster {gamemaster_id}: {str(e)}")
                        # TODO: Endbehandlung (z.B. Auswertung, Siegerehrung, etc.)
                except Exception as e:
                    logger_newLog("error", "game_Scheduler", f"Fehler beim Zeitvergleich für Spiel {game_id}: {str(e)}")
        # ---
        await asyncio.sleep(5) 