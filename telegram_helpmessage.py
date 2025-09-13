async def send_helpmessage(bot, user_id, chat_id):
    from database import db_User_get, db_Game_getField, db_Game_getDuration, db_Game_getStartTime
    from datetime import datetime, timedelta
    
    user = db_User_get(user_id)
    
    # Fall 1: User ist nicht in der Datenbank (nicht registriert)
    if not user:
        msg = "ChaseBot - Hilfe\n\nDu bist noch nicht registriert.\nBitte gib /start ein um dich zu registrieren."
        keyboard = {
            "keyboard": [
                ["/start"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    # Fall 2: User ist registriert aber nicht in einem Spiel
    game_id = user[8]
    if not game_id:
        msg = "ChaseBot - Hilfe\n\nDu bist registriert aber nicht in einem Spiel.\nVerfügbare Befehle:\n/new [Name]\n/join [GameID]\n/listgames\n/help"
        keyboard = {
            "keyboard": [
                ["/new", "/join"],
                ["/listgames", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    # Fall 3: User ist in einem Spiel
    game = db_Game_getField(game_id)
    if not game:
        msg = "Du bist im Spiel, aber die Spieldaten konnten nicht geladen werden.\nVerfügbare Befehle:\n/leave\n/help"
        keyboard = {
            "keyboard": [
                ["/leave", "/help"]
            ],
            "resize_keyboard": True,
            "one_time_keyboard": False
        }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    role = user[6]
    spielname = game[1]
    status = game[3]
    restzeit = None
    if status in ("headstart", "running"):
        duration = db_Game_getDuration(game_id)
        start_time_str = db_Game_getStartTime(game_id)
        if duration and start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                end_time = start_time + timedelta(minutes=duration)
                now = datetime.now()
                if end_time > now:
                    delta = end_time - now
                    mins = delta.seconds // 60
                    restzeit = f"{mins//60:02d}:{mins%60:02d}"
            except Exception:
                pass
    
    # Spiel läuft noch nicht
    if status == 'created':
        if not role or role == 'none':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDas Spiel hat noch nicht begonnen.\nDu hast noch keine Rolle zugewiesen bekommen. Bitte warte, bis der Gamemaster dir eine Rolle zuweist.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'runner':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDu bist Runner. Warte auf den Start durch den Gamemaster.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'hunter':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDu bist Hunter. Warte auf den Start durch den Gamemaster.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'gamemaster':
            msg = f"🎮 Gamemaster-Befehle\n\nDu bist Gamemaster von Spiel {game_id}.\nVerfügbare Befehle:\n/mapedit\n/listusers\n/role [user id] [role]\n/team [user id] [team]\n/startgame\n/help"
            keyboard = {
                "keyboard": [
                    ["/mapedit", "/listusers"],
                    ["/role", "/team"],
                    ["/startgame", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'spectator':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDu bist Zuschauer und kannst das Spiel beobachten.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    # Spiel läuft (headstart/running)
    if status in ('headstart', 'running'):
        status_text = f"Das Spiel läuft. Restzeit: {restzeit}" if restzeit else "Das Spiel läuft."
        
        if role == 'runner':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\n{status_text}\nDu bist auf der Flucht vor den Huntern!\nVerfügbare Befehle:\n/map\n/shop\n/buy [1-4]\n/help"
            keyboard = {
                "keyboard": [
                    ["/map"],
                    ["/shop", "/status", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'hunter':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\n{status_text}\nDu bist auf der Jagd nach den Runnern!\nVerfügbare Befehle:\n/map\n/shop\n/buy [1-4]\n/help"
            keyboard = {
                "keyboard": [
                    ["/map"],
                    ["/shop", "/status", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'gamemaster':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\n{status_text}\nDu bist Gamemaster. Du kannst das Spiel überwachen und ggf. beenden.\nVerfügbare Befehle:\n/status\n/map\n/coins <Team/User> <Betrag>\n/endgame\n/help"
            keyboard = {
                "keyboard": [
                    ["/status", "/map"],
                    ["/coins", "/endgame"],
                    ["/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'spectator':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\n{status_text}\nDu bist Zuschauer und kannst das Spiel beobachten.\nVerfügbare Befehle:\n/map\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/map", "/leave"],
                    ["/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    # Spiel ist beendet
    if status == 'ended':
        if role == 'runner' or role == 'hunter':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDas Spiel ist beendet.\nWarte auf die Auswertung durch den Gamemaster.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'gamemaster':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDas Spiel ist beendet.\nBitte führe die Auswertung und Siegerehrung durch.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        elif role == 'spectator':
            msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nDas Spiel ist beendet.\nDu bist Zuschauer und kannst das Spiel beobachten.\nVerfügbare Befehle:\n/leave\n/help"
            keyboard = {
                "keyboard": [
                    ["/leave", "/help"]
                ],
                "resize_keyboard": True,
                "one_time_keyboard": False
            }
        await bot.send_message(chat_id, msg, reply_markup=keyboard)
        return
    
    # Fallback
    msg = f"ChaseBot - Hilfe\nim Spiel: {spielname}\n\nUnbekannter Spielstatus.\nVerfügbare Befehle:\n/help"
    keyboard = {
        "keyboard": [
            ["/help"]
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }
    await bot.send_message(chat_id, msg, reply_markup=keyboard)