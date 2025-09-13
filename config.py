import os
from dotenv import load_dotenv

# Lade die config.env Datei
load_dotenv('config.env')

def conf_getTelegramAPIkey():
    return os.getenv('TELEGRAM_API_KEY')

def conf_getAdminName():
    return os.getenv('ADMIN')

def conf_getLoglevel():
    return os.getenv('LOGLEVEL', 'debug')

def conf_getDatabaseFile():
    return os.getenv('DATABASE_FILE', 'chasebot.db')

def conf_getMapProvider():
    """Gibt den Map-Provider aus der Konfiguration zurück"""
    return os.getenv('MapProvider', 'OSM-Static-Maps')

def conf_getMaxLocationAgeMinutes():
    import os
    value = os.getenv('MAX_LOCATION_AGE_MINUTES')
    if value is not None:
        try:
            return int(value)
        except Exception:
            pass
    # Fallback: config.env direkt lesen
    try:
        with open('config.env') as f:
            for line in f:
                if line.strip().startswith('MAX_LOCATION_AGE_MINUTES='):
                    return int(line.strip().split('=', 1)[1])
    except Exception:
        pass
    return 5

def conf_checkconfig():
    # Prüfe ob alle Werte vorhanden sind
    api_key = conf_getTelegramAPIkey()
    admin = conf_getAdminName()
    loglevel = conf_getLoglevel()
    database_file = conf_getDatabaseFile()
    
    if not api_key or not admin or not loglevel or not database_file:
        return False
    
    # Prüfe ob API Key plausibel ist (sollte Zahlen und Buchstaben enthalten)
    if not api_key.replace(':', '').replace('_', '').isalnum():
        return False
    
    # Prüfe ob Admin Name plausibel ist (sollte alphanumerisch sein)
    if not admin.replace('_', '').isalnum():
        return False
    
    # Prüfe ob LogLevel plausibel ist
    valid_levels = ['debug', 'info', 'warning', 'error', 'critical']
    if loglevel.lower() not in valid_levels:
        return False
    
    # Prüfe ob Datenbankdateiname plausibel ist (sollte .db Endung haben)
    if not database_file.endswith('.db'):
        return False
    
    return True

# Shop Item Preise
def conf_getRunnerShop1Price():
    return int(os.getenv('RUNNER_SHOP1_PRICE', 50))

def conf_getRunnerShop2Price():
    return int(os.getenv('RUNNER_SHOP2_PRICE', 75))

def conf_getRunnerShop3Price():
    return int(os.getenv('RUNNER_SHOP3_PRICE', 100))

def conf_getRunnerShop4Price():
    return int(os.getenv('RUNNER_SHOP4_PRICE', 150))

def conf_getHunterShop1Price():
    return int(os.getenv('HUNTER_SHOP1_PRICE', 50))

def conf_getHunterShop2Price():
    return int(os.getenv('HUNTER_SHOP2_PRICE', 75))

def conf_getHunterShop3Price():
    return int(os.getenv('HUNTER_SHOP3_PRICE', 100))

def conf_getHunterShop4Price():
    return int(os.getenv('HUNTER_SHOP4_PRICE', 150))

# Shop Item Anzahlen
def conf_getRunnerShop1Amount():
    return int(os.getenv('RUNNER_SHOP1_AMOUNT', 1))

def conf_getRunnerShop2Amount():
    return int(os.getenv('RUNNER_SHOP2_AMOUNT', 1))

def conf_getRunnerShop3Amount():
    return int(os.getenv('RUNNER_SHOP3_AMOUNT', 1))

def conf_getRunnerShop4Amount():
    return int(os.getenv('RUNNER_SHOP4_AMOUNT', 1))

def conf_getHunterShop1Amount():
    return int(os.getenv('HUNTER_SHOP1_AMOUNT', 1))

def conf_getHunterShop2Amount():
    return int(os.getenv('HUNTER_SHOP2_AMOUNT', 1))

def conf_getHunterShop3Amount():
    return int(os.getenv('HUNTER_SHOP3_AMOUNT', 1))

def conf_getHunterShop4Amount():
    return int(os.getenv('HUNTER_SHOP4_AMOUNT', 1))

# Startbudgets
def conf_getRunnerStartBudget():
    return int(os.getenv('RUNNER_START_BUDGET', 100))

def conf_getHunterStartBudget():
    return int(os.getenv('HUNTER_START_BUDGET', 100))

# Shop Cooldown
def conf_getShopCooldown():
    return int(os.getenv('SHOP_COOLDOWN', 15))

# Map Einstellungen
def conf_getSendImageAsDocument():
    return os.getenv('SEND_IMAGE_AS_DOCUMENT', 'false').lower() == 'true'

# POI Reichweiten
def conf_getTrapRangeMeters():
    return int(os.getenv('TRAP_RANGE_METERS', 50))

def conf_getWatchtowerRangeMeters():
    return int(os.getenv('WATCHTOWER_RANGE_METERS', 100))

def conf_getMapExportWidth():
    return int(os.getenv('MAP_EXPORT_WIDTH', 1200))

def conf_getMapExportMaxSize():
    value = os.getenv('PNGMAP_EXPORT_MAXSIZE')
    if value is not None:
        try:
            return int(value)
        except Exception:
            pass
    # Fallback: config.env direkt lesen
    try:
        with open('config.env') as f:
            for line in f:
                if line.strip().startswith('PNGMAP_EXPORT_MAXSIZE='):
                    value = line.strip().split('=', 1)[1]
                    return int(value)
    except Exception:
        pass
    return 4000

def conf_getTileProvider():
    """Gibt den Tile-Provider aus der Konfiguration zurück"""
    return os.getenv('TILE_PROVIDER', 'OSM')

def conf_getTileCaching():
    """Gibt zurück ob Tile-Caching aktiviert ist"""
    return os.getenv('TILE_CACHING', 'false').lower() == 'true'

def conf_getTileCacheDir():
    """Gibt das Tile-Cache Verzeichnis zurück"""
    return os.getenv('TILE_CACHE_DIR', 'tile_cache')

def conf_getTileCacheMaxSize():
    """Gibt die maximale Anzahl gecachter Tiles zurück"""
    value = os.getenv('TILE_CACHE_MAX_SIZE', '1000')
    try:
        return int(value)
    except ValueError:
        return 1000

# Web Export Einstellungen
def conf_getWebExportEnabled():
    """Gibt zurück ob Web Export aktiviert ist"""
    return os.getenv('WEBEXPORT_ENABLED', 'false').lower() == 'true'

def conf_getWebExportFtpHost():
    """Gibt den FTP Host zurück"""
    return os.getenv('WEBEXPORT_FTP_HOST', '')

def conf_getWebExportFtpUser():
    """Gibt den FTP Benutzernamen zurück"""
    return os.getenv('WEBEXPORT_FTP_USER', '')

def conf_getWebExportFtpPass():
    """Gibt das FTP Passwort zurück"""
    return os.getenv('WEBEXPORT_FTP_PASS', '')

def conf_getWebExportFtpPath():
    """Gibt den FTP Pfad zurück"""
    return os.getenv('WEBEXPORT_FTP_PATH', '/maps/')

def conf_getWebExportUpdateInterval():
    """Gibt das Update-Intervall in Sekunden zurück"""
    value = os.getenv('WEBEXPORT_UPDATE_INTERVAL', '60')
    try:
        return int(value)
    except ValueError:
        return 60 