import requests
import tempfile
import os
from logger import logger_newLog
from database import db_Game_getField, db_getRunners, db_getHunters, db_getUserPosition, db_getTeamMembers, db_POI_get_by_type
from config import conf_getMapProvider
import json
from Map_SendMap_LokalMapServer import Map_SendMap_LokalMapServer
from Map_SendMap_LeafletHTML import Map_SendMap_LeafletHTML
from Map_SendMap_pyStaticmapPNG import Map_SendMap_pyStaticmapPNG

def Map_GenerateGeoJSON(game_data, user_id=None):
    """Erstellt ein erweitertes GeoJSON für das Spielfeld, die Ziellinie und die Spielerpositionen"""
    # Spielfeld-Polygon
    field_corners = [
        [game_data[5], game_data[4]],
        [game_data[7], game_data[6]],
        [game_data[9], game_data[8]],
        [game_data[11], game_data[10]],
        [game_data[5], game_data[4]]
    ]
    # Ziellinie
    finishline = [
        [game_data[13], game_data[12]],
        [game_data[15], game_data[14]]
    ]
    features = [
        {
            "type": "Feature",
            "geometry": {
                "type": "Polygon",
                "coordinates": [field_corners]
            },
            "properties": {
                "name": game_data[1],
                "featuretype": "field"
            }
        },
        {
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": finishline
            },
            "properties": {
                "featuretype": "finishline"
            }
        }
    ]
    
    # Hole User-Daten für POI-Filterung
    user = None
    role = None
    team = None
    game_id = game_data[0]
    
    if user_id is not None:
        user = db_getUserPosition(user_id)
        if user:
            role = user[6]
            team = user[2]
    
    # Füge POIs basierend auf Rolle hinzu
    if user_id is not None and user:
        # WATCHTOWER: Für alle User sichtbar (auch Runner)
        watchtowers = db_POI_get_by_type(game_id, 'WATCHTOWER')
        for watchtower in watchtowers:
            poi_id, poi_game_id, poi_type, poi_lat, poi_lon, poi_range, poi_team, poi_creator, poi_timestamp = watchtower
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [poi_lon, poi_lat]
                },
                "properties": {
                    "featuretype": "WATCHTOWER",
                    "team": poi_team,
                    "range": poi_range,
                    "creator_id": poi_creator,
                    "timestamp": poi_timestamp
                }
            })
        
        # TRAP: Für Hunter (ihr Team), Gamemaster und Spectator sichtbar (NICHT für Runner)
        if role in ("gamemaster", "spectator") or (role == "hunter"):
            traps = db_POI_get_by_type(game_id, 'TRAP')
            for trap in traps:
                poi_id, poi_game_id, poi_type, poi_lat, poi_lon, poi_range, poi_team, poi_creator, poi_timestamp = trap
                # Für Hunter nur Fallen des eigenen Teams anzeigen
                if role == "hunter" and poi_team != team:
                    continue
                
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [poi_lon, poi_lat]
                    },
                    "properties": {
                        "featuretype": "TRAP",
                        "team": poi_team,
                        "range": poi_range,
                        "creator_id": poi_creator,
                        "timestamp": poi_timestamp
                    }
                })
        
        # RUNNERTRAP und RUNNERWATCHTOWER: Nur für Hunter des eigenen Teams sichtbar
        if role == "hunter":
            # RUNNERTRAP
            runner_traps = db_POI_get_by_type(game_id, 'RUNNERTRAP')
            for runner_trap in runner_traps:
                poi_id, poi_game_id, poi_type, poi_lat, poi_lon, poi_range, poi_team, poi_creator, poi_timestamp = runner_trap
                # Nur RUNNERTRAP des eigenen Teams anzeigen
                if poi_team == team:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [poi_lon, poi_lat]
                        },
                        "properties": {
                            "featuretype": "RUNNERTRAP",
                            "team": poi_team,
                            "creator_id": poi_creator,
                            "timestamp": poi_timestamp
                        }
                    })
            
            # RUNNERWATCHTOWER
            runner_watchtowers = db_POI_get_by_type(game_id, 'RUNNERWATCHTOWER')
            for runner_watchtower in runner_watchtowers:
                poi_id, poi_game_id, poi_type, poi_lat, poi_lon, poi_range, poi_team, poi_creator, poi_timestamp = runner_watchtower
                # Nur RUNNERWATCHTOWER des eigenen Teams anzeigen
                if poi_team == team:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [poi_lon, poi_lat]
                        },
                        "properties": {
                            "featuretype": "RUNNERWATCHTOWER",
                            "team": poi_team,
                            "creator_id": poi_creator,
                            "timestamp": poi_timestamp
                        }
                    })
        
        # RADARPING: Sichtbarkeit je nach Rolle
        radar_pings = db_POI_get_by_type(game_id, 'RADARPING')
        for radar_ping in radar_pings:
            poi_id, poi_game_id, poi_type, poi_lat, poi_lon, poi_range, poi_team, poi_creator, poi_timestamp = radar_ping
            
            # Filtere nach Rolle
            if role == "runner":
                # Runner sehen nur ihre eigenen Pings
                if poi_creator != user_id:
                    continue
            elif role == "hunter":
                # Hunter sehen nur Pings ihres eigenen Teams
                if poi_team != team:
                    continue
            # Gamemaster und Spectator sehen alle Pings (kein Filter)
            
            features.append({
                "type": "Feature",
                "geometry": {
                    "type": "Point",
                    "coordinates": [poi_lon, poi_lat]
                },
                "properties": {
                    "featuretype": "RADARPING",
                    "team": poi_team,
                    "range": poi_range,  # Entfernung zum Ziel
                    "creator_id": poi_creator,
                    "timestamp": poi_timestamp,
                    "is_radar_ping": True,  # Spezielle Deklaration für spätere Verarbeitung
                    "ping_distance": poi_range  # Explizite Entfernungsangabe
                }
            })
    
    # Spieler-Features je nach Rolle
    if user_id is not None:
        user = db_getUserPosition(user_id)
        if not user:
            return {"type": "FeatureCollection", "features": features}
        role = user[6]
        game_id = user[7]
        if role in ("gamemaster", "spectator"):
            # Alle Runner
            for runner in db_getRunners(game_id):
                if runner[3] is not None and runner[4] is not None:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [runner[4], runner[3]]
                        },
                        "properties": {
                            "featuretype": "runner",
                            "user_id": runner[0],
                            "username": runner[1],
                            "team": runner[2],
                            "timestamp": runner[5]
                        }
                    })
            # Alle Hunter
            for hunter in db_getHunters(game_id):
                if hunter[3] is not None and hunter[4] is not None:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [hunter[4], hunter[3]]
                        },
                        "properties": {
                            "featuretype": "hunter",
                            "user_id": hunter[0],
                            "username": hunter[1],
                            "team": hunter[2],
                            "timestamp": hunter[5]
                        }
                    })
        elif role == "runner":
            # Nur eigene Position
            if user[3] is not None and user[4] is not None:
                features.append({
                    "type": "Feature",
                    "geometry": {
                        "type": "Point",
                        "coordinates": [user[4], user[3]]
                    },
                    "properties": {
                        "featuretype": "runner",
                        "user_id": user[0],
                        "username": user[1],
                        "team": user[2],
                        "timestamp": user[5]
                    }
                })
        elif role == "hunter":
            # Nur Hunter des eigenen Teams
            team = user[2]
            for hunter in db_getTeamMembers(game_id, team):
                if hunter[3] is not None and hunter[4] is not None:
                    features.append({
                        "type": "Feature",
                        "geometry": {
                            "type": "Point",
                            "coordinates": [hunter[4], hunter[3]]
                        },
                        "properties": {
                            "featuretype": "hunter",
                            "user_id": hunter[0],
                            "username": hunter[1],
                            "team": hunter[2],
                            "timestamp": hunter[5]
                        }
                    })
    geojson = {
        "type": "FeatureCollection",
        "features": features
    }
    return geojson

async def Map_SendMap(bot, chat_id, user_id, username, game_id):
    """Sendet eine Karte für das angegebene Spiel, je nach MapProvider"""
    logger_newLog("info", "Map_SendMap", f"Map-Sendung für User {username} ({user_id}) für Spiel {game_id}")
    try:
        game_data = db_Game_getField(game_id)
        if not game_data:
            await bot.send_message(chat_id, "❌ Spiel nicht gefunden oder Spielfeld nicht konfiguriert.")
            return False
        geojson = Map_GenerateGeoJSON(game_data, user_id)
        map_provider = conf_getMapProvider()
        
        # Erstelle user_info für Leaflet-HTML
        user_info = None
        if user_id:
            user = db_getUserPosition(user_id)
            if user:
                user_info = {
                    'role': user[6],
                    'username': user[1] or user[2],  # username oder first_name
                    'team': user[2]
                }
        
        if map_provider == "LokalMapServer-PNG":
            return await Map_SendMap_LokalMapServer(bot, chat_id, game_data, geojson)
        elif map_provider == "Leaflet-HTML":
            return await Map_SendMap_LeafletHTML(bot, chat_id, game_data, geojson, user_info)
        elif map_provider == "py-staticmap-PNG":
            return await Map_SendMap_pyStaticmapPNG(bot, chat_id, game_data, geojson, user_info)
        else:
            await bot.send_message(chat_id, f"❌ Unbekannter MapProvider: {map_provider}")
            return False
    except Exception as e:
        logger_newLog("error", "Map_SendMap", f"Unerwarteter Fehler: {str(e)}")
        await bot.send_message(chat_id, "❌ Unerwarteter Fehler beim Erstellen der Karte.")
        return False
    
    