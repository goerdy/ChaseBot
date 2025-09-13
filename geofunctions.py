from logger import logger_newLog
from database import db_User_get, db_Game_getStatus, db_POI_get_by_type, db_Locations_get_position
import math

# Dictionary für aktive Interaktionen: {user_id: {poi_id: timestamp}}
active_interactions = {}

def calculate_distance(lat1, lon1, lat2, lon2):
    """Berechnet die Entfernung zwischen zwei Koordinaten in Metern (Haversine-Formel)"""
    R = 6371000  # Erdradius in Metern
    
    lat1_rad = math.radians(lat1)
    lon1_rad = math.radians(lon1)
    lat2_rad = math.radians(lat2)
    lon2_rad = math.radians(lon2)
    
    dlat = lat2_rad - lat1_rad
    dlon = lon2_rad - lon1_rad
    
    a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance

def is_interaction_active(user_id, poi_id):
    """Prüft ob eine Interaktion bereits aktiv ist"""
    if user_id in active_interactions and poi_id in active_interactions[user_id]:
        return True
    return False

def set_interaction_active(user_id, poi_id):
    """Markiert eine Interaktion als aktiv"""
    from datetime import datetime
    if user_id not in active_interactions:
        active_interactions[user_id] = {}
    active_interactions[user_id][poi_id] = datetime.now().isoformat()
    logger_newLog("debug", "set_interaction_active", f"Interaktion {poi_id} für User {user_id} als aktiv markiert")

def clear_interaction(user_id, poi_id):
    """Entfernt eine Interaktion aus dem aktiven Tracking"""
    if user_id in active_interactions and poi_id in active_interactions[user_id]:
        del active_interactions[user_id][poi_id]
        # Entferne leere User-Einträge
        if not active_interactions[user_id]:
            del active_interactions[user_id]
        logger_newLog("debug", "clear_interaction", f"Interaktion {poi_id} für User {user_id} entfernt")

async def Check_location(bot, user_id, lat, lon):
    """Prüft die Position eines Spielers auf POI-Interaktionen
    
    Args:
        bot: Telegram Bot Instanz
        user_id: ID des Spielers
        lat: Breitengrad
        lon: Längengrad
    
    Returns:
        True wenn Interaktionen gefunden wurden, False sonst
    """
    logger_newLog("debug", "Check_location", f"Prüfe Position für User {user_id}: {lat}, {lon}")
    
    # Hole User-Daten
    user = db_User_get(user_id)
    if not user:
        logger_newLog("debug", "Check_location", f"User {user_id} nicht gefunden")
        return False
    
    game_id = user[8]  # game_id ist in Spalte 8
    role = user[6]     # role ist in Spalte 6
    
    # Prüfe ob Spieler in einem aktiven Spiel ist
    if not game_id:
        logger_newLog("debug", "Check_location", f"User {user_id} ist in keinem Spiel")
        return False
    
    game_status = db_Game_getStatus(game_id)
    if game_status not in ['headstart', 'running']:
        logger_newLog("debug", "Check_location", f"Spiel {game_id} ist nicht aktiv (Status: {game_status})")
        return False
    
    # Nur Runner werden auf POI-Interaktionen geprüft
    if role != 'runner':
        logger_newLog("debug", "Check_location", f"User {user_id} ist {role}, keine POI-Prüfung nötig")
        return False
    
    logger_newLog("debug", "Check_location", f"Prüfe Runner {user_id} in Spiel {game_id} auf POI-Interaktionen")
    
    interactions_found = False
    current_pois_in_range = set()  # Track POIs die aktuell in Reichweite sind
    
    # Prüfe Fallen
    traps = db_POI_get_by_type(game_id, 'TRAP')
    for trap in traps:
        trap_id, trap_game_id, trap_type, trap_lat, trap_lon, trap_range, trap_team, trap_creator, trap_timestamp = trap
        poi_id = f"poi_{trap_id}"
        
        distance = calculate_distance(lat, lon, trap_lat, trap_lon)
        
        if distance <= trap_range:
            current_pois_in_range.add(poi_id)
            
            # Prüfe ob Interaktion bereits aktiv ist
            if not is_interaction_active(user_id, poi_id):
                logger_newLog("info", "Check_location", f"Runner {user_id} ist in Reichweite einer Falle (ID: {trap_id}, Team: {trap_team}, Distanz: {distance:.1f}m)")
                
                # Markiere Interaktion als aktiv und führe Handling aus
                set_interaction_active(user_id, poi_id)
                await handle_trap_interaction(bot, user_id, trap_id, trap_team, distance)
                interactions_found = True
            else:
                logger_newLog("debug", "Check_location", f"Runner {user_id} ist noch in Reichweite der Falle {trap_id}, aber Interaktion bereits aktiv")
    
    # Prüfe Wachtürme
    watchtowers = db_POI_get_by_type(game_id, 'WATCHTOWER')
    for watchtower in watchtowers:
        tower_id, tower_game_id, tower_type, tower_lat, tower_lon, tower_range, tower_team, tower_creator, tower_timestamp = watchtower
        poi_id = f"poi_{tower_id}"
        
        distance = calculate_distance(lat, lon, tower_lat, tower_lon)
        
        if distance <= tower_range:
            current_pois_in_range.add(poi_id)
            
            # Prüfe ob Interaktion bereits aktiv ist
            if not is_interaction_active(user_id, poi_id):
                logger_newLog("info", "Check_location", f"Runner {user_id} ist in Reichweite eines Wachturms (ID: {tower_id}, Team: {tower_team}, Distanz: {distance:.1f}m)")
                
                # Markiere Interaktion als aktiv und führe Handling aus
                set_interaction_active(user_id, poi_id)
                await handle_watchtower_interaction(bot, user_id, tower_id, tower_team, distance)
                interactions_found = True
            else:
                logger_newLog("debug", "Check_location", f"Runner {user_id} ist noch in Reichweite des Wachturms {tower_id}, aber Interaktion bereits aktiv")
    
    # Prüfe ob User POIs verlassen hat und entferne inaktive Interaktionen
    if user_id in active_interactions:
        for poi_id in list(active_interactions[user_id].keys()):
            if poi_id not in current_pois_in_range:
                logger_newLog("debug", "Check_location", f"Runner {user_id} hat POI {poi_id} verlassen")
                clear_interaction(user_id, poi_id)
    
    if not interactions_found:
        logger_newLog("debug", "Check_location", f"Runner {user_id} ist nicht in Reichweite von neuen POIs")
    
    return interactions_found

async def handle_trap_interaction(bot, user_id, trap_id, trap_team, distance):
    """Behandelt Falleninteraktionen
    
    Args:
        bot: Telegram Bot Instanz
        user_id: ID des Runners
        trap_id: ID der Falle
        trap_team: Team der Falle
        distance: Entfernung zur Falle in Metern
    """
    logger_newLog("info", "handle_trap_interaction", f"FALLENHANDLING: Runner {user_id} hat Falle {trap_id} von Team {trap_team} ausgelöst (Distanz: {distance:.1f}m)")
    
    # Hole User-Daten für Benachrichtigungen
    from database import db_User_get, db_Game_getField, db_getTeamMembers, db_POI_add
    user = db_User_get(user_id)
    if not user:
        logger_newLog("error", "handle_trap_interaction", f"User {user_id} nicht gefunden")
        return
    
    username = user[1] or user[2] or f"User_{user_id}"
    game_id = user[8]
    
    # Hole Spieldaten für Gamemaster-ID
    game = db_Game_getField(game_id)
    if not game:
        logger_newLog("error", "handle_trap_interaction", f"Spiel {game_id} nicht gefunden")
        return
    
    gamemaster_id = game[2]
    
    # Hole aktuelle Position des Runners
    from database import db_getUserPosition
    user_position = db_getUserPosition(user_id)
    if not user_position or user_position[3] is None or user_position[4] is None:
        logger_newLog("error", "handle_trap_interaction", f"Keine Position für Runner {user_id} gefunden")
        return
    
    runner_lat = user_position[3]
    runner_lon = user_position[4]
    
    # 1. Benachrichtige das Team (ohne Runner-Info)
    try:
        team_members = db_getTeamMembers(game_id, trap_team)
        team_message = f"🪤 **Ein Runner hat eure Falle ausgelöst!**\n\n📍 **Fallen-Position:** {runner_lat:.6f}, {runner_lon:.6f}\n📏 **Distanz:** {distance:.1f}m"
        
        for member in team_members:
            try:
                await bot.send_message(member[0], team_message)
                logger_newLog("info", "handle_trap_interaction", f"Team-Benachrichtigung an {member[1]} ({member[0]}) gesendet")
            except Exception as e:
                logger_newLog("error", "handle_trap_interaction", f"Fehler beim Senden der Team-Benachrichtigung an {member[1]}: {str(e)}")
    except Exception as e:
        logger_newLog("error", "handle_trap_interaction", f"Fehler beim Abrufen der Teammitglieder: {str(e)}")
    
    # 2. Benachrichtige den Gamemaster
    try:
        gamemaster_message = f"🪤 **Falle ausgelöst!**\n\n👤 **Runner:** {username} ({user_id})\n🎯 **Team:** {trap_team}\n📍 **Position:** {runner_lat:.6f}, {runner_lon:.6f}\n📏 **Distanz:** {distance:.1f}m"
        await bot.send_message(gamemaster_id, gamemaster_message)
        logger_newLog("info", "handle_trap_interaction", f"Gamemaster-Benachrichtigung gesendet")
    except Exception as e:
        logger_newLog("error", "handle_trap_interaction", f"Fehler beim Senden der Gamemaster-Benachrichtigung: {str(e)}")
    
    # 3. Benachrichtige den Runner
    try:
        runner_message = f"🪤 **Du hast eine Falle ausgelöst!**\n\n🎯 **Team:** {trap_team}\n📏 **Distanz:** {distance:.1f}m\n\n⚠️ Das Team wurde benachrichtigt!"
        await bot.send_message(user_id, runner_message)
        logger_newLog("info", "handle_trap_interaction", f"Runner-Benachrichtigung an {username} ({user_id}) gesendet")
    except Exception as e:
        logger_newLog("error", "handle_trap_interaction", f"Fehler beim Senden der Runner-Benachrichtigung: {str(e)}")
    
    # 4. Erstelle RUNNERTRAP POI-Eintrag
    try:
        if db_POI_add(game_id, "RUNNERTRAP", runner_lat, runner_lon, team=trap_team, creator_id=user_id):
            logger_newLog("info", "handle_trap_interaction", f"RUNNERTRAP POI für Runner {username} ({user_id}) erstellt")
        else:
            logger_newLog("error", "handle_trap_interaction", f"Fehler beim Erstellen des RUNNERTRAP POI")
    except Exception as e:
        logger_newLog("error", "handle_trap_interaction", f"Fehler beim Erstellen des RUNNERTRAP POI: {str(e)}")

async def handle_watchtower_interaction(bot, user_id, tower_id, tower_team, distance):
    """Behandelt Wachturm-Interaktionen
    
    Args:
        bot: Telegram Bot Instanz
        user_id: ID des Runners
        tower_id: ID des Wachturms
        tower_team: Team des Wachturms
        distance: Entfernung zum Wachturm in Metern
    """
    logger_newLog("info", "handle_watchtower_interaction", f"WACHTURMHANDLING: Runner {user_id} ist von Wachturm {tower_id} von Team {tower_team} entdeckt worden (Distanz: {distance:.1f}m)")
    
    # Hole User-Daten für Benachrichtigungen
    from database import db_User_get, db_Game_getField, db_getTeamMembers, db_POI_add
    user = db_User_get(user_id)
    if not user:
        logger_newLog("error", "handle_watchtower_interaction", f"User {user_id} nicht gefunden")
        return
    
    username = user[1] or user[2] or f"User_{user_id}"
    game_id = user[8]
    
    # Hole Spieldaten für Gamemaster-ID
    game = db_Game_getField(game_id)
    if not game:
        logger_newLog("error", "handle_watchtower_interaction", f"Spiel {game_id} nicht gefunden")
        return
    
    gamemaster_id = game[2]
    
    # Hole aktuelle Position des Runners
    from database import db_getUserPosition
    user_position = db_getUserPosition(user_id)
    if not user_position or user_position[3] is None or user_position[4] is None:
        logger_newLog("error", "handle_watchtower_interaction", f"Keine Position für Runner {user_id} gefunden")
        return
    
    runner_lat = user_position[3]
    runner_lon = user_position[4]
    
    # Prüfe ob es die erste Interaktion mit diesem Wachturm ist (Interaktion noch nicht aktiv)
    poi_id = f"poi_{tower_id}"
    is_first_interaction = not is_interaction_active(user_id, poi_id)
    
    if is_first_interaction:
        # 1. Benachrichtige das Team (nur beim ersten Betreten)
        try:
            team_members = db_getTeamMembers(game_id, tower_team)
            team_message = f"🔭 **Ein Runner ist in Reichweite eures Wachturms!**\n\n📍 **Position:** {runner_lat:.6f}, {runner_lon:.6f}\n📏 **Distanz:** {distance:.1f}m"
            
            for member in team_members:
                try:
                    await bot.send_message(member[0], team_message)
                    logger_newLog("info", "handle_watchtower_interaction", f"Team-Benachrichtigung an {member[1]} ({member[0]}) gesendet")
                except Exception as e:
                    logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Senden der Team-Benachrichtigung an {member[1]}: {str(e)}")
        except Exception as e:
            logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Abrufen der Teammitglieder: {str(e)}")
        
        # 2. Benachrichtige den Gamemaster (nur beim ersten Betreten)
        try:
            gamemaster_message = f"🔭 **Wachturm hat Runner entdeckt!**\n\n👤 **Runner:** {username} ({user_id})\n🎯 **Team:** {tower_team}\n📍 **Position:** {runner_lat:.6f}, {runner_lon:.6f}\n📏 **Distanz:** {distance:.1f}m"
            await bot.send_message(gamemaster_id, gamemaster_message)
            logger_newLog("info", "handle_watchtower_interaction", f"Gamemaster-Benachrichtigung gesendet")
        except Exception as e:
            logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Senden der Gamemaster-Benachrichtigung: {str(e)}")
        
        # 3. Benachrichtige den Runner (nur beim ersten Betreten)
        try:
            runner_message = f"🔭 **Du wurdest von einem Wachturm entdeckt!**\n\n🎯 **Team:** {tower_team}\n📏 **Distanz:** {distance:.1f}m\n\n⚠️ Das Team wurde benachrichtigt!"
            await bot.send_message(user_id, runner_message)
            logger_newLog("info", "handle_watchtower_interaction", f"Runner-Benachrichtigung an {username} ({user_id}) gesendet")
        except Exception as e:
            logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Senden der Runner-Benachrichtigung: {str(e)}")
    
    # 4. Erstelle RUNNERWATCHTOWER POI-Eintrag (bei jeder Position in der Range)
    try:
        if db_POI_add(game_id, "RUNNERWATCHTOWER", runner_lat, runner_lon, team=tower_team, creator_id=user_id):
            logger_newLog("info", "handle_watchtower_interaction", f"RUNNERWATCHTOWER POI für Runner {username} ({user_id}) erstellt")
        else:
            logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Erstellen des RUNNERWATCHTOWER POI")
    except Exception as e:
        logger_newLog("error", "handle_watchtower_interaction", f"Fehler beim Erstellen des RUNNERWATCHTOWER POI: {str(e)}") 