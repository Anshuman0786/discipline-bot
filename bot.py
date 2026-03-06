import random
import asyncio
import os
import json
import sqlite3
from datetime import datetime, date, timedelta
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ── Config ──────────────────────────────────────────────────────────────────
TOKEN   = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

DB_FILE = "accountability.db"

# ── Database Setup ───────────────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            date        TEXT NOT NULL,
            type        TEXT NOT NULL,   -- 'exercise' | 'coding'
            did_it      INTEGER,         -- 1=yes, 0=no, NULL=no response
            response    TEXT,
            logged_at   TEXT
        )
    """)
    conn.commit()
    conn.close()

def log_action(log_type: str, did_it: int | None, response: str = ""):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    today = date.today().isoformat()
    c.execute("""
        INSERT OR REPLACE INTO logs (date, type, did_it, response, logged_at)
        VALUES (?, ?, ?, ?, ?)
    """, (today, log_type, did_it, response, datetime.now().isoformat()))
    conn.commit()
    conn.close()

def get_today_log(log_type: str):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT did_it FROM logs WHERE date=? AND type=?",
              (date.today().isoformat(), log_type))
    row = c.fetchone()
    conn.close()
    return row[0] if row else None

# ── Conversation state (in-memory) ──────────────────────────────────────────
# waiting_for: None | 'exercise_check' | 'coding_check'
state = {"waiting_for": None}

# ── Message Banks ────────────────────────────────────────────────────────────
EXERCISE_REMINDER = [
    "🏋️ It's 6 AM! Time to move that body. Do 20 pushups, a quick run — anything. NO EXCUSES.",
    "⏰ Rise & grind! Your 6 AM exercise reminder is here. Get off that bed and MOVE.",
    "💪 6 AM check-in! Your body is a temple — go treat it like one. Exercise NOW.",
]

EXERCISE_FOLLOWUP = [
    "👀 Hey! Did you exercise this morning? Reply YES or NO — no lying to yourself.",
    "🤔 It's 7 AM. Confession time: did you actually exercise? YES or NO?",
    "⏰ Morning accountability check! Exercise — YES or NO? Be honest.",
]

EXERCISE_PRAISE = [
    "🔥 LET'S GOOO! You exercised! That's how champions are built. Keep it up!",
    "💪 BEAST MODE ACTIVATED! You showed up for yourself today. Proud of you!",
    "🏆 YES! That's what I'm talking about! Consistency is your superpower. Amazing work!",
]

EXERCISE_ROAST = [
    "😤 Seriously?! You skipped exercise AGAIN? Your future self is deeply disappointed. Get it together tomorrow!",
    "🛋️ Another day of being a couch potato? Your muscles are literally crying right now. Do better!",
    "💀 No exercise? Wow. Just... wow. Even your grandma probably did more today. Step it UP.",
    "🙄 'No' again? The gym called — it misses you. Your excuses are getting old. Show up TOMORROW.",
]

CODING_REMINDER = [
    "💻 9 AM! Time to open that editor and WRITE SOME CODE. No YouTube, no Twitter — just code.",
    "⌨️ Coding time! It's 9 AM. Build something today. Your side project won't finish itself.",
    "🚀 9 AM reminder: every great developer codes every single day. Are you one of them? PROVE IT.",
]

CODING_FOLLOWUP = [
    "🧐 11 AM check-in! Did you code today? YES or NO — the truth will set you free.",
    "💻 Time's up! Did you write any code today? Reply YES or NO.",
    "🤖 Accountability bot here. Coding check: YES or NO? Don't make me roast you.",
]

CODING_PRAISE = [
    "🚀 You CODED today! That's how skills are built — one day at a time. Keep shipping!",
    "💻 YES! Another day of being a coding warrior! Your future self thanks you. Incredible!",
    "⭐ You showed up and you coded! That's 1% better than yesterday. Stack those wins!",
]

CODING_ROAST = [
    "😱 You didn't code?! Your GitHub is literally a desert. Tumbleweeds everywhere. OPEN THE EDITOR.",
    "🤦 No coding today? That dream project is still a dream because of days like this. Wake up!",
    "💀 0 lines of code today. Absolutely tragic. Your competitors coded today. Sleep on that.",
    "🙄 'No code' again? Every excuse you make, a developer somewhere just shipped a feature. Think about it.",
]

# ── Scheduled Jobs ───────────────────────────────────────────────────────────
async def job_6am(context: ContextTypes.DEFAULT_TYPE):
    """6:00 AM — Exercise reminder"""
    msg = random.choice(EXERCISE_REMINDER)
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)

async def job_7am(context: ContextTypes.DEFAULT_TYPE):
    """7:00 AM — Check if user exercised"""
    state["waiting_for"] = "exercise_check"
    msg = random.choice(EXERCISE_FOLLOWUP)
    await context.bot.send_message(chat_id=CHAT_ID,
        text=msg + "\n\nReply with *YES* or *NO*", parse_mode="Markdown")

async def job_9am(context: ContextTypes.DEFAULT_TYPE):
    """9:00 AM — Coding reminder"""
    msg = random.choice(CODING_REMINDER)
    await context.bot.send_message(chat_id=CHAT_ID, text=msg)

async def job_11am(context: ContextTypes.DEFAULT_TYPE):
    """11:00 AM — Check if user coded"""
    state["waiting_for"] = "coding_check"
    msg = random.choice(CODING_FOLLOWUP)
    await context.bot.send_message(chat_id=CHAT_ID,
        text=msg + "\n\nReply with *YES* or *NO*", parse_mode="Markdown")

# ── Message Handler ──────────────────────────────────────────────────────────
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return

    text = update.message.text.strip().upper()
    waiting = state.get("waiting_for")

    if waiting == "exercise_check":
        state["waiting_for"] = None
        if text in ("YES", "Y"):
            log_action("exercise", 1, text)
            await update.message.reply_text(random.choice(EXERCISE_PRAISE))
        elif text in ("NO", "N"):
            log_action("exercise", 0, text)
            await update.message.reply_text(random.choice(EXERCISE_ROAST))
        else:
            state["waiting_for"] = "exercise_check"
            await update.message.reply_text("Please reply with YES or NO only!")

    elif waiting == "coding_check":
        state["waiting_for"] = None
        if text in ("YES", "Y"):
            log_action("coding", 1, text)
            await update.message.reply_text(random.choice(CODING_PRAISE))
        elif text in ("NO", "N"):
            log_action("coding", 0, text)
            await update.message.reply_text(random.choice(CODING_ROAST))
        else:
            state["waiting_for"] = "coding_check"
            await update.message.reply_text("Please reply with YES or NO only!")

# ── Report Helpers ────────────────────────────────────────────────────────────
def build_report(days: int, label: str) -> str:
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    since = (date.today() - timedelta(days=days - 1)).isoformat()
    c.execute("SELECT date, type, did_it FROM logs WHERE date >= ? ORDER BY date", (since,))
    rows = c.fetchall()
    conn.close()

    if not rows:
        return f"📊 *{label} Report*\n\nNo data recorded yet!"

    # Group by date
    from collections import defaultdict
    by_date = defaultdict(dict)
    for d, t, v in rows:
        by_date[d][t] = v

    exercise_done = sum(1 for v in by_date.values() if v.get("exercise") == 1)
    coding_done   = sum(1 for v in by_date.values() if v.get("coding")   == 1)
    total_days    = len(by_date)

    def pct(n, t): return f"{round(n/t*100)}%" if t else "N/A"

    lines = [f"📊 *{label} Report* ({since} → {date.today().isoformat()})\n"]
    lines.append(f"📅 Days tracked: *{total_days}*")
    lines.append(f"🏋️ Exercise: *{exercise_done}/{total_days}* ({pct(exercise_done, total_days)})")
    lines.append(f"💻 Coding:   *{coding_done}/{total_days}* ({pct(coding_done, total_days)})\n")

    lines.append("📅 *Daily Breakdown:*")
    for d in sorted(by_date.keys()):
        ex  = {1: "✅", 0: "❌", None: "❓"}.get(by_date[d].get("exercise"))
        cod = {1: "✅", 0: "❌", None: "❓"}.get(by_date[d].get("coding"))
        lines.append(f"  {d}  🏋️{ex}  💻{cod}")

    # Motivational footer
    overall_pct = (exercise_done + coding_done) / (total_days * 2) * 100 if total_days else 0
    if overall_pct >= 80:
        lines.append("\n🔥 *Outstanding consistency! You're a machine!*")
    elif overall_pct >= 50:
        lines.append("\n💪 *Good effort, but there's room to improve. Push harder!*")
    else:
        lines.append("\n😤 *Your consistency needs serious work. No more excuses!*")

    return "\n".join(lines)

# ── Commands ──────────────────────────────────────────────────────────────────
async def cmd_report(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Today's progress"""
    if update.effective_chat.id != CHAT_ID:
        return
    ex  = get_today_log("exercise")
    cod = get_today_log("coding")
    ex_str  = {1: "✅ Done", 0: "❌ Skipped", None: "❓ No response yet"}.get(ex)
    cod_str = {1: "✅ Done", 0: "❌ Skipped", None: "❓ No response yet"}.get(cod)
    msg = f"📊 *Today's Report — {date.today().isoformat()}*\n\n🏋️ Exercise: {ex_str}\n💻 Coding: {cod_str}"
    await update.message.reply_text(msg, parse_mode="Markdown")

async def cmd_weekly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text(build_report(7, "Weekly"), parse_mode="Markdown")

async def cmd_monthly(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    await update.message.reply_text(build_report(30, "Monthly"), parse_mode="Markdown")

async def cmd_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """All-time stats"""
    if update.effective_chat.id != CHAT_ID:
        return
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT MIN(date) FROM logs")
    first = c.fetchone()[0]
    conn.close()
    if not first:
        await update.message.reply_text("No data yet!")
        return
    days = (date.today() - date.fromisoformat(first)).days + 1
    await update.message.reply_text(build_report(days, "All-Time Stats"), parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != CHAT_ID:
        return
    help_text = (
        "🤖 *Accountability Bot Commands*\n\n"
        "/report  — Today's exercise & coding status\n"
        "/weekly  — Last 7 days report\n"
        "/monthly — Last 30 days report\n"
        "/stats   — All-time statistics\n"
        "/help    — Show this menu\n\n"
        "⏰ *Daily Schedule (IST):*\n"
        "6:00 PM  — Exercise reminder\n"
        "7:00 PM  — Exercise check-in (reply YES/NO)\n"
        "9:00 PM  — Coding reminder\n"
        "11:00 PM — Coding check-in (reply YES/NO)"
    )
    await update.message.reply_text(help_text, parse_mode="Markdown")

# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    init_db()
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("report",  cmd_report))
    app.add_handler(CommandHandler("weekly",  cmd_weekly))
    app.add_handler(CommandHandler("monthly", cmd_monthly))
    app.add_handler(CommandHandler("stats",   cmd_stats))
    app.add_handler(CommandHandler("help",    cmd_help))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Scheduled jobs — times in UTC (IST = UTC+5:30)
    # 6:00 PM IST  = 12:30 UTC
    # 7:00 PM IST  = 13:30 UTC
    # 9:00 PM IST  = 15:30 UTC
    # 11:00 PM IST = 17:30 UTC
    jq = app.job_queue
    jq.run_daily(job_6am,  time=datetime.strptime("12:30", "%H:%M").time())
    jq.run_daily(job_7am,  time=datetime.strptime("13:30", "%H:%M").time())
    jq.run_daily(job_9am,  time=datetime.strptime("15:30", "%H:%M").time())
    jq.run_daily(job_11am, time=datetime.strptime("17:30", "%H:%M").time())

    print("🤖 Accountability Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()