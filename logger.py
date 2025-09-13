import logging
from config import conf_getLoglevel

def logger_newLog(loglevel, functionname, text):
    # Hole das konfigurierte LogLevel
    config_loglevel = conf_getLoglevel()
    
    # Definiere LogLevel Hierarchie
    level_hierarchy = {
        'debug': 10,
        'info': 20,
        'warning': 30,
        'error': 40,
        'critical': 50
    }
    
    # Prüfe ob geloggt werden muss
    if not loglevel or loglevel.lower() not in level_hierarchy:
        return  # Ungültiges LogLevel
    
    if not config_loglevel or config_loglevel.lower() not in level_hierarchy:
        return  # Ungültiges konfiguriertes LogLevel
    
    # Prüfe ob das aktuelle LogLevel hoch genug ist
    if level_hierarchy[loglevel.lower()] < level_hierarchy[config_loglevel.lower()]:
        return  # LogLevel zu niedrig, nicht loggen
    
    # Ausgabe auf Konsole
    print(f"[{loglevel.upper()}] {functionname}: {text}")
    
    # TODO: Loggen in Datei oder DB noch implementieren 