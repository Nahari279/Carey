import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler

DATA_FILE = "data/reminders.json"
reminder_data = {}

# Ensure data directory exists
if not os.path.exists("data"):
    os.makedirs("data")

# Create empty reminders file if it doesn't exist
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        f.write("{}")

# Load reminders safely
def load_reminders():
    global reminder_data
    try:
        with open(DATA_FILE, "r") as f:
            content = f.read().strip()
            reminder_data = json.loads(content) if content else {}
    except (json.JSONDecodeError, FileNotFoundError):
        reminder_data = {}

def save_reminders():
    with open(DATA_FILE, "w") as f:
        json.dump(reminder_data, f, ensure_ascii=False, indent=2)

def start(update: Update, context: CallbackContext):
    show_main_menu(update)

def show_main_menu(update: Update):
    keyboard = [
        [KeyboardButton("➕ הוסף פעולה חדשה")],
        [KeyboardButton("📝 הזן שביצעת פעולה")],
        [KeyboardButton("📋 הצג תזכורות קיימות")],
        [KeyboardButton("❌ מחק תזכורת")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("בחר פעולה מהתפריט:", reply_markup=reply_markup)

def handle_text(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "➕ הוסף פעולה חדשה":
        return add_reminder_start(update, context)
    elif text == "📝 הזן שביצעת פעולה":
        return log_action(update, context)
    elif text == "📋 הצג תזכורות קיימות":
        return show_reminders(update, context)
    elif text == "❌ מחק תזכורת":
        return delete_reminder_start(update, context)
    else:
        update.message.reply_text("בחר פעולה מהתפריט.")
        return ConversationHandler.END

# === הוספת תזכורת חדשה ===
ADD_NAME, ADD_TYPE, ADD_UNIT, ADD_AMOUNT = range(4)

def add_reminder_start(update: Update, context: CallbackContext):
    update.message.reply_text("הכנס שם פעולה:")
    return ADD_NAME

def add_reminder_name(update: Update, context: CallbackContext):
    context.user_data["name"] = update.message.text
    keyboard = [[KeyboardButton("⏰ קבועה")], [KeyboardButton("🔁 מחזורית מתאפסת")]]
    update.message.reply_text("בחר סוג תזכורת:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ADD_TYPE

def add_reminder_type(update: Update, context: CallbackContext):
    context.user_data["type"] = update.message.text
    keyboard = [[KeyboardButton("דקה")], [KeyboardButton("שעה")], [KeyboardButton("יום")], [KeyboardButton("שבוע")]]
    update.message.reply_text("בחר יחידת זמן:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return ADD_UNIT

def add_reminder_unit(update: Update, context: CallbackContext):
    context.user_data["unit"] = update.message.text
    update.message.reply_text("הכנס מספר יחידות זמן (למשל: 3):")
    return ADD_AMOUNT

def add_reminder_amount(update: Update, context: CallbackContext):
    try:
        amount = int(update.message.text)
        chat_id = str(update.message.chat_id)
        name = context.user_data["name"]
        reminder = {
            "type": context.user_data["type"],
            "unit": context.user_data["unit"],
            "amount": amount,
            "last_done": datetime.now().isoformat() if "מחזורית" in context.user_data["type"] else None
        }
        if chat_id not in reminder_data:
            reminder_data[chat_id] = {}
        reminder_data[chat_id][name] = reminder
        save_reminders()
        update.message.reply_text("התזכורת נוספה בהצלחה.")
    except:
        update.message.reply_text("שגיאה. ודא שהזנת מספר תקין.")
    show_main_menu(update)
    return ConversationHandler.END

# === רישום ביצוע פעולה ===
def log_action(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    if chat_id not in reminder_data or not reminder_data[chat_id]:
        update.message.reply_text("אין תזכורות.")
        return ConversationHandler.END
    keyboard = [[KeyboardButton(name)] for name in reminder_data[chat_id]]
    update.message.reply_text("בחר פעולה שביצעת:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return 100  # Arbitrary state

def mark_done(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    name = update.message.text
    if chat_id in reminder_data and name in reminder_data[chat_id]:
        if "מחזורית" in reminder_data[chat_id][name]["type"]:
            reminder_data[chat_id][name]["last_done"] = datetime.now().isoformat()
            save_reminders()
            update.message.reply_text("הפעולה סומנה כהושלמה.")
        else:
            update.message.reply_text("תזכורת זו אינה מחזורית מתאפסת.")
    else:
        update.message.reply_text("תזכורת לא נמצאה.")
    show_main_menu(update)
    return ConversationHandler.END

# === הצגת תזכורות ===
def show_reminders(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    if chat_id not in reminder_data or not reminder_data[chat_id]:
        update.message.reply_text("אין תזכורות.")
        return
    messages = []
    for name, info in reminder_data[chat_id].items():
        msg = f"🔔 {name} - {info['type']}, כל {info['amount']} {info['unit']}"
        if info.get("last_done"):
            msg += f"\nבוצע לאחרונה: {info['last_done']}"
        messages.append(msg)
    update.message.reply_text("\n\n".join(messages))

# === מחיקת תזכורת ===
def delete_reminder_start(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    if chat_id not in reminder_data or not reminder_data[chat_id]:
        update.message.reply_text("אין תזכורות למחיקה.")
        return ConversationHandler.END
    keyboard = [[KeyboardButton(name)] for name in reminder_data[chat_id]]
    update.message.reply_text("בחר תזכורת למחיקה:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))
    return 200  # Arbitrary state

def delete_reminder_confirm(update: Update, context: CallbackContext):
    chat_id = str(update.message.chat_id)
    name = update.message.text
    if name in reminder_data.get(chat_id, {}):
        del reminder_data[chat_id][name]
        save_reminders()
        update.message.reply_text("התזכורת נמחקה.")
    else:
        update.message.reply_text("תזכורת לא נמצאה.")
    show_main_menu(update)
    return ConversationHandler.END

# === הגדרת הבוט ===
def main():
    load_reminders()
    TOKEN = os.environ.get("BOT_TOKEN")
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(Filters.text & ~Filters.command, handle_text)],
        states={
            ADD_NAME: [MessageHandler(Filters.text & ~Filters.command, add_reminder_name)],
            ADD_TYPE: [MessageHandler(Filters.text & ~Filters.command, add_reminder_type)],
            ADD_UNIT: [MessageHandler(Filters.text & ~Filters.command, add_reminder_unit)],
            ADD_AMOUNT: [MessageHandler(Filters.text & ~Filters.command, add_reminder_amount)],
            100: [MessageHandler(Filters.text & ~Filters.command, mark_done)],
            200: [MessageHandler(Filters.text & ~Filters.command, delete_reminder_confirm)],
        },
        fallbacks=[]
    )

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(conv_handler)

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
