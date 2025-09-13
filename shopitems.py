from logger import logger_newLog
from database import db_getRunners, db_getHunters, db_getTeamMembers, db_Wallet_get_available_items, db_Wallet_decrement_item

# Runner Shop Items
async def ShopItemRunner1(bot, chat_id, user_id, username, game_id):
    """Runner Shop Item 1 - RADAR PING: Zeigt Entfernung zu allen Huntern"""
    logger_newLog("info", "ShopItemRunner1", f"Runner Item 1 (RADAR PING) von {username} ({user_id}) in Spiel {game_id} aktiviert")
    
    # Hole verfügbare Anzahl für Nachricht
    available_items = db_Wallet_get_available_items(game_id, "runner", str(user_id))
    current_count = available_items.get("1", 0)
    
    # Hole aktuelle Position des Runners
    from database import db_getUserPosition
    runner_position = db_getUserPosition(user_id)
    
    if not runner_position or runner_position[3] is None or runner_position[4] is None:
        await bot.send_message(chat_id, f"❌ **RADAR PING konnte nicht gesendet werden!**\n\nDu musst deinen Live-Standort aktiviert haben, um einen Radar Ping zu senden.")
        return
    
    runner_lat = runner_position[3]
    runner_lon = runner_position[4]
    
    # Hole alle Hunter und berechne Entfernungen
    from database import db_getHunters, db_POI_add
    from geofunctions import calculate_distance
    hunters = db_getHunters(game_id)
    
    if not hunters:
        await bot.send_message(chat_id, f"📡 **RADAR PING gesendet!**\n\nKeine Hunter im Spiel gefunden.\n📦 **Verfügbare Pings:** {current_count}")
        return
    
    # Berechne Entfernungen zu allen Huntern und erstelle POI-Einträge
    hunter_distances = []
    for hunter in hunters:
        hunter_user_id, hunter_username, hunter_team, hunter_lat, hunter_lon, hunter_timestamp = hunter
        
        if hunter_lat is not None and hunter_lon is not None:
            distance = calculate_distance(runner_lat, runner_lon, hunter_lat, hunter_lon)
            hunter_distances.append(distance)
            
            # Erstelle POI-Eintrag für diese Entfernung
            # Verwende die Position des Runners als POI-Position
            # Die Entfernung wird als range_meters gespeichert
            db_POI_add(
                game_id=game_id,
                poi_type="RADARPING",
                lat=runner_lat,
                lon=runner_lon,
                range_meters=int(distance),  # Entfernung als range_meters
                team=None,  # Runner haben kein Team
                creator_id=user_id
            )
    
    # Sortiere nach Entfernung (nächster zuerst)
    hunter_distances.sort()
    
    # Erstelle Nachricht für den Runner
    runner_message = f"📡 **RADAR PING von dir gesendet!**\n\n"
    runner_message += f"📍 **Sender-Position:** {runner_lat:.6f}, {runner_lon:.6f}\n\n"
    
    if hunter_distances:
        runner_message += "**Entfernungen zu Huntern:**\n"
        for i, distance in enumerate(hunter_distances, 1):
            runner_message += f"{i}. Hunter: {distance:.1f}m\n"
    else:
        runner_message += "❌ Keine Hunter mit aktuellem Standort gefunden.\n"
    
    runner_message += f"\n📦 **Verfügbare Pings:** {current_count}"
    
    # Sende Nachricht an den Runner
    await bot.send_message(chat_id, runner_message)
    
    # Benachrichtige alle Hunter über den Ping (nur Entfernung)
    for hunter in hunters:
        hunter_user_id, hunter_username, hunter_team, hunter_lat, hunter_lon, hunter_timestamp = hunter
        
        if hunter_lat is not None and hunter_lon is not None:
            distance = calculate_distance(runner_lat, runner_lon, hunter_lat, hunter_lon)
            
            hunter_message = f"📡 **Du wurdest von einem RADAR PING erfasst!**\n\n"
            hunter_message += f"📏 **Entfernung zum Sender:** {distance:.1f}m\n\n"
            hunter_message += "⚠️ Ein Runner kennt jetzt deine ungefähre Position!"
            
            try:
                await bot.send_message(hunter_user_id, hunter_message)
            except Exception as e:
                logger_newLog("error", "ShopItemRunner1", f"Fehler beim Benachrichtigen von Hunter {hunter_user_id}: {str(e)}")
    
    # Benachrichtige den Gamemaster
    from database import db_Game_getField
    game = db_Game_getField(game_id)
    if game:
        gamemaster_id = game[2]
        gamemaster_message = f"📡 **RADAR PING von Runner {username} ({user_id}) gesendet!**\n\n"
        gamemaster_message += f"📍 **Sender-Position:** {runner_lat:.6f}, {runner_lon:.6f}\n\n"
        
        if hunter_distances:
            gamemaster_message += "**Entfernungen zu Huntern:**\n"
            for i, distance in enumerate(hunter_distances, 1):
                gamemaster_message += f"{i}. Hunter: {distance:.1f}m\n"
        else:
            gamemaster_message += "❌ Keine Hunter mit aktuellem Standort gefunden.\n"
        
        try:
            await bot.send_message(gamemaster_id, gamemaster_message)
        except Exception as e:
            logger_newLog("error", "ShopItemRunner1", f"Fehler beim Benachrichtigen des Gamemasters {gamemaster_id}: {str(e)}")
    
    logger_newLog("info", "ShopItemRunner1", f"Radar Ping von Runner {username} ({user_id}) gesendet - {len(hunter_distances)} Hunter erfasst, {len(hunter_distances)} POI-Einträge erstellt")

async def ShopItemRunner2(bot, chat_id, user_id, username, game_id):
    """Runner Shop Item 2 - RADAR PING: Zeigt Entfernung zu allen Huntern (ohne Entfernungsangabe an Hunter)"""
    logger_newLog("info", "ShopItemRunner2", f"Runner Item 2 (RADAR PING) von {username} ({user_id}) in Spiel {game_id} aktiviert")
    
    # Hole verfügbare Anzahl für Nachricht
    available_items = db_Wallet_get_available_items(game_id, "runner", str(user_id))
    current_count = available_items.get("2", 0)
    
    # Hole aktuelle Position des Runners
    from database import db_getUserPosition
    runner_position = db_getUserPosition(user_id)
    
    if not runner_position or runner_position[3] is None or runner_position[4] is None:
        await bot.send_message(chat_id, f"❌ **RADAR PING konnte nicht gesendet werden!**\n\nDu musst deinen Live-Standort aktiviert haben, um einen Radar Ping zu senden.")
        return
    
    runner_lat = runner_position[3]
    runner_lon = runner_position[4]
    
    # Hole alle Hunter und berechne Entfernungen
    from database import db_getHunters, db_POI_add
    from geofunctions import calculate_distance
    hunters = db_getHunters(game_id)
    
    if not hunters:
        await bot.send_message(chat_id, f"📡 **RADAR PING gesendet!**\n\nKeine Hunter im Spiel gefunden.\n📦 **Verfügbare Pings:** {current_count}")
        return
    
    # Berechne Entfernungen zu allen Huntern und erstelle POI-Einträge
    hunter_distances = []
    for hunter in hunters:
        hunter_user_id, hunter_username, hunter_team, hunter_lat, hunter_lon, hunter_timestamp = hunter
        
        if hunter_lat is not None and hunter_lon is not None:
            distance = calculate_distance(runner_lat, runner_lon, hunter_lat, hunter_lon)
            hunter_distances.append(distance)
            
            # Erstelle POI-Eintrag für diese Entfernung
            # Verwende die Position des Runners als POI-Position
            # Die Entfernung wird als range_meters gespeichert
            db_POI_add(
                game_id=game_id,
                poi_type="RADARPING",
                lat=runner_lat,
                lon=runner_lon,
                range_meters=int(distance),  # Entfernung als range_meters
                team=None,  # Runner haben kein Team
                creator_id=user_id
            )
    
    # Sortiere nach Entfernung (nächster zuerst)
    hunter_distances.sort()
    
    # Erstelle Nachricht für den Runner
    runner_message = f"📡 **RADAR PING von dir gesendet!**\n\n"
    runner_message += f"📍 **Sender-Position:** {runner_lat:.6f}, {runner_lon:.6f}\n\n"
    
    if hunter_distances:
        runner_message += "**Entfernungen zu Huntern:**\n"
        for i, distance in enumerate(hunter_distances, 1):
            runner_message += f"{i}. Hunter: {distance:.1f}m\n"
    else:
        runner_message += "❌ Keine Hunter mit aktuellem Standort gefunden.\n"
    
    runner_message += f"\n📦 **Verfügbare Pings:** {current_count}"
    
    # Sende Nachricht an den Runner
    await bot.send_message(chat_id, runner_message)
    
    # Benachrichtige alle Hunter über den Ping (ohne Entfernungsangabe)
    for hunter in hunters:
        hunter_user_id, hunter_username, hunter_team, hunter_lat, hunter_lon, hunter_timestamp = hunter
        
        if hunter_lat is not None and hunter_lon is not None:
            hunter_message = f"📡 **Du wurdest von einem RADAR PING erfasst!**\n\n"
            hunter_message += "⚠️ Ein Runner kennt jetzt deine ungefähre Position!"
            
            try:
                await bot.send_message(hunter_user_id, hunter_message)
            except Exception as e:
                logger_newLog("error", "ShopItemRunner2", f"Fehler beim Benachrichtigen von Hunter {hunter_user_id}: {str(e)}")
    
    # Benachrichtige den Gamemaster
    from database import db_Game_getField
    game = db_Game_getField(game_id)
    if game:
        gamemaster_id = game[2]
        gamemaster_message = f"📡 **RADAR PING von Runner {username} ({user_id}) gesendet!**\n\n"
        gamemaster_message += f"📍 **Sender-Position:** {runner_lat:.6f}, {runner_lon:.6f}\n\n"
        
        if hunter_distances:
            gamemaster_message += "**Entfernungen zu Huntern:**\n"
            for i, distance in enumerate(hunter_distances, 1):
                gamemaster_message += f"{i}. Hunter: {distance:.1f}m\n"
        else:
            gamemaster_message += "❌ Keine Hunter mit aktuellem Standort gefunden.\n"
        
        try:
            await bot.send_message(gamemaster_id, gamemaster_message)
        except Exception as e:
            logger_newLog("error", "ShopItemRunner2", f"Fehler beim Benachrichtigen des Gamemasters {gamemaster_id}: {str(e)}")
    
    logger_newLog("info", "ShopItemRunner2", f"Radar Ping von Runner {username} ({user_id}) gesendet - {len(hunter_distances)} Hunter erfasst, {len(hunter_distances)} POI-Einträge erstellt")

async def ShopItemRunner3(bot, chat_id, user_id, username, game_id):
    """Runner Shop Item 3 - Noch nicht implementiert"""
    logger_newLog("info", "ShopItemRunner3", f"Runner Item 3 von {username} ({user_id}) in Spiel {game_id} versucht zu aktivieren - NICHT IMPLEMENTIERT")
    
    await bot.send_message(chat_id, f"❌ **Diese Funktion ist noch nicht implementiert!**\n\nDiese Funktion wird in einer zukünftigen Version verfügbar sein.\n\n💰 **Kein Geld wurde abgezogen.**")
    
    # Return False um zu signalisieren, dass die Aktivierung fehlgeschlagen ist
    # Dadurch wird kein Geld abgezogen und keine Items reduziert
    return False

async def ShopItemRunner4(bot, chat_id, user_id, username, game_id):
    """Runner Shop Item 4 - ALL OR NOTHING: Noch nicht implementiert"""
    logger_newLog("info", "ShopItemRunner4", f"Runner Item 4 (ALL OR NOTHING) von {username} ({user_id}) in Spiel {game_id} versucht zu aktivieren - NICHT IMPLEMENTIERT")
    
    await bot.send_message(chat_id, f"❌ **ALL OR NOTHING ist noch nicht implementiert!**\n\nDiese Funktion wird in einer zukünftigen Version verfügbar sein.\n\n💰 **Kein Geld wurde abgezogen.**")
    
    # Return False um zu signalisieren, dass die Aktivierung fehlgeschlagen ist
    # Dadurch wird kein Geld abgezogen und keine Items reduziert
    return False

# Hunter Shop Items
async def ShopItemHunter1(bot, chat_id, user_id, username, game_id, team):
    """Hunter Shop Item 1 - TRAP Funktion: Erstellt eine Falle an der aktuellen Position"""
    logger_newLog("info", "ShopItemHunter1", f"Hunter Item 1 (TRAP) von {username} ({user_id}) für Team {team} in Spiel {game_id} aktiviert")
    
    # Hole verfügbare Anzahl für Nachricht
    available_items = db_Wallet_get_available_items(game_id, "hunter", team)
    current_count = available_items.get("1", 0)
    
    # Hole aktuelle Position des Hunters
    from database import db_getUserPosition
    user_position = db_getUserPosition(user_id)
    
    if not user_position or user_position[3] is None or user_position[4] is None:
        await bot.send_message(chat_id, f"❌ **TRAP konnte nicht erstellt werden!**\n\nDu musst deinen Live-Standort aktiviert haben, um eine Falle zu platzieren.")
        return
    
    lat = user_position[3]
    lon = user_position[4]
    
    # Erstelle POI (Falle) in der Datenbank
    from database import db_POI_add
    if db_POI_add(game_id, "TRAP", lat, lon, team=team, creator_id=user_id):
        await bot.send_message(chat_id, f"🎁 **TRAP erfolgreich erstellt!**\n\n📍 **Position:** {lat:.6f}, {lon:.6f}\n🎯 **Team:** {team}\n📦 **Verfügbare Fallen:** {current_count}")
        
        # Benachrichtige Teammitglieder
        await notify_team_members(bot, game_id, team, f"🪤 **{username}** hat eine Falle bei {lat:.6f}, {lon:.6f} erstellt!", exclude_user_id=user_id)
    else:
        await bot.send_message(chat_id, f"❌ **Fehler beim Erstellen der TRAP!**\n\nBitte versuche es später erneut.")

async def ShopItemHunter2(bot, chat_id, user_id, username, game_id, team):
    """Hunter Shop Item 2 - WATCHTOWER: Erstellt einen Wachturm an der aktuellen Position"""
    logger_newLog("info", "ShopItemHunter2", f"Hunter Item 2 (WATCHTOWER) von {username} ({user_id}) für Team {team} in Spiel {game_id} aktiviert")
    
    # Hole verfügbare Anzahl für Nachricht
    available_items = db_Wallet_get_available_items(game_id, "hunter", team)
    current_count = available_items.get("2", 0)
    
    # Hole aktuelle Position des Hunters
    from database import db_getUserPosition
    user_position = db_getUserPosition(user_id)
    
    if not user_position or user_position[3] is None or user_position[4] is None:
        await bot.send_message(chat_id, f"❌ **WATCHTOWER konnte nicht erstellt werden!**\n\nDu musst deinen Live-Standort aktiviert haben, um einen Wachturm zu platzieren.")
        return
    
    lat = user_position[3]
    lon = user_position[4]
    
    # Hole Wachturm-Reichweite aus der Konfiguration
    from config import conf_getWatchtowerRangeMeters
    range_meters = conf_getWatchtowerRangeMeters()
    
    # Erstelle POI (Wachturm) in der Datenbank
    from database import db_POI_add
    if db_POI_add(game_id, "WATCHTOWER", lat, lon, range_meters=range_meters, team=team, creator_id=user_id):
        await bot.send_message(chat_id, f"🔭 **WATCHTOWER erfolgreich erstellt!**\n\n📍 **Position:** {lat:.6f}, {lon:.6f}\n🎯 **Team:** {team}\n📏 **Reichweite:** {range_meters}m\n📦 **Verfügbare Wachtürme:** {current_count}")
        
        # Benachrichtige Teammitglieder
        await notify_team_members(bot, game_id, team, f"🔭 **{username}** hat einen Wachturm bei {lat:.6f}, {lon:.6f} erstellt!", exclude_user_id=user_id)
    else:
        await bot.send_message(chat_id, f"❌ **Fehler beim Erstellen des WATCHTOWER!**\n\nBitte versuche es später erneut.")

async def ShopItemHunter3(bot, chat_id, user_id, username, game_id, team):
    """Hunter Shop Item 3 - RADAR PING: Zeigt Entfernung zu allen Runnern"""
    logger_newLog("info", "ShopItemHunter3", f"Hunter Item 3 (RADAR PING) von {username} ({user_id}) für Team {team} in Spiel {game_id} aktiviert")
    
    # Hole verfügbare Anzahl für Nachricht
    available_items = db_Wallet_get_available_items(game_id, "hunter", team)
    current_count = available_items.get("3", 0)
    
    # Hole aktuelle Position des Hunters
    from database import db_getUserPosition
    hunter_position = db_getUserPosition(user_id)
    
    if not hunter_position or hunter_position[3] is None or hunter_position[4] is None:
        await bot.send_message(chat_id, f"❌ **RADAR PING konnte nicht gesendet werden!**\n\nDu musst deinen Live-Standort aktiviert haben, um einen Radar Ping zu senden.")
        return
    
    hunter_lat = hunter_position[3]
    hunter_lon = hunter_position[4]
    
    # Hole alle Runner und berechne Entfernungen
    from database import db_getRunners, db_POI_add
    from geofunctions import calculate_distance
    runners = db_getRunners(game_id)
    
    if not runners:
        await bot.send_message(chat_id, f"📡 **RADAR PING gesendet!**\n\nKeine Runner im Spiel gefunden.\n📦 **Verfügbare Pings:** {current_count}")
        return
    
    # Berechne Entfernungen zu allen Runnern und erstelle POI-Einträge
    runner_distances = []
    for runner in runners:
        runner_user_id, runner_username, runner_team, runner_lat, runner_lon, runner_timestamp = runner
        
        if runner_lat is not None and runner_lon is not None:
            distance = calculate_distance(hunter_lat, hunter_lon, runner_lat, runner_lon)
            runner_distances.append(distance)
            
            # Erstelle POI-Eintrag für diese Entfernung
            # Verwende die Position des Hunters als POI-Position
            # Die Entfernung wird als range_meters gespeichert
            db_POI_add(
                game_id=game_id,
                poi_type="RADARPING",
                lat=hunter_lat,
                lon=hunter_lon,
                range_meters=int(distance),  # Entfernung als range_meters
                team=team,
                creator_id=user_id
            )
    
    # Sortiere nach Entfernung (nächster zuerst)
    runner_distances.sort()
    
    # Erstelle Nachricht für das Team
    team_message = f"📡 **RADAR PING von {username} gesendet!**\n\n"
    team_message += f"📍 **Sender-Position:** {hunter_lat:.6f}, {hunter_lon:.6f}\n\n"
    
    if runner_distances:
        team_message += "**Entfernungen zu Runnern:**\n"
        for i, distance in enumerate(runner_distances, 1):
            team_message += f"{i}. Runner: {distance:.1f}m\n"
    else:
        team_message += "❌ Keine Runner mit aktuellem Standort gefunden.\n"
    
    team_message += f"\n📦 **Verfügbare Pings:** {current_count}"
    
    # Sende Nachricht an das Team
    await bot.send_message(chat_id, team_message)
    
    # Benachrichtige Teammitglieder
    await notify_team_members(bot, game_id, team, team_message, exclude_user_id=user_id)
    
    # Benachrichtige alle Runner über den Ping (nur Entfernung)
    for runner in runners:
        runner_user_id, runner_username, runner_team, runner_lat, runner_lon, runner_timestamp = runner
        
        if runner_lat is not None and runner_lon is not None:
            distance = calculate_distance(hunter_lat, hunter_lon, runner_lat, runner_lon)
            
            runner_message = f"📡 **Du wurdest von einem RADAR PING erfasst!**\n\n"
            runner_message += f"📏 **Entfernung zum Sender:** {distance:.1f}m\n\n"
            runner_message += "⚠️ Ein Hunter-Team kennt jetzt deine ungefähre Position!"
            
            try:
                await bot.send_message(runner_user_id, runner_message)
            except Exception as e:
                logger_newLog("error", "ShopItemHunter3", f"Fehler beim Benachrichtigen von Runner {runner_user_id}: {str(e)}")
    
    # Benachrichtige den Gamemaster
    from database import db_Game_getField
    game = db_Game_getField(game_id)
    if game:
        gamemaster_id = game[2]
        gamemaster_message = f"📡 **RADAR PING von Hunter {username} ({user_id}) für Team {team} gesendet!**\n\n"
        gamemaster_message += f"📍 **Sender-Position:** {hunter_lat:.6f}, {hunter_lon:.6f}\n\n"
        
        if runner_distances:
            gamemaster_message += "**Entfernungen zu Runnern:**\n"
            for i, distance in enumerate(runner_distances, 1):
                gamemaster_message += f"{i}. Runner: {distance:.1f}m\n"
        else:
            gamemaster_message += "❌ Keine Runner mit aktuellem Standort gefunden.\n"
        
        try:
            await bot.send_message(gamemaster_id, gamemaster_message)
        except Exception as e:
            logger_newLog("error", "ShopItemHunter3", f"Fehler beim Benachrichtigen des Gamemasters {gamemaster_id}: {str(e)}")
    
    logger_newLog("info", "ShopItemHunter3", f"Radar Ping von {username} ({user_id}) für Team {team} gesendet - {len(runner_distances)} Runner erfasst, {len(runner_distances)} POI-Einträge erstellt")

async def ShopItemHunter4(bot, chat_id, user_id, username, game_id, team):
    """Hunter Shop Item 4 - Spurensuche: Noch nicht implementiert"""
    logger_newLog("info", "ShopItemHunter4", f"Hunter Item 4 (Spurensuche) von {username} ({user_id}) für Team {team} in Spiel {game_id} versucht zu aktivieren - NICHT IMPLEMENTIERT")
    
    await bot.send_message(chat_id, f"❌ **Spurensuche ist noch nicht implementiert!**\n\nDiese Funktion wird in einer zukünftigen Version verfügbar sein.\n\n💰 **Kein Geld wurde abgezogen.**")
    
    # Return False um zu signalisieren, dass die Aktivierung fehlgeschlagen ist
    # Dadurch wird kein Geld abgezogen und keine Items reduziert
    return False

# Hilfsfunktionen für Shop-Items
async def notify_team_members(bot, game_id, team, message, exclude_user_id=None):
    """Benachrichtigt alle Teammitglieder"""
    try:
        team_members = db_getTeamMembers(game_id, team)
        for member in team_members:
            member_user_id = member[0]
            if exclude_user_id and member_user_id == exclude_user_id:
                continue
            try:
                await bot.send_message(member_user_id, message)
            except Exception as e:
                logger_newLog("error", "notify_team_members", f"Fehler beim Benachrichtigen von Teammitglied {member_user_id}: {str(e)}")
    except Exception as e:
        logger_newLog("error", "notify_team_members", f"Fehler beim Abrufen der Teammitglieder: {str(e)}")

async def notify_all_runners(bot, game_id, message, exclude_user_id=None):
    """Benachrichtigt alle Runner"""
    try:
        runners = db_getRunners(game_id)
        for runner in runners:
            runner_user_id = runner[0]
            if exclude_user_id and runner_user_id == exclude_user_id:
                continue
            try:
                await bot.send_message(runner_user_id, message)
            except Exception as e:
                logger_newLog("error", "notify_all_runners", f"Fehler beim Benachrichtigen von Runner {runner_user_id}: {str(e)}")
    except Exception as e:
        logger_newLog("error", "notify_all_runners", f"Fehler beim Abrufen der Runner: {str(e)}")

async def notify_all_hunters(bot, game_id, message, exclude_user_id=None):
    """Benachrichtigt alle Hunter"""
    try:
        hunters = db_getHunters(game_id)
        for hunter in hunters:
            hunter_user_id = hunter[0]
            if exclude_user_id and hunter_user_id == exclude_user_id:
                continue
            try:
                await bot.send_message(hunter_user_id, message)
            except Exception as e:
                logger_newLog("error", "notify_all_hunters", f"Fehler beim Benachrichtigen von Hunter {hunter_user_id}: {str(e)}")
    except Exception as e:
        logger_newLog("error", "notify_all_hunters", f"Fehler beim Abrufen der Hunter: {str(e)}") 