import json
import os
import logging
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler

from config import BOT_TOKEN

# === הגדרות ===
LOCALE_FOLDER = "locale"
DATA_FOLDER = "data"
REMINDERS_FILE = f"{DATA_FOLDER}/reminders.json"
DEFAULT_LANGUAGE = "he"
TIMEZONE = timezone("Asia/Jerusalem")

# === יומן ===
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === טוען שפות ===
translations = {}
for lang_code in os.listdir(LOCALE_FOLDER):
    if lang_code.endswith(".json"):
        with open(f"{LOCALE_FOLDER}/{lang_code}", encoding="utf-8") as f:
            translations[lang_code.replace(".json", "")] = json.load(f)

def t(key: str, lang: str) -> str:
    return translations.get(lang, translations[DEFAULT_LANGUAGE]).get(key, key)

# === ניהול מידע למשתמשים ===
if not os.path.exists(REMINDERS_FILE):
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump({"user_data": {}, "reminders": []}, f)

with open(REMINDERS_FILE, encoding="utf-8") as f:
    state = json.load(f)

def save_state():
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

# === מתזמן ===
scheduler = AsyncIOScheduler(timezone=TIMEZONE)

async def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    user_id = job_data["user_id"]
    text = job_data["text"]
    lang = state["user_data"].get(str(user_id), {}).get("lang", DEFAULT_LANGUAGE)
    await context.bot.send_message(chat_id=user_id, text=f"{t('reminder', lang)}: {text}")

# === פקודות ===

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state["user_data"].setdefault(str(user_id), {"lang": DEFAULT_LANGUAGE})
    save_state()
    keyboard = [
        [InlineKeyboardButton("עברית", callback_data="lang_he")],
        [InlineKeyboardButton("English", callback_data="lang_en")]
    ]
    await update.message.reply_text(
        t("start", DEFAULT_LANGUAGE),
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    state["user_data"][str(user_id)]["lang"] = lang
    save_state()
    await query.edit_message_text(t("choose_language", lang))

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = state["user_data"].get(str(user_id), {}).get("lang", DEFAULT_LANGUAGE)

    try:
        # שימוש: /add 3h תזכורת
        duration, *message_parts = context.args
        message = " ".join(message_parts)
        delta = parse_duration(duration)
        due = datetime.now(TIMEZONE) + delta

        job = scheduler.add_job(
            send_reminder,
            trigger="interval",
            seconds=delta.total_seconds(),
            args=[],
            kwargs={},
            data={"user_id": user_id, "text": message}
        )

        state["reminders"].append({
            "user_id": user_id,
            "text": message,
            "interval_seconds": delta.total_seconds(),
            "lang": lang
        })
        save_state()

        await update.message.reply_text(f"{t('reminder_added', lang)} ({duration})")

    except Exception as e:
        logger.error(str(e))
        await update.message.reply_text(t("error_format", lang))

def parse_duration(duration_str: str) -> timedelta:
    if duration_str.endswith("h"):
        return timedelta(hours=int(duration_str[:-1]))
    elif duration_str.endswith("m"):
        return timedelta(minutes=int(duration_str[:-1]))
    elif duration_str.endswith("d"):
        return timedelta(days=int(duration_str[:-1]))
    else:
        raise ValueError("Invalid duration format")

# === הרצה ===

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CommandHandler("add", add_reminder))

    scheduler.start()
    app.run_polling()

if __name__ == "__main__":
    main()
