import telebot
import logging


class TelegramAlerter:
    def __init__(self, token: str, chat_id: str):
        self.bot = telebot.TeleBot(token)
        self.chat_id = chat_id

    def send_message(self, text: str):
        try:
            self.bot.send_message(self.chat_id, text, parse_mode="Markdown")
        except Exception as e:
            logging.error(f"Erro Telegram: {e}")
