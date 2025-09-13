from flask import Flask, request, send_file
import requests
import io
from PIL import Image, ImageDraw, ImageFont
import math

app = Flask(__name__)

def get_osm_tile_url(lat, lon, zoom):
    """Generiert OSM Tile URL für gegebene Koordinaten"""
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2.0 * n)
    return f"https://tile.openstreetmap.org/{zoom}/{xtile}/{ytile}.png"

def deg2num(lat_deg, lon_deg, zoom):
    """Wandelt Längen-/Breitengrad in Tile-Nummern um"""
    lat_rad = math.radians(lat_deg)
    n = 2.0 ** zoom
    xtile = int((lon_deg + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return (xtile, ytile)

def num2deg(xtile, ytile, zoom):
    """Wandelt Tile-Nummern in Längen-/Breitengrad um (obere linke Ecke)"""
    n = 2.0 ** zoom
    lon_deg = xtile / n * 360.0 - 180.0
    lat_rad = math.atan(math.sinh(math.pi * (1 - 2 * ytile / n)))
    lat_deg = math.degrees(lat_rad)
    return (lat_deg, lon_deg)

def adjust_bbox_to_aspect(min_lon, min_lat, max_lon, max_lat, width, height):
    """Passt die Bounding Box an das gewünschte Seitenverhältnis an, sodass alles sichtbar bleibt."""
    bbox_width = max_lon - min_lon
    bbox_height = max_lat - min_lat
    bbox_aspect = bbox_width / bbox_height
    img_aspect = width / height
    if bbox_aspect > img_aspect:
        # Bounding Box ist zu breit, Höhe anpassen
        new_height = bbox_width / img_aspect
        center_lat = (min_lat + max_lat) / 2
        min_lat = center_lat - new_height / 2
        max_lat = center_lat + new_height / 2
    else:
        # Bounding Box ist zu hoch, Breite anpassen
        new_width = bbox_height * img_aspect
        center_lon = (min_lon + max_lon) / 2
        min_lon = center_lon - new_width / 2
        max_lon = center_lon + new_width / 2
    return min_lon, min_lat, max_lon, max_lat

def latlon_to_global_pixel(lat, lon, zoom):
    """Berechnet die globalen Pixelkoordinaten im OSM-Tile-Raster für gegebene Lat/Lon und Zoom"""
    n = 2.0 ** zoom
    x = (lon + 180.0) / 360.0 * n * 256
    y = (1.0 - math.log(math.tan(math.radians(lat)) + 1 / math.cos(math.radians(lat))) / math.pi) / 2.0 * n * 256
    return x, y

def create_map_image(bbox, field_corners, finish_line, size=(800, 600)):
    """Erstellt eine Karte mit Spielfeld und Ziellinie"""
    min_lon, min_lat, max_lon, max_lat = map(float, bbox.split(','))
    # Passe Bounding Box an das Bildseitenverhältnis an
    min_lon, min_lat, max_lon, max_lat = adjust_bbox_to_aspect(min_lon, min_lat, max_lon, max_lat, size[0], size[1])
    lat_diff = max_lat - min_lat
    lon_diff = max_lon - min_lon
    max_diff = max(lat_diff, lon_diff)
    if max_diff > 0.1:
        zoom = 12
    elif max_diff > 0.01:
        zoom = 14
    elif max_diff > 0.001:
        zoom = 16
    else:
        zoom = 18
    # Berechne benötigte Tiles (oben links und unten rechts der neuen Bounding Box!)
    x_min, y_min = deg2num(max_lat, min_lon, zoom)  # oben links
    x_max, y_max = deg2num(min_lat, max_lon, zoom)  # unten rechts
    x_min, x_max = min(x_min, x_max), max(x_min, x_max)
    y_min, y_max = min(y_min, y_max), max(y_min, y_max)
    tiles_x = x_max - x_min + 1
    tiles_y = y_max - y_min + 1
    tile_size = 256
    map_px_width = tiles_x * tile_size
    map_px_height = tiles_y * tile_size
    map_img = Image.new('RGB', (map_px_width, map_px_height), (240, 240, 240))
    headers = {'User-Agent': 'Mozilla/5.0 (compatible; TelegramChaseBot/1.0)'}
    for x in range(x_min, x_max + 1):
        for y in range(y_min, y_max + 1):
            tile_url = get_osm_tile_url(*num2deg(x, y, zoom), zoom)
            try:
                response = requests.get(tile_url, timeout=10, headers=headers)
                print(f"Tile-URL: {tile_url}, Status: {response.status_code}")
                if response.status_code == 200:
                    tile_img = Image.open(io.BytesIO(response.content))
                    map_img.paste(tile_img, ((x - x_min) * tile_size, (y - y_min) * tile_size))
            except Exception as e:
                print(f"Fehler beim Tile-Download: {e}")
    # Berechne globale Pixelkoordinaten der Bounding Box (oben links)
    px0, py0 = latlon_to_global_pixel(max_lat, min_lon, zoom)
    # Projektion: Lat/Lon -> Pixel im zusammengesetzten Bild
    def latlon_to_pixel(lat, lon):
        px, py = latlon_to_global_pixel(lat, lon, zoom)
        rel_x = px - px0
        rel_y = py - py0
        # Skaliere auf die Bildgröße
        rel_x = rel_x * (size[0] / map_px_width)
        rel_y = rel_y * (size[1] / map_px_height)
        return int(rel_x), int(rel_y)
    map_img = map_img.resize(size, Image.Resampling.LANCZOS)
    draw = ImageDraw.Draw(map_img)
    field_pixels = [latlon_to_pixel(lat, lon) for lat, lon in field_corners]
    if len(field_pixels) >= 3:
        overlay = Image.new('RGBA', size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.polygon(field_pixels, fill=(255, 0, 0, 128), outline=(255, 0, 0, 255), width=3)
        map_img = Image.alpha_composite(map_img.convert('RGBA'), overlay).convert('RGB')
    if len(finish_line) >= 2:
        finish_pixels = [latlon_to_pixel(lat, lon) for lat, lon in finish_line]
        draw = ImageDraw.Draw(map_img)
        draw.line(finish_pixels, fill=(0, 255, 0), width=5)
        for x, y in finish_pixels:
            draw.ellipse([x-5, y-5, x+5, y+5], fill=(0, 255, 0), outline=(0, 200, 0), width=2)
    for i, (x, y) in enumerate(field_pixels):
        color = (255, 0, 0) if i == 0 else (200, 0, 0)
        draw.ellipse([x-4, y-4, x+4, y+4], fill=color, outline=(150, 0, 0), width=2)
    return map_img

@app.route('/staticmap.php')
def staticmap():
    """OSM Static Map kompatibler Endpoint"""
    try:
        # Parameter aus der URL
        bbox = request.args.get('bbox', '')
        size_param = request.args.get('size', '800x600')
        markers = request.args.get('markers', '')
        polygon = request.args.get('polygon', '')
        path = request.args.get('path', '')
        
        # Parse size
        width, height = map(int, size_param.split('x'))
        size = (width, height)
        
        # Parse Spielfeld-Koordinaten aus Polygon-Parameter
        field_corners = []
        finish_line = []
        
        if polygon:
            parts = polygon.split(',')
            if len(parts) >= 6:  # Mindestens 3 Punkte für Polygon
                color = parts[0]
                opacity = float(parts[1])
                border_opacity = float(parts[2])
                
                # Extrahiere Koordinaten (lon,lat Paare)
                coords = parts[3:]
                for i in range(0, len(coords), 2):
                    if i + 1 < len(coords):
                        lon = float(coords[i])
                        lat = float(coords[i + 1])
                        field_corners.append((lat, lon))
        
        if path:
            parts = path.split(',')
            if len(parts) >= 4:  # Mindestens 2 Punkte für Linie
                color = parts[0]
                width = int(parts[1])
                
                # Extrahiere Koordinaten (lon,lat Paare)
                coords = parts[2:]
                for i in range(0, len(coords), 2):
                    if i + 1 < len(coords):
                        lon = float(coords[i])
                        lat = float(coords[i + 1])
                        finish_line.append((lat, lon))
        
        # Erstelle Karte
        map_img = create_map_image(bbox, field_corners, finish_line, size)
        
        # Konvertiere zu Bytes
        img_io = io.BytesIO()
        map_img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')
        
    except Exception as e:
        # Fehler-Response
        error_img = Image.new('RGB', (800, 600), (255, 240, 240))
        draw = ImageDraw.Draw(error_img)
        draw.text((10, 10), f"Fehler: {str(e)}", fill=(255, 0, 0))
        
        img_io = io.BytesIO()
        error_img.save(img_io, 'PNG')
        img_io.seek(0)
        
        return send_file(img_io, mimetype='image/png')

if __name__ == '__main__':
    print("🚀 Starte lokalen OSM Static Map Server auf http://localhost:5000")
    print("📡 Endpoint: http://localhost:5000/staticmap.php")
    app.run(host='0.0.0.0', port=5000, debug=True) 