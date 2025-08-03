import json
import os
import logging
from datetime import datetime, timedelta
from pytz import timezone
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler,
    ContextTypes, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# הגדרות בסיסיות
TIMEZONE = timezone("Asia/Jerusalem")
LANGUAGES = {"he": "עברית", "en": "English"}
REMINDERS_FILE = "reminders.json"
LOCALE_FOLDER = "locale"
DEFAULT_LANGUAGE = "he"

# טוקן מהסביבה (Render)
from config import BOT_TOKEN

# הגדרת לוגינג
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# זיכרון זמני
user_languages = {}
scheduler = AsyncIOScheduler()

# טעינת קבצי שפה
translations = {}
for lang_code in LANGUAGES:
    with open(f"{LOCALE_FOLDER}/{lang_code}.json", encoding="utf-8") as f:
        translations[lang_code] = json.load(f)

def t(user_id, key):
    lang = user_languages.get(user_id, DEFAULT_LANGUAGE)
    return translations.get(lang, translations[DEFAULT_LANGUAGE]).get(key, key)

# טעינת תזכורות מקובץ
def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, encoding="utf-8") as f:
        return json.load(f)

def save_reminders(reminders):
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

# שליחת תזכורת עם כפתור אישור
async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    text = job_data["text"]
    chat_ids = job_data["chat_ids"]

    for chat_id in chat_ids:
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(t(chat_id, "done_button"), callback_data=f"done|{text}")
        ]])
        await context.bot.send_message(chat_id=chat_id, text=text, reply_markup=keyboard)

# התחלת שיחה
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_languages[user.id] = DEFAULT_LANGUAGE
    await update.message.reply_text(t(user.id, "start_message"))

# תפריט בחירת שפה
async def language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    buttons = [
        [InlineKeyboardButton(name, callback_data=f"lang|{code}")]
        for code, name in LANGUAGES.items()
    ]
    await update.message.reply_text(t(user.id, "choose_language"),
                                    reply_markup=InlineKeyboardMarkup(buttons))

# שינוי שפה
async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    data = query.data

    if data.startswith("lang|"):
        lang = data.split("|")[1]
        user_languages[user_id] = lang
        await query.edit_message_text(t(user_id, "language_set"))
    elif data.startswith("done|"):
        task = data.split("|", 1)[1]
        await query.edit_message_text(t(user_id, "task_completed") + f": {task}")

# טיפול בטקסט חופשי כהוספת תזכורת
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # פרשנות מבנית פשוטה — ציפייה לקלט בסגנון:
    # [טקסט] | [מספר זמן] | [יחידה: דקות/שעות/ימים]
    if "|" not in text:
        await update.message.reply_text(t(user_id, "invalid_format"))
        return

    try:
        task_text, amount, unit = [s.strip() for s in text.split("|")]
        amount = int(amount)
    except Exception:
        await update.message.reply_text(t(user_id, "invalid_format"))
        return

    now = datetime.now(TIMEZONE)
    delay = {"minutes": "minutes", "hours": "hours", "days": "days"}.get(unit, "minutes")
    next_time = now + timedelta(**{delay: amount})

    job_data = {"text": task_text, "chat_ids": [user_id]}
    scheduler.add_job(send_reminder, "interval", **{delay: amount}, next_run_time=next_time, args=[context], kwargs={"job": None, "data": job_data})

    await update.message.reply_text(t(user_id, "reminder_set"))

# פונקציה ראשית
import asyncio

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    scheduler.configure(timezone=str(TIMEZONE))
    scheduler.start()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button))

    asyncio.run(app.run_polling())

if __name__ == "__main__":
    main()
