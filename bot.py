import random
import schedule
import time
from telegram import Bot

TOKEN = "YOUR_BOT_TOKEN"
CHAT_ID = "YOUR_CHAT_ID"

bot = Bot(token=TOKEN)

messages = [
"Did you code today?",
"Stop scrolling and start coding.",
"Time for exercise. Do 20 pushups.",
"Consistency builds champions."
]

def send_msg():
    msg = random.choice(messages)
    bot.send_message(chat_id=CHAT_ID, text=msg)

schedule.every().day.at("18:00").do(send_msg)

while True:
    schedule.run_pending()
    time.sleep(60)