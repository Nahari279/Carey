import json
import os
import datetime
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters, ConversationHandler

DATA_FILE = "data/reminders.json"
if not os.path.exists("data"):
    os.makedirs("data")
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, "w") as f:
        json.dump({}, f)

CHOOSING_ACTION, TYPING_NAME, CHOOSING_TYPE, CHOOSING_UNIT, TYPING_INTERVAL = range(5)
ADDING_ACTION, MARKING_DONE, SHOWING_REMINDERS, DELETING_REMINDER = range(5, 9)

main_menu_keyboard = [
    ["➕ הוסף פעולה חדשה"],
    ["📝 הזן שביצעת פעולה"],
    ["📋 הצג תזכורות קיימות"],
    ["❌ מחק תזכורת"]
]
main_menu_markup = ReplyKeyboardMarkup(main_menu_keyboard, one_time_keyboard=False, resize_keyboard=True)

type_keyboard = [["⏰ קבועה", "🔁 מחזורית מתאפסת"]]
type_markup = ReplyKeyboardMarkup(type_keyboard, one_time_keyboard=True, resize_keyboard=True)

unit_keyboard = [["דקה", "שעה"], ["יום", "שבוע"]]
unit_markup = ReplyKeyboardMarkup(unit_keyboard, one_time_keyboard=True, resize_keyboard=True)

reminder_data = {}

def load_reminders():
    global reminder_data
    with open(DATA_FILE, "r") as f:
        reminder_data = json.load(f)

def save_reminders():
    with open(DATA_FILE, "w") as f:
        json.dump(reminder_data, f, ensure_ascii=False)

def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    update.message.reply_text("שלום! אני הבוט BabyCareBot 👶", reply_markup=main_menu_markup)
    return CHOOSING_ACTION

def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "➕ הוסף פעולה חדשה":
        update.message.reply_text("כתוב את שם הפעולה שברצונך להוסיף:")
        return TYPING_NAME
    elif text == "📝 הזן שביצעת פעולה":
        return handle_mark_action(update, context)
    elif text == "📋 הצג תזכורות קיימות":
        return show_reminders(update, context)
    elif text == "❌ מחק תזכורת":
        return delete_reminder(update, context)
    else:
        update.message.reply_text("אנא בחר פעולה מהתפריט.", reply_markup=main_menu_markup)
        return CHOOSING_ACTION

def receive_action_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["action_name"] = update.message.text
    update.message.reply_text("בחר את סוג התזכורת:", reply_markup=type_markup)
    return CHOOSING_TYPE

def receive_action_type(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["reminder_type"] = "fixed" if "קבועה" in update.message.text else "reset"
    update.message.reply_text("בחר את יחידת הזמן:", reply_markup=unit_markup)
    return CHOOSING_UNIT

def receive_time_unit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["unit"] = update.message.text
    update.message.reply_text("הכנס את מספר יחידות הזמן (למשל: 3):")
    return TYPING_INTERVAL

def receive_time_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        interval = int(update.message.text)
    except ValueError:
        update.message.reply_text("יש להזין מספר בלבד. נסה שוב:")
        return TYPING_INTERVAL

    user_id = str(update.message.from_user.id)
    name = context.user_data["action_name"]
    reminder_type = context.user_data["reminder_type"]
    unit = context.user_data["unit"]
    value = interval
    now = datetime.datetime.now().isoformat()

    if user_id not in reminder_data:
        reminder_data[user_id] = []

    reminder_data[user_id].append({
        "name": name,
        "type": reminder_type,
        "unit": unit,
        "interval": value,
        "last_done": now
    })

    save_reminders()

    update.message.reply_text("✅ הפעולה נוספה בהצלחה!", reply_markup=main_menu_markup)
    return CHOOSING_ACTION

def handle_mark_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in reminder_data or not reminder_data[user_id]:
        update.message.reply_text("אין פעולות להזין עבורן ביצוע.", reply_markup=main_menu_markup)
        return CHOOSING_ACTION

    buttons = [[r["name"]] for r in reminder_data[user_id] if r["type"] == "reset"]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("בחר את הפעולה שביצעת כעת:", reply_markup=markup)
    return MARKING_DONE

def mark_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    action_name = update.message.text
    found = False

    for r in reminder_data.get(user_id, []):
        if r["name"] == action_name and r["type"] == "reset":
            r["last_done"] = datetime.datetime.now().isoformat()
            found = True
            break

    if found:
        save_reminders()
        update.message.reply_text("⏱️ התזכורת אופסה!", reply_markup=main_menu_markup)
    else:
        update.message.reply_text("לא נמצאה פעולה כזו למחזורית מתאפסת.", reply_markup=main_menu_markup)

    return CHOOSING_ACTION

def show_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    reminders = reminder_data.get(user_id, [])

    if not reminders:
        update.message.reply_text("אין תזכורות קיימות.", reply_markup=main_menu_markup)
        return CHOOSING_ACTION

    msg = "📋 רשימת תזכורות:\n"
    for r in reminders:
        msg += f"🔹 {r['name']} – {'קבועה' if r['type']=='fixed' else 'מחזורית מתאפסת'}, כל {r['interval']} {r['unit']}\n"

    update.message.reply_text(msg, reply_markup=main_menu_markup)
    return CHOOSING_ACTION

def delete_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    if user_id not in reminder_data or not reminder_data[user_id]:
        update.message.reply_text("אין תזכורות למחיקה.", reply_markup=main_menu_markup)
        return CHOOSING_ACTION

    buttons = [[r["name"]] for r in reminder_data[user_id]]
    markup = ReplyKeyboardMarkup(buttons, one_time_keyboard=True, resize_keyboard=True)
    update.message.reply_text("בחר את התזכורת שברצונך למחוק:", reply_markup=markup)
    return DELETING_REMINDER

def confirm_delete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.message.from_user.id)
    name = update.message.text

    reminder_data[user_id] = [r for r in reminder_data[user_id] if r["name"] != name]
    save_reminders()

    update.message.reply_text("❌ התזכורת נמחקה.", reply_markup=main_menu_markup)
    return CHOOSING_ACTION

def main():
    load_reminders()
    app = ApplicationBuilder().token(os.environ["BOT_TOKEN"]).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            CHOOSING_ACTION: [MessageHandler(filters.TEXT, handle_menu)],
            TYPING_NAME: [MessageHandler(filters.TEXT, receive_action_name)],
            CHOOSING_TYPE: [MessageHandler(filters.TEXT, receive_action_type)],
            CHOOSING_UNIT: [MessageHandler(filters.TEXT, receive_time_unit)],
            TYPING_INTERVAL: [MessageHandler(filters.TEXT, receive_time_interval)],
            MARKING_DONE: [MessageHandler(filters.TEXT, mark_done)],
            DELETING_REMINDER: [MessageHandler(filters.TEXT, confirm_delete)],
        },
        fallbacks=[]
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == "__main__":
    main()
