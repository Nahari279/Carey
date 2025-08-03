import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from config import BOT_TOKEN
import json
from apscheduler.schedulers.background import BackgroundScheduler
from datetime import datetime, timedelta

# Load translations
def load_translations(lang):
    with open(f'locale/{lang}.json', encoding='utf-8') as f:
        return json.load(f)

user_lang = {}
reminders = {}

# Setup scheduler
scheduler = BackgroundScheduler()
scheduler.start()

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇮🇱 עברית", callback_data='lang_he')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
    ]
    await update.message.reply_text("בחר שפה / Choose language:", reply_markup=InlineKeyboardMarkup(keyboard))

async def change_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇮🇱 עברית", callback_data='lang_he')],
        [InlineKeyboardButton("🇬🇧 English", callback_data='lang_en')],
    ]
    await update.message.reply_text("בחר שפה חדשה:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = query.data.split("_")[1]
    user_lang[user_id] = lang
    translations = load_translations(lang)
    await query.edit_message_text(translations["language_set"])

async def add_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'en')
    translations = load_translations(lang)

    keyboard = [
        [InlineKeyboardButton(translations["fixed_reminder"], callback_data='reminder_fixed')],
        [InlineKeyboardButton(translations["dynamic_reminder"], callback_data='reminder_dynamic')],
    ]
    await update.message.reply_text(translations["select_reminder_type"], reply_markup=InlineKeyboardMarkup(keyboard))

async def cancel_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'en')
    translations = load_translations(lang)

    user_reminders = reminders.get(user_id, [])
    if not user_reminders:
        await update.message.reply_text("אין תזכורות לבטל.")
        return

    keyboard = [
        [InlineKeyboardButton(f"❌ {r['text']}", callback_data=f"cancel_{i}")]
        for i, r in enumerate(user_reminders)
    ]
    await update.message.reply_text("בחר תזכורת לביטול:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    lang = user_lang.get(user_id, 'en')
    translations = load_translations(lang)

    index = int(query.data.split("_")[1])
    if user_id in reminders and index < len(reminders[user_id]):
        reminder = reminders[user_id].pop(index)
        scheduler.remove_job(reminder["job_id"])
        await query.edit_message_text(translations["cancel_success"])

def send_reminder(context: ContextTypes.DEFAULT_TYPE):
    job_data = context.job.data
    context.bot.send_message(chat_id=job_data["chat_id"], text=f"{job_data['text']}")

async def handle_reminder_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    context.user_data["type"] = query.data
    await query.edit_message_text("שלח את טקסט התזכורת:")
    return

async def receive_reminder_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    context.user_data["text"] = text

    if context.user_data.get("type") == "reminder_fixed":
        await update.message.reply_text("באיזו שעה ביום לשלוח את התזכורת? (למשל 09:00)")
    else:
        await update.message.reply_text("כל כמה זמן מהביצוע לשלוח תזכורת? (למשל 3h או 2h30m)")

async def receive_reminder_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    lang = user_lang.get(user_id, 'en')
    translations = load_translations(lang)

    if context.user_data.get("type") == "reminder_fixed":
        hour_str = update.message.text
        hour = datetime.strptime(hour_str, "%H:%M").time()
        now = datetime.now()
        first_run = datetime.combine(now.date(), hour)
        if first_run < now:
            first_run += timedelta(days=1)
        job_id = f"{user_id}_{len(reminders.get(user_id, []))}"

        scheduler.add_job(
            send_reminder, "interval", days=1, start_date=first_run,
            args=[context], id=job_id, replace_existing=True,
            kwargs={"context": context, "job": None},
            data={"chat_id": update.effective_chat.id, "text": context.user_data["text"]}
        )

        reminders.setdefault(user_id, []).append({
            "text": context.user_data["text"],
            "type": "fixed",
            "job_id": job_id
        })
        await update.message.reply_text(translations["reminder_set"])
    else:
        await update.message.reply_text("⏱️ פונקציית תזכורת לפי ביצוע תתווסף בקרוב (שלב 2).")

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_reminder", add_reminder))
    app.add_handler(CommandHandler("cancel_menu", cancel_menu))
    app.add_handler(CommandHandler("change_language", change_language))

    app.add_handler(CallbackQueryHandler(handle_language, pattern="^lang_"))
    app.add_handler(CallbackQueryHandler(handle_cancel, pattern="^cancel_"))
    app.add_handler(CallbackQueryHandler(handle_reminder_type, pattern="^reminder_"))

    app.add_handler(CommandHandler("list_reminders", cancel_menu))
    app.add_handler(CommandHandler("cancel", cancel_menu))

    app.add_handler(CommandHandler("help", start))
    app.add_handler(CommandHandler("language", change_language))

    app.add_handler(CommandHandler("set", receive_reminder_time))
    app.add_handler(CommandHandler("text", receive_reminder_text))

    app.run_polling()

if __name__ == "__main__":
    main()
