import os
import json
import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")
REMINDERS_FILE = "data/reminders.json"

reminders = {}
user_states = {}

TIME_UNITS = {
    "דקה": 60,
    "שעה": 3600,
    "יום": 86400,
    "שבוע": 604800,
}

def load_reminders():
    global reminders
    if not os.path.exists("data"):
        os.makedirs("data")
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as f:
                reminders = json.load(f)
        except json.JSONDecodeError:
            reminders = {}
    else:
        reminders = {}

def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

def build_main_menu():
    buttons = [
        [InlineKeyboardButton("➕ הוסף פעולה חדשה", callback_data="new_action")],
        [InlineKeyboardButton("📝 הזן שביצעת פעולה", callback_data="mark_done")],
        [InlineKeyboardButton("📋 הצג תזכורות קיימות", callback_data="list")],
        [InlineKeyboardButton("❌ מחק תזכורת", callback_data="delete")],
    ]
    return InlineKeyboardMarkup(buttons)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    user_states[user_id] = {}
    await update.message.reply_text("שלום! אני הבוט BabyCareBot 👶", reply_markup=build_main_menu())

# שלב ראשון: הוספת פעולה חדשה
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    state = user_states.setdefault(user_id, {})

    if query.data == "new_action":
        state["step"] = "awaiting_action_name"
        await query.message.reply_text("מה שם הפעולה שתרצה לעקוב אחריה?")
    elif query.data == "mark_done":
        await handle_mark_done(query, context)
    elif query.data == "list":
        await show_reminders_list(query, context)
    elif query.data == "delete":
        await handle_delete_request(query, context)

# שלב שני: קלט מהמשתמש
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    text = update.message.text
    state = user_states.setdefault(user_id, {})

    if state.get("step") == "awaiting_action_name":
        state["action_name"] = text
        state["step"] = "choose_type"
        keyboard = [
            [InlineKeyboardButton("⏰ קבועה", callback_data="fixed")],
            [InlineKeyboardButton("🔁 מחזורית מתאפסת", callback_data="cyclic")],
        ]
        await update.message.reply_text("בחר סוג תזכורת:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif state.get("step") == "awaiting_interval_value":
        if not text.isdigit():
            await update.message.reply_text("אנא הזן מספר בלבד.")
            return
        state["interval_value"] = int(text)
        await finalize_reminder(update, context, user_id)
    elif state.get("step") == "awaiting_done_selection":
        await update.message.reply_text("בחר פעולה מתוך התפריט כדי לסמן שבוצעה.")
    elif state.get("step") == "awaiting_delete_selection":
        await update.message.reply_text("בחר פעולה שברצונך למחוק מהתפריט.")

# בחירת סוג תזכורת
async def type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    state = user_states.setdefault(user_id, {})

    if query.data in ["fixed", "cyclic"]:
        state["type"] = query.data
        state["step"] = "choose_unit"
        keyboard = [[InlineKeyboardButton(unit, callback_data=f"unit_{unit}")] for unit in TIME_UNITS.keys()]
        await query.message.reply_text("בחר יחידת זמן:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif query.data.startswith("unit_"):
        unit = query.data.split("_")[1]
        state["unit"] = unit
        state["step"] = "awaiting_interval_value"
        await query.message.reply_text(f"הזן כל כמה {unit}(ות) תישלח תזכורת (מספר בלבד):")

# יצירת תזכורת חדשה
async def finalize_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id):
    state = user_states[user_id]
    action_name = state["action_name"]
    reminder_type = state["type"]
    unit = state["unit"]
    interval_value = state["interval_value"]
    interval_seconds = TIME_UNITS[unit] * interval_value

    reminder = {
        "name": action_name,
        "type": reminder_type,
        "interval_seconds": interval_seconds,
        "last_trigger": datetime.datetime.now().timestamp()
    }

    if user_id not in reminders:
        reminders[user_id] = []
    reminders[user_id].append(reminder)
    save_reminders()
    user_states[user_id] = {}
    await update.message.reply_text("התזכורת נוספה בהצלחה ✅", reply_markup=build_main_menu())

# סימון ביצוע פעולה
async def handle_mark_done(query, context):
    user_id = str(query.from_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await query.message.reply_text("אין תזכורות פעולות לסמן שבוצעו.")
        return

    user_states[user_id] = {"step": "awaiting_done_selection"}
    buttons = [
        [InlineKeyboardButton(r["name"], callback_data=f"done_{i}")]
        for i, r in enumerate(reminders[user_id]) if r["type"] == "cyclic"
    ]
    if buttons:
        await query.message.reply_text("בחר את הפעולה שביצעת:", reply_markup=InlineKeyboardMarkup(buttons))
    else:
        await query.message.reply_text("אין תזכורות מחזוריות מתאפסות.")

@CommandHandler
async def handle_done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    index = int(query.data.split("_")[1])
    reminders[user_id][index]["last_trigger"] = datetime.datetime.now().timestamp()
    save_reminders()
    await query.message.reply_text("הפעולה סומנה שבוצעה ✅")

# הצגת רשימת תזכורות
async def show_reminders_list(query, context):
    user_id = str(query.from_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await query.message.reply_text("אין תזכורות.")
        return

    msg = "📋 תזכורות:\n"
    for r in reminders[user_id]:
        t = "קבועה" if r["type"] == "fixed" else "מחזורית מתאפסת"
        msg += f"- {r['name']} ({t}) כל {r['interval_seconds']//60} דקות\n"
    await query.message.reply_text(msg)

# מחיקת תזכורת
async def handle_delete_request(query, context):
    user_id = str(query.from_user.id)
    if user_id not in reminders or not reminders[user_id]:
        await query.message.reply_text("אין תזכורות למחיקה.")
        return

    user_states[user_id] = {"step": "awaiting_delete_selection"}
    buttons = [
        [InlineKeyboardButton(r["name"], callback_data=f"del_{i}")]
        for i, r in enumerate(reminders[user_id])
    ]
    await query.message.reply_text("בחר תזכורת למחיקה:", reply_markup=InlineKeyboardMarkup(buttons))

@CommandHandler
async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = str(query.from_user.id)
    index = int(query.data.split("_")[1])
    removed = reminders[user_id].pop(index)
    save_reminders()
    await query.message.reply_text(f"התזכורת '{removed['name']}' נמחקה.")

def main():
    load_reminders()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(new_action|mark_done|list|delete)$"))
    app.add_handler(CallbackQueryHandler(type_selection, pattern="^(fixed|cyclic|unit_.*)$"))
    app.add_handler(CallbackQueryHandler(handle_done_callback, pattern="^done_"))
    app.add_handler(CallbackQueryHandler(handle_delete_callback, pattern="^del_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
