import os
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler,
    filters, ContextTypes
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")

reminders = {}
user_states = {}
TEMP_DATA = {}

UNITS = {
    "דקה": "minutes",
    "שעה": "hours",
    "יום": "days",
    "שבוע": "weeks"
}

logging.basicConfig(level=logging.INFO)


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


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("➕ הוסף פעולה חדשה", callback_data="add_reminder")],
        [InlineKeyboardButton("📝 הזן שביצעת פעולה", callback_data="mark_done")],
        [InlineKeyboardButton("📋 הצג תזכורות קיימות", callback_data="show_reminders")],
        [InlineKeyboardButton("❌ מחק תזכורת", callback_data="delete_reminder")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("שלום! בחר פעולה מהתפריט:", reply_markup=reply_markup)


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    if query.data == "add_reminder":
        TEMP_DATA[user_id] = {}
        user_states[user_id] = "WAITING_NAME"
        await query.message.reply_text("הכנס שם לפעולה:")
    elif query.data == "mark_done":
        await handle_mark_done_menu(update, context)
    elif query.data == "show_reminders":
        await list_reminders(update, context)
    elif query.data == "delete_reminder":
        await handle_delete_menu(update, context)


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text

    state = user_states.get(user_id)
    temp = TEMP_DATA.get(user_id, {})

    if state == "WAITING_NAME":
        temp["name"] = text
        user_states[user_id] = "WAITING_TYPE"
        TEMP_DATA[user_id] = temp
        keyboard = [
            [InlineKeyboardButton("⏰ קבועה", callback_data="fixed")],
            [InlineKeyboardButton("🔁 מחזורית מתאפסת", callback_data="resetting")]
        ]
        await update.message.reply_text("בחר סוג תזכורת:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif state == "WAITING_UNIT":
        if text not in UNITS:
            await update.message.reply_text("יחידת זמן לא חוקית. בחר אחת: דקה, שעה, יום, שבוע.")
            return
        temp["unit"] = text
        user_states[user_id] = "WAITING_AMOUNT"
        await update.message.reply_text("הכנס מספר יחידות זמן (למשל: 3):")
    elif state == "WAITING_AMOUNT":
        if not text.isdigit():
            await update.message.reply_text("נא להזין מספר תקין.")
            return
        temp["amount"] = int(text)
        save_final_reminder(user_id, temp)
        await update.message.reply_text("התזכורת נשמרה בהצלחה!")
        user_states.pop(user_id, None)
        TEMP_DATA.pop(user_id, None)
    elif state == "WAITING_DONE_SELECTION":
        await update.message.reply_text("אנא בחר פעולה מתוך התפריט.")


def save_final_reminder(user_id, temp):
    now = datetime.now()
    if user_id not in reminders:
        reminders[user_id] = []

    reminder = {
        "name": temp["name"],
        "type": temp["type"],
        "unit": temp["unit"],
        "amount": temp["amount"],
        "last_time": now.isoformat()
    }
    reminders[user_id].append(reminder)
    save_reminders()


async def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    temp = TEMP_DATA.get(user_id, {})
    choice = query.data

    if choice == "fixed":
        temp["type"] = "fixed"
    elif choice == "resetting":
        temp["type"] = "resetting"
    else:
        await query.message.reply_text("בחירה לא חוקית.")
        return

    user_states[user_id] = "WAITING_UNIT"
    TEMP_DATA[user_id] = temp
    await query.message.reply_text("בחר יחידת זמן: דקה, שעה, יום, שבוע.")


async def handle_mark_done_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_reminders = reminders.get(user_id, [])

    buttons = []
    for i, r in enumerate(user_reminders):
        if r["type"] == "resetting":
            buttons.append([InlineKeyboardButton(r["name"], callback_data=f"done_{i}")])

    if not buttons:
        await query.message.reply_text("אין תזכורות מחזוריות לסימון.")
        return

    await query.message.reply_text("בחר תזכורת לביצוע:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    index = int(query.data.replace("done_", ""))
    reminders[user_id][index]["last_time"] = datetime.now().isoformat()
    save_reminders()
    await query.message.reply_text("עודכן! הזמן אופס בהצלחה.")


async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_reminders = reminders.get(user_id, [])

    if not user_reminders:
        await query.message.reply_text("אין תזכורות.")
        return

    msg = "📋 רשימת תזכורות:\n"
    for i, r in enumerate(user_reminders, 1):
        msg += f"{i}. {r['name']} ({'קבועה' if r['type']=='fixed' else 'מחזורית'}, כל {r['amount']} {r['unit']})\n"
    await query.message.reply_text(msg)


async def handle_delete_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    user_reminders = reminders.get(user_id, [])

    if not user_reminders:
        await query.message.reply_text("אין מה למחוק.")
        return

    buttons = []
    for i, r in enumerate(user_reminders):
        buttons.append([InlineKeyboardButton(r["name"], callback_data=f"delete_{i}")])

    await query.message.reply_text("בחר תזכורת למחיקה:", reply_markup=InlineKeyboardMarkup(buttons))


async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    index = int(query.data.replace("delete_", ""))
    name = reminders[user_id][index]["name"]
    del reminders[user_id][index]
    save_reminders()
    await query.message.reply_text(f"התזכורת '{name}' נמחקה.")


def main():
    load_reminders()

    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(add_reminder|mark_done|show_reminders|delete_reminder)$"))
    app.add_handler(CallbackQueryHandler(handle_type_selection, pattern="^(fixed|resetting)$"))
    app.add_handler(CallbackQueryHandler(handle_done_callback, pattern="^done_\\d+$"))
    app.add_handler(CallbackQueryHandler(handle_delete_callback, pattern="^delete_\\d+$"))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_text))
    app.run_polling()


if __name__ == "__main__":
    main()
