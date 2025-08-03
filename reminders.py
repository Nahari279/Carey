import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes


DATA_FOLDER = "data"
REMINDERS_FILE = os.path.join(DATA_FOLDER, "reminders.json")

def load_reminders():
    if not os.path.exists(REMINDERS_FILE):
        return {}
    with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_reminders(reminders):
    os.makedirs(DATA_FOLDER, exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, ensure_ascii=False, indent=2)

def add_reminder(user_id, reminder):
    reminders = load_reminders()
    user_key = str(user_id)
    reminders.setdefault(user_key, []).append(reminder)
    save_reminders(reminders)

def get_due_reminders():
    now = datetime.now()
    due = []
    reminders = load_reminders()
    for user_id, user_reminders in reminders.items():
        for reminder in user_reminders:
            reminder_time = datetime.fromisoformat(reminder["time"])
            if now >= reminder_time and not reminder.get("notified"):
                due.append((user_id, reminder))
    return due

def mark_reminder_as_sent(user_id, reminder):
    reminders = load_reminders()
    user_key = str(user_id)
    for r in reminders.get(user_key, []):
        if r == reminder:
            r["notified"] = True
            break
    save_reminders(reminders)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Available commands:\n/start\n/help\n/add_daily\n/add_cyclic\n/list\n/done\n/cancel")

