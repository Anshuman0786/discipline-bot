import random
import schedule
import time
import os
import asyncio
from telegram import Bot

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=TOKEN)

messages = [
"I Love You",
"You Are My Sunshine",
]

async def send_msg():
    msg = random.choice(messages)
    await bot.send_message(chat_id=CHAT_ID, text=msg)

def job():
    asyncio.run(send_msg())

schedule.every(1).minutes.do(job)

while True:
    schedule.run_pending()
    time.sleep(60)