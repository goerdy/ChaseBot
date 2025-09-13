import asyncio
import aiohttp
from config import conf_getTelegramAPIkey
from logger import logger_newLog
from telegram_commands import cmd_start, cmd_new, cmd_join, cmd_leave, cmd_fieldsetup, cmd_map, cmd_mapedit, cmd_unknown, handle_text, handle_location, cmd_role, cmd_startgame, cmd_listgames, cmd_listusers, cmd_team, cmd_shop, cmd_buy, cmd_status, cmd_endgame, cmd_keyboard
from telegram_helpmessage import send_helpmessage

class TelegramBot:
    def __init__(self):
        self.api_key = conf_getTelegramAPIkey()
        self.base_url = f"https://api.telegram.org/bot{self.api_key}"
        self.offset = 0
        
    async def get_updates(self):
        """Holt Updates von der Telegram API"""
        try:
            url = f"{self.base_url}/getUpdates"
            params = {'offset': self.offset, 'timeout': 30}
            
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('ok'):
                            return data.get('result', [])
            return []
        except Exception as e:
            logger_newLog("error", "get_updates", f"Fehler beim Abrufen der Updates: {str(e)}")
            return []
    
    async def handle_command(self, message):
        """Behandelt eingehende Befehle und Nachrichten"""
        chat_id = message['chat']['id']
        user_id = message['from']['id']
        username = message['from'].get('username', '')
        first_name = message['from'].get('first_name', '')
        
        # Prüfe ob User in der Datenbank existiert (außer bei /start)
        from database import db_User_get
        existing_user = db_User_get(user_id)
        
        # Prüfe ob es ein Befehl ist (beginnt mit /)
        text = message.get('text', '')
        
        # Prüfe auf Live-Location-Nachrichten
        if 'location' in message:
            location = message.get('location', {})
            lat = location.get('latitude')
            lon = location.get('longitude')
            
            if lat is not None and lon is not None:
                from telegram_commands import handle_location
                await handle_location(self, chat_id, user_id, username, lat, lon)
            else:
                logger_newLog("warning", "handle_command", f"Ungültige Standortdaten von {username}")
            return
        
        # Prüfe ob es ein Befehl ist (beginnt mit /)
        if text.startswith('/'):
            command = text.split(' ', 1)[0]  # Erste Teil ist der Befehl
            
            # Erlaube /start auch für nicht registrierte User
            if command == '/start':
                from telegram_commands import cmd_start
                await cmd_start(self, chat_id, user_id, username)
                return
        
        # Blockiere alle anderen Nachrichten für nicht registrierte User
        if not existing_user:
            welcome_message = "🎮 Willkommen beim ChaseBot!\n\n"
            welcome_message += "Du bist ein Telegram-Bot für Live-Action-Spiele im Stil von 'Capture the Flag'.\n\n"
            welcome_message += "Spielprinzip:\n"
            welcome_message += "🏃 Runner versuchen, ein Ziel zu erreichen\n"
            welcome_message += "🦊 Hunter versuchen, die Runner zu fangen\n"
            welcome_message += "🎮 Gamemaster leitet das Spiel\n\n"
            welcome_message += "Um loszulegen:\n"
            welcome_message += "1. Registriere dich mit /start\n"
            welcome_message += "2. Tritt einem Spiel bei oder erstelle ein neues\n"
            welcome_message += "3. Teile deinen Live-Standort\n"
            welcome_message += "4. Das Spiel beginnt!"
            
            keyboard = {
                "keyboard": [
                    ["/start"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
            
            await self.send_message(chat_id, welcome_message, reply_markup=keyboard)
            return
        
        # Normale Befehlsverarbeitung für registrierte User
        if text.startswith('/'):
            # Befehl verarbeiten
            parts = text.split(' ', 1)  # Teile bei erstem Leerzeichen
            command = parts[0]
            command_text = parts[1] if len(parts) > 1 else ""
            
            if command == '/start':
                from telegram_commands import cmd_start
                await cmd_start(self, chat_id, user_id, username)
            elif command == '/new':
                from telegram_commands import cmd_new
                await cmd_new(self, chat_id, user_id, username, command_text)
            elif command == '/join':
                from telegram_commands import cmd_join
                await cmd_join(self, chat_id, user_id, username, command_text)
            elif command == '/fieldsetup':
                from telegram_commands import cmd_fieldsetup
                await cmd_fieldsetup(self, chat_id, user_id, username, command_text)
            elif command == '/leave':
                from telegram_commands import cmd_leave
                await cmd_leave(self, chat_id, user_id, username, command_text)
            elif command == '/map':
                from telegram_commands import cmd_map
                await cmd_map(self, chat_id, user_id, username, command_text)
            elif command == '/mapedit':
                from telegram_commands import cmd_mapedit
                await cmd_mapedit(self, chat_id, user_id, username, command_text)
            elif command == '/listusers':
                from telegram_commands import cmd_listusers
                await cmd_listusers(self, chat_id, user_id, username, command_text)
                return
            elif command == '/role':
                from telegram_commands import cmd_role
                await cmd_role(self, chat_id, user_id, username, command_text)
                return
            elif command == '/team':
                from telegram_commands import cmd_team
                await cmd_team(self, chat_id, user_id, username, command_text)
                return
            elif command == '/shop':
                from telegram_commands import cmd_shop
                await cmd_shop(self, chat_id, user_id, username, command_text)
                return
            elif command == '/buy':
                from telegram_commands import cmd_buy
                await cmd_buy(self, chat_id, user_id, username, command_text)
                return
            elif command == '/status':
                from telegram_commands import cmd_status
                await cmd_status(self, chat_id, user_id, username, command_text)
                return
            elif command == '/endgame':
                from telegram_commands import cmd_endgame
                await cmd_endgame(self, chat_id, user_id, username, command_text)
                return
            elif command == '/startgame':
                from telegram_commands import cmd_startgame
                await cmd_startgame(self, chat_id, user_id, username, command_text)
            elif command == '/listgames':
                from telegram_commands import cmd_listgames
                await cmd_listgames(self, chat_id)
                return
            elif command == '/help':
                from telegram_helpmessage import send_helpmessage
                await send_helpmessage(self, user_id, chat_id)
                return
            elif command == '/keyboard':
                from telegram_commands import cmd_keyboard
                await cmd_keyboard(self, chat_id, user_id, username, command_text)
                return
            elif command == '/coins':
                from telegram_commands import cmd_coins
                await cmd_coins(self, chat_id, user_id, username, command_text)
                return
            else:
                # Unbekannter Befehl
                from telegram_commands import cmd_unknown
                await cmd_unknown(self, chat_id, user_id, username, text)
        else:
            # Normaler Text
            from telegram_commands import handle_text
            await handle_text(self, chat_id, user_id, username, text)
    
    async def send_message(self, chat_id, text, reply_markup=None):
        """Sendet eine Nachricht"""
        try:
            url = f"{self.base_url}/sendMessage"
            data = {'chat_id': chat_id, 'text': text}
            
            if reply_markup:
                data['reply_markup'] = reply_markup
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data) as response:
                    if response.status == 200:
                        logger_newLog("debug", "send_message", f"Nachricht gesendet an {chat_id}")
                    else:
                        logger_newLog("error", "send_message", f"Fehler beim Senden: {response.status}")
        except Exception as e:
            logger_newLog("error", "send_message", f"Fehler beim Senden der Nachricht: {str(e)}")
    
    async def send_photo(self, chat_id, photo_file, caption=""):
        """Sendet ein Foto"""
        try:
            url = f"{self.base_url}/sendPhoto"
            
            data = aiohttp.FormData()
            data.add_field('chat_id', str(chat_id))
            data.add_field('photo', photo_file, filename='map.png', content_type='image/png')
            if caption:
                data.add_field('caption', caption)
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger_newLog("debug", "send_photo", f"Foto gesendet an {chat_id}")
                    else:
                        logger_newLog("error", "send_photo", f"Fehler beim Senden des Fotos: {response.status}")
        except Exception as e:
            logger_newLog("error", "send_photo", f"Fehler beim Senden des Fotos: {str(e)}")
    
    async def send_document(self, chat_id, document_file, caption=""):
        """Sendet ein Dokument (z.B. HTML-Datei)"""
        try:
            url = f"{self.base_url}/sendDocument"
            data = aiohttp.FormData()
            data.add_field('chat_id', str(chat_id))
            data.add_field('document', document_file, filename=getattr(document_file, 'name', 'file.html'), content_type='application/octet-stream')
            if caption:
                data.add_field('caption', caption)
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as response:
                    if response.status == 200:
                        logger_newLog("debug", "send_document", f"Dokument gesendet an {chat_id}")
                    else:
                        logger_newLog("error", "send_document", f"Fehler beim Senden des Dokuments: {response.status}")
        except Exception as e:
            logger_newLog("error", "send_document", f"Fehler beim Senden des Dokuments: {str(e)}")
    
    async def run(self):
        """Hauptschleife des Bots"""
        logger_newLog("info", "telegram_bot", "Telegram Bot gestartet")
        
        while True:
            try:
                updates = await self.get_updates()
                
                for update in updates:
                    self.offset = update.get('update_id', 0) + 1
                    
                    if 'message' in update:
                        await self.handle_command(update['message'])
                    elif 'edited_message' in update:
                        # Verarbeite Live-Location-Updates
                        await self.handle_command(update['edited_message'])
                
                await asyncio.sleep(1)  # Kurze Pause zwischen Polls
                
            except Exception as e:
                logger_newLog("error", "telegram_bot", f"Fehler in Bot-Schleife: {str(e)}")
                await asyncio.sleep(5)  # Längere Pause bei Fehler 