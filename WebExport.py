import json
import io
import psutil
import platform
from datetime import datetime
from ftplib import FTP_TLS
from logger import logger_newLog
from config import (conf_getWebExportEnabled, conf_getWebExportFtpHost, 
                   conf_getWebExportFtpUser, conf_getWebExportFtpPass, 
                   conf_getWebExportFtpPath, conf_getAdminName)
from database import (db_WebExport_getAllGames, db_WebExport_getAllPlayers, 
                     db_WebExport_getGameById, db_WebExport_getPlayersByGameId,
                     db_WebExport_getPOIsByGameId, db_WebExport_getGameField,
                     db_WebExport_getActiveGamesCount, db_WebExport_getOnlinePlayersCount,
                     db_Game_setGamemasterToken, db_User_setPlayerToken, db_TeamToken_set,
                     db_getRunners, db_getHunters, db_Game_getGamemasterToken, 
                     db_TeamToken_getAllForGame)
from Chase import get_bot_name

# Token-Generierung
def generate_token(length=8):
    """Generiert einen 8-stelligen alphanumerischen Token (Großbuchstaben und Zahlen)"""
    import secrets
    import string
    characters = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(characters) for _ in range(length))

def generate_game_tokens(game_id):
    """Generiert alle Tokens für ein Spiel (Gamemaster, Teams, Runners)"""
    try:
        logger_newLog("info", "generate_game_tokens", f"Generiere Tokens für Spiel {game_id}")
        
        # 1. Gamemaster-Token generieren
        gamemaster_token = generate_token()
        if not db_Game_setGamemasterToken(game_id, gamemaster_token):
            logger_newLog("error", "generate_game_tokens", f"Fehler beim Setzen des Gamemaster-Tokens für Spiel {game_id}")
            return False
        
        # 2. Runner-Tokens generieren
        runners = db_getRunners(game_id)
        for runner in runners:
            runner_user_id = runner[0]
            runner_token = generate_token()
            if not db_User_setPlayerToken(runner_user_id, runner_token):
                logger_newLog("error", "generate_game_tokens", f"Fehler beim Setzen des Runner-Tokens für User {runner_user_id}")
                return False
        
        # 3. Team-Tokens generieren
        hunters = db_getHunters(game_id)
        teams_processed = set()
        for hunter in hunters:
            team = hunter[2]  # team ist in Spalte 2
            if team and team not in teams_processed:
                team_token = generate_token()
                if not db_TeamToken_set(game_id, team, team_token):
                    logger_newLog("error", "generate_game_tokens", f"Fehler beim Setzen des Team-Tokens für Team {team}")
                    return False
                teams_processed.add(team)
        
        logger_newLog("info", "generate_game_tokens", f"✅ Alle Tokens für Spiel {game_id} generiert: 1 Gamemaster, {len(runners)} Runner, {len(teams_processed)} Teams")
        return True
        
    except Exception as e:
        logger_newLog("error", "generate_game_tokens", f"Fehler beim Generieren der Tokens für Spiel {game_id}: {str(e)}")
        return False

def WebExport_ServerData():
    """Erstellt Server-Daten JSON mit Bot-Info, System-Status und Spieler-Übersicht"""
    try:
        logger_newLog("info", "WebExport_ServerData", "Erstelle Server-Daten JSON")
        
        # System-Informationen sammeln
        system_info = get_system_info()
        
        # Bot-Name aus globaler Variable abrufen (bereits beim Start geladen)
        bot_name = get_bot_name()
        
        # Bot-Informationen
        bot_info = {
            "name": bot_name,
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "admin_user": conf_getAdminName(),
            "system": system_info,
            "stats": {
                "active_games": db_WebExport_getActiveGamesCount(),
                "online_players": db_WebExport_getOnlinePlayersCount()
            }
        }
        
        # Spiele-Daten aus Datenbank
        games_data = get_games_data()
        
        # Spieler-Daten aus Datenbank
        players_data = get_players_data()
        
        # JSON zusammenstellen
        server_data = {
            "bot": bot_info,
            "games": games_data,
            "players": players_data
        }
        
        # Als JSON-String konvertieren
        json_data = json.dumps(server_data, indent=2, ensure_ascii=False)
        
        # Upload JSON per FTP
        json_filename = "ChaseBotServer.json"
        json_success = WebExport_FTPupload(json_filename, json_data.encode('utf-8'))
        
        if json_success:
            logger_newLog("info", "WebExport_ServerData", f"✅ Server-Daten erfolgreich exportiert: {json_filename}")
            return True
        else:
            logger_newLog("error", "WebExport_ServerData", f"❌ JSON-Upload fehlgeschlagen")
            return False
            
    except Exception as e:
        logger_newLog("error", "WebExport_ServerData", f"Fehler beim Erstellen der Server-Daten: {str(e)}")
        return False

def WebExport_GameData(game_id):
    """
    Erstellt eine JSON-Datei mit allen Spieldaten, strukturiert nach Tokens,
    und lädt sie per FTP hoch.
    """
    try:
        logger_newLog("info", "WebExport_GameData", f"Starte Game-Daten-Export für Spiel {game_id}")
        
        # 1. Grundlegende Spieldaten holen
        game_data = db_WebExport_getGameById(game_id)
        if not game_data:
            logger_newLog("error", "WebExport_GameData", f"Spiel {game_id} nicht gefunden")
            return False
        
        # 2. Spieler-Daten holen
        players_data = db_WebExport_getPlayersByGameId(game_id)
        if not players_data:
            logger_newLog("error", "WebExport_GameData", f"Keine Spieler für Spiel {game_id} gefunden")
            return False
        
        # 3. POIs holen
        pois_data = db_WebExport_getPOIsByGameId(game_id)
        
        # 4. Spielfeld-Daten holen
        field_data = db_WebExport_getGameField(game_id)
        
        # 5. Tokens holen
        gamemaster_token = db_Game_getGamemasterToken(game_id)
        team_tokens = db_TeamToken_getAllForGame(game_id)
        
        # 6. Daten strukturieren
        game_info = {
            "id": game_data[0],
            "name": game_data[1],
            "status": game_data[3],
            "start_time": game_data[4],
            "duration_minutes": game_data[5],
            "runner_headstart_minutes": game_data[6],
            "gamemaster_id": game_data[2]
        }
        
        # Spielfeld-Daten
        map_data = {
            "field": {
                "corner1": {"lat": field_data[0], "lon": field_data[1]} if field_data[0] else None,
                "corner2": {"lat": field_data[2], "lon": field_data[3]} if field_data[2] else None,
                "corner3": {"lat": field_data[4], "lon": field_data[5]} if field_data[4] else None,
                "corner4": {"lat": field_data[6], "lon": field_data[7]} if field_data[6] else None
            },
            "finish_line": {
                "point1": {"lat": field_data[8], "lon": field_data[9]} if field_data[8] else None,
                "point2": {"lat": field_data[10], "lon": field_data[11]} if field_data[10] else None
            },
            "pois": []
        }
        
        # POIs hinzufügen
        for poi in pois_data:
            map_data["pois"].append({
                "id": poi[0],
                "type": poi[2],
                "lat": poi[3],
                "lon": poi[4],
                "range_meters": poi[5],
                "team": poi[6],
                "creator_id": poi[7],
                "timestamp": poi[8]
            })
        
        # Spieler-Daten strukturieren (alle Spieler in einer Liste)
        players = []
        teams_budget = {}  # Team-Budgets sammeln
        
        # Erst alle normalen Spieler hinzufügen
        for player in players_data:
            # Budget für Spieler holen
            from database import db_Wallet_getBalance
            player_budget = db_Wallet_getBalance(game_id, player[4], str(player[0]) if player[4] == "runner" else player[5])
            
            player_info = {
                "user_id": player[0],
                "username": player[1],
                "first_name": player[2],
                "role": player[4],
                "team": player[5],
                "location": {
                    "lat": player[6],
                    "lon": player[7],
                    "timestamp": player[8]
                } if player[6] else None,
                "last_seen": player[3],
                "budget": player_budget if player_budget is not None else 0,
                "token": player[9] if player[9] else None  # Player-Token direkt in Player-Info
            }
            
            players.append(player_info)
            
            # Team-Budget sammeln (nur für Hunter)
            if player[4] == "hunter" and player[5]:
                if player[5] not in teams_budget:
                    teams_budget[player[5]] = player_budget if player_budget is not None else 0
        
        # Gamemaster hinzufügen (falls nicht schon in players_data)
        gamemaster_id = game_data[2]
        gamemaster_in_players = any(p["user_id"] == gamemaster_id for p in players)
        
        if not gamemaster_in_players:
            # Gamemaster-Daten holen
            from database import db_User_get
            gamemaster_data = db_User_get(gamemaster_id)
            if gamemaster_data:
                gamemaster_info = {
                    "user_id": gamemaster_data[0],
                    "username": gamemaster_data[1],
                    "first_name": gamemaster_data[2],
                    "role": "gamemaster",
                    "team": None,
                    "location": None,
                    "last_seen": gamemaster_data[4],
                    "budget": 0,  # Gamemaster hat kein Budget
                    "token": gamemaster_token
                }
                players.append(gamemaster_info)
        
        # 7. Team-Tokens hinzufügen
        team_tokens_list = []
        for team, token in team_tokens:
            team_tokens_list.append({
                "team": team,
                "token": token,
                "type": "hunter_team"
            })
        
        # 8. Finale JSON-Struktur
        export_data = {
            "game": game_info,
            "map": map_data,
            "players": players,
            "teams_budget": teams_budget,
            "team_tokens": team_tokens_list,
            "timestamp": datetime.now().isoformat()
        }
        
        # 9. JSON erstellen und hochladen
        json_data = json.dumps(export_data, indent=2, ensure_ascii=False)
        json_filename = f"ChaseBotGame_{game_id}.json"
        
        if WebExport_FTPupload(json_filename, json_data.encode('utf-8')):
            logger_newLog("info", "WebExport_GameData", f"✅ Game-Daten für Spiel {game_id} erfolgreich exportiert: {json_filename}")
            return True
        else:
            logger_newLog("error", "WebExport_GameData", f"❌ FTP-Upload für Spiel {game_id} fehlgeschlagen")
            return False
            
    except Exception as e:
        logger_newLog("error", "WebExport_GameData", f"Fehler beim Game-Daten-Export für Spiel {game_id}: {str(e)}")
        return False

def WebExport_FTPupload(filename, file_content):
    """Upload von Dateien per FTPS (FTP über SSL/TLS)"""
    try:
        # Prüfe ob WebExport aktiviert ist
        if not conf_getWebExportEnabled():
            logger_newLog("debug", "WebExport_FTPupload", "WebExport ist deaktiviert")
            return True
        
        # FTP-Verbindung herstellen
        ftp_host = conf_getWebExportFtpHost()
        ftp_user = conf_getWebExportFtpUser()
        ftp_pass = conf_getWebExportFtpPass()
        ftp_path = conf_getWebExportFtpPath()
        
        if not ftp_host or not ftp_user or not ftp_pass:
            logger_newLog("error", "WebExport_FTPupload", "FTP-Konfiguration unvollständig")
            return False
        
        logger_newLog("info", "WebExport_FTPupload", f"Verbinde mit FTP-Server: {ftp_host}")
        
        with FTP_TLS() as ftp:
            # Verbindung mit SSL/TLS
            ftp.connect(ftp_host, 21)
            ftp.login(ftp_user, ftp_pass)
            
            # Explizit in den sicheren Modus wechseln
            ftp.prot_p()
            
            logger_newLog("debug", "WebExport_FTPupload", f"Erfolgreich mit FTPS verbunden als {ftp_user}")
            
            # In Verzeichnis wechseln
            if ftp_path:
                try:
                    ftp.cwd(ftp_path)
                    logger_newLog("debug", "WebExport_FTPupload", f"Verzeichnis gewechselt zu: {ftp_path}")
                except Exception as e:
                    logger_newLog("warning", "WebExport_FTPupload", f"Verzeichnis {ftp_path} nicht gefunden: {str(e)}")
                    # Versuche Verzeichnis zu erstellen
                    try:
                        for part in ftp_path.split('/'):
                            if part:
                                try:
                                    ftp.cwd(part)
                                except:
                                    ftp.mkd(part)
                                    ftp.cwd(part)
                        logger_newLog("info", "WebExport_FTPupload", f"Verzeichnis {ftp_path} erstellt")
                    except Exception as mkdir_error:
                        logger_newLog("error", "WebExport_FTPupload", f"Fehler beim Erstellen des Verzeichnisses: {str(mkdir_error)}")
                        return False
            
            # Datei als Bytes-Objekt erstellen
            file_obj = io.BytesIO(file_content)
            
            # Upload
            ftp.storbinary(f'STOR {filename}', file_obj)
            
            logger_newLog("info", "WebExport_FTPupload", f"✅ Datei erfolgreich hochgeladen: {filename}")
            return True
            
    except Exception as e:
        logger_newLog("error", "WebExport_FTPupload", f"❌ FTPS-Upload fehlgeschlagen: {str(e)}")
        return False

def get_system_info():
    """Sammelt System-Informationen"""
    try:
        # CPU-Auslastung
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # RAM-Informationen
        memory = psutil.virtual_memory()
        ram_total = memory.total
        ram_used = memory.used
        ram_percent = memory.percent
        
        # Disk-Informationen
        disk = psutil.disk_usage('/')
        disk_total = disk.total
        disk_used = disk.used
        disk_percent = (disk.used / disk.total) * 100
        
        # Uptime
        boot_time = psutil.boot_time()
        uptime_seconds = datetime.now().timestamp() - boot_time
        uptime_hours = uptime_seconds / 3600
        
        # System-Info
        system_name = platform.system()
        system_release = platform.release()
        
        return {
            "cpu_percent": round(cpu_percent, 2),
            "ram": {
                "total_gb": round(ram_total / (1024**3), 2),
                "used_gb": round(ram_used / (1024**3), 2),
                "percent": round(ram_percent, 2)
            },
            "disk": {
                "total_gb": round(disk_total / (1024**3), 2),
                "used_gb": round(disk_used / (1024**3), 2),
                "percent": round(disk_percent, 2)
            },
            "uptime_hours": round(uptime_hours, 2),
            "system": f"{system_name} {system_release}",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        logger_newLog("error", "get_system_info", f"Fehler beim Sammeln der System-Info: {str(e)}")
        return {
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }

def get_games_data():
    """Holt Spiele-Daten aus der Datenbank"""
    try:
        games = db_WebExport_getAllGames()
        games_data = []
        
        for game in games:
            game_id, name, gamemaster_id, status, start_time, duration_minutes, created_at, updated_at = game
            
            # Zähle Spieler für dieses Spiel
            players = db_WebExport_getPlayersByGameId(game_id)
            players_count = len(players)
            
            games_data.append({
                "game_id": game_id,
                "name": name,
                "gamemaster_id": gamemaster_id,
                "status": status,
                "start_time": start_time,
                "duration_minutes": duration_minutes,
                "players_count": players_count,
                "created_at": created_at,
                "updated_at": updated_at
            })
        
        return games_data
    except Exception as e:
        logger_newLog("error", "get_games_data", f"Fehler beim Holen der Spiele-Daten: {str(e)}")
        return []

def get_players_data():
    """Holt Spieler-Daten aus der Datenbank"""
    try:
        players = db_WebExport_getAllPlayers()
        players_data = []
        
        for player in players:
            (user_id, username, first_name, last_seen, role, team, game_id,
             location_lat, location_lon, location_timestamp, created_at) = player
            
            players_data.append({
                "user_id": user_id,
                "username": username,
                "first_name": first_name,
                "game_id": game_id,
                "role": role,
                "team": team,
                "last_seen": last_seen,
                "last_location_update": location_timestamp,
                "has_location": location_lat is not None and location_lon is not None,
                "created_at": created_at
            })
        
        return players_data
    except Exception as e:
        logger_newLog("error", "get_players_data", f"Fehler beim Holen der Spieler-Daten: {str(e)}")
        return []


# Test-Funktion
def test_webexport():
    """Test-Funktion für WebExport"""
    logger_newLog("info", "test_webexport", "Starte WebExport Test")
    
    # Server-Daten exportieren
    success = WebExport_ServerData()
    
    if success:
        logger_newLog("info", "test_webexport", "WebExport Test erfolgreich")
    else:
        logger_newLog("error", "test_webexport", "WebExport Test fehlgeschlagen")
    
    return success

def test_gamedata_export(game_id):
    """Test-Funktion für GameData-Export"""
    logger_newLog("info", "test_gamedata_export", f"Starte GameData-Export Test für Spiel {game_id}")
    success = WebExport_GameData(game_id)
    if success:
        logger_newLog("info", "test_gamedata_export", f"✅ GameData-Export Test für Spiel {game_id} erfolgreich")
    else:
        logger_newLog("error", "test_gamedata_export", f"❌ GameData-Export Test für Spiel {game_id} fehlgeschlagen")
    return success
