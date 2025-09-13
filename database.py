import sqlite3
from logger import logger_newLog
from config import conf_getDatabaseFile
from datetime import datetime

def db_init():
    """Initialisiert die SQLite Datenbank"""
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Erstelle users Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                first_seen TIMESTAMP,
                last_seen TIMESTAMP,
                is_banned BOOLEAN DEFAULT 0,
                role TEXT DEFAULT 'none',
                team TEXT,
                game_id INTEGER,
                location_lat REAL,
                location_lon REAL,
                location_timestamp TIMESTAMP,
                player_token TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        ''')
        
        # Erstelle games Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS games (
                game_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                gamemaster_id INTEGER NOT NULL,
                status TEXT DEFAULT 'created',
                start_time TIMESTAMP,
                duration_minutes INTEGER,
                runner_headstart_minutes INTEGER,
                gamemaster_token TEXT,
                -- Spielfeld-Ecken (Rechteck)
                field_corner1_lat REAL,
                field_corner1_lon REAL,
                field_corner2_lat REAL,
                field_corner2_lon REAL,
                field_corner3_lat REAL,
                field_corner3_lon REAL,
                field_corner4_lat REAL,
                field_corner4_lon REAL,
                -- Ziellinie (2 Punkte)
                finish_line1_lat REAL,
                finish_line1_lon REAL,
                finish_line2_lat REAL,
                finish_line2_lon REAL,
                -- Shop-Konfiguration
                StartBudgetRunner INTEGER,
                StartBudgetHunter INTEGER,
                ShopCooldown INTEGER DEFAULT 15,
                -- Hunter Shop Items (1-4)
                HunterShop1price INTEGER,
                HunterShop1amount INTEGER,
                HunterShop2price INTEGER,
                HunterShop2amount INTEGER,
                HunterShop3price INTEGER,
                HunterShop3amount INTEGER,
                HunterShop4price INTEGER,
                HunterShop4amount INTEGER,
                -- Runner Shop Items (1-4)
                RunnerShop1price INTEGER,
                RunnerShop1amount INTEGER,
                RunnerShop2price INTEGER,
                RunnerShop2amount INTEGER,
                RunnerShop3price INTEGER,
                RunnerShop3amount INTEGER,
                RunnerShop4price INTEGER,
                RunnerShop4amount INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (gamemaster_id) REFERENCES users(user_id)
            )
        ''')
        
        # Erstelle wallet Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wallet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                name TEXT NOT NULL,
                budget INTEGER NOT NULL DEFAULT 0,
                last_purchase TEXT,
                Item1available INTEGER DEFAULT 0,
                Item2available INTEGER DEFAULT 0,
                Item3available INTEGER DEFAULT 0,
                Item4available INTEGER DEFAULT 0,
                UNIQUE(game_id, type, name),
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        ''')
        
        # Erstelle locations Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS locations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                game_id INTEGER NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(user_id),
                FOREIGN KEY (game_id) REFERENCES games(game_id)
            )
        ''')
        
        # Erstelle POI Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS poi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                type TEXT NOT NULL,
                lat REAL NOT NULL,
                lon REAL NOT NULL,
                range_meters INTEGER NOT NULL,
                team TEXT,
                creator_id INTEGER NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                FOREIGN KEY (creator_id) REFERENCES users(user_id)
            )
        ''')
        
        # Erstelle team_tokens Tabelle
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS team_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id INTEGER NOT NULL,
                team TEXT NOT NULL,
                token TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (game_id) REFERENCES games(game_id),
                UNIQUE(game_id, team)
            )
        ''')
        
        conn.commit()
        conn.close()
        logger_newLog("info", "db_init", "Datenbank erfolgreich initialisiert")
        return True
    except Exception as e:
        logger_newLog("error", "db_init", f"Datenbankfehler: {str(e)}")
        return False

def db_get_connection():
    """Gibt eine Datenbankverbindung zurück"""
    db_file = conf_getDatabaseFile()
    conn = sqlite3.connect(db_file, timeout=30.0)  # 30 Sekunden Timeout
    conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging für bessere Performance
    return conn

def db_User_setGameID(user_id, game_id):
    """Setzt die Game ID eines Users"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET game_id = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (game_id, user_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_User_setGameID", f"Game ID für User {user_id} auf {game_id} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_setGameID", f"Fehler beim Setzen der Game ID: {str(e)}")
        return False

def db_User_setTeam(user_id, team):
    """Setzt das Team eines Users (nur Hunter-Farben erlaubt oder None)"""
    # Erlaubte Hunter-Team-Farben
    allowed_teams = ["red", "blue", "green", "yellow", "purple"]
    
    if team is not None and team not in allowed_teams:
        logger_newLog("error", "db_User_setTeam", f"Ungültige Team-Farbe: {team}")
        return False
    
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET team = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (team, user_id))
        
        conn.commit()
        conn.close()
        
        if team is None:
            logger_newLog("info", "db_User_setTeam", f"Team für User {user_id} zurückgesetzt")
        else:
            logger_newLog("info", "db_User_setTeam", f"Team für User {user_id} auf '{team}' gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_setTeam", f"Fehler beim Setzen des Teams: {str(e)}")
        return False

def db_User_setRole(user_id, role):
    """Setzt die Rolle eines Users"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users SET role = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (role, user_id))
        
        conn.commit()
        conn.close()
        db_User_setTeam(user_id, "red")
        logger_newLog("info", "db_User_setRole", f"Rolle für User {user_id} auf '{role}' gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_setRole", f"Fehler beim Setzen der Rolle: {str(e)}")
        return False

def db_Game_new(name, gamemaster_id):
    """Erstellt ein neues Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        # Hole config-Werte
        from config import (conf_getRunnerStartBudget, conf_getHunterStartBudget,
                           conf_getRunnerShop1Price, conf_getRunnerShop1Amount,
                           conf_getRunnerShop2Price, conf_getRunnerShop2Amount,
                           conf_getRunnerShop3Price, conf_getRunnerShop3Amount,
                           conf_getRunnerShop4Price, conf_getRunnerShop4Amount,
                           conf_getHunterShop1Price, conf_getHunterShop1Amount,
                           conf_getHunterShop2Price, conf_getHunterShop2Amount,
                           conf_getHunterShop3Price, conf_getHunterShop3Amount,
                           conf_getHunterShop4Price, conf_getHunterShop4Amount,
                           conf_getShopCooldown)
        
        cursor.execute('''
            INSERT INTO games (name, gamemaster_id, 
                              StartBudgetRunner, StartBudgetHunter,
                              RunnerShop1price, RunnerShop1amount,
                              RunnerShop2price, RunnerShop2amount,
                              RunnerShop3price, RunnerShop3amount,
                              RunnerShop4price, RunnerShop4amount,
                              HunterShop1price, HunterShop1amount,
                              HunterShop2price, HunterShop2amount,
                              HunterShop3price, HunterShop3amount,
                              HunterShop4price, HunterShop4amount,
                              ShopCooldown)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, gamemaster_id,
              conf_getRunnerStartBudget(), conf_getHunterStartBudget(),
              conf_getRunnerShop1Price(), conf_getRunnerShop1Amount(),
              conf_getRunnerShop2Price(), conf_getRunnerShop2Amount(),
              conf_getRunnerShop3Price(), conf_getRunnerShop3Amount(),
              conf_getRunnerShop4Price(), conf_getRunnerShop4Amount(),
              conf_getHunterShop1Price(), conf_getHunterShop1Amount(),
              conf_getHunterShop2Price(), conf_getHunterShop2Amount(),
              conf_getHunterShop3Price(), conf_getHunterShop3Amount(),
              conf_getHunterShop4Price(), conf_getHunterShop4Amount(),
              conf_getShopCooldown()))
        
        game_id = cursor.lastrowid
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_new", f"Neues Spiel erstellt: {name} (ID: {game_id}, Gamemaster: {gamemaster_id})")
        return game_id
    except Exception as e:
        logger_newLog("error", "db_Game_new", f"Fehler beim Erstellen des Spiels: {str(e)}")
        return None

def db_getUsers():
    """Holt alle aktiven User aus der Datenbank"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT user_id, username, first_name, location_lat, location_lon, location_timestamp, role, team, game_id FROM users WHERE is_banned = 0')
        users = cursor.fetchall()
        
        conn.close()
        return users
    except Exception as e:
        logger_newLog("error", "db_getUsers", f"Fehler beim Abrufen der User: {str(e)}")
        return []

def db_User_update_location(user_id, lat, lon):
    """Aktualisiert die Standortdaten eines Users"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE users SET location_lat = ?, location_lon = ?, location_timestamp = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (lat, lon, now, user_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("debug", "db_User_update_location", f"Standort aktualisiert für User {user_id}: {lat}, {lon}")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_update_location", f"Fehler beim Aktualisieren des Standorts: {str(e)}")
        return False

def db_User_get(user_id):
    """Holt einen User aus der Datenbank"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = cursor.fetchone()
        
        conn.close()
        return user
    except Exception as e:
        logger_newLog("error", "db_User_get", f"Fehler beim Abrufen des Users: {str(e)}")
        return None

def db_User_update_lastseen(user_id):
    """Aktualisiert last_seen für einen User"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            UPDATE users SET last_seen = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE user_id = ?
        ''', (now, user_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("debug", "db_User_update_lastseen", f"Last seen aktualisiert für User {user_id}")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_update_lastseen", f"Fehler beim Aktualisieren: {str(e)}")
        return False

def db_User_new(user_id, username, first_name):
    """Fügt einen neuen User zur Datenbank hinzu"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        
        cursor.execute('''
            INSERT INTO users (user_id, username, first_name, first_seen, last_seen, role)
            VALUES (?, ?, ?, ?, ?, 'none')
        ''', (user_id, username, first_name, now, now))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_User_new", f"Neuer User hinzugefügt: {username} ({user_id})")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_new", f"Fehler beim Hinzufügen des Users: {str(e)}")
        return False

def db_Game_setField(game_id, field_coords, finish_coords):
    """Setzt die Spielfeld- und Ziellinien-Koordinaten für ein Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        # Extrahiere die 4 Spielfeld-Koordinaten
        field_corner1_lat, field_corner1_lon = field_coords[0]
        field_corner2_lat, field_corner2_lon = field_coords[1]
        field_corner3_lat, field_corner3_lon = field_coords[2]
        field_corner4_lat, field_corner4_lon = field_coords[3]
        
        # Extrahiere die 2 Ziellinien-Koordinaten
        finish_line1_lat, finish_line1_lon = finish_coords[0]
        finish_line2_lat, finish_line2_lon = finish_coords[1]
        
        cursor.execute('''
            UPDATE games SET 
                field_corner1_lat = ?, field_corner1_lon = ?,
                field_corner2_lat = ?, field_corner2_lon = ?,
                field_corner3_lat = ?, field_corner3_lon = ?,
                field_corner4_lat = ?, field_corner4_lon = ?,
                finish_line1_lat = ?, finish_line1_lon = ?,
                finish_line2_lat = ?, finish_line2_lon = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE game_id = ?
        ''', (field_corner1_lat, field_corner1_lon,
              field_corner2_lat, field_corner2_lon,
              field_corner3_lat, field_corner3_lon,
              field_corner4_lat, field_corner4_lon,
              finish_line1_lat, finish_line1_lon,
              finish_line2_lat, finish_line2_lon,
              game_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_setField", f"Spielfeld für Spiel {game_id} gespeichert")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setField", f"Fehler beim Speichern des Spielfelds: {str(e)}")
        return False

def db_Game_isGamemaster(user_id, game_id):
    """Prüft ob ein User der Gamemaster eines Spiels ist"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT gamemaster_id FROM games WHERE game_id = ?', (game_id,))
        game = cursor.fetchone()
        
        conn.close()
        
        if game and game[0] == user_id:
            logger_newLog("debug", "db_Game_isGamemaster", f"User {user_id} ist Gamemaster von Spiel {game_id}")
            return True
        else:
            logger_newLog("debug", "db_Game_isGamemaster", f"User {user_id} ist nicht Gamemaster von Spiel {game_id}")
            return False
    except Exception as e:
        logger_newLog("error", "db_Game_isGamemaster", f"Fehler beim Prüfen des Gamemaster-Status: {str(e)}")
        return False

def db_Game_getField(game_id):
    """Holt die Spielfeld-Daten für ein Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT game_id, name, gamemaster_id, status,
                   field_corner1_lat, field_corner1_lon,
                   field_corner2_lat, field_corner2_lon,
                   field_corner3_lat, field_corner3_lon,
                   field_corner4_lat, field_corner4_lon,
                   finish_line1_lat, finish_line1_lon,
                   finish_line2_lat, finish_line2_lon,
                   created_at, updated_at
            FROM games WHERE game_id = ?
        ''', (game_id,))
        game = cursor.fetchone()
        
        conn.close()
        
        if game:
            logger_newLog("debug", "db_Game_getField", f"Spielfeld-Daten für Spiel {game_id} gefunden")
            return game
        else:
            logger_newLog("debug", "db_Game_getField", f"Spiel {game_id} nicht gefunden")
            return None
    except Exception as e:
        logger_newLog("error", "db_Game_getField", f"Fehler beim Holen der Spielfeld-Daten: {str(e)}")
        return None

def db_getRunners(game_id):
    """Gibt alle Runner-Positionen für ein Spiel zurück"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, team, location_lat, location_lon, location_timestamp
            FROM users
            WHERE game_id = ? AND role = 'runner' AND is_banned = 0
        ''', (game_id,))
        runners = cursor.fetchall()
        conn.close()
        return runners
    except Exception as e:
        logger_newLog("error", "db_getRunners", f"Fehler: {str(e)}")
        return []

def db_getHunters(game_id, team=None):
    """Gibt alle Hunter-Positionen für ein Spiel zurück, optional nach Team gefiltert"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        if team:
            cursor.execute('''
                SELECT user_id, username, team, location_lat, location_lon, location_timestamp
                FROM users
                WHERE game_id = ? AND role = 'hunter' AND team = ? AND is_banned = 0
            ''', (game_id, team))
        else:
            cursor.execute('''
                SELECT user_id, username, team, location_lat, location_lon, location_timestamp
                FROM users
                WHERE game_id = ? AND role = 'hunter' AND is_banned = 0
            ''', (game_id,))
        hunters = cursor.fetchall()
        conn.close()
        return hunters
    except Exception as e:
        logger_newLog("error", "db_getHunters", f"Fehler: {str(e)}")
        return []

def db_getUserPosition(user_id):
    """Gibt die aktuelle Position eines Users zurück"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, team, location_lat, location_lon, location_timestamp, role, game_id
            FROM users
            WHERE user_id = ? AND is_banned = 0
        ''', (user_id,))
        user = cursor.fetchone()
        conn.close()
        return user
    except Exception as e:
        logger_newLog("error", "db_getUserPosition", f"Fehler: {str(e)}")
        return None

def db_getTeamMembers(game_id, team):
    """Gibt alle Hunter eines Teams in einem Spiel zurück"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT user_id, username, team, location_lat, location_lon, location_timestamp
            FROM users
            WHERE game_id = ? AND role = 'hunter' AND team = ? AND is_banned = 0
        ''', (game_id, team))
        members = cursor.fetchall()
        conn.close()
        return members
    except Exception as e:
        logger_newLog("error", "db_getTeamMembers", f"Fehler: {str(e)}")
        return []

def db_Game_setStartTime(game_id, start_time):
    """Setzt die Startzeit für ein Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE games SET start_time = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE game_id = ?
        ''', (start_time, game_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_setStartTime", f"Startzeit für Spiel {game_id} auf {start_time} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setStartTime", f"Fehler beim Setzen der Startzeit: {str(e)}")
        return False

def db_Game_getStartTime(game_id):
    """Holt die Startzeit eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT start_time FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            logger_newLog("debug", "db_Game_getStartTime", f"Startzeit für Spiel {game_id} gefunden: {result[0]}")
            return result[0]
        else:
            logger_newLog("debug", "db_Game_getStartTime", f"Spiel {game_id} nicht gefunden")
            return None
    except Exception as e:
        logger_newLog("error", "db_Game_getStartTime", f"Fehler beim Holen der Startzeit: {str(e)}")
        return None

def db_Game_setDuration(game_id, duration_minutes):
    """Setzt die Spieldauer für ein Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE games SET duration_minutes = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE game_id = ?
        ''', (duration_minutes, game_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_setDuration", f"Spieldauer für Spiel {game_id} auf {duration_minutes} Minuten gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setDuration", f"Fehler beim Setzen der Spieldauer: {str(e)}")
        return False

def db_Game_getDuration(game_id):
    """Holt die Spieldauer eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT duration_minutes FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            logger_newLog("debug", "db_Game_getDuration", f"Spieldauer für Spiel {game_id} gefunden: {result[0]} Minuten")
            return result[0]
        else:
            logger_newLog("debug", "db_Game_getDuration", f"Spiel {game_id} nicht gefunden")
            return None
    except Exception as e:
        logger_newLog("error", "db_Game_getDuration", f"Fehler beim Holen der Spieldauer: {str(e)}")
        return None

def db_Game_setRunnerHeadstart(game_id, headstart_minutes):
    """Setzt den Vorsprung der Runner für ein Spiel"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE games SET runner_headstart_minutes = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE game_id = ?
        ''', (headstart_minutes, game_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_setRunnerHeadstart", f"Runner-Vorsprung für Spiel {game_id} auf {headstart_minutes} Minuten gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerHeadstart", f"Fehler beim Setzen des Runner-Vorsprungs: {str(e)}")
        return False

def db_Game_getRunnerHeadstart(game_id):
    """Holt den Vorsprung der Runner eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT runner_headstart_minutes FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            logger_newLog("debug", "db_Game_getRunnerHeadstart", f"Runner-Vorsprung für Spiel {game_id} gefunden: {result[0]} Minuten")
            return result[0]
        else:
            logger_newLog("debug", "db_Game_getRunnerHeadstart", f"Spiel {game_id} nicht gefunden")
            return None
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerHeadstart", f"Fehler beim Holen des Runner-Vorsprungs: {str(e)}")
        return None 

def db_Game_setStatus(game_id, status):
    """Setzt den Status eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE games SET status = ?, updated_at = CURRENT_TIMESTAMP 
            WHERE game_id = ?
        ''', (status, game_id))
        
        conn.commit()
        conn.close()
        
        logger_newLog("info", "db_Game_setStatus", f"Status für Spiel {game_id} auf '{status}' gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setStatus", f"Fehler beim Setzen des Status: {str(e)}")
        return False

def db_Game_getStatus(game_id):
    """Holt den Status eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT status FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        
        conn.close()
        
        if result:
            logger_newLog("debug", "db_Game_getStatus", f"Status für Spiel {game_id} gefunden: {result[0]}")
            return result[0]
        else:
            logger_newLog("debug", "db_Game_getStatus", f"Spiel {game_id} nicht gefunden")
            return None
    except Exception as e:
        logger_newLog("error", "db_Game_getStatus", f"Fehler beim Holen des Status: {str(e)}")
        return None 

def db_getGamesWithStatus(status):
    """Gibt alle Spiele mit bestimmtem Status zurück"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM games WHERE status = ?', (status,))
        games = cursor.fetchall()
        conn.close()
        return games
    except Exception as e:
        logger_newLog("error", "db_getGamesWithStatus", f"Fehler: {str(e)}")
        return [] 

# Shop Getter für games Tabelle
def db_Game_getStartBudgetRunner(game_id):
    """Holt das Start-Budget für Runner eines Spiels"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT StartBudgetRunner FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 100
    except Exception as e:
        logger_newLog("error", "db_Game_getStartBudgetRunner", f"Fehler: {str(e)}")
        return 100
    finally:
        if conn:
            conn.close()

def db_Game_getStartBudgetHunter(game_id):
    """Holt das Start-Budget für Hunter eines Spiels"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT StartBudgetHunter FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 100
    except Exception as e:
        logger_newLog("error", "db_Game_getStartBudgetHunter", f"Fehler: {str(e)}")
        return 100
    finally:
        if conn:
            conn.close()

def db_Game_getShopCooldown(game_id):
    """Holt den Shop-Cooldown eines Spiels"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT ShopCooldown FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        if result and result[0] is not None:
            return result[0]
        else:
            # Verwende Config-Wert wenn kein Wert in der Datenbank gesetzt ist
            from config import conf_getShopCooldown
            return conf_getShopCooldown()
    except Exception as e:
        logger_newLog("error", "db_Game_getShopCooldown", f"Fehler: {str(e)}")
        # Fallback auf Config-Wert bei Fehler
        from config import conf_getShopCooldown
        return conf_getShopCooldown()
    finally:
        if conn:
            conn.close()

# Hunter Shop Getter
def db_Game_getHunterShop1price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop1price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 50
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop1price", f"Fehler: {str(e)}")
        return 50
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop1amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop1amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop1amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop2price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop2price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 75
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop2price", f"Fehler: {str(e)}")
        return 75
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop2amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop2amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop2amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop3price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop3price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 100
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop3price", f"Fehler: {str(e)}")
        return 100
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop3amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop3amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop3amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop4price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop4price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 150
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop4price", f"Fehler: {str(e)}")
        return 150
    finally:
        if conn:
            conn.close()

def db_Game_getHunterShop4amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT HunterShop4amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getHunterShop4amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

# Runner Shop Getter
def db_Game_getRunnerShop1price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop1price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 50
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop1price", f"Fehler: {str(e)}")
        return 50
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop1amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop1amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop1amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop2price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop2price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 75
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop2price", f"Fehler: {str(e)}")
        return 75
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop2amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop2amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop2amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop3price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop3price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 100
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop3price", f"Fehler: {str(e)}")
        return 100
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop3amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop3amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop3amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop4price(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop4price FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 150
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop4price", f"Fehler: {str(e)}")
        return 150
    finally:
        if conn:
            conn.close()

def db_Game_getRunnerShop4amount(game_id):
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT RunnerShop4amount FROM games WHERE game_id = ?', (game_id,))
        result = cursor.fetchone()
        return result[0] if result else 1
    except Exception as e:
        logger_newLog("error", "db_Game_getRunnerShop4amount", f"Fehler: {str(e)}")
        return 1
    finally:
        if conn:
            conn.close()

# Shop Setter für games Tabelle
def db_Game_setStartBudgetRunner(game_id, budget):
    """Setzt das Start-Budget für Runner eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET StartBudgetRunner = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (budget, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setStartBudgetRunner", f"Runner-Startbudget für Spiel {game_id} auf {budget} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setStartBudgetRunner", f"Fehler: {str(e)}")
        return False

def db_Game_setStartBudgetHunter(game_id, budget):
    """Setzt das Start-Budget für Hunter eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET StartBudgetHunter = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (budget, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setStartBudgetHunter", f"Hunter-Startbudget für Spiel {game_id} auf {budget} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setStartBudgetHunter", f"Fehler: {str(e)}")
        return False

def db_Game_setShopCooldown(game_id, cooldown):
    """Setzt den Shop-Cooldown eines Spiels"""
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET ShopCooldown = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (cooldown, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setShopCooldown", f"Shop-Cooldown für Spiel {game_id} auf {cooldown} Minuten gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setShopCooldown", f"Fehler: {str(e)}")
        return False

# Hunter Shop Setter
def db_Game_setHunterShop1price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop1price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop1price", f"Hunter Shop 1 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop1price", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop1amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop1amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop1amount", f"Hunter Shop 1 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop1amount", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop2price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop2price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop2price", f"Hunter Shop 2 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop2price", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop2amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop2amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop2amount", f"Hunter Shop 2 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop2amount", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop3price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop3price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop3price", f"Hunter Shop 3 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop3price", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop3amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop3amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop3amount", f"Hunter Shop 3 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop3amount", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop4price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop4price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop4price", f"Hunter Shop 4 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop4price", f"Fehler: {str(e)}")
        return False

def db_Game_setHunterShop4amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET HunterShop4amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setHunterShop4amount", f"Hunter Shop 4 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setHunterShop4amount", f"Fehler: {str(e)}")
        return False

# Runner Shop Setter
def db_Game_setRunnerShop1price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop1price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop1price", f"Runner Shop 1 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop1price", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop1amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop1amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop1amount", f"Runner Shop 1 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop1amount", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop2price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop2price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop2price", f"Runner Shop 2 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop2price", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop2amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop2amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop2amount", f"Runner Shop 2 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop2amount", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop3price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop3price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop3price", f"Runner Shop 3 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop3price", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop3amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop3amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop3amount", f"Runner Shop 3 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop3amount", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop4price(game_id, price):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop4price = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (price, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop4price", f"Runner Shop 4 Preis für Spiel {game_id} auf {price} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop4price", f"Fehler: {str(e)}")
        return False

def db_Game_setRunnerShop4amount(game_id, amount):
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE games SET RunnerShop4amount = ?, updated_at = CURRENT_TIMESTAMP WHERE game_id = ?', (amount, game_id))
        conn.commit()
        conn.close()
        logger_newLog("info", "db_Game_setRunnerShop4amount", f"Runner Shop 4 Menge für Spiel {game_id} auf {amount} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setRunnerShop4amount", f"Fehler: {str(e)}")
        return False

# Wallet Getter und Setter
def db_Wallet_get(game_id, wallet_type, name):
    """Holt ein Wallet aus der Datenbank"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM wallet WHERE game_id = ? AND type = ? AND name = ?', (game_id, wallet_type, name))
        wallet = cursor.fetchone()
        return wallet
    except Exception as e:
        logger_newLog("error", "db_Wallet_get", f"Fehler: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_Wallet_create(game_id, wallet_type, name, budget):
    """Erstellt ein neues Wallet"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        # Hole die verfügbaren Items aus der games Tabelle
        if wallet_type == "runner":
            cursor.execute('''
                SELECT RunnerShop1amount, RunnerShop2amount, RunnerShop3amount, RunnerShop4amount 
                FROM games WHERE game_id = ?
            ''', (game_id,))
        else:  # hunter
            cursor.execute('''
                SELECT HunterShop1amount, HunterShop2amount, HunterShop3amount, HunterShop4amount 
                FROM games WHERE game_id = ?
            ''', (game_id,))
        
        result = cursor.fetchone()
        if result:
            item1_available, item2_available, item3_available, item4_available = result
        else:
            item1_available, item2_available, item3_available, item4_available = 0, 0, 0, 0
        
        cursor.execute('''
            INSERT INTO wallet (game_id, type, name, budget, Item1available, Item2available, Item3available, Item4available) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (game_id, wallet_type, name, budget, item1_available, item2_available, item3_available, item4_available))
        
        conn.commit()
        logger_newLog("info", "db_Wallet_create", f"Wallet erstellt: {wallet_type} {name} für Spiel {game_id} mit Budget {budget} und Items: {item1_available},{item2_available},{item3_available},{item4_available}")
        return True
    except Exception as e:
        logger_newLog("error", "db_Wallet_create", f"Fehler: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Wallet_update_budget(game_id, wallet_type, name, new_budget):
    """Aktualisiert das Budget eines Wallets"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE wallet SET budget = ? WHERE game_id = ? AND type = ? AND name = ?', (new_budget, game_id, wallet_type, name))
        conn.commit()
        logger_newLog("info", "db_Wallet_update_budget", f"Budget für {wallet_type} {name} in Spiel {game_id} auf {new_budget} aktualisiert")
        return True
    except Exception as e:
        logger_newLog("error", "db_Wallet_update_budget", f"Fehler: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Wallet_update_last_purchase(game_id, wallet_type, name):
    """Aktualisiert den last_purchase Timestamp eines Wallets"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute('UPDATE wallet SET last_purchase = ? WHERE game_id = ? AND type = ? AND name = ?', (now, game_id, wallet_type, name))
        conn.commit()
        logger_newLog("info", "db_Wallet_update_last_purchase", f"Last purchase für {wallet_type} {name} in Spiel {game_id} aktualisiert")
        return True
    except Exception as e:
        logger_newLog("error", "db_Wallet_update_last_purchase", f"Fehler: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Wallet_get_all_for_game(game_id):
    """Holt alle Wallets für ein Spiel"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM wallet WHERE game_id = ?', (game_id,))
        wallets = cursor.fetchall()
        return wallets
    except Exception as e:
        logger_newLog("error", "db_Wallet_get_all_for_game", f"Fehler: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def db_Wallet_get_available_items(game_id, wallet_type, name):
    """Holt die verfügbaren Items eines Wallets"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT Item1available, Item2available, Item3available, Item4available 
            FROM wallet WHERE game_id = ? AND type = ? AND name = ?
        ''', (game_id, wallet_type, name))
        result = cursor.fetchone()
        if result:
            return {
                "1": result[0],
                "2": result[1], 
                "3": result[2],
                "4": result[3]
            }
        return {"1": 0, "2": 0, "3": 0, "4": 0}
    except Exception as e:
        logger_newLog("error", "db_Wallet_get_available_items", f"Fehler: {str(e)}")
        return {"1": 0, "2": 0, "3": 0, "4": 0}
    finally:
        if conn:
            conn.close()

def db_Wallet_decrement_item(game_id, wallet_type, name, item_id):
    """Reduziert die verfügbare Anzahl eines Items um 1"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        # Hole aktuelle verfügbare Anzahl
        cursor.execute(f'SELECT Item{item_id}available FROM wallet WHERE game_id = ? AND type = ? AND name = ?', 
                      (game_id, wallet_type, name))
        result = cursor.fetchone()
        
        if result and result[0] > 0:
            new_count = result[0] - 1
            cursor.execute(f'UPDATE wallet SET Item{item_id}available = ? WHERE game_id = ? AND type = ? AND name = ?', 
                          (new_count, game_id, wallet_type, name))
            conn.commit()
            
            logger_newLog("info", "db_Wallet_decrement_item", f"Item {item_id} für {wallet_type} {name} in Spiel {game_id} reduziert auf {new_count}")
            return True
        else:
            logger_newLog("warning", "db_Wallet_decrement_item", f"Item {item_id} für {wallet_type} {name} in Spiel {game_id} nicht verfügbar")
            return False
    except Exception as e:
        logger_newLog("error", "db_Wallet_decrement_item", f"Fehler: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Wallet_can_buy_item(game_id, wallet_type, name, item_id):
    """Prüft ob ein Item noch gekauft werden kann"""
    try:
        available_items = db_Wallet_get_available_items(game_id, wallet_type, name)
        return available_items.get(str(item_id), 0) > 0
    except Exception as e:
        logger_newLog("error", "db_Wallet_can_buy_item", f"Fehler: {str(e)}")
        return False

def db_Locations_add(user_id, game_id, lat, lon):
    """Fügt einen neuen Standort-Eintrag zur locations Tabelle hinzu"""
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO locations (user_id, game_id, lat, lon)
            VALUES (?, ?, ?, ?)
        ''', (user_id, game_id, lat, lon))
        
        conn.commit()
        logger_newLog("debug", "db_Locations_add", f"Standort für User {user_id} in Spiel {game_id} gespeichert: {lat}, {lon}")
        return True
    except Exception as e:
        logger_newLog("error", "db_Locations_add", f"Fehler beim Speichern des Standorts: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Locations_get_position(game_id, user_id, age_minutes=0):
    """Holt die Standort-Position eines Spielers in einem Spiel
    
    Args:
        game_id: ID des Spiels
        user_id: ID des Spielers
        age_minutes: Alter in Minuten (0 = neueste Position, 5 = Position von vor 5 Minuten, etc.)
    
    Returns:
        Tuple (lat, lon, timestamp) oder None wenn keine Position gefunden
    """
    conn = None
    try:
        conn = db_get_connection()
        cursor = conn.cursor()
        
        if age_minutes == 0:
            # Neueste Position
            cursor.execute('''
                SELECT lat, lon, timestamp 
                FROM locations 
                WHERE game_id = ? AND user_id = ? 
                ORDER BY timestamp DESC 
                LIMIT 1
            ''', (game_id, user_id))
        else:
            # Position von vor X Minuten (±1 Minute Toleranz)
            cursor.execute('''
                SELECT lat, lon, timestamp 
                FROM locations 
                WHERE game_id = ? AND user_id = ? 
                AND timestamp <= datetime('now', '-{} minutes')
                AND timestamp >= datetime('now', '-{} minutes')
                ORDER BY timestamp DESC 
                LIMIT 1
            '''.format(age_minutes - 1, age_minutes + 1), (game_id, user_id))
        
        result = cursor.fetchone()
        
        if result:
            lat, lon, timestamp = result
            logger_newLog("debug", "db_Locations_get_position", f"Position für User {user_id} in Spiel {game_id} gefunden (age: {age_minutes}min ±1min): {lat}, {lon}")
            return (lat, lon, timestamp)
        else:
            logger_newLog("debug", "db_Locations_get_position", f"Keine Position für User {user_id} in Spiel {game_id} gefunden (age: {age_minutes}min ±1min)")
            return None
            
    except Exception as e:
        logger_newLog("error", "db_Locations_get_position", f"Fehler beim Holen der Position: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_POI_add(game_id, poi_type, lat, lon, range_meters=None, team=None, creator_id=None):
    """Fügt einen neuen POI (Point of Interest) hinzu
    
    Args:
        game_id: ID des Spiels
        poi_type: Typ des POI ('TRAP', 'WATCHTOWER', 'RUNNERTRAP', 'RUNNERWATCHTOWER', 'RADARPING')
        lat: Breitengrad
        lon: Längengrad
        range_meters: Reichweite in Metern (optional, verwendet config-Default wenn None)
        team: Team des Erstellers (optional)
        creator_id: ID des Erstellers
    
    Returns:
        True bei Erfolg, False bei Fehler
    """
    conn = None
    try:
        # Validiere POI-Typ
        if poi_type not in ['TRAP', 'WATCHTOWER', 'RUNNERTRAP', 'RUNNERWATCHTOWER', 'RADARPING']:
            logger_newLog("error", "db_POI_add", f"Ungültiger POI-Typ: {poi_type}")
            return False
        
        # Verwende config-Default wenn range_meters nicht angegeben (nur für TRAP und WATCHTOWER)
        if range_meters is None and poi_type in ['TRAP', 'WATCHTOWER']:
            from config import conf_getTrapRangeMeters, conf_getWatchtowerRangeMeters
            if poi_type == 'TRAP':
                range_meters = conf_getTrapRangeMeters()
            else:  # WATCHTOWER
                range_meters = conf_getWatchtowerRangeMeters()
        elif range_meters is None:
            range_meters = 0  # Für RUNNERTRAP, RUNNERWATCHTOWER und RADARPING
        
        # Validiere Range (nur für TRAP und WATCHTOWER)
        if poi_type in ['TRAP', 'WATCHTOWER'] and range_meters <= 0:
            logger_newLog("error", "db_POI_add", f"Ungültiger Range: {range_meters} (muss > 0)")
            return False
        
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO poi (game_id, type, lat, lon, range_meters, team, creator_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (game_id, poi_type, lat, lon, range_meters, team, creator_id))
        
        conn.commit()
        logger_newLog("info", "db_POI_add", f"POI {poi_type} für Spiel {game_id} hinzugefügt: {lat}, {lon} (Range: {range_meters}m, Team: {team}, Erstellt von {creator_id})")
        return True
    except Exception as e:
        logger_newLog("error", "db_POI_add", f"Fehler beim Hinzufügen des POI: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_POI_get_by_type(game_id, poi_type):
    """Holt alle POIs eines bestimmten Typs in einem Spiel
    
    Args:
        game_id: ID des Spiels
        poi_type: Typ des POI ('TRAP', 'WATCHTOWER', 'RUNNERTRAP', 'RUNNERWATCHTOWER', 'RADARPING')
    
    Returns:
        Liste von Tuples (id, game_id, type, lat, lon, range_meters, team, creator_id, timestamp) oder leere Liste
    """
    conn = None
    try:
        # Validiere POI-Typ
        if poi_type not in ['TRAP', 'WATCHTOWER', 'RUNNERTRAP', 'RUNNERWATCHTOWER', 'RADARPING']:
            logger_newLog("error", "db_POI_get_by_type", f"Ungültiger POI-Typ: {poi_type}")
            return []
        
        conn = db_get_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, game_id, type, lat, lon, range_meters, team, creator_id, timestamp
            FROM poi 
            WHERE game_id = ? AND type = ?
            ORDER BY timestamp DESC
        ''', (game_id, poi_type))
        
        pois = cursor.fetchall()
        logger_newLog("debug", "db_POI_get_by_type", f"{len(pois)} POIs vom Typ {poi_type} für Spiel {game_id} gefunden")
        return pois
    except Exception as e:
        logger_newLog("error", "db_POI_get_by_type", f"Fehler beim Holen der POIs: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

# Token Getter/Setter-Funktionen
def db_Game_setGamemasterToken(game_id, token):
    """Setzt den Gamemaster-Token für ein Spiel"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE games 
            SET gamemaster_token = ?, updated_at = CURRENT_TIMESTAMP
            WHERE game_id = ?
        ''', (token, game_id))
        
        conn.commit()
        logger_newLog("debug", "db_Game_setGamemasterToken", f"Gamemaster-Token für Spiel {game_id} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_Game_setGamemasterToken", f"Fehler beim Setzen des Gamemaster-Tokens: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_Game_getGamemasterToken(game_id):
    """Holt den Gamemaster-Token für ein Spiel"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT gamemaster_token FROM games WHERE game_id = ?
        ''', (game_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger_newLog("error", "db_Game_getGamemasterToken", f"Fehler beim Holen des Gamemaster-Tokens: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_User_setPlayerToken(user_id, token):
    """Setzt den Player-Token für einen User"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE users 
            SET player_token = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        ''', (token, user_id))
        
        conn.commit()
        logger_newLog("debug", "db_User_setPlayerToken", f"Player-Token für User {user_id} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_User_setPlayerToken", f"Fehler beim Setzen des Player-Tokens: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_User_getPlayerToken(user_id):
    """Holt den Player-Token für einen User"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT player_token FROM users WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger_newLog("error", "db_User_getPlayerToken", f"Fehler beim Holen des Player-Tokens: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_TeamToken_set(game_id, team, token):
    """Setzt einen Team-Token"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO team_tokens (game_id, team, token)
            VALUES (?, ?, ?)
        ''', (game_id, team, token))
        
        conn.commit()
        logger_newLog("debug", "db_TeamToken_set", f"Team-Token für Spiel {game_id}, Team {team} gesetzt")
        return True
    except Exception as e:
        logger_newLog("error", "db_TeamToken_set", f"Fehler beim Setzen des Team-Tokens: {str(e)}")
        return False
    finally:
        if conn:
            conn.close()

def db_TeamToken_get(game_id, team):
    """Holt einen Team-Token"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT token FROM team_tokens WHERE game_id = ? AND team = ?
        ''', (game_id, team))
        
        result = cursor.fetchone()
        if result:
            return result[0]
        return None
    except Exception as e:
        logger_newLog("error", "db_TeamToken_get", f"Fehler beim Holen des Team-Tokens: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_TeamToken_getAllForGame(game_id):
    """Holt alle Team-Tokens für ein Spiel"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT team, token FROM team_tokens WHERE game_id = ?
            ORDER BY team
        ''', (game_id,))
        
        results = cursor.fetchall()
        return results
    except Exception as e:
        logger_newLog("error", "db_TeamToken_getAllForGame", f"Fehler beim Holen der Team-Tokens: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

# WebExport Getter-Funktionen
def db_WebExport_getAllGames():
    """Holt alle Spiele für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT game_id, name, gamemaster_id, status, start_time, duration_minutes, 
                   created_at, updated_at
            FROM games
            ORDER BY created_at DESC
        ''')
        
        games = cursor.fetchall()
        logger_newLog("debug", "db_WebExport_getAllGames", f"{len(games)} Spiele für WebExport gefunden")
        return games
    except Exception as e:
        logger_newLog("error", "db_WebExport_getAllGames", f"Fehler beim Holen aller Spiele: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def db_WebExport_getAllPlayers():
    """Holt alle Spieler für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, last_seen, role, team, game_id,
                   location_lat, location_lon, location_timestamp, created_at
            FROM users
            ORDER BY last_seen DESC
        ''')
        
        players = cursor.fetchall()
        logger_newLog("debug", "db_WebExport_getAllPlayers", f"{len(players)} Spieler für WebExport gefunden")
        return players
    except Exception as e:
        logger_newLog("error", "db_WebExport_getAllPlayers", f"Fehler beim Holen aller Spieler: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def db_WebExport_getGameById(game_id):
    """Holt ein spezifisches Spiel für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT game_id, name, gamemaster_id, status, start_time, duration_minutes,
                   runner_headstart_minutes, created_at, updated_at
            FROM games
            WHERE game_id = ?
        ''', (game_id,))
        
        game = cursor.fetchone()
        if game:
            logger_newLog("debug", "db_WebExport_getGameById", f"Spiel {game_id} für WebExport gefunden")
        else:
            logger_newLog("warning", "db_WebExport_getGameById", f"Spiel {game_id} nicht gefunden")
        return game
    except Exception as e:
        logger_newLog("error", "db_WebExport_getGameById", f"Fehler beim Holen des Spiels {game_id}: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_WebExport_getPlayersByGameId(game_id):
    """Holt alle Spieler eines spezifischen Spiels für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_id, username, first_name, last_seen, role, team, game_id,
                   location_lat, location_lon, location_timestamp, created_at
            FROM users
            WHERE game_id = ?
            ORDER BY role, team, username
        ''', (game_id,))
        
        players = cursor.fetchall()
        logger_newLog("debug", "db_WebExport_getPlayersByGameId", f"{len(players)} Spieler für Spiel {game_id} gefunden")
        return players
    except Exception as e:
        logger_newLog("error", "db_WebExport_getPlayersByGameId", f"Fehler beim Holen der Spieler für Spiel {game_id}: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def db_WebExport_getPOIsByGameId(game_id):
    """Holt alle POIs eines spezifischen Spiels für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, game_id, type, lat, lon, range_meters, team, creator_id, timestamp
            FROM poi
            WHERE game_id = ?
            ORDER BY timestamp DESC
        ''', (game_id,))
        
        pois = cursor.fetchall()
        logger_newLog("debug", "db_WebExport_getPOIsByGameId", f"{len(pois)} POIs für Spiel {game_id} gefunden")
        return pois
    except Exception as e:
        logger_newLog("error", "db_WebExport_getPOIsByGameId", f"Fehler beim Holen der POIs für Spiel {game_id}: {str(e)}")
        return []
    finally:
        if conn:
            conn.close()

def db_WebExport_getGameField(game_id):
    """Holt Spielfeld-Daten eines Spiels für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT field_corner1_lat, field_corner1_lon, field_corner2_lat, field_corner2_lon,
                   field_corner3_lat, field_corner3_lon, field_corner4_lat, field_corner4_lon,
                   finish_line1_lat, finish_line1_lon, finish_line2_lat, finish_line2_lon
            FROM games
            WHERE game_id = ?
        ''', (game_id,))
        
        field = cursor.fetchone()
        if field:
            logger_newLog("debug", "db_WebExport_getGameField", f"Spielfeld für Spiel {game_id} gefunden")
        else:
            logger_newLog("warning", "db_WebExport_getGameField", f"Spielfeld für Spiel {game_id} nicht gefunden")
        return field
    except Exception as e:
        logger_newLog("error", "db_WebExport_getGameField", f"Fehler beim Holen des Spielfelds für Spiel {game_id}: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def db_WebExport_getActiveGamesCount():
    """Holt Anzahl aktiver Spiele für WebExport"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM games 
            WHERE status IN ('headstart', 'running')
        ''')
        
        count = cursor.fetchone()[0]
        logger_newLog("debug", "db_WebExport_getActiveGamesCount", f"{count} aktive Spiele gefunden")
        return count
    except Exception as e:
        logger_newLog("error", "db_WebExport_getActiveGamesCount", f"Fehler beim Zählen aktiver Spiele: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close()

def db_WebExport_getOnlinePlayersCount():
    """Holt Anzahl online Spieler für WebExport (letzte 5 Minuten)"""
    conn = None
    try:
        db_file = conf_getDatabaseFile()
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT COUNT(*) FROM users 
            WHERE last_seen > datetime('now', '-5 minutes')
        ''')
        
        count = cursor.fetchone()[0]
        logger_newLog("debug", "db_WebExport_getOnlinePlayersCount", f"{count} online Spieler gefunden")
        return count
    except Exception as e:
        logger_newLog("error", "db_WebExport_getOnlinePlayersCount", f"Fehler beim Zählen online Spieler: {str(e)}")
        return 0
    finally:
        if conn:
            conn.close() 