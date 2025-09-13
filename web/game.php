<?php
// game.php - Game-spezifische Ansicht mit Token-basierter Filterung

// Parameter aus URL holen
$game_id = isset($_GET['id']) ? intval($_GET['id']) : null;
$token = isset($_GET['token']) ? $_GET['token'] : null;

if (!$game_id || !$token) {
    die('Fehler: Game ID und Token erforderlich');
}

// JSON-Daten laden
$json_file = "ChaseBotGame_{$game_id}.json";
$json_data = @file_get_contents($json_file);

if (!$json_data) {
    die('Fehler: Spieldaten nicht gefunden');
}

$game_data = json_decode($json_data, true);
if (!$game_data) {
    die('Fehler: Ungültige Spieldaten');
}

// Token validieren und Typ bestimmen
$token_type = null;
$user_id = null;
$team = null;

// Gamemaster-Token prüfen
foreach ($game_data['players'] as $player) {
    if ($player['role'] === 'gamemaster' && $player['token'] === $token) {
        $token_type = 'gamemaster';
        $user_id = $player['user_id'];
        break;
    }
}

// Runner-Token prüfen
if (!$token_type) {
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'runner' && $player['token'] === $token) {
            $token_type = 'runner';
            $user_id = $player['user_id'];
            break;
        }
    }
}

// Team-Token prüfen
if (!$token_type) {
    foreach ($game_data['team_tokens'] as $team_token) {
        if ($team_token['token'] === $token) {
            $token_type = 'hunter_team';
            $team = $team_token['team'];
            break;
        }
    }
}

if (!$token_type) {
    die('Fehler: Ungültiger Token');
}

// Spieler filtern basierend auf Token
$visible_players = []; // Für die Karte
$visible_pois = [];
$visible_watchtowers = []; // Wachtürme sind immer für alle sichtbar

// Für die Spielerliste: Alle Spieler anzeigen (unabhängig von der Rolle)
$all_players = $game_data['players'];

if ($token_type === 'gamemaster') {
    // Gamemaster sieht alle Spieler auf der Karte
    $visible_players = $game_data['players'];
    // Gamemaster sieht alle POIs
    $visible_pois = $game_data['map']['pois'];
    $visible_watchtowers = $game_data['map']['pois']; // Alle POIs inkl. Wachtürme
} elseif ($token_type === 'hunter_team') {
    // Hunter-Team sieht nur eigenes Team auf der Karte (KEINE Runner!)
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'hunter' && $player['team'] === $team) {
            $visible_players[] = $player;
        }
    }
    // Nur POIs des eigenen Teams (außer Wachtürme)
    foreach ($game_data['map']['pois'] as $poi) {
        if ($poi['team'] === $team) {
            $visible_pois[] = $poi;
        }
        // Wachtürme sind immer sichtbar
        if ($poi['type'] === 'WATCHTOWER') {
            $visible_watchtowers[] = $poi;
        }
    }
} elseif ($token_type === 'runner') {
    // Runner sieht nur sich selbst auf der Karte
    foreach ($game_data['players'] as $player) {
        if ($player['user_id'] === $user_id) {
            $visible_players[] = $player;
            break;
        }
    }
    // Runner sieht keine POIs außer Wachtürme
    foreach ($game_data['map']['pois'] as $poi) {
        if ($poi['type'] === 'WATCHTOWER') {
            $visible_watchtowers[] = $poi;
        }
    }
}

// Spielzeit berechnen
$start_time = new DateTime($game_data['game']['start_time']);
$now = new DateTime();
$duration_minutes = $game_data['game']['duration_minutes'];
$headstart_minutes = $game_data['game']['runner_headstart_minutes'];

$elapsed_minutes = $now->diff($start_time)->i + ($now->diff($start_time)->h * 60);
$remaining_minutes = $duration_minutes - $elapsed_minutes;

// Gamemaster-Name finden
$gamemaster_name = 'Unbekannt';
foreach ($game_data['players'] as $player) {
    if ($player['role'] === 'gamemaster') {
        $gamemaster_name = $player['first_name'] . ' (@' . $player['username'] . ')';
        break;
    }
}

// Aktueller User basierend auf Token ermitteln
$current_user = null;
$current_user_role = 'Unbekannt';
$current_user_team = null;

if ($token_type === 'gamemaster') {
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'gamemaster' && $player['token'] === $token) {
            $current_user = $player;
            $current_user_role = 'Gamemaster';
            break;
        }
    }
} elseif ($token_type === 'hunter_team') {
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'hunter' && $player['team'] === $team) {
            $current_user = $player;
            $current_user_role = 'Hunter';
            $current_user_team = $team;
            break;
        }
    }
} elseif ($token_type === 'runner') {
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'runner' && $player['token'] === $token) {
            $current_user = $player;
            $current_user_role = 'Runner';
            break;
        }
    }
}
?>

<!DOCTYPE html>
<html lang="de">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChaseBot - <?php echo htmlspecialchars($game_data['game']['name']); ?></title>
    
    <!-- Leaflet CSS -->
    <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
    
    <!-- Leaflet JavaScript -->
    <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
    
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: #f5f5f5;
            height: 100vh;
            overflow: hidden;
        }
        
        .container {
            display: flex;
            height: 100vh;
        }
        
        .map-container {
            flex: 2;
            position: relative;
        }
        
        #map {
            height: 100%;
            width: 100%;
        }
        
        .sidebar {
            flex: 1;
            background: white;
            padding: 20px;
            overflow-y: auto;
            box-shadow: -2px 0 10px rgba(0,0,0,0.1);
        }
        
        .game-info {
            background: #2c3e50;
            color: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
        }
        
        .game-title {
            font-size: 1.5em;
            font-weight: bold;
            margin-bottom: 10px;
        }
        
        .game-details {
            font-size: 0.9em;
            opacity: 0.9;
        }
        
        .time-info {
            margin-top: 10px;
            padding: 10px;
            background: rgba(255,255,255,0.1);
            border-radius: 5px;
        }
        
        .players-section {
            margin-bottom: 20px;
        }
        
        .section-title {
            font-size: 1.2em;
            font-weight: bold;
            margin-bottom: 10px;
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        .player-list {
            background: #f8f9fa;
            border-radius: 8px;
            padding: 10px;
        }
        
        .player-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 8px 12px;
            margin: 5px 0;
            background: white;
            border-radius: 5px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        .player-name {
            font-weight: bold;
        }
        
        .player-budget {
            color: #f39c12;
            font-weight: bold;
        }
        
        .status-indicator {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-left: 10px;
        }
        
        .status-green { background: #27ae60; }
        .status-orange { background: #f39c12; }
        .status-red { background: #e74c3c; }
        
        .team-header {
            background: #3498db;
            color: white;
            font-weight: bold;
            margin: 10px 0 5px 0;
            padding: 8px 12px;
            border-radius: 5px;
        }
        
        .role-runner { color: #27ae60; }
        .role-hunter { color: #e74c3c; }
        .role-gamemaster { color: #9b59b6; }
        
        .refresh-btn {
            position: absolute;
            top: 20px;
            right: 20px;
            background: #3498db;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            font-weight: bold;
            z-index: 1000;
        }
        
        .refresh-btn:hover {
            background: #2980b9;
        }
        
        .coin {
            color: #f39c12;
            font-weight: bold;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="map-container">
            <div id="map"></div>
            <button class="refresh-btn" onclick="location.reload()">🔄 Aktualisieren</button>
        </div>
        
        <div class="sidebar">
            <div class="game-info">
                <div class="game-title"><?php echo htmlspecialchars($game_data['game']['name']); ?></div>
                <div class="game-details">
                    <div>Gamemaster: <?php echo htmlspecialchars($gamemaster_name); ?></div>
                    <div>Status: <?php echo ucfirst($game_data['game']['status']); ?></div>
                </div>
                <div class="time-info">
                    <div>Spielzeit: <?php echo $elapsed_minutes; ?> Min</div>
                    <div>Verbleibend: <?php echo max(0, $remaining_minutes); ?> Min</div>
                </div>
                <?php if ($current_user): ?>
                <div class="user-info" style="margin-top: 15px; padding-top: 15px; border-top: 1px solid #34495e;">
                    <div style="font-weight: bold; color: #ecf0f1;">Eingeloggt als:</div>
                    <div style="margin-top: 5px;">
                        <span style="color: #3498db;"><?php echo htmlspecialchars($current_user['first_name']); ?></span>
                        <span style="color: #95a5a6;">(@<?php echo htmlspecialchars($current_user['username']); ?>)</span>
                    </div>
                    <div style="margin-top: 3px; font-size: 0.9em;">
                        <span style="color: #e74c3c; font-weight: bold;"><?php echo $current_user_role; ?></span>
                        <?php if ($current_user_team): ?>
                        <span style="color: #95a5a6;">- Team <?php echo htmlspecialchars($current_user_team); ?></span>
                        <?php endif; ?>
                    </div>
                </div>
                <?php endif; ?>
            </div>
            
            <div class="players-section">
                <div class="section-title">Spieler</div>
                <div class="player-list">
                    <?php
                    // Spieler nach Rolle gruppieren
                    $runners = [];
                    $hunters_by_team = [];
                    $gamemaster = null;
                    
                    foreach ($all_players as $player) {
                        if ($player['role'] === 'gamemaster') {
                            $gamemaster = $player;
                        } elseif ($player['role'] === 'runner') {
                            $runners[] = $player;
                        } elseif ($player['role'] === 'hunter') {
                            $team = $player['team'];
                            if (!isset($hunters_by_team[$team])) {
                                $hunters_by_team[$team] = [];
                            }
                            $hunters_by_team[$team][] = $player;
                        }
                    }
                    
                    // Gamemaster anzeigen
                    if ($gamemaster) {
                        $last_seen = new DateTime($gamemaster['last_seen']);
                        $minutes_ago = $now->diff($last_seen)->i + ($now->diff($last_seen)->h * 60);
                        $status_class = $minutes_ago <= 3 ? 'status-green' : ($minutes_ago <= 6 ? 'status-orange' : 'status-red');
                        
                        echo '<div class="player-item">';
                        echo '<div>';
                        echo '<span class="player-name role-gamemaster">' . htmlspecialchars($gamemaster['first_name']) . ' (@' . htmlspecialchars($gamemaster['username']) . ')</span>';
                        if ($token_type === 'gamemaster') {
                            echo ' <span class="player-budget coin">' . $gamemaster['budget'] . ' Coins</span>';
                        }
                        echo '</div>';
                        echo '<div class="status-indicator ' . $status_class . '"></div>';
                        echo '</div>';
                    }
                    
                    // Runners anzeigen
                    if (!empty($runners)) {
                        echo '<div class="team-header">Runner:</div>';
                        foreach ($runners as $runner) {
                            $last_seen = new DateTime($runner['last_seen']);
                            $minutes_ago = $now->diff($last_seen)->i + ($now->diff($last_seen)->h * 60);
                            $status_class = $minutes_ago <= 3 ? 'status-green' : ($minutes_ago <= 6 ? 'status-orange' : 'status-red');
                            
                            echo '<div class="player-item">';
                            echo '<div>';
                        echo '<span class="player-name role-runner">' . htmlspecialchars($runner['first_name']) . ' (@' . htmlspecialchars($runner['username']) . ')</span>';
                        if ($token_type === 'gamemaster') {
                            echo ' <span class="player-budget coin">' . $runner['budget'] . ' Coins</span>';
                        }
                            echo '</div>';
                            echo '<div class="status-indicator ' . $status_class . '"></div>';
                            echo '</div>';
                        }
                    }
                    
                    // Hunter-Teams anzeigen
                    foreach ($hunters_by_team as $team_name => $hunters) {
                        $team_budget = isset($game_data['teams_budget'][$team_name]) ? $game_data['teams_budget'][$team_name] : 0;
                        echo '<div class="team-header">Team ' . htmlspecialchars($team_name);
                        if ($token_type === 'gamemaster') {
                            echo ' <span class="coin">' . $team_budget . ' Coins</span>';
                        }
                        echo '</div>';
                        
                        foreach ($hunters as $hunter) {
                            $last_seen = new DateTime($hunter['last_seen']);
                            $minutes_ago = $now->diff($last_seen)->i + ($now->diff($last_seen)->h * 60);
                            $status_class = $minutes_ago <= 3 ? 'status-green' : ($minutes_ago <= 6 ? 'status-orange' : 'status-red');
                            
                            echo '<div class="player-item">';
                            echo '<div>';
                            echo '<span class="player-name role-hunter">' . htmlspecialchars($hunter['first_name']) . ' (@' . htmlspecialchars($hunter['username']) . ')</span>';
                            echo '</div>';
                            echo '<div class="status-indicator ' . $status_class . '"></div>';
                            echo '</div>';
                        }
                    }
                    ?>
                </div>
            </div>
        </div>
    </div>

    <script>
        // Karte initialisieren
        const map = L.map('map').setView([53.5, 8.0], 10);
        
        // OpenStreetMap Tile Layer
        L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
            attribution: '© OpenStreetMap contributors'
        }).addTo(map);
        
        // Spielfeld zeichnen
        const field = <?php echo json_encode($game_data['map']['field']); ?>;
        let fieldBounds = null;
        if (field.corner1 && field.corner2 && field.corner3 && field.corner4) {
            const fieldCoords = [
                [field.corner1.lat, field.corner1.lon],
                [field.corner2.lat, field.corner2.lon],
                [field.corner3.lat, field.corner3.lon],
                [field.corner4.lat, field.corner4.lon]
            ];
            
            L.polygon(fieldCoords, {
                color: '#3498db',
                weight: 3,
                fillOpacity: 0.1
            }).addTo(map);
            
            // Bounds für Auto-Zoom berechnen
            fieldBounds = L.latLngBounds(fieldCoords);
        }
        
        // Ziellinie zeichnen
        const finishLine = <?php echo json_encode($game_data['map']['finish_line']); ?>;
        if (finishLine.point1 && finishLine.point2) {
            L.polyline([
                [finishLine.point1.lat, finishLine.point1.lon],
                [finishLine.point2.lat, finishLine.point2.lon]
            ], {
                color: '#e74c3c',
                weight: 5
            }).addTo(map);
        }
        
        // Spieler-Marker hinzufügen (außer Gamemaster)
        const players = <?php echo json_encode($visible_players); ?>;
        players.forEach(player => {
            if (player.location && player.location.lat && player.location.lon && player.role !== 'gamemaster') {
                let markerIcon;
                
                if (player.role === 'runner') {
                    // Runner: Schwarzer Marker
                    markerIcon = L.divIcon({
                        className: 'player-marker',
                        html: '<div style="background-color: #000000; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.8);"></div>',
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    });
                } else if (player.role === 'hunter') {
                    // Hunter: Teamfarbe
                    const teamColors = {
                        'red': '#e74c3c',
                        'blue': '#3498db',
                        'green': '#27ae60',
                        'yellow': '#f1c40f',
                        'purple': '#9b59b6'
                    };
                    const teamColor = teamColors[player.team] || '#95a5a6';
                    markerIcon = L.divIcon({
                        className: 'player-marker',
                        html: `<div style="background-color: ${teamColor}; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>`,
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    });
                } else {
                    // Fallback: Grauer Marker
                    markerIcon = L.divIcon({
                        className: 'player-marker',
                        html: '<div style="background-color: #95a5a6; width: 20px; height: 20px; border-radius: 50%; border: 2px solid white; box-shadow: 0 0 5px rgba(0,0,0,0.5);"></div>',
                        iconSize: [20, 20],
                        iconAnchor: [10, 10]
                    });
                }
                
                const marker = L.marker([player.location.lat, player.location.lon], {
                    icon: markerIcon
                }).addTo(map);
                
                marker.bindPopup(`
                    <strong>${player.first_name} (@${player.username})</strong><br>
                    Rolle: ${player.role}<br>
                    Team: ${player.team || 'Kein Team'}<br>
                    Budget: ${player.budget} Coins<br>
                    Letztes Update: ${new Date(player.location.timestamp).toLocaleString()}
                `);
            }
        });
        
        // POI-Marker hinzufügen (Fallen, etc.)
        const pois = <?php echo json_encode($visible_pois); ?>;
        pois.forEach(poi => {
            if (poi.lat && poi.lon && poi.type !== 'WATCHTOWER') {
                let poiColor = '#f39c12';
                if (poi.type === 'TRAP') poiColor = '#e74c3c';
                
                const poiMarker = L.circleMarker([poi.lat, poi.lon], {
                    color: poiColor,
                    fillColor: poiColor,
                    fillOpacity: 0.6,
                    radius: 6
                }).addTo(map);
                
                poiMarker.bindPopup(`
                    <strong>${poi.type}</strong><br>
                    Team: ${poi.team || 'Kein Team'}<br>
                    Radius: ${poi.range_meters}m<br>
                    Erstellt: ${new Date(poi.timestamp).toLocaleString()}
                `);
                
                // Radius-Kreis zeichnen
                if (poi.range_meters > 0) {
                    L.circle([poi.lat, poi.lon], {
                        color: poiColor,
                        fillColor: poiColor,
                        fillOpacity: 0.1,
                        radius: poi.range_meters
                    }).addTo(map);
                }
            }
        });
        
        // Wachtürme separat hinzufügen (immer sichtbar, in Team-Farbe)
        const watchtowers = <?php echo json_encode($visible_watchtowers); ?>;
        watchtowers.forEach(poi => {
            if (poi.lat && poi.lon && poi.type === 'WATCHTOWER') {
                // Team-Farben definieren
                const teamColors = {
                    'red': '#e74c3c',
                    'blue': '#3498db',
                    'green': '#27ae60',
                    'yellow': '#f1c40f',
                    'purple': '#9b59b6',
                    'orange': '#e67e22'
                };
                
                const teamColor = teamColors[poi.team] || '#3498db'; // Standard: Blau
                
                // Wachturm ohne Mittelpunkt - nur äußerer Ring
                const watchtowerMarker = L.circle([poi.lat, poi.lon], {
                    color: teamColor,
                    fillColor: teamColor,
                    fillOpacity: 0.1,
                    radius: 8,
                    weight: 2
                }).addTo(map);
                
                watchtowerMarker.bindPopup(`
                    <strong>🗼 Wachturm</strong><br>
                    Team: <span style="color: ${teamColor}; font-weight: bold;">${poi.team}</span><br>
                    Reichweite: ${poi.range_meters}m<br>
                    Erstellt: ${new Date(poi.timestamp).toLocaleString()}
                `);
                
                // Reichweite-Kreis hinzufügen
                L.circle([poi.lat, poi.lon], {
                    color: teamColor,
                    fillColor: teamColor,
                    fillOpacity: 0.1,
                    radius: poi.range_meters,
                    weight: 2
                }).addTo(map);
            }
        });
        
        // Auto-Zoom auf Spielfeld
        if (fieldBounds) {
            // Füge etwas Padding hinzu, damit das Spielfeld nicht am Rand klebt
            map.fitBounds(fieldBounds, { padding: [20, 20] });
        }
        
        // Auto-Refresh alle 30 Sekunden
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
