from logger import logger_newLog
from database import db_User_new, db_User_get, db_User_update_lastseen, db_User_update_location, db_Game_new, db_User_setRole, db_User_setGameID, db_User_setTeam, db_Game_setField, db_Game_isGamemaster, db_get_connection
from Map import Map_SendMap
import os
from telegram_helpmessage import send_helpmessage

async def send_Helpmessage(bot, chat_id):
    """Sendet eine Hilfemeldung"""
    help_text = """
🤖 TelegramChaseBot - Hilfe

Verfügbare Befehle:
/start - Registriere dich beim Bot
/new [Name] - Erstelle ein neues Spiel
/join [GameID] - Tritt einem Spiel bei
/help - Zeige diese Hilfe

Spielrollen:
• Gamemaster - Spielleiter
• Runner - Läufer
• Hunter - Jäger
• Spectator - Zuschauer

Standort teilen:
Sende deinen Live-Standort um am Spiel teilzunehmen.

Für weitere Hilfe kontaktiere den Admin.
    """
    
    await bot.send_message(chat_id, help_text)
    logger_newLog("info", "send_Helpmessage", f"Hilfemeldung gesendet an {chat_id}")

async def handle_location(bot, chat_id, user_id, username, lat, lon):
    """Behandelt Live-Location-Nachrichten"""
    logger_newLog("info", "handle_location", f"Live-Location von {username} ({user_id}): {lat}, {lon}")
    
    # Speichere Standort in Datenbank
    if db_User_update_location(user_id, lat, lon):
        logger_newLog("info", "handle_location", f"Standort gespeichert für User {username}")
    else:
        await bot.send_message(chat_id, "❌ Fehler beim Speichern des Standorts")
        logger_newLog("error", "handle_location", f"Fehler beim Speichern des Standorts für User {username}")
        return
    
    # Prüfe Position auf POI-Interaktionen
    try:
        from geofunctions import Check_location
        interactions_found = await Check_location(bot, user_id, lat, lon)
        
        if interactions_found:
            logger_newLog("info", "handle_location", f"POI-Interaktionen für User {username} gefunden")
        else:
            logger_newLog("debug", "handle_location", f"Keine POI-Interaktionen für User {username}")
            
    except Exception as e:
        logger_newLog("error", "handle_location", f"Fehler bei POI-Prüfung für User {username}: {str(e)}")

async def cmd_start(bot, chat_id, user_id, username):
    """Behandelt /start Befehl"""
    logger_newLog("info", "cmd_start", f"Start Befehl von {username} ({user_id})")
    
    # Prüfe ob User bereits existiert
    existing_user = db_User_get(user_id)
    
    if existing_user:
        # User existiert bereits - aktualisiere last_seen
        if db_User_update_lastseen(user_id):
            await bot.send_message(chat_id, f"Willkommen zurück {username or f'User_{user_id}'}!")
        else:
            await bot.send_message(chat_id, "Fehler beim Aktualisieren. Bitte versuche es später erneut.")
    else:
        # Neuer User - prüfe ob Username vorhanden ist
        if not username:
            await bot.send_message(chat_id, "❌ Bitte vergib einen Username in den Telegram-Einstellungen und rufe /start erneut auf.")
            logger_newLog("warning", "cmd_start", f"Registrierung verweigert - kein Username für User {user_id}")
            return
        
        # Neuer User mit Username - füge zur Datenbank hinzu
        first_name = username  # Verwende Username als first_name
        if db_User_new(user_id, username, first_name):
            await bot.send_message(chat_id, f"Willkommen {first_name}! Du bist jetzt registriert.")
            # Zeige Hilfe nach erfolgreicher Registrierung
            await send_helpmessage(bot, user_id, chat_id)
        else:
            await bot.send_message(chat_id, "Fehler bei der Registrierung. Bitte versuche es später erneut.")
            return
    
async def cmd_new(bot, chat_id, user_id, username, command_text):
    """Behandelt /new Befehl"""
    logger_newLog("info", "cmd_new", f"New Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib einen Spielnamen an: /new [Name]")
        return
    
    # Prüfe ob User bereits in einem Spiel ist
    existing_user = db_User_get(user_id)
    if existing_user and existing_user[8] is not None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du musst das Spiel erst verlassen, bevor du ein neues Spiel erstellen kannst.")
        return
    
    # Erstelle neues Spiel
    game_id = db_Game_new(command_text.strip(), user_id)
    
    if game_id:
        # Setze User-Game-ID, Rolle auf Gamemaster und Team auf None
        if db_User_setGameID(user_id, game_id) and db_User_setRole(user_id, "gamemaster") and db_User_setTeam(user_id, None):
            await bot.send_message(chat_id, f"✅ Spiel '{command_text.strip()}' erfolgreich erstellt! (Game ID: {game_id})\n🎮 Du bist jetzt Gamemaster!")
            # Sende Standard-Tastatur
            await send_helpmessage(bot, user_id, chat_id)
        else:
            await bot.send_message(chat_id, f"✅ Spiel '{command_text.strip()}' erstellt! (Game ID: {game_id})\n⚠️ Fehler beim Setzen der Gamemaster-Rolle, Game-ID oder Team")
    else:
        await bot.send_message(chat_id, "❌ Fehler beim Erstellen des Spiels")
    
async def cmd_join(bot, chat_id, user_id, username, command_text):
    """Behandelt /join Befehl"""
    logger_newLog("info", "cmd_join", f"Join Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib eine Game ID an: /join [GameID]\n💡 Verwende /listgames um verfügbare Spiele zu sehen.")
        return
    
    try:
        game_id = int(command_text.strip())
    except ValueError:
        await bot.send_message(chat_id, "❌ Ungültige Game ID. Bitte gib eine Zahl ein.")
        return
    
    # Prüfe ob das Spiel existiert
    from database import db_Game_getField
    game_data = db_Game_getField(game_id)
    if not game_data:
        await bot.send_message(chat_id, f"❌ Spiel {game_id} existiert nicht!\n💡 Verwende /listgames um verfügbare Spiele zu sehen.")
        return
    
    # Prüfe ob User existiert
    existing_user = db_User_get(user_id)
    if not existing_user:
        # Nur wenn User wirklich nicht existiert, erstelle ihn
        first_name = username or f"User_{user_id}"
        if not db_User_new(user_id, username, first_name):
            await bot.send_message(chat_id, "❌ Fehler bei der User-Erstellung")
            return
        existing_user = db_User_get(user_id)
    
    # Prüfe ob User bereits in einem anderen Spiel ist
    if existing_user and existing_user[8] is not None and existing_user[8] != game_id:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du musst das Spiel erst verlassen, bevor du einem neuen Spiel beitreten kannst.")
        return
    
    # Prüfe ob User bereits als Gamemaster in diesem Spiel eingetragen ist
    # Dazu müssen wir prüfen, ob er in der games Tabelle als gamemaster_id eingetragen ist
    is_gamemaster = db_Game_isGamemaster(user_id, game_id)
    
    # Setze User zum Spiel hinzu
    if db_User_setGameID(user_id, game_id):
        # Setze Rolle basierend auf Gamemaster-Status
        if is_gamemaster:
            role_to_set = "gamemaster"
            role_message = "Gamemaster"
        else:
            role_to_set = "none"
            role_message = "Keine"
        
        if db_User_setRole(user_id, role_to_set):
            # Leere das Team
            if db_User_setTeam(user_id, None):
                await bot.send_message(chat_id, f"✅ Du bist erfolgreich Spiel {game_id} beigetreten!\n🎮 Rolle: {role_message}\n🎨 Team: Noch nicht zugewiesen")
                
                # Benachrichtige den Gamemaster (außer wenn der User selbst Gamemaster ist)
                if not is_gamemaster:
                    from database import db_Game_getField
                    game = db_Game_getField(game_id)
                    if game:
                        gamemaster_id = game[2]
                        player_name = username or f"User_{user_id}"
                        try:
                            await bot.send_message(gamemaster_id, f"👋 {player_name} ist dem Spiel beigetreten!\n\nSchau dir `/listusers` an um einen Überblick zu bekommen.")
                        except Exception as e:
                            logger_newLog("error", "cmd_join", f"Fehler beim Benachrichtigen des Gamemasters: {str(e)}")
                
                # Zeige Hilfe nach erfolgreichem Join
                await send_helpmessage(bot, user_id, chat_id)
            else:
                await bot.send_message(chat_id, f"✅ Du bist Spiel {game_id} beigetreten!\n🎮 Rolle: {role_message}\n⚠️ Fehler beim Zurücksetzen des Teams")
        else:
            await bot.send_message(chat_id, f"✅ Du bist Spiel {game_id} beigetreten!\n⚠️ Fehler beim Setzen der Rolle")
    else:
        await bot.send_message(chat_id, f"❌ Fehler beim Beitreten zu Spiel {game_id}")

async def cmd_leave(bot, chat_id, user_id, username, command_text):
    """Behandelt /leave Befehl"""
    logger_newLog("info", "cmd_leave", f"Leave Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Hole Gamemaster-ID vor dem Zurücksetzen der Werte
    from database import db_Game_getField
    game = db_Game_getField(game_id)
    gamemaster_id = None
    if game:
        gamemaster_id = game[2]
    
    # Setze alle Werte zurück
    if db_User_setGameID(user_id, None) and db_User_setRole(user_id, "none") and db_User_setTeam(user_id, None):
        await bot.send_message(chat_id, f"✅ Du hast Spiel {game_id} erfolgreich verlassen.\n🎮 Rolle und Team wurden zurückgesetzt.")
        
        # Benachrichtige den Gamemaster (außer wenn der User selbst Gamemaster ist)
        if gamemaster_id and gamemaster_id != user_id:
            player_name = username or f"User_{user_id}"
            try:
                await bot.send_message(gamemaster_id, f"👋 {player_name} hat das Spiel verlassen.")
            except Exception as e:
                logger_newLog("error", "cmd_leave", f"Fehler beim Benachrichtigen des Gamemasters: {str(e)}")
        
        # Zeige Hilfe nach erfolgreichem Leave
        await send_helpmessage(bot, user_id, chat_id)
    else:
        await bot.send_message(chat_id, f"⚠️ Du hast Spiel {game_id} verlassen, aber es gab Probleme beim Zurücksetzen der Werte.")

async def cmd_unknown(bot, chat_id, user_id, username, command):
    """Behandelt unbekannte Befehle"""
    logger_newLog("info", "cmd_unknown", f"Unbekannter Befehl '{command}' von {username} ({user_id})")
    # Sende Fehlermeldung
    await bot.send_message(chat_id, f"❌ Unbekannter Befehl: {command}")
    # Sende Hilfemeldung
    await send_helpmessage(bot, user_id, chat_id)

async def handle_text(bot, chat_id, user_id, username, text):
    from database import db_User_get, db_getRunners, db_getHunters, db_getTeamMembers, db_Game_getField
    from telegram_helpmessage import send_helpmessage
    
    # Prüfe ob es ein Befehl ist (beginnt mit /)
    if text.startswith('/'):
        logger_newLog("info", "handle_text", f"Befehl '{text}' von Keyboard-Button erkannt")
        
        # Leite an den entsprechenden Befehl weiter
        if text == "/start":
            await cmd_start(bot, chat_id, user_id, username)
        elif text == "/new":
            await bot.send_message(chat_id, "❌ Bitte gib einen Spielnamen an: /new [Name]")
        elif text == "/join":
            await bot.send_message(chat_id, "❌ Bitte gib eine Game ID an: /join [GameID]")
        elif text == "/help":
            await send_helpmessage(bot, user_id, chat_id)
        elif text == "/leave":
            await cmd_leave(bot, chat_id, user_id, username, "")
        elif text == "/listgames":
            await cmd_listgames(bot, chat_id)
        elif text == "/mapedit":
            await cmd_mapedit(bot, chat_id, user_id, username, "")
        elif text == "/listusers":
            await cmd_listusers(bot, chat_id, user_id, username, "")
        elif text == "/role":
            await bot.send_message(chat_id, "❌ Bitte gib Name und Rolle an: /role <Name> <rolle>")
        elif text == "/team":
            await bot.send_message(chat_id, "❌ Bitte gib Name und Team an: /team <Name> <farbe>")
        elif text == "/startgame":
            await cmd_startgame(bot, chat_id, user_id, username, "")
        elif text == "/map":
            await cmd_map(bot, chat_id, user_id, username, "")
        elif text == "/shop":
            await cmd_shop(bot, chat_id, user_id, username, "")
        elif text == "/status":
            await cmd_status(bot, chat_id, user_id, username, "")
        elif text == "/endgame":
            await cmd_endgame(bot, chat_id, user_id, username, "")
        elif text == "/coins":
            await bot.send_message(chat_id, "❌ Bitte gib Ziel und Betrag an: /coins <Team/User> <Betrag>")
        elif text == "/back":
            await send_helpmessage(bot, user_id, chat_id)
        else:
            # Unbekannter Befehl
            await cmd_unknown(bot, chat_id, user_id, username, text)
        return
    
    # Normale Textnachrichten-Behandlung (Chat-System)
    user = db_User_get(user_id)
    if not user:
        await bot.send_message(chat_id, "Du bist nicht in einem Spiel. Textnachrichten werden ignoriert.")
        return
    role = user[6]
    game_id = user[8]
    if not game_id:
        await bot.send_message(chat_id, "Du bist nicht in einem Spiel. Textnachrichten werden ignoriert.")
        return
    game = db_Game_getField(game_id)
    if not game:
        await bot.send_message(chat_id, "Fehler: Spiel nicht gefunden.")
        return
    gamemaster_id = game[2]
    # Gamemaster: Nachricht an alle Spieler
    if role == 'gamemaster':
        runners = db_getRunners(game_id)
        hunters = db_getHunters(game_id)
        for runner in runners:
            await bot.send_message(runner[0], f"[Gamemaster]: {text}")
        for hunter in hunters:
            await bot.send_message(hunter[0], f"[Gamemaster]: {text}")
        await bot.send_message(chat_id, "Nachricht an alle Spieler gesendet.")
        return
    # Runner: Nachricht an Gamemaster
    if role == 'runner':
        await bot.send_message(gamemaster_id, f"[Runner {username}]: {text}")
        await bot.send_message(chat_id, "Nachricht an den Gamemaster gesendet.")
        return
    # Hunter: Nachricht an Team und Gamemaster
    if role == 'hunter':
        team = user[7]
        team_members = db_getTeamMembers(game_id, team)
        for member in team_members:
            await bot.send_message(member[0], f"[Team {team} | Hunter {username}]: {text}")
        await bot.send_message(gamemaster_id, f"[Team {team} | Hunter {username}]: {text}")
        await bot.send_message(chat_id, "Nachricht an dein Team und den Gamemaster gesendet.")
        return
    # Sonst: Standardantwort
    await bot.send_message(chat_id, "die Chatfunktion ist noch nicht implementiert. sorry, wir arbeiten dran.")

async def cmd_fieldsetup(bot, chat_id, user_id, username, command_text):
    """Behandelt /fieldsetup Befehl mit JSON-Eingabe"""
    logger_newLog("info", "cmd_fieldsetup", f"Fieldsetup Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib JSON-Daten an: /fieldsetup {\"field_coords\":\"...\",\"finish_coords\":\"...\",\"duration_minutes\":60,\"runner_headstart_minutes\":5}")
        return
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können das Spielfeld einrichten.")
        return
    
    try:
        # Parse JSON
        import json
        fieldsetup_data = json.loads(command_text.strip())
        
        # Validiere erforderliche Felder
        required_fields = ["field_coords", "finish_coords", "duration_minutes", "runner_headstart_minutes"]
        for field in required_fields:
            if field not in fieldsetup_data:
                await bot.send_message(chat_id, f"❌ Fehlendes Feld in JSON: {field}")
                return
        
        # Parse Spielfeld-Koordinaten
        field_coords = fieldsetup_data["field_coords"].split(';')
        if len(field_coords) != 4:
            await bot.send_message(chat_id, "❌ Spielfeld benötigt genau 4 Koordinatenpaare.")
            return
        
        field_lat_lon = []
        for coord in field_coords:
            try:
                lat, lon = coord.split(',')
                field_lat_lon.append((float(lat), float(lon)))
            except ValueError:
                await bot.send_message(chat_id, f"❌ Ungültige Koordinate: {coord}")
                return
        
        # Parse Ziellinien-Koordinaten
        finish_coords = fieldsetup_data["finish_coords"].split(';')
        if len(finish_coords) != 2:
            await bot.send_message(chat_id, "❌ Ziellinie benötigt genau 2 Koordinatenpaare.")
            return
        
        finish_lat_lon = []
        for coord in finish_coords:
            try:
                lat, lon = coord.split(',')
                finish_lat_lon.append((float(lat), float(lon)))
            except ValueError:
                await bot.send_message(chat_id, f"❌ Ungültige Ziellinien-Koordinate: {coord}")
                return
        
        # Validiere Zahlen
        duration_minutes = fieldsetup_data["duration_minutes"]
        runner_headstart_minutes = fieldsetup_data["runner_headstart_minutes"]
        
        if not isinstance(duration_minutes, int) or duration_minutes <= 0:
            await bot.send_message(chat_id, "❌ Spieldauer muss eine positive Zahl sein.")
            return
        
        if not isinstance(runner_headstart_minutes, int) or runner_headstart_minutes < 0:
            await bot.send_message(chat_id, "❌ Runner-Vorsprung muss eine nicht-negative Zahl sein.")
            return
        
        # Speichere alle Daten in der Datenbank
        from database import db_Game_setField, db_Game_setDuration, db_Game_setRunnerHeadstart
        
        if (db_Game_setField(game_id, field_lat_lon, finish_lat_lon) and 
            db_Game_setDuration(game_id, duration_minutes) and 
            db_Game_setRunnerHeadstart(game_id, runner_headstart_minutes)):
            
            await bot.send_message(chat_id, f"✅ Spielfeld für Spiel {game_id} erfolgreich eingerichtet!\n🎯 4 Spielfeld-Ecken und 2 Ziellinien-Punkte gespeichert.\n⏱️ Spieldauer: {duration_minutes} Minuten\n🏃 Runner-Vorsprung: {runner_headstart_minutes} Minuten")
        else:
            await bot.send_message(chat_id, f"❌ Fehler beim Speichern der Spielfeld-Daten für Spiel {game_id}")
            
    except json.JSONDecodeError:
        await bot.send_message(chat_id, "❌ Ungültiges JSON-Format. Bitte überprüfe die Syntax.")
    except Exception as e:
        logger_newLog("error", "cmd_fieldsetup", f"Unerwarteter Fehler: {str(e)}")
        await bot.send_message(chat_id, "❌ Unerwarteter Fehler beim Verarbeiten der Spielfeld-Daten.")

async def cmd_map(bot, chat_id, user_id, username, command_text):
    """Behandelt /map Befehl"""
    logger_newLog("info", "cmd_map", f"Map Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Rufe die Map-Funktion auf
    await Map_SendMap(bot, chat_id, user_id, username, game_id) 

async def cmd_mapedit(bot, chat_id, user_id, username, command_text):
    """Behandelt /mapedit Befehl - Gamemaster bekommt fieldsetup.html"""
    logger_newLog("info", "cmd_mapedit", f"Mapedit Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können die Karten-Einstellungen bearbeiten.")
        return
    
    # Sende fieldsetup.html Datei
    try:
        with open('fieldsetup.html', 'r', encoding='utf-8') as file:
            html_content = file.read()
        
        await bot.send_message(chat_id, "🗺️ Hier ist die Karten-Einstellungsdatei:")
        
        # Erstelle BytesIO Objekt für die Datei
        import io
        file_obj = io.BytesIO(html_content.encode('utf-8'))
        file_obj.name = 'fieldsetup.html'
        
        await bot.send_document(chat_id, file_obj)
        logger_newLog("info", "cmd_mapedit", f"fieldsetup.html an Gamemaster {username} ({user_id}) gesendet")
    except FileNotFoundError:
        await bot.send_message(chat_id, "❌ Die fieldsetup.html Datei wurde nicht gefunden.")
        logger_newLog("error", "cmd_mapedit", "fieldsetup.html Datei nicht gefunden")
    except Exception as e:
        await bot.send_message(chat_id, "❌ Fehler beim Senden der Karten-Einstellungsdatei.")
        logger_newLog("error", "cmd_mapedit", f"Fehler beim Senden der fieldsetup.html: {str(e)}")

async def cmd_listusers(bot, chat_id, user_id, username, command_text):
    from database import db_User_get, db_getUsers
    user = db_User_get(user_id)
    if not user:
        await bot.send_message(chat_id, "Du bist in keinem Spiel.")
        return
    game_id = user[8]
    if not game_id:
        await bot.send_message(chat_id, "Du bist in keinem Spiel.")
        return
    if user[6] != 'gamemaster':
        await bot.send_message(chat_id, "Nur der Gamemaster darf diesen Befehl ausführen.")
        return
    users = db_getUsers()
    spieler = [u for u in users if u[8] == game_id]  # u[8] = game_id
    if not spieler:
        await bot.send_message(chat_id, "Keine Spieler im Spiel gefunden.")
        return
    msg = f"Spieler im Spiel {game_id}:\n"
    msg += "Name | Rolle | Team\n"
    msg += "-------------------\n"
    for u in spieler:
        name = u[1] or u[2] or f"User_{u[0]}"  # username or first_name
        rolle = u[6] if len(u) > 6 else "?"  # role
        team = u[7] if len(u) > 7 else "-"  # team
        msg += f"{name} | {rolle} | {team}\n"
    
    msg += "\nBefehle zur Spielerverwaltung:\n"
    msg += "• `/role <Name> <rolle>` - Rolle zuweisen\n"
    msg += "  Rollen: runner, hunter, spectator\n"
    msg += "• `/team <Name> <farbe>` - Team zuweisen (nur für Hunter)\n"
    msg += "  Farben: red, blue, green, yellow, purple\n"
    
    await bot.send_message(chat_id, msg)

async def cmd_role(bot, chat_id, user_id, username, command_text):
    """Behandelt /role Befehl - Gamemaster weist Spielern Rollen zu"""
    logger_newLog("info", "cmd_role", f"Role Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib Name und Rolle an: /role <Name> <rolle>")
        return
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können Rollen zuweisen.")
        return
    
    # Parse Kommando
    parts = command_text.strip().split()
    if len(parts) != 2:
        await bot.send_message(chat_id, "❌ Bitte gib genau Name und Rolle an: /role <Name> <rolle>")
        return
    
    target_name, role = parts
    
    # Validiere Rolle
    allowed_roles = ["runner", "hunter", "spectator"]
    if role.lower() not in allowed_roles:
        await bot.send_message(chat_id, f"❌ Ungültige Rolle. Erlaubt: {', '.join(allowed_roles)}")
        return
    
    # Finde den Zielspieler
    from database import db_getUsers
    users = db_getUsers()
    target_user = None
    
    for user in users:
        if user[8] == game_id:  # Nur Spieler im gleichen Spiel
            name = user[1] or user[2] or f"User_{user[0]}"  # username or first_name
            if name.lower() == target_name.lower():
                target_user = user
                break
    
    if not target_user:
        await bot.send_message(chat_id, f"❌ Spieler '{target_name}' nicht im Spiel gefunden.")
        return
    
    target_user_id = target_user[0]
    current_role = target_user[6]
    
    # Prüfe ob Zielspieler bereits Gamemaster ist
    if current_role == "gamemaster":
        await bot.send_message(chat_id, f"❌ Die Rolle des Gamemasters kann nicht geändert werden.")
        return
    
    # Weise Rolle zu
    if db_User_setRole(target_user_id, role.lower()):
        # Wenn Rolle auf hunter gesetzt wird, setze automatisch ein Standard-Team
        if role.lower() == "hunter":
            db_User_setTeam(target_user_id, "red")  # Standard-Team für neue Hunter
            await bot.send_message(chat_id, f"✅ Rolle '{role}' erfolgreich an '{target_name}' zugewiesen. Standard-Team 'red' gesetzt.")
            # Benachrichtige den Spieler
            try:
                await bot.send_message(target_user_id, f"🎮 Der Gamemaster hat dir die Rolle '{role}' zugewiesen. Standard-Team 'red' gesetzt.")
            except Exception as e:
                logger_newLog("error", "cmd_role", f"Fehler beim Benachrichtigen von {target_name}: {str(e)}")
        else:
            # Für andere Rollen Team zurücksetzen
            db_User_setTeam(target_user_id, None)
            await bot.send_message(chat_id, f"✅ Rolle '{role}' erfolgreich an '{target_name}' zugewiesen.")
            # Benachrichtige den Spieler
            try:
                await bot.send_message(target_user_id, f"🎮 Der Gamemaster hat dir die Rolle '{role}' zugewiesen.")
            except Exception as e:
                logger_newLog("error", "cmd_role", f"Fehler beim Benachrichtigen von {target_name}: {str(e)}")
        
        logger_newLog("info", "cmd_role", f"Rolle {role} an {target_name} ({target_user_id}) zugewiesen")
    else:
        await bot.send_message(chat_id, f"❌ Fehler beim Zuweisen der Rolle an '{target_name}'.")
        logger_newLog("error", "cmd_role", f"Fehler beim Zuweisen der Rolle {role} an {target_name}")

async def cmd_team(bot, chat_id, user_id, username, command_text):
    """Behandelt /team Befehl - Gamemaster weist Hunter ein Team zu"""
    logger_newLog("info", "cmd_team", f"Team Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib Name und Team an: /team <Name> <farbe>")
        return
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können Teams zuweisen.")
        return
    
    # Parse Kommando
    parts = command_text.strip().split()
    if len(parts) != 2:
        await bot.send_message(chat_id, "❌ Bitte gib genau Name und Team an: /team <Name> <farbe>")
        return
    
    target_name, team_color = parts
    
    # Validiere Team-Farbe
    allowed_teams = ["red", "blue", "green", "yellow", "purple"]
    if team_color.lower() not in allowed_teams:
        await bot.send_message(chat_id, f"❌ Ungültige Team-Farbe. Erlaubt: {', '.join(allowed_teams)}")
        return
    
    # Finde den Zielspieler
    from database import db_getUsers
    users = db_getUsers()
    target_user = None
    
    for user in users:
        if user[8] == game_id:  # Nur Spieler im gleichen Spiel
            name = user[1] or user[2] or f"User_{user[0]}"  # username or first_name
            if name.lower() == target_name.lower():
                target_user = user
                break
    
    if not target_user:
        await bot.send_message(chat_id, f"❌ Spieler '{target_name}' nicht im Spiel gefunden.")
        return
    
    target_user_id = target_user[0]
    target_role = target_user[6]
    
    # Prüfe ob Zielspieler ein Hunter ist
    if target_role != "hunter":
        await bot.send_message(chat_id, f"❌ Nur Hunter können Teams zugewiesen bekommen. '{target_name}' ist {target_role}.")
        return
    
    # Weise Team zu
    if db_User_setTeam(target_user_id, team_color.lower()):
        await bot.send_message(chat_id, f"✅ Team '{team_color}' erfolgreich an Hunter '{target_name}' zugewiesen.")
        # Benachrichtige den Spieler
        try:
            await bot.send_message(target_user_id, f"🎨 Der Gamemaster hat dir das Team '{team_color}' zugewiesen.")
        except Exception as e:
            logger_newLog("error", "cmd_team", f"Fehler beim Benachrichtigen von {target_name}: {str(e)}")
        logger_newLog("info", "cmd_team", f"Team {team_color} an Hunter {target_name} ({target_user_id}) zugewiesen")
    else:
        await bot.send_message(chat_id, f"❌ Fehler beim Zuweisen des Teams an '{target_name}'.")
        logger_newLog("error", "cmd_team", f"Fehler beim Zuweisen des Teams {team_color} an Hunter {target_name}")

async def cmd_shop(bot, chat_id, user_id, username, command_text):
    """Behandelt /shop Befehl - Zeigt verfügbare Items und Budget"""
    logger_newLog("info", "cmd_shop", f"Shop Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    role = existing_user[6]
    team = existing_user[7]
    
    # Prüfe ob Spiel läuft
    from database import db_Game_getStatus, db_Game_getStartTime, db_Game_getRunnerHeadstart
    game_status = db_Game_getStatus(game_id)
    if game_status not in ['headstart', 'running']:
        await bot.send_message(chat_id, "❌ Der Shop ist nur während des Spiels verfügbar.")
        return
    
    # Prüfe Headstart für Hunter
    if role == 'hunter':
        if game_status == 'headstart':
            await bot.send_message(chat_id, "⏳ Der Shop ist für Hunter noch nicht verfügbar.\n🦌 Runner haben noch Headstart - warte bis das Spiel richtig beginnt!")
        return
    
    # Spezielle Ansicht für Gamemaster
    if role == 'gamemaster':
        await show_gamemaster_shop_overview(bot, chat_id, game_id)
        return
    
    # Normale Shop-Ansicht für Runner und Hunter
    # Hole Wallet
    from database import db_Wallet_get
    if role == 'runner':
        wallet = db_Wallet_get(game_id, "runner", str(user_id))
        wallet_type = "runner"
        wallet_name = str(user_id)
    elif role == 'hunter' and team:
        wallet = db_Wallet_get(game_id, "hunter", team)
        wallet_type = "hunter"
        wallet_name = team
    else:
        await bot.send_message(chat_id, "❌ Du hast kein Wallet. Nur Runner und Hunter mit Team können den Shop nutzen.")
        return
    
    if not wallet:
        await bot.send_message(chat_id, "❌ Wallet nicht gefunden. Bitte kontaktiere den Gamemaster.")
        return
    
    budget = wallet[4]  # budget ist in Spalte 4
    last_purchase = wallet[5]  # last_purchase ist in Spalte 5
    
    # Prüfe Cooldown
    from database import db_Game_getShopCooldown
    from datetime import datetime, timedelta
    cooldown_minutes = db_Game_getShopCooldown(game_id)
    
    cooldown_active = False
    if last_purchase:
        try:
            last_purchase_dt = datetime.fromisoformat(last_purchase)
            now = datetime.now()
            if now - last_purchase_dt < timedelta(minutes=cooldown_minutes):
                cooldown_active = True
                remaining = cooldown_minutes - int((now - last_purchase_dt).total_seconds() / 60)
        except Exception:
            pass
    
    # Erstelle Shop-Nachricht
    shop_message = f"🛒 Shop - Spiel {game_id}\n\n"
    shop_message += f"💰 Dein Budget: {budget} Coins\n"
    
    if cooldown_active:
        shop_message += f"⏳ Cooldown: Noch {remaining} Minuten\n\n"
    else:
        shop_message += "✅ Bereit zum Kaufen\n\n"
    
    # Hole Shop-Items basierend auf Rolle
    if role == 'runner':
        from database import (db_Game_getRunnerShop1price, db_Game_getRunnerShop1amount,
                             db_Game_getRunnerShop2price, db_Game_getRunnerShop2amount,
                             db_Game_getRunnerShop3price, db_Game_getRunnerShop3amount,
                             db_Game_getRunnerShop4price, db_Game_getRunnerShop4amount)
        
        items = [
            (1, "Radar Ping", db_Game_getRunnerShop1price(game_id), db_Game_getRunnerShop1amount(game_id)),
            (2, "Radar Stealth Mode", db_Game_getRunnerShop2price(game_id), db_Game_getRunnerShop2amount(game_id)),
            (3, "Runner Item 3", db_Game_getRunnerShop3price(game_id), db_Game_getRunnerShop3amount(game_id)),
            (4, "Runner Item 4", db_Game_getRunnerShop4price(game_id), db_Game_getRunnerShop4amount(game_id))
        ]
    else:  # hunter
        from database import (db_Game_getHunterShop1price, db_Game_getHunterShop1amount,
                             db_Game_getHunterShop2price, db_Game_getHunterShop2amount,
                             db_Game_getHunterShop3price, db_Game_getHunterShop3amount,
                             db_Game_getHunterShop4price, db_Game_getHunterShop4amount)
        
        items = [
            (1, "TRAP", db_Game_getHunterShop1price(game_id), db_Game_getHunterShop1amount(game_id)),
            (2, "Watchtower", db_Game_getHunterShop2price(game_id), db_Game_getHunterShop2amount(game_id)),
            (3, "Radar Ping", db_Game_getHunterShop3price(game_id), db_Game_getHunterShop3amount(game_id)),
            (4, "Hunter Item 4", db_Game_getHunterShop4price(game_id), db_Game_getHunterShop4amount(game_id))
        ]
    
    shop_message += "Verfügbare Items:\n"
    for item_id, item_name, price, max_amount in items:
        if budget >= price:
            status = "✅"
        else:
            status = "❌"
        
        # Hole verfügbare Anzahl
        from database import db_Wallet_get_available_items
        available_items = db_Wallet_get_available_items(game_id, wallet_type, wallet_name)
        available_count = available_items.get(str(item_id), 0)
        
        shop_message += f"{status} {item_name} - {price} Coins (Verfügbar: {available_count})\n"
    
    shop_message += "\nKauf-Befehle:\n"
    for item_id, item_name, price, max_amount in items:
        # Prüfe ob Item noch gekauft werden kann
        from database import db_Wallet_can_buy_item
        can_buy = db_Wallet_can_buy_item(game_id, wallet_type, wallet_name, item_id)
        
        if budget >= price and not cooldown_active and can_buy:
            shop_message += f"• `/buy {item_id}` - {item_name}\n"
        else:
            shop_message += f"• ~~`/buy {item_id}`~~ - {item_name}\n"
    
    # Erstelle Reply-Keyboard - Shop-spezifische Tastatur
    keyboard = {
        "keyboard": [
            ["/buy 1", "/buy 2", "/buy 3", "/buy 4"],
            ["/back", "/help"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    await bot.send_message(chat_id, shop_message, reply_markup=keyboard)

async def show_gamemaster_shop_overview(bot, chat_id, game_id):
    """Zeigt Gamemaster eine Übersicht aller Wallets und Items"""
    logger_newLog("info", "show_gamemaster_shop_overview", f"Shop-Übersicht für Gamemaster in Spiel {game_id}")
    
    from database import (db_Wallet_get_all_for_game, db_getRunners, db_getHunters, 
                         db_Game_getRunnerShop1amount, db_Game_getRunnerShop2amount, 
                         db_Game_getRunnerShop3amount, db_Game_getRunnerShop4amount,
                         db_Game_getHunterShop1amount, db_Game_getHunterShop2amount,
                         db_Game_getHunterShop3amount, db_Game_getHunterShop4amount)
    
    # Hole alle Wallets für das Spiel
    wallets = db_Wallet_get_all_for_game(game_id)
    
    if not wallets:
        await bot.send_message(chat_id, "🛒 Shop-Übersicht\n\n❌ Keine Wallets gefunden. Das Spiel muss erst gestartet werden.")
        return
    
    # Hole Shop-Cooldown für das Spiel
    from database import db_Game_getShopCooldown
    cooldown_minutes = db_Game_getShopCooldown(game_id)
    
    # Erstelle Übersicht
    overview_message = f"🛒 Shop-Übersicht - Spiel {game_id}\n\n"
    
    # Trenne Runner und Hunter Wallets
    runner_wallets = [w for w in wallets if w[2] == "runner"]  # type ist in Spalte 2
    hunter_wallets = [w for w in wallets if w[2] == "hunter"]
    
    # Runner-Übersicht
    if runner_wallets:
        overview_message += "🏃 Runner:\n"
        for wallet in runner_wallets:
            runner_user_id = wallet[3]  # name ist in Spalte 3 (enthält user_id als String)
            budget = wallet[4]  # budget ist in Spalte 4
            last_purchase = wallet[5]  # last_purchase ist in Spalte 5
            
            # Hole User-Name aus der Datenbank
            from database import db_User_get
            user = db_User_get(int(runner_user_id))
            if user:
                runner_name = user[1] or user[2] or f"User_{runner_user_id}"  # username or first_name
            else:
                runner_name = f"User_{runner_user_id}"
            
            # Hole verfügbare Items
            from database import db_Wallet_get_available_items
            available_items = db_Wallet_get_available_items(game_id, "runner", runner_user_id)
            
            # Formatiere Items als [1] 2 [2] 1 [3] 0 [4] 1
            items_display = ""
            for item_id in range(1, 5):
                count = available_items.get(str(item_id), 0)
                items_display += f"[{item_id}] {count} "
            
            # Prüfe Cooldown
            cooldown_status = "✅"
            if last_purchase:
                from datetime import datetime, timedelta
                try:
                    last_purchase_dt = datetime.fromisoformat(last_purchase)
                    now = datetime.now()
                    if now - last_purchase_dt < timedelta(minutes=cooldown_minutes):
                        remaining = cooldown_minutes - int((now - last_purchase_dt).total_seconds() / 60)
                        cooldown_status = f"⏳{remaining}m"
                except Exception:
                    pass
            
            overview_message += f"• {runner_name} {budget}💰 {cooldown_status}\n"
            overview_message += f"  {items_display.strip()}\n\n"
    
    # Hunter-Übersicht
    if hunter_wallets:
        overview_message += "🦊 Hunter Teams:\n"
        for wallet in hunter_wallets:
            team_name = wallet[3]  # name ist in Spalte 3
            budget = wallet[4]  # budget ist in Spalte 4
            last_purchase = wallet[5]  # last_purchase ist in Spalte 5
            
            # Hole verfügbare Items
            from database import db_Wallet_get_available_items
            available_items = db_Wallet_get_available_items(game_id, "hunter", team_name)
            
            # Formatiere Items als [1] 2 [2] 1 [3] 0 [4] 1
            items_display = ""
            for item_id in range(1, 5):
                count = available_items.get(str(item_id), 0)
                items_display += f"[{item_id}] {count} "
            
            # Prüfe Cooldown
            cooldown_status = "✅"
            if last_purchase:
                from datetime import datetime, timedelta
                try:
                    last_purchase_dt = datetime.fromisoformat(last_purchase)
                    now = datetime.now()
                    if now - last_purchase_dt < timedelta(minutes=cooldown_minutes):
                        remaining = cooldown_minutes - int((now - last_purchase_dt).total_seconds() / 60)
                        cooldown_status = f"⏳{remaining}m"
                except Exception:
                    pass
            
            overview_message += f"• {team_name} {budget}💰 {cooldown_status}\n"
            overview_message += f"  {items_display.strip()}\n\n"
    
    # Erstelle Reply-Keyboard für Gamemaster
    keyboard = {
        "keyboard": [
            ["/status", "/map"],
            ["/coins", "/endgame"],
            ["/help"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    
    await bot.send_message(chat_id, overview_message, reply_markup=keyboard)

async def cmd_buy(bot, chat_id, user_id, username, command_text):
    """Behandelt /buy Befehl - Kauft ein Shop-Item"""
    logger_newLog("info", "cmd_buy", f"Buy Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib eine Item-ID an: /buy [1-4]")
        return
    
    try:
        item_id = int(command_text.strip())
        if item_id < 1 or item_id > 4:
            await bot.send_message(chat_id, "❌ Ungültige Item-ID. Verwende 1-4.")
            return
    except ValueError:
        await bot.send_message(chat_id, "❌ Ungültige Item-ID. Bitte gib eine Zahl zwischen 1 und 4 ein.")
        return
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    role = existing_user[6]
    team = existing_user[7]
    
    # Prüfe ob Spiel läuft
    from database import db_Game_getStatus, db_Game_getStartTime, db_Game_getRunnerHeadstart
    game_status = db_Game_getStatus(game_id)
    if game_status not in ['headstart', 'running']:
        await bot.send_message(chat_id, "❌ Der Shop ist nur während des Spiels verfügbar.")
        return
    
    # Prüfe Headstart für Hunter
    if role == 'hunter':
        if game_status == 'headstart':
            await bot.send_message(chat_id, "⏳ Der Shop ist für Hunter noch nicht verfügbar.\n🦌 Runner haben noch Headstart - warte bis das Spiel richtig beginnt!")
        return
    
    # Hole Wallet
    from database import db_Wallet_get
    if role == 'runner':
        wallet = db_Wallet_get(game_id, "runner", str(user_id))
        wallet_type = "runner"
        wallet_name = str(user_id)
    elif role == 'hunter' and team:
        wallet = db_Wallet_get(game_id, "hunter", team)
        wallet_type = "hunter"
        wallet_name = team
    else:
        await bot.send_message(chat_id, "❌ Du hast kein Wallet. Nur Runner und Hunter mit Team können den Shop nutzen.")
        return
    
    if not wallet:
        await bot.send_message(chat_id, "❌ Wallet nicht gefunden. Bitte kontaktiere den Gamemaster.")
        return
    
    budget = wallet[4]  # budget ist in Spalte 4
    last_purchase = wallet[5]  # last_purchase ist in Spalte 5
    
    # Prüfe Cooldown
    from database import db_Game_getShopCooldown
    from datetime import datetime, timedelta
    cooldown_minutes = db_Game_getShopCooldown(game_id)
    
    if last_purchase:
        try:
            last_purchase_dt = datetime.fromisoformat(last_purchase)
            now = datetime.now()
            if now - last_purchase_dt < timedelta(minutes=cooldown_minutes):
                remaining = cooldown_minutes - int((now - last_purchase_dt).total_seconds() / 60)
                await bot.send_message(chat_id, f"⏳ Du musst noch {remaining} Minuten warten, bevor du wieder kaufen kannst.")
                return
        except Exception:
            pass
    
    # Hole Item-Preis und Limit basierend auf Rolle
    if role == 'runner':
        from database import (db_Game_getRunnerShop1price, db_Game_getRunnerShop1amount,
                             db_Game_getRunnerShop2price, db_Game_getRunnerShop2amount,
                             db_Game_getRunnerShop3price, db_Game_getRunnerShop3amount,
                             db_Game_getRunnerShop4price, db_Game_getRunnerShop4amount)
        
        prices = [
            db_Game_getRunnerShop1price(game_id),
            db_Game_getRunnerShop2price(game_id),
            db_Game_getRunnerShop3price(game_id),
            db_Game_getRunnerShop4price(game_id)
        ]
        amounts = [
            db_Game_getRunnerShop1amount(game_id),
            db_Game_getRunnerShop2amount(game_id),
            db_Game_getRunnerShop3amount(game_id),
            db_Game_getRunnerShop4amount(game_id)
        ]
        item_names = ["Runner Item 1", "Runner Item 2", "Runner Item 3", "Runner Item 4"]
    else:  # hunter
        from database import (db_Game_getHunterShop1price, db_Game_getHunterShop1amount,
                             db_Game_getHunterShop2price, db_Game_getHunterShop2amount,
                             db_Game_getHunterShop3price, db_Game_getHunterShop3amount,
                             db_Game_getHunterShop4price, db_Game_getHunterShop4amount)
        
        prices = [
            db_Game_getHunterShop1price(game_id),
            db_Game_getHunterShop2price(game_id),
            db_Game_getHunterShop3price(game_id),
            db_Game_getHunterShop4price(game_id)
        ]
        amounts = [
            db_Game_getHunterShop1amount(game_id),
            db_Game_getHunterShop2amount(game_id),
            db_Game_getHunterShop3amount(game_id),
            db_Game_getHunterShop4amount(game_id)
        ]
        item_names = ["Hunter Item 1", "Hunter Item 2", "Hunter Item 3", "Hunter Item 4"]
    
    price = prices[item_id - 1]
    max_amount = amounts[item_id - 1]
    item_name = item_names[item_id - 1]
    
    # Prüfe Budget
    if budget < price:
        await bot.send_message(chat_id, f"❌ Du hast nicht genug Coins. Du brauchst {price} Coins, hast aber nur {budget}.")
        return
    
    # Prüfe ob Item noch gekauft werden kann
    from database import db_Wallet_can_buy_item
    if not db_Wallet_can_buy_item(game_id, wallet_type, wallet_name, item_id):
        await bot.send_message(chat_id, f"❌ Du hast bereits die maximale Anzahl von {item_name} gekauft ({max_amount}x).")
        return
    
    # Führe Item-spezifische Funktion AUS (vor dem Geldabbuchen)
    try:
        from shopitems import (ShopItemRunner1, ShopItemRunner2, ShopItemRunner3, ShopItemRunner4,
                              ShopItemHunter1, ShopItemHunter2, ShopItemHunter3, ShopItemHunter4)
        
        item_success = False
        if role == 'runner':
            if item_id == 1:
                await ShopItemRunner1(bot, chat_id, user_id, username, game_id)
                item_success = True
            elif item_id == 2:
                await ShopItemRunner2(bot, chat_id, user_id, username, game_id)
                item_success = True
            elif item_id == 3:
                await ShopItemRunner3(bot, chat_id, user_id, username, game_id)
                item_success = True
            elif item_id == 4:
                await ShopItemRunner4(bot, chat_id, user_id, username, game_id)
                item_success = True
        else:  # hunter
            if item_id == 1:
                await ShopItemHunter1(bot, chat_id, user_id, username, game_id, team)
                item_success = True
            elif item_id == 2:
                await ShopItemHunter2(bot, chat_id, user_id, username, game_id, team)
                item_success = True
            elif item_id == 3:
                await ShopItemHunter3(bot, chat_id, user_id, username, game_id, team)
                item_success = True
            elif item_id == 4:
                await ShopItemHunter4(bot, chat_id, user_id, username, game_id, team)
                item_success = True
    except Exception as e:
        logger_newLog("error", "cmd_buy", f"Fehler bei Item-Funktion: {str(e)}")
        await bot.send_message(chat_id, "❌ Fehler bei der Item-Aktivierung. Kauf abgebrochen.")
        return
    
    # Nur wenn Item-Funktion erfolgreich war: Geld abbuchen
    if item_success:
        from database import db_Wallet_update_budget, db_Wallet_update_last_purchase, db_Wallet_decrement_item, db_Wallet_get_available_items
        
        new_budget = budget - price
        if db_Wallet_update_budget(game_id, wallet_type, wallet_name, new_budget) and db_Wallet_update_last_purchase(game_id, wallet_type, wallet_name):
            # Reduziere verfügbare Items
            if db_Wallet_decrement_item(game_id, wallet_type, wallet_name, item_id):
                # Hole neue verfügbare Anzahl für Nachricht
                available_items = db_Wallet_get_available_items(game_id, wallet_type, wallet_name)
                new_available_count = available_items.get(str(item_id), 0)
                
                await bot.send_message(chat_id, f"✅ Kauf erfolgreich!\n\n🛒 Item: {item_name}\n💰 Preis: {price} Coins\n💳 Neues Budget: {new_budget} Coins\n📦 Verfügbar: {new_available_count}\n⏳ Nächster Kauf in: {cooldown_minutes} Minuten")
                
                # Sende Standard-Tastatur zurück
                from telegram_helpmessage import send_helpmessage
                await send_helpmessage(bot, user_id, chat_id)
                
                logger_newLog("info", "cmd_buy", f"Item {item_id} von {username} ({user_id}) gekauft für {price} Coins")
            else:
                await bot.send_message(chat_id, f"❌ Item nicht mehr verfügbar. Kauf abgebrochen.")
                return
        else:
            await bot.send_message(chat_id, "❌ Fehler beim Kauf. Bitte versuche es später erneut.")
            logger_newLog("error", "cmd_buy", f"Fehler beim Kauf von Item {item_id} durch {username}")
    else:
        await bot.send_message(chat_id, "❌ Item-Aktivierung fehlgeschlagen. Kauf abgebrochen.")

async def cmd_status(bot, chat_id, user_id, username, command_text):
    """Behandelt /status Befehl - Zeigt aktuellen Spielstatus"""
    logger_newLog("info", "cmd_status", f"Status Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    role = existing_user[6]
    
    # Hole Spieldaten
    from database import db_Game_getField, db_Game_getStatus, db_Game_getDuration, db_Game_getStartTime, db_Game_getRunnerHeadstart
    from datetime import datetime, timedelta
    
    game = db_Game_getField(game_id)
    if not game:
        await bot.send_message(chat_id, "❌ Spieldaten konnten nicht geladen werden.")
        return
    
    spielname = game[1]
    status = db_Game_getStatus(game_id)
    
    # Erstelle Status-Nachricht
    status_message = f"🎮 Spielstatus: {spielname}\n\n"
    status_message += f"📊 Status: {status}\n"
    status_message += f"🎭 Deine Rolle: {role}\n"
    
    if status in ("headstart", "running"):
        # Berechne Restzeit
        duration = db_Game_getDuration(game_id)
        start_time_str = db_Game_getStartTime(game_id)
        headstart_minutes = db_Game_getRunnerHeadstart(game_id) or 0
        
        if duration and start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                end_time = start_time + timedelta(minutes=duration)
                now = datetime.now()
                
                if end_time > now:
                    delta = end_time - now
                    mins = delta.seconds // 60
                    restzeit = f"{mins//60:02d}:{mins%60:02d}"
                    status_message += f"⏱️ Restzeit: {restzeit}\n"
                else:
                    status_message += "⏱️ Restzeit: Spiel beendet\n"
                
                # Zeige Headstart-Info
                if status == "headstart":
                    status_message += f"🏃 Runner-Vorsprung: {headstart_minutes} Minuten\n"
                    status_message += "🦊 Hunter: Warten noch auf Start\n"
                elif status == "running":
                    status_message += "🏃 Runner: Auf der Flucht\n"
                    status_message += "🦊 Hunter: Auf der Jagd\n"
                    
            except Exception as e:
                logger_newLog("error", "cmd_status", f"Fehler bei Zeitberechnung: {str(e)}")
                status_message += "⏱️ Restzeit: Fehler bei Berechnung\n"
    
    # Hole Spieler-Statistiken
    from database import db_getRunners, db_getHunters
    runners = db_getRunners(game_id)
    hunters = db_getHunters(game_id)
    
    status_message += f"\n👥 Spieler:\n"
    status_message += f"🏃 Runner: {len(runners)}\n"
    status_message += f"🦊 Hunter: {len(hunters)}\n"
    
    # Zeige Team-Info für Hunter
    if role == "hunter":
        team = existing_user[7]
        if team:
            from database import db_getTeamMembers
            team_members = db_getTeamMembers(game_id, team)
            status_message += f"🎨 Dein Team: {team} ({len(team_members)} Mitglieder)\n"
    
    await bot.send_message(chat_id, status_message)

async def cmd_endgame(bot, chat_id, user_id, username, command_text):
    # TODO: Implementierung /endgame
    await bot.send_message(chat_id, "/endgame ist noch nicht implementiert.")

async def cmd_startgame(bot, chat_id, user_id, username, command_text):
    """Behandelt /startgame Befehl - Gamemaster startet das Spiel"""
    logger_newLog("info", "cmd_startgame", f"Startgame Befehl von {username} ({user_id})")
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können das Spiel starten.")
        return
    
    # Prüfe ob Spielfeld konfiguriert ist
    from database import db_Game_getField
    game = db_Game_getField(game_id)
    if not game:
        await bot.send_message(chat_id, "❌ Spieldaten konnten nicht geladen werden.")
        return
    
    # Prüfe Spielfeld-Ecken (mindestens 4 Koordinaten)
    field_corners = [
        game[4], game[5],   # corner1_lat, corner1_lon
        game[6], game[7],   # corner2_lat, corner2_lon
        game[8], game[9],   # corner3_lat, corner3_lon
        game[10], game[11]  # corner4_lat, corner4_lon
    ]
    
    if any(corner is None for corner in field_corners):
        await bot.send_message(chat_id, "❌ Das Spielfeld ist nicht vollständig konfiguriert.\n\nBitte verwende `/fieldsetup` um alle 4 Spielfeld-Ecken zu setzen.")
        return
    
    # Prüfe Ziellinie (mindestens 2 Koordinaten)
    finish_line = [
        game[12], game[13],  # finish_line1_lat, finish_line1_lon
        game[14], game[15]   # finish_line2_lat, finish_line2_lon
    ]
    
    if any(finish is None for finish in finish_line):
        await bot.send_message(chat_id, "❌ Die Ziellinie ist nicht konfiguriert.\n\nBitte verwende `/fieldsetup` um die Ziellinie zu setzen.")
        return
    
    # Prüfe Spieldauer
    from database import db_Game_getDuration
    duration = db_Game_getDuration(game_id)
    if not duration or duration <= 0:
        await bot.send_message(chat_id, "❌ Die Spieldauer ist nicht konfiguriert.\n\nBitte verwende `/fieldsetup` um eine Spieldauer zu setzen.")
        return
    
    # Prüfe ob Spiel bereits läuft
    from database import db_Game_getStatus
    current_status = db_Game_getStatus(game_id)
    if current_status in ['headstart', 'running']:
        await bot.send_message(chat_id, f"❌ Das Spiel läuft bereits!\n\nAktueller Status: {current_status.capitalize()}\n\nVerwende `/endgame` um das Spiel zu beenden.")
        logger_newLog("warning", "cmd_startgame", f"Spiel {game_id} bereits gestartet (Status: {current_status}) - Start abgebrochen")
        return
    
    # Setze Startzeit und Status
    from datetime import datetime
    start_time = datetime.now().isoformat()
    
    from database import db_Game_setStartTime, db_Game_setStatus, db_Game_getDuration, db_getRunners, db_getHunters, db_Game_getRunnerHeadstart
    from config import conf_getMaxLocationAgeMinutes
    max_age_min = conf_getMaxLocationAgeMinutes()
    
    if db_Game_setStartTime(game_id, start_time) and db_Game_setStatus(game_id, 'headstart'):
        logger_newLog("info", "cmd_startgame", f"Spiel {game_id} von Gamemaster {username} ({user_id}) gestartet")
        
        # Erstelle Wallets für alle Runner und Teams
        from database import (db_Game_getStartBudgetRunner, db_Game_getStartBudgetHunter, 
                             db_Wallet_create, db_getRunners, db_getHunters)
        
        runner_budget = db_Game_getStartBudgetRunner(game_id)
        hunter_budget = db_Game_getStartBudgetHunter(game_id)
        
        # Erstelle Wallets für Runner
        runners = db_getRunners(game_id)
        for runner in runners:
            runner_user_id = runner[0]
            db_Wallet_create(game_id, "runner", str(runner_user_id), runner_budget)
        
        # Erstelle Wallets für Hunter-Teams
        hunters = db_getHunters(game_id)
        teams_created = set()
        for hunter in hunters:
            team = hunter[2]  # team ist in Spalte 2
            if team and team not in teams_created:
                db_Wallet_create(game_id, "hunter", team, hunter_budget)
                teams_created.add(team)
        
        logger_newLog("info", "cmd_startgame", f"Wallets erstellt: {len(runners)} Runner, {len(teams_created)} Teams")
        
        # Generiere Tokens für alle Spieler
        from WebExport import generate_game_tokens
        if generate_game_tokens(game_id):
            logger_newLog("info", "cmd_startgame", f"✅ Tokens für Spiel {game_id} erfolgreich generiert")
        else:
            logger_newLog("error", "cmd_startgame", f"❌ Fehler beim Generieren der Tokens für Spiel {game_id}")
            await bot.send_message(chat_id, "⚠️ Spiel gestartet, aber Fehler beim Generieren der Web-Tokens.")
        
        # Exportiere GameData beim Spielstart
        from WebExport import WebExport_GameData
        if WebExport_GameData(game_id):
            logger_newLog("info", "cmd_startgame", f"✅ GameData für Spiel {game_id} erfolgreich exportiert")
        else:
            logger_newLog("error", "cmd_startgame", f"❌ Fehler beim GameData-Export für Spiel {game_id}")
            await bot.send_message(chat_id, "⚠️ Spiel gestartet, aber Fehler beim Web-Export.")
        
        # Hole alle Runner und Hunter
        from database import db_getRunners, db_getHunters
        runners = db_getRunners(game_id)
        hunters = db_getHunters(game_id)
        from datetime import datetime, timedelta
        now = datetime.now()
        # Hole Spieldauer für Nachricht
        duration_minutes = db_Game_getDuration(game_id) or 0
        hours = duration_minutes // 60
        minutes = duration_minutes % 60
        time_str = f"{hours:02d}:{minutes:02d}"
        # Prüfe Standortdaten
        player_status = []
        all_ok = True
        for runner in runners:
            name = runner[1] or f"User_{runner[0]}"
            ts = runner[5]
            ok = False
            if ts:
                try:
                    ts_dt = datetime.fromisoformat(ts)
                    if now - ts_dt < timedelta(minutes=max_age_min):
                        ok = True
                except Exception:
                    pass
            if not ok:
                all_ok = False
                await bot.send_message(runner[0], f"❌ Bitte aktiviere deinen Live-Standort für mindestens {time_str} und teile ihn erneut, damit das Spiel starten kann!")
            player_status.append((name, ok, 'Runner'))
        for hunter in hunters:
            name = hunter[1] or f"User_{hunter[0]}"
            ts = hunter[5]
            ok = False
            if ts:
                try:
                    ts_dt = datetime.fromisoformat(ts)
                    if now - ts_dt < timedelta(minutes=max_age_min):
                        ok = True
                except Exception:
                    pass
            if not ok:
                all_ok = False
                await bot.send_message(hunter[0], f"❌ Bitte aktiviere deinen Live-Standort für mindestens {time_str} und teile ihn erneut, damit das Spiel starten kann!")
            player_status.append((name, ok, 'Hunter'))
        if not all_ok:
            # Sende Übersicht an Gamemaster
            status_lines = []
            for name, ok, role in player_status:
                if not ok:
                    # Berechne Zeit seit letztem Standort
                    ts = None
                    if role == 'Runner':
                        for runner in runners:
                            if (runner[1] or f"User_{runner[0]}") == name:
                                ts = runner[5]
                                break
                    else:  # Hunter
                        for hunter in hunters:
                            if (hunter[1] or f"User_{hunter[0]}") == name:
                                ts = hunter[5]
                                break
                    
                    time_since_location = "unbekannt"
                    if ts:
                        try:
                            ts_dt = datetime.fromisoformat(ts)
                            time_diff = now - ts_dt
                            minutes = int(time_diff.total_seconds() // 60)
                            seconds = int(time_diff.total_seconds() % 60)
                            time_since_location = f"{minutes:02d}:{seconds:02d}"
                        except Exception:
                            pass
                    
                    status_lines.append(f"{name} ⏰ {time_since_location}")
            
            await bot.send_message(chat_id, f"❌ Das Spiel kann nicht gestartet werden.\n\nSpieler ohne aktuellen Standort:\n" + "\n".join(status_lines))
            logger_newLog("warning", "cmd_startgame", f"Spielstart abgebrochen, nicht alle Spieler haben aktuelle Standortdaten.")
            return
        
        # Hole Spieldauer
        duration_minutes = db_Game_getDuration(game_id)
        # Hole Runner-Vorsprung
        headstart_minutes = db_Game_getRunnerHeadstart(game_id) or 0
        if duration_minutes:
            # Formatiere Zeit als hh:mm
            hours = duration_minutes // 60
            minutes = duration_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            # Hole alle Runner
            runners = db_getRunners(game_id)
            
            # Live-Map-Links für alle Spieler generieren
            from WebExport import get_live_map_link
            from database import db_User_getPlayerToken, db_TeamToken_get
            
            # Sende Nachricht an alle Runner
            runner_count = 0
            for runner in runners:
                try:
                    runner_user_id = runner[0]  # user_id ist in Spalte 0
                    runner_token = db_User_getPlayerToken(runner_user_id)
                    live_map_link = get_live_map_link(game_id, runner_token) if runner_token else "Token nicht verfügbar"
                    
                    runner_message = f"🏁 Das Spiel ist gestartet!\n\n⏱️ Du hast {time_str} Zeit um das Ziel zu erreichen.\n\n🗺️ Sende `/map` um eine aktuelle Karte zu bekommen.\n\n🌐 Live-Map: {live_map_link}\n💡 Die Live-Karte aktualisiert sich automatisch und funktioniert auch auf Tablet/Handy!"
                    await bot.send_message(runner_user_id, runner_message)
                    # Sende Standard-Tastatur
                    await send_helpmessage(bot, runner_user_id, runner_user_id)
                    runner_count += 1
                    logger_newLog("info", "cmd_startgame", f"Runner-Nachricht an User {runner[1]} ({runner_user_id}) gesendet")
                except Exception as e:
                    logger_newLog("error", "cmd_startgame", f"Fehler beim Senden der Runner-Nachricht an User {runner[1]} ({runner[0]}): {str(e)}")
            
            # Hole alle Hunter
            hunters = db_getHunters(game_id)
            hunter_count = 0
            for hunter in hunters:
                try:
                    hunter_user_id = hunter[0]  # user_id ist in Spalte 0
                    hunter_team = hunter[2]  # team ist in Spalte 2
                    team_token = db_TeamToken_get(game_id, hunter_team) if hunter_team else None
                    live_map_link = get_live_map_link(game_id, team_token) if team_token else "Token nicht verfügbar"
                    
                    hunter_message = f"🏁 Das Spiel wurde gestartet!\n\nDie Runner haben {time_str} Zeit das Ziel zu erreichen.\nDu musst noch {headstart_minutes} Minuten warten, bis du die Verfolgung aufnehmen darfst.\n\n🌐 Live-Map: {live_map_link}\n💡 Die Live-Karte aktualisiert sich automatisch und funktioniert auch auf Tablet/Handy!"
                    await bot.send_message(hunter_user_id, hunter_message)
                    # Sende Standard-Tastatur
                    await send_helpmessage(bot, hunter_user_id, hunter_user_id)
                    hunter_count += 1
                    logger_newLog("info", "cmd_startgame", f"Hunter-Nachricht an User {hunter[1]} ({hunter_user_id}) gesendet")
                except Exception as e:
                    logger_newLog("error", "cmd_startgame", f"Fehler beim Senden der Hunter-Nachricht an User {hunter[1]} ({hunter[0]}): {str(e)}")
            
            # Sende auch /help an den Gamemaster
            try:
                await send_helpmessage(bot, user_id, chat_id)
                logger_newLog("info", "cmd_startgame", f"Gamemaster-Tastatur an User {username} ({user_id}) gesendet")
            except Exception as e:
                logger_newLog("error", "cmd_startgame", f"Fehler beim Senden der Gamemaster-Tastatur an {username}: {str(e)}")
            
            # Sende Bestätigung an Gamemaster
            runner_list = "\n".join([f"• {runner[1] or f'User_{runner[0]}'}" for runner in runners])
            hunter_list = "\n".join([f"• {hunter[1] or f'User_{hunter[0]}'}" for hunter in hunters])
            
            # Live-Map-Link generieren
            from WebExport import get_live_map_link
            from database import db_Game_getGamemasterToken
            gamemaster_token = db_Game_getGamemasterToken(game_id)
            live_map_link = get_live_map_link(game_id, gamemaster_token) if gamemaster_token else "Token nicht verfügbar"
            
            message = f"✅ Spiel erfolgreich gestartet!\n⏱️ Spieldauer: {time_str}\n🏃 {runner_count} von {len(runners)} Runner benachrichtigt:\n{runner_list}\n\n🦊 {hunter_count} von {len(hunters)} Hunter benachrichtigt:\n{hunter_list}\n\n🗺️ Live-Map: {live_map_link}\n💡 Die Live-Karte kann auch auf einem Tablet oder ähnlichem genutzt werden und aktualisiert oft schneller als die Karte in Telegram!"
            await bot.send_message(chat_id, message)
        else:
            await bot.send_message(chat_id, "✅ Spiel gestartet, aber Spieldauer nicht konfiguriert.")
    else:
        logger_newLog("error", "cmd_startgame", f"Fehler beim Starten des Spiels {game_id}")
        await bot.send_message(chat_id, "❌ Fehler beim Starten des Spiels.")
        return 

async def cmd_listgames(bot, chat_id):
    from database import db_getGamesWithStatus
    games = db_getGamesWithStatus('created')
    if not games:
        msg = "Es gibt aktuell keine offenen Spiele.\nDu kannst mit /new Spielname ein neues Spiel erstellen."
    else:
        msg = "Offene Spiele:\n"
        for game in games:
            msg += f"ID: {game[0]} | Name: {game[1]}\n"
        msg += "\nMit /join <GameID> kannst du einem Spiel beitreten.\nMit /new <Spielname> kannst du ein neues Spiel erstellen."
    await bot.send_message(chat_id, msg) 

async def cmd_keyboard(bot, chat_id, user_id, username, command_text):
    """Behandelt /keyboard Befehl - Zeigt rollenabhängige Reply-Keyboards"""
    logger_newLog("info", "cmd_keyboard", f"Keyboard Befehl von {username} ({user_id})")
    
    from database import db_User_get, db_Game_getField, db_Game_getDuration, db_Game_getStartTime
    from datetime import datetime, timedelta
    
    user = db_User_get(user_id)
    if not user:
        # Nicht registriert - nur /start
        keyboard = {
            "keyboard": [
                ["/start"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, "🎮 ChaseBot - Registrierung\n\nDu bist noch nicht registriert.", reply_markup=keyboard)
        return
    
    game_id = user[8]
    role = user[6]
    
    if not game_id:
        # Registriert aber nicht in Spiel - ohne /start
        keyboard = {
            "keyboard": [
                ["/new", "/join"],
                ["/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, "🎮 ChaseBot - Hauptmenü\n\nDu bist registriert aber nicht in einem Spiel.", reply_markup=keyboard)
        return
    
    game = db_Game_getField(game_id)
    if not game:
        # Spieldaten nicht gefunden
        keyboard = {
            "keyboard": [
                ["/leave", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, "❌ Spieldaten konnten nicht geladen werden.", reply_markup=keyboard)
        return
    
    spielname = game[1]
    status = game[3]
    
    # Berechne Restzeit für laufende Spiele
    restzeit = None
    if status in ("headstart", "running"):
        duration = db_Game_getDuration(game_id)
        start_time_str = db_Game_getStartTime(game_id)
        if duration and start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                end_time = start_time + timedelta(minutes=duration)
                now = datetime.now()
                if end_time > now:
                    delta = end_time - now
                    mins = delta.seconds // 60
                    restzeit = f"{mins//60:02d}:{mins%60:02d}"
            except Exception:
                pass
    
    # Erstelle Keyboard basierend auf Status und Rolle
    if status == 'created':
        # Spiel läuft noch nicht
        if not role or role == 'none':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nDas Spiel hat noch nicht begonnen.\nDu hast noch keine Rolle zugewiesen bekommen.", reply_markup=keyboard)
        elif role == 'runner':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nDu bist Runner. Warte auf den Start durch den Gamemaster.", reply_markup=keyboard)
        elif role == 'hunter':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nDu bist Hunter. Warte auf den Start durch den Gamemaster.", reply_markup=keyboard)
        elif role == 'gamemaster':
            keyboard = {
                "keyboard": [
                    ["/mapedit", "/listusers"],
                    ["/role", "/team"],
                    ["/coins", "/startgame"],
                    ["/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Gamemaster - Spiel: {spielname}\n\nVerfügbare Befehle:", reply_markup=keyboard)
        elif role == 'spectator':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nDu bist Zuschauer.", reply_markup=keyboard)
    
    elif status in ('headstart', 'running'):
        # Spiel läuft
        status_text = f"Das Spiel läuft. Restzeit: {restzeit}" if restzeit else "Das Spiel läuft."
        
        if role == 'runner':
            keyboard = {
                "keyboard": [
                    ["/map"],
                    ["/shop", "/status", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Runner - Spiel: {spielname}\n\n{status_text}\nDu bist auf der Flucht vor den Huntern!", reply_markup=keyboard)
        elif role == 'hunter':
            keyboard = {
                "keyboard": [
                    ["/map"],
                    ["/shop", "/status", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Hunter - Spiel: {spielname}\n\n{status_text}\nDu bist auf der Jagd nach den Runnern!", reply_markup=keyboard)
        elif role == 'gamemaster':
            keyboard = {
                "keyboard": [
                    ["/status", "/map"],
                    ["/coins", "/endgame"],
                    ["/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Gamemaster - Spiel: {spielname}\n\n{status_text}\nDu kannst das Spiel überwachen und ggf. beenden.", reply_markup=keyboard)
        elif role == 'spectator':
            keyboard = {
                "keyboard": [
                    ["/map", "/leave"],
                    ["/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Zuschauer - Spiel: {spielname}\n\n{status_text}", reply_markup=keyboard)
    
    elif status == 'ended':
        # Spiel ist beendet
        if role == 'runner' or role == 'hunter':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nDas Spiel ist beendet.\nWarte auf die Auswertung durch den Gamemaster.", reply_markup=keyboard)
        elif role == 'gamemaster':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Gamemaster - Spiel: {spielname}\n\nDas Spiel ist beendet.\nBitte führe die Auswertung und Siegerehrung durch.", reply_markup=keyboard)
        elif role == 'spectator':
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            await bot.send_message(chat_id, f"🎮 Zuschauer - Spiel: {spielname}\n\nDas Spiel ist beendet.", reply_markup=keyboard)
    
    else:
        # Fallback
        keyboard = {
            "keyboard": [
                ["/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, f"🎮 Spiel: {spielname}\n\nUnbekannter Spielstatus.", reply_markup=keyboard)

async def cmd_coins(bot, chat_id, user_id, username, command_text):
    """Behandelt /coins Befehl - Gamemaster fügt Coins hinzu oder entfernt sie"""
    logger_newLog("info", "cmd_coins", f"Coins Befehl von {username} ({user_id}): {command_text}")
    
    if not command_text.strip():
        await bot.send_message(chat_id, "❌ Bitte gib Ziel und Betrag an: /coins <Team/User> <Betrag>")
        return
    
    # Prüfe ob User existiert und in einem Spiel ist
    existing_user = db_User_get(user_id)
    if not existing_user:
        await bot.send_message(chat_id, "❌ Du bist in keinem Spiel registriert.")
        return
    
    if existing_user[8] is None:  # game_id ist in Spalte 8
        await bot.send_message(chat_id, "❌ Du bist derzeit in keinem Spiel.")
        return
    
    game_id = existing_user[8]
    
    # Prüfe ob User Gamemaster ist
    if existing_user[6] != "gamemaster":  # role ist in Spalte 6
        await bot.send_message(chat_id, "❌ Nur Gamemaster können Coins verwalten.")
        return
    
    # Parse Kommando
    parts = command_text.strip().split()
    if len(parts) != 2:
        await bot.send_message(chat_id, "❌ Bitte gib genau Ziel und Betrag an: /coins <Team/User> <Betrag>")
        return
    
    target_name, coin_amount_str = parts
    
    # Validiere Coin-Betrag
    try:
        coin_amount = int(coin_amount_str)
    except ValueError:
        await bot.send_message(chat_id, "❌ Ungültiger Betrag. Bitte gib eine Zahl ein.")
        return
    
    # Finde das Ziel (User oder Team)
    from database import db_getUsers, db_Wallet_get, db_Wallet_update_budget
    users = db_getUsers()
    target_user = None
    target_team = None
    
    # Prüfe ob es ein Team ist (erlaubte Team-Farben)
    allowed_teams = ["red", "blue", "green", "yellow", "purple"]
    if target_name.lower() in allowed_teams:
        target_team = target_name.lower()
        wallet = db_Wallet_get(game_id, "hunter", target_team)
        if not wallet:
            await bot.send_message(chat_id, f"❌ Team '{target_team}' hat kein Wallet. Das Team muss erst im Spiel sein.")
            return
    else:
        # Suche nach User
        for user in users:
            if user[8] == game_id:  # Nur Spieler im gleichen Spiel
                name = user[1] or user[2] or f"User_{user[0]}"  # username or first_name
                if name.lower() == target_name.lower():
                    target_user = user
                    break
        
        if not target_user:
            await bot.send_message(chat_id, f"❌ Spieler '{target_name}' nicht im Spiel gefunden.")
            return
        
        # Prüfe ob User Runner ist (nur Runner haben individuelle Wallets)
        if target_user[6] != "runner":
            await bot.send_message(chat_id, f"❌ Nur Runner haben individuelle Wallets. '{target_name}' ist {target_user[6]}.")
            return
        
        target_user_id = target_user[0]
        wallet = db_Wallet_get(game_id, "runner", str(target_user_id))
        if not wallet:
            await bot.send_message(chat_id, f"❌ Runner '{target_name}' hat kein Wallet. Das Spiel muss erst gestartet sein.")
            return
    
    # Hole aktuelles Budget
    current_budget = wallet[4]  # budget ist in Spalte 4
    new_budget = current_budget + coin_amount
    
    # Prüfe ob Budget nicht negativ wird
    if new_budget < 0:
        await bot.send_message(chat_id, f"❌ Das Budget würde negativ werden ({new_budget}). Mindestbetrag ist 0.")
        return
    
    # Aktualisiere Budget
    if target_team:
        wallet_type = "hunter"
        wallet_name = target_team
        target_display = f"Team {target_team}"
    else:
        wallet_type = "runner"
        wallet_name = str(target_user_id)
        target_display = target_name
    
    if db_Wallet_update_budget(game_id, wallet_type, wallet_name, new_budget):
        # Erstelle Nachricht
        if coin_amount > 0:
            action = "hinzugefügt"
            emoji = "➕"
        else:
            action = "entfernt"
            emoji = "➖"
        
        message = f"✅ Coins erfolgreich {action}!\n\n"
        message += f"🎯 Ziel: {target_display}\n"
        message += f"{emoji} Betrag: {abs(coin_amount)} Coins\n"
        message += f"💰 Altes Budget: {current_budget} Coins\n"
        message += f"💳 Neues Budget: {new_budget} Coins"
        
        await bot.send_message(chat_id, message)
        
        # Benachrichtige den betroffenen Spieler (nur bei Runnern)
        if not target_team:
            try:
                notification = f"💰 Der Gamemaster hat dir {abs(coin_amount)} Coins {action}.\n"
                notification += f"💳 Dein neues Budget: {new_budget} Coins"
                await bot.send_message(target_user_id, notification)
            except Exception as e:
                logger_newLog("error", "cmd_coins", f"Fehler beim Benachrichtigen von {target_name}: {str(e)}")
        
        logger_newLog("info", "cmd_coins", f"Coins {action}: {abs(coin_amount)} für {target_display} durch Gamemaster {username}")
    else:
        await bot.send_message(chat_id, "❌ Fehler beim Aktualisieren des Budgets. Bitte versuche es später erneut.")
        logger_newLog("error", "cmd_coins", f"Fehler beim Aktualisieren des Budgets für {target_display}")