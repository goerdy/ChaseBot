import staticmaps
import tempfile
import os
from logger import logger_newLog
from database import db_getRunners, db_getHunters, db_getUserPosition, db_getTeamMembers
from config import conf_getSendImageAsDocument
from PIL import ImageDraw, ImageFont
from geofunctions import calculate_distance
from config import conf_getMapExportWidth, conf_getMapExportMaxSize, conf_getTileProvider, conf_getTileCaching
from cached_tile_provider import CachedTileProvider

# Monkey-Patch für Pillow 11.x Kompatibilität
# Entfernt - nicht benötigt und verursacht Linter-Fehler

async def Map_SendMap_pyStaticmapPNG(bot, chat_id, game_data, geojson, user_info):
    """Sendet eine PNG-Karte erstellt mit py-staticmaps"""
    logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"Erstelle py-staticmaps PNG für Spiel {game_data[0]}")
    
    try:
        # Erstelle staticmaps Context
        context = staticmaps.Context()
        
        # Lese Tile-Provider und Caching-Einstellungen aus Konfiguration
        tile_provider_name = conf_getTileProvider()
        cache_enabled = conf_getTileCaching()
        logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"Verwende Tile-Provider: {tile_provider_name}, Caching: {cache_enabled}")
        
        # Wähle Original-Tile-Provider
        original_provider = None
        if tile_provider_name == "OSM":
            original_provider = staticmaps.tile_provider_OSM
        elif tile_provider_name == "CartoDarkNoLabels":
            original_provider = staticmaps.tile_provider_CartoDarkNoLabels
        elif tile_provider_name == "CartoNoLabels":
            original_provider = staticmaps.tile_provider_CartoNoLabels
        elif tile_provider_name == "ArcGISWorldImagery":
            original_provider = staticmaps.tile_provider_ArcGISWorldImagery
        elif tile_provider_name in ["StamenTonerLite", "StamenToner", "StamenTerrain"]:
            logger_newLog("warning", "Map_SendMap_pyStaticmapPNG", f"{tile_provider_name} ist nicht mehr verfügbar, verwende OSM")
            original_provider = staticmaps.tile_provider_OSM
        else:
            logger_newLog("warning", "Map_SendMap_pyStaticmapPNG", f"Unbekannter Tile-Provider '{tile_provider_name}', verwende OSM")
            original_provider = staticmaps.tile_provider_OSM
        
        # Erstelle Cached-Tile-Provider wenn Caching aktiviert ist
        if cache_enabled:
            try:
                cached_provider = CachedTileProvider(original_provider, cache_enabled=True)
                context.set_tile_provider(cached_provider)
                logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"Verwende Cached-Tile-Provider: {cached_provider.name()}")
            except Exception as e:
                logger_newLog("warning", "Map_SendMap_pyStaticmapPNG", f"Fehler beim Erstellen des Cached-Tile-Providers: {str(e)}, verwende Original-Provider")
                context.set_tile_provider(original_provider)
        else:
            context.set_tile_provider(original_provider)
            logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"Verwende Original-Tile-Provider: {original_provider.name()}")
        
        # Spielfeld als Polygon hinzufügen
        field_corners = [
            staticmaps.create_latlng(game_data[4], game_data[5]),  # corner1
            staticmaps.create_latlng(game_data[6], game_data[7]),  # corner2
            staticmaps.create_latlng(game_data[8], game_data[9]),  # corner3
            staticmaps.create_latlng(game_data[10], game_data[11]), # corner4
            staticmaps.create_latlng(game_data[4], game_data[5])   # corner1 wiederholen (Polygon schließen)
        ]
        context.add_object(staticmaps.Area(
            field_corners,
            fill_color=staticmaps.parse_color("#FF000020"),  # Rot mit Transparenz
            width=2,
            color=staticmaps.RED
        ))
        
        # Ziellinie als Linie hinzufügen
        finish_line = [
            staticmaps.create_latlng(game_data[12], game_data[13]),  # finish1
            staticmaps.create_latlng(game_data[14], game_data[15])   # finish2
        ]
        context.add_object(staticmaps.Line(
            finish_line,
            color=staticmaps.GREEN,
            width=4
        ))
        
        # POIs aus der GeoJSON hinzufügen
        if geojson and 'features' in geojson:
            for feature in geojson['features']:
                if feature['type'] == 'Feature' and feature['geometry']['type'] == 'Point':
                    props = feature['properties']
                    feature_type = props.get('featuretype')
                    
                    if feature_type in ['TRAP', 'WATCHTOWER', 'RADARPING']:
                        coords = feature['geometry']['coordinates']
                        lat, lon = coords[1], coords[0]  # GeoJSON: [lon, lat]
                        pos = staticmaps.create_latlng(lat, lon)
                        
                        # Bestimme Farbe und Größe basierend auf POI-Typ
                        if feature_type == 'TRAP':
                            color = staticmaps.parse_color("#FF0000")  # Rot
                            size = 8
                        elif feature_type == 'WATCHTOWER':
                            color = staticmaps.parse_color("#0000FF")  # Blau
                            size = 10
                        elif feature_type == 'RADARPING':
                            color = staticmaps.parse_color("#FF00FF")  # Magenta
                            size = 6
                        else:
                            continue
                        
                        # Füge POI-Marker hinzu (außer WATCHTOWER, die werden als Ringe dargestellt)
                        if feature_type != 'WATCHTOWER':
                            context.add_object(staticmaps.Marker(
                                pos,
                                color=color,
                                size=size
                            ))
                        
                        # Range-Kreise für TRAP und WATCHTOWER
                        if feature_type in ['TRAP', 'WATCHTOWER'] and 'range' in props:
                            range_meters = props['range']
                            if range_meters and range_meters > 0:
                                # Berechne Kreis-Radius (ungefähre Umrechnung)
                                # 1 Grad ≈ 111km, also range_meters / 111000 Grad
                                radius_degrees = range_meters / 111000.0
                                
                                # Erstelle Kreis-Polygon (vereinfacht als 32-Punkt-Polygon für bessere Darstellung)
                                import math
                                circle_points = []
                                for i in range(32):
                                    angle = i * 2 * math.pi / 32
                                    dlat = radius_degrees * math.cos(angle)
                                    dlon = radius_degrees * math.sin(angle) / math.cos(math.radians(lat))
                                    circle_points.append(staticmaps.create_latlng(lat + dlat, lon + dlon))
                                
                                # Schließe den Kreis, indem der erste Punkt am Ende wiederholt wird
                                if circle_points:
                                    circle_points.append(circle_points[0])
                                
                                if feature_type == 'TRAP':
                                    # TRAP: Gefüllter Kreis mit Transparenz
                                    range_color = staticmaps.parse_color("#FF000020")  # Rot mit Transparenz
                                    context.add_object(staticmaps.Area(
                                        circle_points,
                                        fill_color=range_color,
                                        width=2,
                                        color=color
                                    ))
                                elif feature_type == 'WATCHTOWER':
                                    # WATCHTOWER: Nur Ring (keine Füllung) + kleiner Marker in der Mitte
                                    context.add_object(staticmaps.Area(
                                        circle_points,
                                        fill_color=staticmaps.parse_color("#00000000"),  # Transparent
                                        width=3,
                                        color=color
                                    ))
                                    # Kleiner Marker in der Mitte des Wachturms
                                    context.add_object(staticmaps.Marker(
                                        pos,
                                        color=color,
                                        size=6
                                    ))
        
        # Spieler-Marker hinzufügen basierend auf user_info
        if user_info:
            role = user_info['role']
            game_id = game_data[0]
            
            if role in ("gamemaster", "spectator"):
                # Alle Runner
                for runner in db_getRunners(game_id):
                    if runner[3] is not None and runner[4] is not None:
                        pos = staticmaps.create_latlng(runner[3], runner[4])
                        context.add_object(staticmaps.Marker(
                            pos,
                            color=staticmaps.parse_color("#808080"),  # Grau
                            size=10
                        ))
                
                # Alle Hunter
                for hunter in db_getHunters(game_id):
                    if hunter[3] is not None and hunter[4] is not None:
                        pos = staticmaps.create_latlng(hunter[3], hunter[4])
                        # Farbe basierend auf Team
                        team_color = hunter[2] if hunter[2] else "blue"
                        color_map = {
                            "red": staticmaps.RED,
                            "blue": staticmaps.BLUE,
                            "green": staticmaps.GREEN,
                            "yellow": staticmaps.YELLOW,
                            "purple": staticmaps.PURPLE
                        }
                        marker_color = color_map.get(team_color, staticmaps.BLUE)
                        context.add_object(staticmaps.Marker(
                            pos,
                            color=marker_color,
                            size=12
                        ))
            
            elif role == "runner":
                # Nur eigene Position
                user = db_getUserPosition(user_info.get('user_id'))
                if user and user[3] is not None and user[4] is not None:
                    pos = staticmaps.create_latlng(user[3], user[4])
                    context.add_object(staticmaps.Marker(
                        pos,
                        color=staticmaps.parse_color("#808080"),  # Grau
                        size=10
                    ))
            
            elif role == "hunter":
                # Nur Hunter des eigenen Teams
                team = user_info['team']
                for hunter in db_getTeamMembers(game_id, team):
                    if hunter[3] is not None and hunter[4] is not None:
                        pos = staticmaps.create_latlng(hunter[3], hunter[4])
                        # Farbe basierend auf Team
                        team_color = hunter[2] if hunter[2] else "blue"
                        color_map = {
                            "red": staticmaps.RED,
                            "blue": staticmaps.BLUE,
                            "green": staticmaps.GREEN,
                            "yellow": staticmaps.YELLOW,
                            "purple": staticmaps.PURPLE
                        }
                        marker_color = color_map.get(team_color, staticmaps.BLUE)
                        context.add_object(staticmaps.Marker(
                            pos,
                            color=marker_color,
                            size=12
                        ))
        
        # Berechne Zentrum
        lons = [game_data[4], game_data[6], game_data[8], game_data[10]]  # Alle Lon-Werte
        lats = [game_data[5], game_data[7], game_data[9], game_data[11]]  # Alle Lat-Werte
        center_lat = sum(lats) / 4
        center_lon = sum(lons) / 4
        logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"center_lat: {center_lat}, center_lon: {center_lon}")
        context.set_center(staticmaps.create_latlng(center_lon, center_lat))
        
        # Berechne Seitenverhältnis vor dem Rendering
        corners = [
            (game_data[4], game_data[5]),  # Ecke 1: (lon, lat)
            (game_data[6], game_data[7]),  # Ecke 2
            (game_data[8], game_data[9]),  # Ecke 3
            (game_data[10], game_data[11]) # Ecke 4
        ]
        for idx, (lon, lat) in enumerate(corners):
            logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"Ecke {idx+1}: Lon={lon}, Lat={lat}")
        
        # Länge: Ecke 1 zu 2, Breite: Ecke 2 zu 3
        lat1, lon1 = corners[0][0], corners[0][1]
        lat2, lon2 = corners[1][0], corners[1][1]
        lat3, lon3 = corners[2][0], corners[2][1]
        field_length = calculate_distance(lat1, lon1, lat2, lon2)
        field_width = calculate_distance(lat2, lon2, lat3, lon3)
        logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"Distanz Ecke1-Ecke2 (Länge): {field_length:.2f}m, Ecke2-Ecke3 (Breite): {field_width:.2f}m")
        
        # Seitenverhältnis = Breite / Höhe
        aspect = field_width / field_length if field_length > 0 else 1
        logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"Seitenverhältnis Spielfeld: {aspect:.3f} (Breite: {field_width:.1f}m, Höhe: {field_length:.1f}m)")
        
        # Berechne Bildgröße basierend auf Seitenverhältnis und maximaler Kantenlänge
        max_size = conf_getMapExportMaxSize()
        logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"Maximale Kantenlänge aus Config: {max_size}")
        if aspect > 1:  # Spielfeld ist breiter als hoch
            width_px = max_size
            height_px = int(max_size / aspect)
        else:  # Spielfeld ist höher als breit oder quadratisch
            height_px = max_size
            width_px = int(max_size * aspect)
        
        logger_newLog("debug", "Map_SendMap_pyStaticmapPNG", f"Rendere Bild in Größe: {width_px}x{height_px}")
        
        # Erstelle temporäre Datei für PNG
        with tempfile.NamedTemporaryFile(suffix='.png', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        # Nutze automatischen Zoom von staticmaps
        try:
            image = context.render_cairo(width_px, height_px)
            image.write_to_png(tmp_path)
            logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"PNG mit Cairo gerendert (Auto-Zoom)")
        except Exception as e:
            logger_newLog("warning", "Map_SendMap_pyStaticmapPNG", f"Cairo nicht verfügbar, verwende Pillow: {str(e)} (Auto-Zoom)")
            image = context.render_pillow(width_px, height_px)
            image.save(tmp_path)
            logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"PNG mit Pillow gerendert (Auto-Zoom)")
        
        # Sende PNG
        send_as_document = conf_getSendImageAsDocument()
        with open(tmp_path, 'rb') as png_file:
            if send_as_document:
                await bot.send_document(chat_id, png_file, caption=f"🗺️ Chase: {game_data[1]}")
            else:
                await bot.send_photo(chat_id, png_file, caption=f"🗺️ Chase: {game_data[1]}")
        
        # Lösche temporäre Datei
        os.unlink(tmp_path)
        
        logger_newLog("info", "Map_SendMap_pyStaticmapPNG", f"PNG-Karte erfolgreich gesendet für Spiel {game_data[0]} (als {'Dokument' if send_as_document else 'Photo'})")
        return True
        
    except Exception as e:
        logger_newLog("error", "Map_SendMap_pyStaticmapPNG", f"Fehler beim Erstellen der PNG-Karte: {str(e)}")
        await bot.send_message(chat_id, "❌ Fehler beim Erstellen der Karte.")
        return False 