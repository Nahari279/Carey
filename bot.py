import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)

REMINDERS_FILE = "data/reminders.json"
BOT_TOKEN = os.environ.get("BOT_TOKEN", "your_token_here")

reminders = {}

def load_reminders():
    global reminders
    if os.path.exists(REMINDERS_FILE):
        try:
            with open(REMINDERS_FILE, "r") as f:
                content = f.read().strip()
                if content:
                    reminders = json.loads(content)
                else:
                    reminders = {}
        except Exception:
            reminders = {}
    else:
        reminders = {}

def save_reminders():
    with open(REMINDERS_FILE, "w") as f:
        json.dump(reminders, f)

def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    main_menu_keyboard = [
        [InlineKeyboardButton("➕ הוסף פעולה חדשה", callback_data='add_action')],
        [InlineKeyboardButton("📝 הזן שביצעת פעולה", callback_data='submit_action')],
        [InlineKeyboardButton("📋 הצג תזכורות קיימות", callback_data='list_reminders')],
        [InlineKeyboardButton("❌ מחק תזכורת", callback_data='delete_reminder')],
    ]
    reply_markup = InlineKeyboardMarkup(main_menu_keyboard)
    update.message.reply_text("שלום! אני הבוט BabyCareBot 👶", reply_markup=reply_markup)

def handle_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()

    if query.data == 'add_action':
        show_reminder_type_selection(query)
    elif query.data == 'submit_action':
        query.edit_message_text("בחר את הפעולה שביצעת (כאן תוצג רשימת פעולות שלך)...")
        # תרחיב כאן את ההתנהגות בפועל
    elif query.data == 'list_reminders':
        user_id = str(query.from_user.id)
        if user_id not in reminders or not reminders[user_id]:
            query.edit_message_text("אין תזכורות.")
            return

        msg = "📋 התזכורות שלך:\n"
        for idx, r in enumerate(reminders[user_id], 1):
            msg += f"{idx}. {r['text']}\n"
        query.edit_message_text(msg)
    elif query.data == 'delete_reminder':
        query.edit_message_text("בחר תזכורת שברצונך למחוק (בהמשך תתווסף רשימה ניתנת למחיקה).")

def show_reminder_type_selection(query):
    keyboard = [
        [InlineKeyboardButton("⏰ תזכורת קבועה", callback_data='fixed')],
        [InlineKeyboardButton("🔁 תזכורת מחזורית מתאפסת", callback_data='recurring')],
        [InlineKeyboardButton("🔙 חזרה לתפריט", callback_data='menu')]
    ]
    query.edit_message_text("בחר את סוג התזכורת:", reply_markup=InlineKeyboardMarkup(keyboard))

def handle_type_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    query.answer()

    if query.data in ['fixed', 'recurring']:
        reminder_type = 'קבועה' if query.data == 'fixed' else 'מחזורית מתאפסת'
        query.edit_message_text(f"הגדרת תזכורת {reminder_type} בתהליך...\n(כאן תתווסף בחירת טווח זמן וערך)")
        # בהמשך נוסיף את השלבים של בחירת יחידת זמן + מספר יחידות
    elif query.data == 'menu':
        start(update, context)

def main():
    load_reminders()
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_menu, pattern='^(add_action|submit_action|list_reminders|delete_reminder)$'))
    app.add_handler(CallbackQueryHandler(handle_type_selection, pattern='^(fixed|recurring|menu)$'))

    app.run_polling()

if __name__ == "__main__":
    main()
