# TelegramChaseBot.py 
from config import conf_checkconfig
from game import game_Scheduler
from telegram_bot import TelegramBot
from database import db_init
from logger import logger_newLog
import asyncio
import sys

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
    bot = TelegramBot()
    await asyncio.gather(
        game_Scheduler(),
        bot.run()
    )

if __name__ == "__main__":
    asyncio.run(main()) 