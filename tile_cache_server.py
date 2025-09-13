import os
import requests
import time
from collections import OrderedDict
from logger import logger_newLog
from config import conf_getTileCacheDir, conf_getTileCacheMaxSize
import threading
from http.server import HTTPServer, SimpleHTTPRequestHandler
import urllib.parse

# Lokaler Tile-Cache
class LocalTileCache:
    def __init__(self, cache_dir, max_size=1000):
        self.cache_dir = cache_dir
        self.max_size = max_size
        self.cache_usage = OrderedDict()  # Für LRU-Cache
        os.makedirs(cache_dir, exist_ok=True)
        logger_newLog("info", "LocalTileCache", f"Tile-Cache initialisiert: {cache_dir}, max {max_size} Tiles")
    
    def get_cache_path(self, provider, z, x, y):
        """Erstellt den Cache-Pfad für ein Tile"""
        # Erstelle Provider-Unterverzeichnis
        provider_dir = os.path.join(self.cache_dir, provider)
        os.makedirs(provider_dir, exist_ok=True)
        
        # Erstelle Zoom-Unterverzeichnis
        zoom_dir = os.path.join(provider_dir, str(z))
        os.makedirs(zoom_dir, exist_ok=True)
        
        # Erstelle X-Unterverzeichnis
        x_dir = os.path.join(zoom_dir, str(x))
        os.makedirs(x_dir, exist_ok=True)
        
        return os.path.join(x_dir, f"{y}.png")
    
    def get_tile(self, provider, z, x, y, original_url):
        """Holt ein Tile aus dem Cache oder lädt es von der Original-URL"""
        cache_path = self.get_cache_path(provider, z, x, y)
        
        # Prüfe ob Tile im Cache existiert
        if os.path.exists(cache_path):
            # Aktualisiere Cache-Nutzung (LRU)
            cache_key = f"{provider}/{z}/{x}/{y}"
            if cache_key in self.cache_usage:
                self.cache_usage.move_to_end(cache_key)
            else:
                self.cache_usage[cache_key] = time.time()
            
            logger_newLog("debug", "LocalTileCache", f"Tile {z}/{x}/{y} aus Cache geladen")
            return cache_path
        
        # Tile nicht im Cache - lade von Original-URL
        try:
            logger_newLog("debug", "LocalTileCache", f"Lade Tile {z}/{x}/{y} von {original_url}")
            headers = {
                'User-Agent': 'TelegramChaseBot/1.0 (https://github.com/your-repo; your-email@example.com)'
            }
            response = requests.get(original_url, timeout=10, headers=headers)
            response.raise_for_status()
            
            # Speichere in Cache
            with open(cache_path, 'wb') as f:
                f.write(response.content)
            
            # Aktualisiere Cache-Nutzung
            cache_key = f"{provider}/{z}/{x}/{y}"
            self.cache_usage[cache_key] = time.time()
            
            # Prüfe Cache-Größe und entferne alte Tiles wenn nötig
            self._cleanup_cache()
            
            logger_newLog("debug", "LocalTileCache", f"Tile {z}/{x}/{y} gecacht")
            return cache_path
            
        except Exception as e:
            logger_newLog("error", "LocalTileCache", f"Fehler beim Laden von Tile {z}/{x}/{y}: {str(e)}")
            return None
    
    def _cleanup_cache(self):
        """Entfernt alte Tiles wenn Cache zu groß wird"""
        if self.max_size <= 0 or len(self.cache_usage) <= self.max_size:
            return
        
        # Entferne die ältesten Tiles
        tiles_to_remove = len(self.cache_usage) - self.max_size
        for _ in range(tiles_to_remove):
            if self.cache_usage:
                oldest_key = next(iter(self.cache_usage))
                oldest_tile = self.cache_usage.pop(oldest_key)
                
                # Parse Tile-Pfad
                try:
                    provider, z, x, y = oldest_key.split('/')
                    tile_path = self.get_cache_path(provider, z, x, y)
                    if os.path.exists(tile_path):
                        os.remove(tile_path)
                        logger_newLog("debug", "LocalTileCache", f"Altes Tile entfernt: {oldest_key}")
                except Exception as e:
                    logger_newLog("error", "LocalTileCache", f"Fehler beim Entfernen von Tile {oldest_key}: {str(e)}")

# HTTP-Request-Handler für Tiles
class TileRequestHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, cache_dir=None, **kwargs):
        self.cache_dir = cache_dir
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        """Behandelt GET-Requests für Tiles"""
        try:
            # Parse URL: /tiles/{provider}/{z}/{x}/{y}.png
            path = urllib.parse.unquote(self.path)
            if path.startswith('/tiles/'):
                # Extrahiere Tile-Parameter
                parts = path.split('/')
                if len(parts) >= 6:
                    provider = parts[2]
                    z = parts[3]
                    x = parts[4]
                    y = parts[5].replace('.png', '')
                    
                    # Erstelle Tile-Pfad
                    tile_path = os.path.join(self.cache_dir, provider, z, x, f"{y}.png")
                    
                    if os.path.exists(tile_path):
                        # Sende Tile
                        self.send_response(200)
                        self.send_header('Content-type', 'image/png')
                        self.send_header('Cache-Control', 'public, max-age=86400')  # 24h Cache
                        self.end_headers()
                        
                        with open(tile_path, 'rb') as f:
                            self.wfile.write(f.read())
                        
                        logger_newLog("debug", "TileRequestHandler", f"Tile gesendet: {provider}/{z}/{x}/{y}")
                        return
                    else:
                        # Tile nicht gefunden
                        self.send_response(404)
                        self.end_headers()
                        return
            
            # Fallback zu Standard-HTTP-Handler
            super().do_GET()
            
        except Exception as e:
            logger_newLog("error", "TileRequestHandler", f"Fehler beim Behandeln von Tile-Request: {str(e)}")
            self.send_response(500)
            self.end_headers()

# Globale Variablen
tile_cache = None
tile_server = None
tile_server_thread = None

def start_tile_server(cache_dir, port=5001):
    """Startet den lokalen Tile-Server in einem separaten Thread"""
    global tile_server, tile_server_thread
    
    if tile_server is None:
        try:
            # Erstelle benutzerdefinierten Request-Handler
            class CustomTileRequestHandler(TileRequestHandler):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, cache_dir=cache_dir, **kwargs)
            
            # Starte Server
            tile_server = HTTPServer(('localhost', port), CustomTileRequestHandler)
            tile_server_thread = threading.Thread(target=tile_server.serve_forever, daemon=True)
            tile_server_thread.start()
            
            logger_newLog("info", "TileServer", f"Lokaler Tile-Server gestartet auf http://localhost:{port}")
            return True
            
        except Exception as e:
            logger_newLog("error", "TileServer", f"Fehler beim Starten des Tile-Servers: {str(e)}")
            return False
    
    return True

def get_tile_cache():
    """Gibt die globale Tile-Cache Instanz zurück"""
    global tile_cache
    if tile_cache is None:
        cache_dir = conf_getTileCacheDir()
        max_size = conf_getTileCacheMaxSize()
        tile_cache = LocalTileCache(cache_dir, max_size)
    return tile_cache

def get_cached_tile_url(provider_name, z, x, y):
    """Gibt die URL für ein gecachtes Tile zurück"""
    return f"http://localhost:5001/tiles/{provider_name}/{z}/{x}/{y}.png" 