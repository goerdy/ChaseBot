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
$visible_players = [];
$visible_pois = [];

if ($token_type === 'gamemaster') {
    // Gamemaster sieht alle Spieler und POIs
    $visible_players = $game_data['players'];
    $visible_pois = $game_data['map']['pois'];
} elseif ($token_type === 'hunter_team') {
    // Hunter-Team sieht nur eigenes Team und alle Runner
    foreach ($game_data['players'] as $player) {
        if ($player['role'] === 'runner' || ($player['role'] === 'hunter' && $player['team'] === $team)) {
            $visible_players[] = $player;
        }
    }
    // Nur POIs des eigenen Teams
    foreach ($game_data['map']['pois'] as $poi) {
        if ($poi['team'] === $team) {
            $visible_pois[] = $poi;
        }
    }
} elseif ($token_type === 'runner') {
    // Runner sieht nur sich selbst
    foreach ($game_data['players'] as $player) {
        if ($player['user_id'] === $user_id) {
            $visible_players[] = $player;
            break;
        }
    }
    // Runner sieht keine POIs
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
            </div>
            
            <div class="players-section">
                <div class="section-title">Spieler</div>
                <div class="player-list">
                    <?php
                    // Spieler nach Rolle gruppieren
                    $runners = [];
                    $hunters_by_team = [];
                    $gamemaster = null;
                    
                    foreach ($visible_players as $player) {
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
                            echo ' <span class="player-budget coin">' . $runner['budget'] . ' Coins</span>';
                            echo '</div>';
                            echo '<div class="status-indicator ' . $status_class . '"></div>';
                            echo '</div>';
                        }
                    }
                    
                    // Hunter-Teams anzeigen
                    foreach ($hunters_by_team as $team_name => $hunters) {
                        $team_budget = isset($game_data['teams_budget'][$team_name]) ? $game_data['teams_budget'][$team_name] : 0;
                        echo '<div class="team-header">Team ' . htmlspecialchars($team_name) . ' <span class="coin">' . $team_budget . ' Coins</span></div>';
                        
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
        
        // Spieler-Marker hinzufügen
        const players = <?php echo json_encode($visible_players); ?>;
        players.forEach(player => {
            if (player.location && player.location.lat && player.location.lon) {
                let markerColor = '#95a5a6';
                if (player.role === 'runner') markerColor = '#27ae60';
                else if (player.role === 'hunter') markerColor = '#e74c3c';
                else if (player.role === 'gamemaster') markerColor = '#9b59b6';
                
                const marker = L.circleMarker([player.location.lat, player.location.lon], {
                    color: markerColor,
                    fillColor: markerColor,
                    fillOpacity: 0.7,
                    radius: 8
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
        
        // POI-Marker hinzufügen
        const pois = <?php echo json_encode($visible_pois); ?>;
        pois.forEach(poi => {
            if (poi.lat && poi.lon) {
                let poiColor = '#f39c12';
                if (poi.type === 'trap') poiColor = '#e74c3c';
                else if (poi.type === 'watchtower') poiColor = '#3498db';
                
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
        
        // Auto-Refresh alle 30 Sekunden
        setInterval(() => {
            location.reload();
        }, 30000);
    </script>
</body>
</html>
