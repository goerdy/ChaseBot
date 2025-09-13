import staticmaps
from tile_cache_server import get_tile_cache, start_tile_server, get_cached_tile_url
from logger import logger_newLog

class CachedTileProvider(staticmaps.TileProvider):
    def __init__(self, original_provider, cache_enabled=True):
        self.original_provider = original_provider
        self.cache_enabled = cache_enabled
        self.provider_name = self._get_provider_name(original_provider)
        
        # Initialisiere Parent-Klasse mit dem Original-URL-Pattern
        super().__init__(
            name=f"Cached{self.provider_name}",
            url_pattern=self.original_provider.url_pattern if hasattr(self.original_provider, 'url_pattern') else "dummy",
            attribution=original_provider.attribution(),
            max_zoom=original_provider.max_zoom()
        )
        
        if cache_enabled:
            # Starte Tile-Server
            cache_dir = get_tile_cache().cache_dir
            if not start_tile_server(cache_dir):
                logger_newLog("warning", "CachedTileProvider", "Tile-Server konnte nicht gestartet werden, verwende Original-Provider")
                self.cache_enabled = False
            else:
                logger_newLog("info", "CachedTileProvider", f"Tile-Server gestartet für Provider: {self.provider_name}")
    
    def _get_provider_name(self, provider):
        """Extrahiert den Provider-Namen aus dem Provider-Objekt"""
        if hasattr(provider, 'name'):
            return provider.name()
        elif hasattr(provider, '__class__'):
            return provider.__class__.__name__
        else:
            return "unknown"
    
    def url(self, z, x, y):
        """Gibt die URL für ein Tile zurück"""
        if self.cache_enabled:
            # Verwende Cache über lokalen HTTP-Server
            original_url = self.original_provider.url(z, x, y)
            if original_url:
                # Lade Tile in Cache (falls noch nicht vorhanden)
                cache = get_tile_cache()
                cached_path = cache.get_tile(self.provider_name, z, x, y, original_url)
                if cached_path:
                    # Verwende lokalen HTTP-Server
                    return get_cached_tile_url(self.provider_name, z, x, y)
        
        # Fallback zu Original-Provider
        return self.original_provider.url(z, x, y) 