import json
import logging
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (ApplicationBuilder, CallbackContext, CommandHandler,
                          CallbackQueryHandler, MessageHandler, filters, Application)

# --- Globals ---
DATA_FILE = "data/reminders.json"
BOT_TOKEN = os.getenv("BOT_TOKEN")
LANGUAGES = {"he": "עברית", "en": "English"}

# --- Logger ---
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Load reminders ---
def load_reminders() -> Dict:
    if not os.path.exists(DATA_FILE):
        return {"daily": [], "recurring": []}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        data.setdefault("daily", [])
        data.setdefault("recurring", [])
        return data

def save_reminders(data: Dict):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# --- Send Reminder ---
async def send_reminder(context: CallbackContext):
    job = context.job
    await context.bot.send_message(chat_id=job.chat_id, text=job.data)

# --- Commands ---
async def start(update: Update, context: CallbackContext):
    buttons = [
        [InlineKeyboardButton("הוסף תזכורת יומית", callback_data="add_daily")],
        [InlineKeyboardButton("הוסף תזכורת מחזורית", callback_data="add_recurring")],
        [InlineKeyboardButton("שנה שפה / Change Language", callback_data="change_lang")]
    ]
    await update.message.reply_text("בחר פעולה:", reply_markup=InlineKeyboardMarkup(buttons))

async def handle_buttons(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    data = query.data
    if data == "add_daily":
        context.user_data["mode"] = "daily"
        await query.message.reply_text("הכנס את הטקסט של התזכורת היומית:")
    elif data == "add_recurring":
        context.user_data["mode"] = "recurring"
        await query.message.reply_text("הכנס תזכורת מחזורית בפורמט: טקסט | ימים (3=כל 3 ימים):")
    elif data == "change_lang":
        buttons = [[InlineKeyboardButton(v, callback_data=f"set_lang_{k}")] for k, v in LANGUAGES.items()]
        await query.message.reply_text("Select language:", reply_markup=InlineKeyboardMarkup(buttons))
    elif data.startswith("set_lang_"):
        lang = data.split("_")[-1]
        context.user_data["lang"] = lang
        await query.message.reply_text(f"השפה עודכנה ל: {LANGUAGES[lang]}")

async def handle_message(update: Update, context: CallbackContext):
    text = update.message.text
    data = load_reminders()
    chat_id = update.effective_chat.id
    mode = context.user_data.get("mode")

    if mode == "daily":
        data["daily"].append({"chat_id": chat_id, "text": text})
        save_reminders(data)
        await update.message.reply_text("✅ נוספה תזכורת יומית")
    elif mode == "recurring":
        try:
            parts = text.split("|")
            rem_text = parts[0].strip()
            days = int(parts[1].strip())
            data["recurring"].append({"chat_id": chat_id, "text": rem_text, "interval": days, "last": datetime.utcnow().isoformat()})
            save_reminders(data)
            await update.message.reply_text("✅ נוספה תזכורת מחזורית")
        except:
            await update.message.reply_text("❌ פורמט שגוי. השתמש בפורמט: טקסט | ימים")

    context.user_data["mode"] = None

# --- Scheduler ---
def schedule_jobs(app: Application):
    scheduler = AsyncIOScheduler()
    data = load_reminders()
    for rem in data["daily"]:
        scheduler.add_job(app.bot.send_message, 'cron', hour=9, minute=0, kwargs={"chat_id": rem["chat_id"], "text": rem["text"]})
    for rem in data["recurring"]:
        last = datetime.fromisoformat(rem["last"])
        now = datetime.utcnow()
        days = rem["interval"]
        next_run = last + timedelta(days=days)
        if next_run <= now:
            app.create_task(app.bot.send_message(chat_id=rem["chat_id"], text=rem["text"]))
            rem["last"] = now.isoformat()
            save_reminders(data)
    scheduler.start()

# --- Main ---
async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_buttons))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    schedule_jobs(app)
    print("Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
