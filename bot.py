import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, filters
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")  # אל תשכח לשים ברנדר!

reminders = {}

# Load reminders from file
def load_reminders():
    global reminders
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            reminders = json.load(f)
    else:
        reminders = {}

# Save reminders to file
def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום! אני הבוט BabyCareBot 👶")

# Simple /add command
async def add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("הזן תזכורת כלשהי.")
        return

    if user_id not in reminders:
        reminders[user_id] = []

    reminders[user_id].append({"text": text})
    save_reminders()
    await update.message.reply_text("התזכורת נשמרה!")

# /list command
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await update.message.reply_text("אין תזכורות.")
        return

    msg = "📋 התזכורות שלך:\n"
    for idx, r in enumerate(reminders[user_id], 1):
        msg += f"{idx}. {r['text']}\n"
    await update.message.reply_text(msg)

# /clear command
async def clear(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    reminders[user_id] = []
    save_reminders()
    await update.message.reply_text("כל התזכורות נמחקו.")

# Main setup
def main():
    load_reminders()

    application = ApplicationBuilder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("clear", clear))

    application.run_polling()

if __name__ == "__main__":
    main()
