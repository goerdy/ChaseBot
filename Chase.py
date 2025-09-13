# TelegramChaseBot.py 
from config import conf_checkconfig
from game import game_Scheduler
from telegram_bot import TelegramBot
from database import db_init
from logger import logger_newLog
import asyncio
import sys

# Globale Variable für Bot-Name
BOT_NAME = "ChaseGame2025Bot"  # Fallback-Name

def get_bot_name():
    """Gibt den aktuellen Bot-Namen zurück"""
    return BOT_NAME

# Prüfe Konfiguration beim Start
if not conf_checkconfig():
    logger_newLog("error", "on startup", "Fehler: Konfiguration ungültig oder unvollständig")
    sys.exit(1)

# Initialisiere Datenbank
if not db_init():
    logger_newLog("error", "on startup", "Fehler: Datenbankinitialisierung fehlgeschlagen")
    sys.exit(1)

# Starte den asynchronen Scheduler und Bot
async def main():
    global BOT_NAME
    
    # Bot-Name einmal beim Start abrufen
    bot = TelegramBot()
    bot_info = await bot.get_bot_info()
    if bot_info:
        BOT_NAME = bot_info.get('first_name', BOT_NAME)
        logger_newLog("info", "main", f"Bot-Name abgerufen: {BOT_NAME}")
    else:
        logger_newLog("warning", "main", f"Bot-Name konnte nicht abgerufen werden, verwende Fallback: {BOT_NAME}")
    
    await asyncio.gather(
        game_Scheduler(),
        bot.run()
    )

if __name__ == "__main__":
    asyncio.run(main()) 