import requests
import tempfile
import os
from logger import logger_newLog

async def Map_SendMap_LokalMapServer(bot, chat_id, game_data, geojson):
    """Sendet eine PNG-Karte vom lokalen Map-Server"""
    lats = [game_data[4], game_data[6], game_data[8], game_data[10]]
    lons = [game_data[5], game_data[7], game_data[9], game_data[11]]
    min_lat, max_lat = min(lats), max(lats)
    min_lon, max_lon = min(lons), max(lons)
    lat_padding = (max_lat - min_lat) * 0.1
    lon_padding = (max_lon - min_lon) * 0.1
    bbox = f"{min_lon - lon_padding},{min_lat - lat_padding},{max_lon + lon_padding},{max_lat + lat_padding}"
    field_polygon = "&polygon=red,0.5,0.2"
    for i in range(4):
        field_polygon += f",{game_data[5+2*i]},{game_data[4+2*i]}"
    map_url = f"http://localhost:5000/staticmap.php?bbox={bbox}&size=800x600{field_polygon}"
    logger_newLog("debug", "Map_SendMap_LokalMapServer", f"Lokale OSM Map URL: {map_url}")
    try:
        response = requests.get(map_url, timeout=30)
        if response.status_code != 200:
            logger_newLog("error", "Map_SendMap_LokalMapServer", f"Fehler beim Laden der Karte: HTTP {response.status_code}")
            await bot.send_message(chat_id, "❌ Fehler beim Laden der Karte. Stelle sicher, dass der lokale Map-Server läuft.")
            return False
        with tempfile.NamedTemporaryFile(delete=False, suffix='.png') as temp_file:
            temp_file.write(response.content)
            temp_file_path = temp_file.name
        with open(temp_file_path, 'rb') as image_file:
            await bot.send_photo(
                chat_id,
                image_file,
                caption=f"🗺️ Spielfeld für Spiel: {game_data[1]}\n\n"
                       f"📍 Spielfeld: Rotes Polygon"
            )
        os.unlink(temp_file_path)
        logger_newLog("info", "Map_SendMap_LokalMapServer", f"Karte erfolgreich an User gesendet")
        return True
    except Exception as e:
        logger_newLog("error", "Map_SendMap_LokalMapServer", f"Fehler: {str(e)}")
        await bot.send_message(chat_id, "❌ Fehler beim Laden der Karte.")
        return False 