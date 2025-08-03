import asyncio
import json
import os
from datetime import datetime, timedelta
from pytz import timezone
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import BOT_TOKEN

LOCALE_FOLDER = "locale"
DATA_FOLDER = "data"
REMINDER_FILE = f"{DATA_FOLDER}/reminders.json"
DEFAULT_LANG = "he"

scheduler = AsyncIOScheduler()
scheduler.start()

user_languages = {}
reminders = {}

# Load language files
translations = {}
for lang_code in ["he", "en"]:
    with open(f"{LOCALE_FOLDER}/{lang_code}.json", encoding="utf-8") as f:
        translations[lang_code] = json.load(f)

def t(user_id, key):
    lang = user_languages.get(user_id, DEFAULT_LANG)
    return translations[lang].get(key, key)

def load_reminders():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_reminders():
    with open(REMINDER_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_languages[user_id] = DEFAULT_LANG
    await update.message.reply_text(t(user_id, "welcome"))

async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("עברית", callback_data="lang_he")],
        [InlineKeyboardButton("English", callback_data="lang_en")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Choose language / בחר שפה:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data.startswith("lang_"):
        lang_code = query.data.split("_")[1]
        user_languages[query.from_user.id] = lang_code
        await query.edit_message_text(text=t(query.from_user.id, "language_set"))

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)

    try:
        interval_minutes = int(context.args[0])
        text = " ".join(context.args[1:])
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add <minutes> <text>")
        return

    now = datetime.now(timezone("Asia/Jerusalem"))
    next_time = now + timedelta(minutes=interval_minutes)

    job_id = f"{user_id}_{int(next_time.timestamp())}"

    def send_reminder():
        context.bot.send_message(
            chat_id=user_id,
            text=f"⏰ {text}"
        )

    scheduler.add_job(send_reminder, trigger="date", run_date=next_time)
    reminders.setdefault(user_id, []).append({
        "text": text,
        "interval": interval_minutes,
        "next_time": next_time.isoformat()
    })
    save_reminders()

    await update.message.reply_text(f"{t(update.effective_user.id, 'reminder_set')} {interval_minutes} דקות")

def main():
    if not os.path.exists(DATA_FOLDER):
        os.makedirs(DATA_FOLDER)

    global reminders
    reminders = load_reminders()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("lang", set_lang))
    app.add_handler(CommandHandler("add", add_reminder))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
