import os
from telegram import Bot
from datetime import datetime

class TelegramBot:
    def __init__(self, token, chat_id):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
    
    def send_alert(self, image_path="unauthorized.jpg"):
        try:
            with open(image_path, "rb") as photo:
                self.bot.send_photo(
                    chat_id=self.chat_id,
                    photo=photo,
                    caption=f"🚨 Unauthorized Access!\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            os.remove(image_path)  # Delete after sending
        except Exception as e:
            print(f"Telegram Error: {e}")