import os
import json
import datetime
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    CallbackQueryHandler, MessageHandler, ConversationHandler, filters
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")

reminders = {}
REMINDER_TYPES = ["⏰ קבועה", "🔁 מחזורית"]
TIME_UNITS = ["דקה", "שעה", "יום", "שבוע"]

CHOOSING_ACTION, ENTER_NAME, CHOOSE_TYPE, CHOOSE_UNIT, ENTER_VALUE, HANDLE_DONE, DELETE_SELECT = range(7)

# Load and save
def load_reminders():
    global reminders
    if os.path.exists(REMINDERS_FILE):
        with open(REMINDERS_FILE, "r") as f:
            reminders = json.load(f)
    else:
        reminders = {}

def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, ensure_ascii=False)

# Start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["➕ הוסף פעולה חדשה"],
        ["📝 הזן שביצעת פעולה"],
        ["📋 הצג תזכורות קיימות"],
        ["❌ מחק תזכורת"]
    ]
    await update.message.reply_text("שלום! בחר פעולה מהתפריט:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True))

# Handle main menu text
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ הוסף פעולה חדשה":
        await update.message.reply_text("הכנס שם לפעולה:")
        return ENTER_NAME
    elif text == "📝 הזן שביצעת פעולה":
        return await show_done_actions(update)
    elif text == "📋 הצג תזכורות קיימות":
        return await list_reminders(update, context)
    elif text == "❌ מחק תזכורת":
        return await show_delete_menu(update)
    else:
        await update.message.reply_text("בחר פעולה מהתפריט:")
        return CHOOSING_ACTION

# Step 1 - enter name
async def enter_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["name"] = update.message.text
    keyboard = [[btn] for btn in REMINDER_TYPES]
    await update.message.reply_text("בחר סוג תזכורת:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    return CHOOSE_TYPE

# Step 2 - choose type
async def choose_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["type"] = update.message.text
    keyboard = [[unit] for unit in TIME_UNITS]
    await update.message.reply_text("בחר יחידת זמן:", reply_markup=ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True))
    return CHOOSE_UNIT

# Step 3 - choose unit
async def choose_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["unit"] = update.message.text
    await update.message.reply_text("הכנס מספר יחידות זמן (למשל: 3):")
    return ENTER_VALUE

# Step 4 - enter value
async def enter_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = int(update.message.text)
        context.user_data["value"] = value
    except ValueError:
        await update.message.reply_text("הכנס מספר חוקי.")
        return ENTER_VALUE

    user_id = str(update.effective_user.id)
    if user_id not in reminders:
        reminders[user_id] = []

    reminder = {
        "name": context.user_data["name"],
        "type": context.user_data["type"],
        "unit": context.user_data["unit"],
        "value": context.user_data["value"],
        "last_done": None
    }
    reminders[user_id].append(reminder)
    save_reminders()
    await update.message.reply_text("✅ התזכורת נוספה!")
    return ConversationHandler.END

# Show reminders
async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await update.message.reply_text("אין תזכורות קיימות.")
        return CHOOSING_ACTION

    msg = "📋 התזכורות שלך:\n"
    for idx, r in enumerate(reminders[user_id], 1):
        msg += f"{idx}. {r['name']} – {r['type']} כל {r['value']} {r['unit']}\n"
    await update.message.reply_text(msg)
    return CHOOSING_ACTION

# Done actions
async def show_done_actions(update: Update):
    user_id = str(update.effective_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await update.message.reply_text("אין תזכורות לסמן.")
        return CHOOSING_ACTION

    buttons = []
    for i, r in enumerate(reminders[user_id]):
        if r["type"] == "🔁 מחזורית":
            buttons.append([InlineKeyboardButton(r["name"], callback_data=f"done:{i}")])

    if not buttons:
        await update.message.reply_text("אין תזכורות מחזוריות לסמן.")
        return CHOOSING_ACTION

    await update.message.reply_text("בחר פעולה שביצעת:", reply_markup=InlineKeyboardMarkup(buttons))
    return HANDLE_DONE

async def handle_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)

    index = int(query.data.split(":")[1])
    reminders[user_id][index]["last_done"] = datetime.datetime.now().isoformat()
    save_reminders()
    await query.edit_message_text("🎉 עודכן שביצעת את הפעולה!")
    return ConversationHandler.END

# Delete reminders
async def show_delete_menu(update: Update):
    user_id = str(update.effective_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await update.message.reply_text("אין תזכורות למחיקה.")
        return CHOOSING_ACTION

    keyboard = [[InlineKeyboardButton(r["name"], callback_data=f"delete:{i}")] for i, r in enumerate(reminders[user_id])]
    await update.message.reply_text("בחר תזכורת למחיקה:", reply_markup=InlineKeyboardMarkup(keyboard))
    return DELETE_SELECT

async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    index = int(query.data.split(":")[1])
    deleted = reminders[user_id].pop(index)
    save_reminders()
    await query.edit_message_text(f"🗑️ התזכורת '{deleted['name']}' נמחקה.")
    return ConversationHandler.END

# Main
def main():
    load_reminders()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)],
            ENTER_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_name)],
            CHOOSE_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_type)],
            CHOOSE_UNIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_unit)],
            ENTER_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_value)],
            HANDLE_DONE: [CallbackQueryHandler(handle_done_callback, pattern="^done:\\d+")],
            DELETE_SELECT: [CallbackQueryHandler(handle_delete_callback, pattern="^delete:\\d+")]
        },
        fallbacks=[CommandHandler("start", start)],
        allow_reentry=True
    )

    app.add_handler(conv)
    app.run_polling()

if __name__ == "__main__":
    main()
