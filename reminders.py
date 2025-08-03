import json
import os
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

DATA_FILE = "data/reminders.json"

LANGUAGES = {
    "en": {
        "start": "Welcome to BabyCareBot! Choose an option:",
        "add_daily": "Add Daily Reminder",
        "add_cyclic": "Add Cyclic Reminder",
        "cancel": "Cancel Reminder",
        "done": "Mark Reminder as Done",
        "language": "Change Language",
        "set_lang": "Language set to English.",
        "no_reminders": "You have no reminders yet.",
        "list_title": "Your Reminders:",
    },
    "he": {
        "start": "ברוך הבא לבייבי-קייר בוט! בחר פעולה:",
        "add_daily": "הוסף תזכורת יומית",
        "add_cyclic": "הוסף תזכורת מחזורית",
        "cancel": "בטל תזכורת",
        "done": "סמן כהושלם",
        "language": "שנה שפה",
        "set_lang": "השפה עודכנה לעברית.",
        "no_reminders": "אין לך תזכורות עדיין.",
        "list_title": "התזכורות שלך:",
    },
}

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_lang(user_id):
    data = load_data()
    return data.get(str(user_id), {}).get("lang", "he")

def get_text(user_id, key):
    lang = get_lang(user_id)
    return LANGUAGES[lang].get(key, key)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    if user_id not in data:
        data[user_id] = {"lang": "he", "reminders": []}
        save_data(data)

    keyboard = [
        [InlineKeyboardButton(get_text(user_id, "add_daily"), callback_data="add_daily")],
        [InlineKeyboardButton(get_text(user_id, "add_cyclic"), callback_data="add_cyclic")],
        [InlineKeyboardButton(get_text(user_id, "done"), callback_data="done")],
        [InlineKeyboardButton(get_text(user_id, "cancel"), callback_data="cancel")],
        [InlineKeyboardButton(get_text(user_id, "language"), callback_data="change_lang")],
    ]
    await update.message.reply_text(get_text(user_id, "start"), reply_markup=InlineKeyboardMarkup(keyboard))

async def add_daily_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🕒 Feature to add daily reminders is not implemented yet.")

async def add_cyclic_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("🔁 Feature to add cyclic reminders is not implemented yet.")

async def done_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("✅ Feature to mark reminders as done is not implemented yet.")

async def cancel_reminder(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text("❌ Feature to cancel reminders is not implemented yet.")

async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    keyboard = [
        [InlineKeyboardButton("עברית", callback_data="lang_he")],
        [InlineKeyboardButton("English", callback_data="lang_en")],
    ]
    await update.message.reply_text(get_text(user_id, "language"), reply_markup=InlineKeyboardMarkup(keyboard))

async def set_language(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = str(query.from_user.id)
    lang_code = query.data.split("_")[1]
    data = load_data()
    if user_id not in data:
        data[user_id] = {"lang": lang_code, "reminders": []}
    else:
        data[user_id]["lang"] = lang_code
    save_data(data)
    await query.answer()
    await query.edit_message_text(get_text(user_id, "set_lang"))

async def list_reminders(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = str(update.effective_user.id)
    data = load_data()
    reminders = data.get(user_id, {}).get("reminders", [])
    if not reminders:
        await update.message.reply_text(get_text(user_id, "no_reminders"))
        return

    message = get_text(user_id, "list_title") + "\n\n"
    for i, r in enumerate(reminders, 1):
        message += f"{i}. {r.get('text', '🔔 Reminder')}\n"
    await update.message.reply_text(message)
