import asyncio
import json
import os
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# שלב 1: הטוקן
from config import BOT_TOKEN

# שלב 2: קובץ התזכורות
REMINDERS_FILE = "reminders.json"
reminders = {}
user_languages = {}
scheduler = AsyncIOScheduler()

# שלב 3: מילון תרגום
LANG = {
    "he": {
        "start": "ברוך הבא! אנא בחר שפה:",
        "language_selected": "השפה עודכנה לעברית 🇮🇱",
        "add_reminder": "הזן את שם התזכורת:",
        "reminder_added": "התזכורת נוספה!",
        "cancel": "ביטול",
        "reminder_due": "תזכורת: {text}\n\nסמן כבוצע?",
        "done": "בוצע ✔️",
        "noted_done": "סומן כבוצע.",
    },
    "en": {
        "start": "Welcome! Please select a language:",
        "language_selected": "Language set to English 🇬🇧",
        "add_reminder": "Enter reminder text:",
        "reminder_added": "Reminder added!",
        "cancel": "Cancel",
        "reminder_due": "Reminder: {text}\n\nMark as done?",
        "done": "Done ✔️",
        "noted_done": "Marked as done.",
    }
}

# שלב 4: טעינה ושמירה
def load_reminders():
    global reminders
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
            reminders = json.load(f)

def save_reminders():
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False)

# שלב 5: התחלה ובחירת שפה
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("עברית 🇮🇱", callback_data="lang_he")],
        [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en")]
    ]
    await update.message.reply_text("Welcome! Please select a language:",
                                    reply_markup=InlineKeyboardMarkup(buttons))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.split("_")[1]
    user_languages[query.from_user.id] = lang
    await query.edit_message_text(text=LANG[lang]["language_selected"])

# שלב 6: הוספת תזכורת
async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_languages.get(user_id, "en")
    context.user_data["adding_reminder"] = True
    await update.message.reply_text(LANG[lang]["add_reminder"])

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    lang = user_languages.get(user_id, "en")
    if context.user_data.get("adding_reminder"):
        text = update.message.text
        remind_at = datetime.now() + timedelta(minutes=1)
        reminders[str(user_id)] = {"text": text, "time": remind_at.isoformat()}
        save_reminders()
        scheduler.add_job(send_reminder, "date", run_date=remind_at, args=[user_id])
        context.user_data["adding_reminder"] = False
        await update.message.reply_text(LANG[lang]["reminder_added"])

# שלב 7: שליחת תזכורת
async def send_reminder(user_id):
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    lang = user_languages.get(user_id, "en")
    reminder = reminders.get(str(user_id))
    if reminder:
        await app.bot.send_message(
            chat_id=user_id,
            text=LANG[lang]["reminder_due"].format(text=reminder["text"]),
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton(LANG[lang]["done"], callback_data=f"done_{user_id}")
            ]])
        )

# שלב 8: סימון ביצוע
async def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = int(query.data.split("_")[1])
    lang = user_languages.get(user_id, "en")
    await query.answer()
    await query.edit_message_text(LANG[lang]["noted_done"])

# שלב 9: הפעלת הבוט
def main():
    load_reminders()
    scheduler.start()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_reminder))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(mark_done, pattern="^done_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
