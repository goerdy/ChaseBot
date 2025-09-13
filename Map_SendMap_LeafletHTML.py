import tempfile
import os
import json
from logger import logger_newLog

# Mapping von Teamnamen zu Markerfarben
TEAM_MARKER_COLORS = {
    "red": "red",
    "blue": "blue",
    "green": "green",
    "yellow": "yellow",
    "purple": "purple",
    None: "grey"
}

async def Map_SendMap_LeafletHTML(bot, chat_id, game_data, geojson, user_info=None):
    """Sendet eine HTML-Karte mit Leaflet und GeoJSON, Hunter in Teamfarbe, Runner grau"""
    try:
        # Bestimme Untertitel basierend auf user_info
        subtitle = "Gamemasterkarte"
        if user_info:
            if user_info.get('role') == 'hunter':
                subtitle = f"Hunterkarte - {user_info.get('username', 'Unbekannt')} (Team: {user_info.get('team', 'Unbekannt')})"
            elif user_info.get('role') == 'runner':
                subtitle = f"Runnerkarte - {user_info.get('username', 'Unbekannt')}"
        
        marker_js = '''
        var markerIcons = {
            red: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-red.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]}),
            blue: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-blue.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]}),
            green: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-green.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]}),
            yellow: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-yellow.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]}),
            purple: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-purple.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]}),
            grey: new L.Icon({iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-grey.png', shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png', iconSize: [25,41], iconAnchor: [12,41], popupAnchor: [1,-34], shadowSize: [41,41]})
        };
        
        // POI Icons
        var poiIcons = {
            TRAP: L.divIcon({
                className: 'poi-icon',
                html: '<div style="background-color: #ff0000; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>',
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            }),
            WATCHTOWER: L.divIcon({
                className: 'poi-icon',
                html: '<div style="background-color: #0000ff; width: 24px; height: 24px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>',
                iconSize: [24, 24],
                iconAnchor: [12, 12]
            }),
            RADARPING: L.divIcon({
                className: 'poi-icon',
                html: '<div style="background-color: #ff00ff; width: 16px; height: 16px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            })
        };
        '''
        html = f'''<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="utf-8" />
    <title>Chase: {game_data[1]}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" href="https://unpkg.com/leaflet/dist/leaflet.css" />
    <style>#map {{ height: 90vh; }}</style>
    <style>
        .legend {{
            background: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 0 15px rgba(0,0,0,0.2);
            font-size: 12px;
            line-height: 1.4;
        }}
        .legend h4 {{
            margin: 0 0 10px 0;
            font-size: 14px;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            margin: 5px 0;
        }}
        .legend-icon {{
            width: 20px;
            height: 20px;
            margin-right: 8px;
            border-radius: 50%;
            border: 2px solid white;
            box-shadow: 0 0 3px rgba(0,0,0,0.3);
        }}
        .legend-icon.trap {{ background-color: #ff0000; }}
        .legend-icon.watchtower {{ background-color: #0000ff; }}
        .legend-icon.radarping {{ background-color: #ff00ff; }}
        .legend-icon.runner {{ background-color: #808080; }}
        .legend-icon.hunter {{ background-color: #ff6600; }}
    </style>
</head>
<body>
    <h2>Chase: {game_data[1]}</h2>
    <h3>{subtitle}</h3>
    <div id="map"></div>
    <script src="https://unpkg.com/leaflet/dist/leaflet.js"></script>
    <script>
        var map = L.map('map');
        L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{ maxZoom: 19 }}).addTo(map);
        {marker_js}
        
        // Legende hinzufügen
        var legend = L.control({{position: 'bottomright'}});
        legend.onAdd = function (map) {{
            var div = L.DomUtil.create('div', 'legend');
            div.innerHTML = '<h4>Legende</h4>' +
                '<div class="legend-item"><div class="legend-icon trap"></div>TRAP (Falle)</div>' +
                '<div class="legend-item"><div class="legend-icon watchtower"></div>WACHTTURM</div>' +
                '<div class="legend-item"><div class="legend-icon radarping"></div>RADAR PING</div>' +
                '<div class="legend-item"><div class="legend-icon runner"></div>Runner</div>' +
                '<div class="legend-item"><div class="legend-icon hunter"></div>Hunter</div>';
            return div;
        }};
        legend.addTo(map);
        
        var geojson = {json.dumps(geojson)};
        // Flächen und Linien
        var geoJsonLayer = L.geoJSON(geojson, {{
            filter: function(feature) {{
                return feature.geometry.type !== 'Point';
            }},
            style: function (feature) {{
                if (feature.properties.featuretype === 'field') return {{ color: '#f00', weight: 3, fillOpacity: 0.3 }};
                if (feature.properties.featuretype === 'finishline') return {{ color: '#0c0', weight: 5 }};
                // POI Range-Kreise
                if (feature.properties.featuretype === 'TRAP') return {{ color: '#ff0000', weight: 2, fillOpacity: 0.2, fillColor: '#ff0000' }};
                if (feature.properties.featuretype === 'WATCHTOWER') return {{ color: '#0000ff', weight: 3, fillOpacity: 0, fillColor: '#0000ff' }};
            }}
        }}).addTo(map);
        
        // Marker für Spieler und POIs
        var markerLayer = L.geoJSON(geojson, {{
            filter: function(feature) {{ return feature.geometry.type === 'Point'; }},
            pointToLayer: function (feature, latlng) {{
                var t = feature.properties.featuretype;
                
                // Spieler-Marker
                if (t === 'hunter') {{
                    var color = feature.properties.team || 'grey';
                    if (!markerIcons[color]) color = 'grey';
                    return L.marker(latlng, {{icon: markerIcons[color]}}).bindPopup('Hunter: ' + feature.properties.username + '<br>Team: ' + feature.properties.team);
                }}
                if (t === 'runner') {{
                    return L.marker(latlng, {{icon: markerIcons['grey']}}).bindPopup('Runner: ' + feature.properties.username);
                }}
                
                // POI-Marker
                if (t === 'TRAP') {{
                    var popup = 'TRAP<br>Reichweite: ' + (feature.properties.range || 'unbekannt') + 'm';
                    return L.marker(latlng, {{icon: poiIcons.TRAP}}).bindPopup(popup);
                }}
                if (t === 'WATCHTOWER') {{
                    var popup = 'WACHTTURM<br>Reichweite: ' + (feature.properties.range || 'unbekannt') + 'm';
                    return L.marker(latlng, {{icon: poiIcons.WATCHTOWER}}).bindPopup(popup);
                }}
                if (t === 'RADARPING') {{
                    var popup = 'RADAR PING<br>Reichweite: ' + (feature.properties.range || 'unbekannt') + 'm';
                    return L.marker(latlng, {{icon: poiIcons.RADARPING}}).bindPopup(popup);
                }}
                
                return L.marker(latlng);
            }}
        }}).addTo(map);
        // Automatisch auf alle Features zoomen
        var allLayers = L.featureGroup([geoJsonLayer, markerLayer]);
        map.fitBounds(allLayers.getBounds(), {{ padding: [20, 20] }});
    </script>
</body>
</html>'''
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as temp_file:
            temp_file.write(html)
            temp_file_path = temp_file.name
        with open(temp_file_path, 'rb') as html_file:
            await bot.send_document(
                chat_id,
                html_file,
                caption=f"🗺️ Leaflet-Karte für Spiel: {game_data[1]} (GeoJSON)"
            )
        os.unlink(temp_file_path)
        logger_newLog("info", "Map_SendMap_LeafletHTML", f"Leaflet-HTML erfolgreich an User gesendet")
        return True
    except Exception as e:
        logger_newLog("error", "Map_SendMap_LeafletHTML", f"Fehler: {str(e)}")
        await bot.send_message(chat_id, "❌ Fehler beim Erstellen der Leaflet-Karte.")
        return False 