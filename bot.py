import os
import json
import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")

reminders = {}
user_languages = {}
SUPPORTED_LANGUAGES = ["en", "he"]

# Load and save
def load_data():
    global reminders, user_languages
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            data = json.load(f)
            reminders = data.get("reminders", {})
            user_languages = data.get("languages", {})
    else:
        reminders = {}
        user_languages = {}

def save_data():
    with open(REMINDERS_FILE, "w") as f:
        json.dump({"reminders": reminders, "languages": user_languages}, f)

# Translation
def t(user_id, key):
    he = {
        "start": "שלום! אני הבוט BabyCareBot 👶",
        "ask_reminder": "הזן תזכורת כלשהי.",
        "saved": "התזכורת נשמרה!",
        "none": "אין תזכורות.",
        "your_reminders": "📋 התזכורות שלך:",
        "cleared": "כל התזכורות נמחקו.",
        "menu": "בחר פעולה:",
        "add_daily": "➕ תזכורת יומית",
        "add_cycle": "🔁 תזכורת מחזורית",
        "change_lang": "🌐 שנה שפה",
        "done": "בוצע",
        "cancel": "❌ ביטול",
        "ask_text": "מה הטקסט של התזכורת?",
        "ask_hour": "באיזו שעה לשלוח (HH:MM)?",
        "ask_days": "כל כמה ימים לחזור (מספר)?",
        "language_set": "השפה עודכנה לעברית.",
    }

    en = {
        "start": "Hello! I'm BabyCareBot 👶",
        "ask_reminder": "Please enter a reminder.",
        "saved": "Reminder saved!",
        "none": "No reminders found.",
        "your_reminders": "📋 Your reminders:",
        "cleared": "All reminders cleared.",
        "menu": "Choose an action:",
        "add_daily": "➕ Daily Reminder",
        "add_cycle": "🔁 Cyclic Reminder",
        "change_lang": "🌐 Change Language",
        "done": "Done",
        "cancel": "❌ Cancel",
        "ask_text": "What is the reminder text?",
        "ask_hour": "What time to remind (HH:MM)?",
        "ask_days": "Repeat every how many days?",
        "language_set": "Language set to English.",
    }

    lang = user_languages.get(str(user_id), "he")
    return (en if lang == "en" else he).get(key, f"[{key}]")

# Start command
def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_languages[user_id] = "he"
    save_data()
    update.message.reply_text(t(user_id, "start"))

# /add command (simple one-off reminder)
def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = " ".join(context.args)
    if not text:
        update.message.reply_text(t(user_id, "ask_reminder"))
        return
    reminders.setdefault(user_id, []).append({
        "text": text,
        "type": "once"
    })
    save_data()
    update.message.reply_text(t(user_id, "saved"))

# /list command
def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if not reminders.get(user_id):
        update.message.reply_text(t(user_id, "none"))
        return
    msg = t(user_id, "your_reminders") + "\n"
    for idx, r in enumerate(reminders[user_id], 1):
        msg += f"{idx}. {r['text']}\n"
    update.message.reply_text(msg)

# /clear command
def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reminders[user_id] = []
    save_data()
    update.message.reply_text(t(user_id, "cleared"))

# /menu command
def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    buttons = [
        [InlineKeyboardButton(t(user_id, "add_daily"), callback_data="add_daily")],
        [InlineKeyboardButton(t(user_id, "add_cycle"), callback_data="add_cycle")],
        [InlineKeyboardButton(t(user_id, "change_lang"), callback_data="lang")]
    ]
    update.message.reply_text(t(user_id, "menu"), reply_markup=InlineKeyboardMarkup(buttons))

# Button handler
def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    query.answer()
    data = query.data

    if data == "add_daily":
        context.user_data["adding"] = "daily"
        context.bot.send_message(chat_id=query.message.chat_id, text=t(user_id, "ask_text"))
    elif data == "add_cycle":
        context.user_data["adding"] = "cycle"
        context.bot.send_message(chat_id=query.message.chat_id, text=t(user_id, "ask_text"))
    elif data == "lang":
        current = user_languages.get(user_id, "he")
        user_languages[user_id] = "en" if current == "he" else "he"
        save_data()
        context.bot.send_message(chat_id=query.message.chat_id, text=t(user_id, "language_set"))

# Handle reply for adding
def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    state = context.user_data.get("adding")

    if state == "daily":
        context.user_data["text"] = update.message.text
        context.user_data["adding"] = "daily_time"
        update.message.reply_text(t(user_id, "ask_hour"))
    elif state == "daily_time":
        context.user_data["time"] = update.message.text
        reminders.setdefault(user_id, []).append({
            "type": "daily",
            "text": context.user_data["text"],
            "time": context.user_data["time"]
        })
        context.user_data.clear()
        save_data()
        update.message.reply_text(t(user_id, "saved"))
    elif state == "cycle":
        context.user_data["text"] = update.message.text
        context.user_data["adding"] = "cycle_days"
        update.message.reply_text(t(user_id, "ask_days"))
    elif state == "cycle_days":
        context.user_data["days"] = update.message.text
        context.user_data["adding"] = "cycle_time"
        update.message.reply_text(t(user_id, "ask_hour"))
    elif state == "cycle_time":
        reminders.setdefault(user_id, []).append({
            "type": "cycle",
            "text": context.user_data["text"],
            "every_days": context.user_data["days"],
            "time": update.message.text
        })
        context.user_data.clear()
        save_data()
        update.message.reply_text(t(user_id, "saved"))

# Main
def main():
    load_data()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("clear", clear))
    application.add_handler(CommandHandler("menu", menu))
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
