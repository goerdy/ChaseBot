# ChaseBot Web Interface

## Übersicht
Das Web Interface zeigt Server-Status und Spieldaten des ChaseBot an.

## Dateien
- `index.html` - Hauptseite mit Server-Status und Token-Eingabe

## Features
- **Server Status**: Zeigt Bot-Name, letztes Update, aktive Spiele und online Spieler
- **Daten-Tabelle**: Übersicht aller Spiele mit Status und Spieleranzahl
- **Token-Eingabe**: Formular für Game ID und Token (GameData-Ansicht noch nicht implementiert)
- **Auto-Refresh**: Aktualisiert sich alle 60 Sekunden automatisch
- **Responsive Design**: Funktioniert auf Desktop und Mobile

## Abhängigkeiten
- `ChaseBotServer.csv` - Wird vom Bot automatisch generiert und per FTP hochgeladen
- `ChaseBotServer.json` - Zusätzliche JSON-Daten (optional)

## Installation
1. Dateien auf Webserver hochladen
2. Sicherstellen, dass `ChaseBotServer.csv` im gleichen Verzeichnis liegt
3. Bot so konfigurieren, dass er die CSV-Datei per FTP hochlädt

## Konfiguration
Der Bot lädt die CSV-Datei automatisch per FTP hoch, wenn `WEBEXPORT_ENABLED=true` in der `config.env` gesetzt ist.

## TODO
- GameData-Ansicht für Token-basierten Zugriff implementieren
- Erweiterte Filter und Suchfunktionen
- Echtzeit-Updates via WebSocket (optional)
