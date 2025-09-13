import staticmaps
from PIL import ImageDraw, ImageFont

# Monkey-Patch für Pillow 11.x Kompatibilität
def textsize_patch(self, text, font=None, spacing=4, direction=None, features=None, language=None, stroke_width=0, image_mode=None, anchor=None):
    """Ersatz für die entfernte textsize Methode"""
    if font is None:
        font = ImageFont.load_default()
    
    # Verwende getbbox statt textsize
    bbox = font.getbbox(text)
    if bbox:
        return bbox[2] - bbox[0], bbox[3] - bbox[1]
    return 0, 0

# Patch anwenden
ImageDraw.ImageDraw.textsize = textsize_patch

# Deine vier Ecken
field_corners = [
    staticmaps.create_latlng(53.485694, 7.768707),
    staticmaps.create_latlng(53.636658, 7.768707),
    staticmaps.create_latlng(53.636658, 8.158356),
    staticmaps.create_latlng(53.485694, 8.158356)
]

# Kontext und Tile-Provider
context = staticmaps.Context()
context.set_tile_provider(staticmaps.tile_provider_OSM)

# Polygon hinzufügen
context.add_object(staticmaps.Area(
    field_corners,
    fill_color=staticmaps.parse_color("#FF000020"),  # Rot mit Transparenz
    width=2,
    color=staticmaps.RED
))

# Zentrum und Zoom setzen
center_lat = (53.485694 + 53.636658) / 2
center_lon = (7.768707 + 8.158356) / 2
context.set_center(staticmaps.create_latlng(center_lat, center_lon))
context.set_zoom(12)

try:
    # Rendern und speichern
    image = context.render_pillow(800, 600)
    print("Bild gerendert:", image)
    image.save("testfeld.png")
    print("PNG gespeichert als testfeld.png")
except Exception as e:
    print("Fehler beim Rendern oder Speichern:", e)