import os
import json
import time
import threading
from datetime import datetime, timedelta
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")
REMINDERS_FILE = "data/reminders.json"

reminders = {}
user_states = {}
temp_data = {}

# טען תזכורות מהקובץ
def load_reminders():
    global reminders
    try:
        if os.path.exists(REMINDERS_FILE):
            with open(REMINDERS_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    reminders = json.loads(content)
                else:
                    reminders = {}
        else:
            reminders = {}
    except:
        reminders = {}

# שמור תזכורות
def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

# הפעלת תזכורות
def reminder_loop():
    while True:
        now = time.time()
        for user_id in reminders:
            for reminder in reminders[user_id]:
                if reminder["type"] == "קבועה":
                    if now - reminder["last_sent"] >= reminder["interval"]:
                        send_reminder(int(user_id), reminder)
                        reminder["last_sent"] = now
                elif reminder["type"] == "מחזורית מתאפסת":
                    if now - reminder["last_done"] >= reminder["interval"]:
                        send_reminder(int(user_id), reminder)
        save_reminders()
        time.sleep(60)

# שליחת תזכורת
def send_reminder(user_id, reminder):
    try:
        app.bot.send_message(chat_id=user_id, text=f"🔔 הגיע הזמן לבצע: {reminder['title']}")
    except:
        pass

# התחלה
def start(update, context):
    user_id = str(update.effective_user.id)
    show_main_menu(update)

def show_main_menu(update):
    keyboard = [
        [KeyboardButton("➕ הוסף פעולה חדשה")],
        [KeyboardButton("📝 הזן שביצעת פעולה")],
        [KeyboardButton("📋 הצג תזכורות קיימות")],
        [KeyboardButton("❌ מחק תזכורת")]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("בחר פעולה מהתפריט:", reply_markup=reply_markup)

# הודעות טקסט
def handle_message(update, context):
    user_id = str(update.effective_user.id)
    text = update.message.text

    state = user_states.get(user_id)

    if state == "awaiting_title":
        temp_data[user_id]["title"] = text
        keyboard = [[
            InlineKeyboardButton("⏰ קבועה", callback_data="type_קבועה"),
            InlineKeyboardButton("🔁 מחזורית מתאפסת", callback_data="type_מחזורית מתאפסת")
        ]]
        update.message.reply_text("בחר סוג תזכורת:", reply_markup=InlineKeyboardMarkup(keyboard))
        user_states[user_id] = "awaiting_type"
        return

    if state == "awaiting_unit":
        temp_data[user_id]["unit"] = text
        update.message.reply_text("הכנס מספר יחידות זמן (למשל: 2):")
        user_states[user_id] = "awaiting_amount"
        return

    if state == "awaiting_amount":
        try:
            amount = int(text)
            unit = temp_data[user_id]["unit"]
            seconds = convert_to_seconds(unit, amount)
            if seconds is None:
                update.message.reply_text("יחידת זמן לא חוקית.")
                return
            reminder = {
                "title": temp_data[user_id]["title"],
                "type": temp_data[user_id]["type"],
                "interval": seconds,
                "last_sent": 0,
                "last_done": time.time()
            }
            if user_id not in reminders:
                reminders[user_id] = []
            reminders[user_id].append(reminder)
            save_reminders()
            update.message.reply_text("✅ התזכורת נשמרה!")
            user_states[user_id] = None
            temp_data[user_id] = {}
        except:
            update.message.reply_text("אנא הכנס מספר חוקי.")
        return

    if text == "➕ הוסף פעולה חדשה":
        user_states[user_id] = "awaiting_title"
        temp_data[user_id] = {}
        update.message.reply_text("הכנס את שם הפעולה:")
    elif text == "📝 הזן שביצעת פעולה":
        if user_id not in reminders or not reminders[user_id]:
            update.message.reply_text("אין פעולות להזין.")
            return
        buttons = [[InlineKeyboardButton(r["title"], callback_data=f"done_{i}")]
                   for i, r in enumerate(reminders[user_id])]
        update.message.reply_text("בחר פעולה שביצעת:", reply_markup=InlineKeyboardMarkup(buttons))
    elif text == "📋 הצג תזכורות קיימות":
        if user_id not in reminders or not reminders[user_id]:
            update.message.reply_text("אין תזכורות.")
            return
        msg = "📋 התזכורות שלך:\n"
        for i, r in enumerate(reminders[user_id], 1):
            msg += f"{i}. {r['title']} ({r['type']})\n"
        update.message.reply_text(msg)
    elif text == "❌ מחק תזכורת":
        if user_id not in reminders or not reminders[user_id]:
            update.message.reply_text("אין מה למחוק.")
            return
        buttons = [[InlineKeyboardButton(r["title"], callback_data=f"delete_{i}")]
                   for i, r in enumerate(reminders[user_id])]
        update.message.reply_text("בחר תזכורת למחיקה:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        update.message.reply_text("לא זוהתה פעולה. השתמש בתפריט.")

# המרה לשניות
def convert_to_seconds(unit, amount):
    if unit == "דקה":
        return amount * 60
    elif unit == "שעה":
        return amount * 3600
    elif unit == "יום":
        return amount * 86400
    elif unit == "שבוע":
        return amount * 604800
    else:
        return None

# לחיצה על כפתור
def handle_callback(update, context):
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    query.answer()

    if data.startswith("type_"):
        temp_data[user_id]["type"] = data.split("_")[1]
        keyboard = [[
            InlineKeyboardButton("דקה", callback_data="unit_דקה"),
            InlineKeyboardButton("שעה", callback_data="unit_שעה"),
            InlineKeyboardButton("יום", callback_data="unit_יום"),
            InlineKeyboardButton("שבוע", callback_data="unit_שבוע"),
        ]]
        query.edit_message_text("בחר יחידת זמן:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("unit_"):
        unit = data.split("_")[1]
        temp_data[user_id]["unit"] = unit
        query.edit_message_text(f"הכנס מספר יחידות של {unit}:")
        user_states[user_id] = "awaiting_amount"

    elif data.startswith("done_"):
        index = int(data.split("_")[1])
        if 0 <= index < len(reminders[user_id]):
            if reminders[user_id][index]["type"] == "מחזורית מתאפסת":
                reminders[user_id][index]["last_done"] = time.time()
                save_reminders()
                query.edit_message_text("👌 הפעולה נרשמה והתזכורת אופסה.")
            else:
                query.edit_message_text("⚠️ פעולה זו אינה מסוג מחזורית מתאפסת.")

    elif data.startswith("delete_"):
        index = int(data.split("_")[1])
        if 0 <= index < len(reminders[user_id]):
            title = reminders[user_id][index]["title"]
            del reminders[user_id][index]
            save_reminders()
            query.edit_message_text(f"❌ התזכורת '{title}' נמחקה.")

# הרצה
def main():
    load_reminders()
    threading.Thread(target=reminder_loop, daemon=True).start()

    global app
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.run_polling()

if __name__ == "__main__":
    main()
