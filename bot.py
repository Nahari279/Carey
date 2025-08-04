import os
import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, MessageHandler, filters
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")

reminders = {}
user_states = {}

TIME_UNITS = {
    "דקה": 60,
    "שעה": 3600,
    "יום": 86400,
    "שבוע": 604800
}

def load_reminders():
    global reminders
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            reminders = json.load(f)
    else:
        reminders = {}

def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

def get_main_menu():
    keyboard = [
        [InlineKeyboardButton("➕ הוסף פעולה חדשה", callback_data="add_action")],
        [InlineKeyboardButton("📝 הזן שביצעת פעולה", callback_data="log_action")],
        [InlineKeyboardButton("📋 הצג תזכורות קיימות", callback_data="show_reminders")],
        [InlineKeyboardButton("❌ מחק תזכורת", callback_data="delete_reminder")]
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("שלום! אני הבוט BabyCareBot 👶", reply_markup=get_main_menu())

async def handle_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    data = query.data

    if data == "add_action":
        user_states[user_id] = {"step": "name"}
        await query.message.reply_text("הכנס שם לפעולה:")
    elif data == "log_action":
        actions = reminders.get(user_id, {}).keys()
        if not actions:
            await query.message.reply_text("אין פעולות זמינות להזנה.")
            return
        keyboard = [[InlineKeyboardButton(name, callback_data=f"log:{name}")] for name in actions]
        await query.message.reply_text("בחר את הפעולה שביצעת:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "show_reminders":
        msg = ""
        for action, info in reminders.get(user_id, {}).items():
            msg += f"🔔 {action} ({info['type']}) כל {info['every']} {info['unit']}\n"
        await query.message.reply_text(msg if msg else "אין תזכורות.")
    elif data == "delete_reminder":
        actions = reminders.get(user_id, {}).keys()
        if not actions:
            await query.message.reply_text("אין מה למחוק.")
            return
        keyboard = [[InlineKeyboardButton(name, callback_data=f"del:{name}")] for name in actions]
        await query.message.reply_text("בחר תזכורת למחיקה:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data.startswith("log:"):
        action = data.split(":")[1]
        reminders[user_id][action]["last"] = datetime.datetime.now().isoformat()
        save_reminders()
        await query.message.reply_text(f"הפעולה \"{action}\" הוזנה והזמן אופס.")
    elif data.startswith("del:"):
        action = data.split(":")[1]
        reminders[user_id].pop(action, None)
        save_reminders()
        await query.message.reply_text(f"התזכורת \"{action}\" נמחקה.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text.strip()

    if user_id not in user_states:
        await update.message.reply_text("בחר מהתפריט:", reply_markup=get_main_menu())
        return

    state = user_states[user_id]
    step = state.get("step")

    if step == "name":
        state["name"] = text
        state["step"] = "type"
        keyboard = [
            [InlineKeyboardButton("⏰ קבועה", callback_data="type:fixed")],
            [InlineKeyboardButton("🔁 מחזורית מתאפסת", callback_data="type:resetting")]
        ]
        await update.message.reply_text("בחר סוג תזכורת:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif step == "value":
        try:
            value = int(text)
            if value <= 0:
                raise ValueError()
            state["every"] = value
            data = reminders.setdefault(user_id, {})
            data[state["name"]] = {
                "type": state["type"],
                "unit": state["unit"],
                "every": state["every"],
                "last": datetime.datetime.now().isoformat()
            }
            save_reminders()
            user_states.pop(user_id)
            await update.message.reply_text("התזכורת נוספה!", reply_markup=get_main_menu())
        except ValueError:
            await update.message.reply_text("הזן מספר תקין.")

async def handle_inline_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    state = user_states.get(user_id, {})

    data = query.data

    if data.startswith("type:"):
        state["type"] = "קבועה" if data.endswith("fixed") else "מחזורית מתאפסת"
        state["step"] = "unit"
        keyboard = [[InlineKeyboardButton(u, callback_data=f"unit:{u}")] for u in TIME_UNITS]
        await query.message.reply_text("בחר יחידת זמן:", reply_markup=InlineKeyboardMarkup(keyboard))

    elif data.startswith("unit:"):
        unit = data.split(":")[1]
        state["unit"] = unit
        state["step"] = "value"
        await query.message.reply_text(f"הזן כל כמה {unit} התזכורת תחזור (מספר בלבד):")

def main():
    load_reminders()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_button))
    app.add_handler(CallbackQueryHandler(handle_inline_selection))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
