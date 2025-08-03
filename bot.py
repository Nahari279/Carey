import asyncio
import logging
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)
from reminders import (
    help_command,
    list_reminders,
    cancel_reminder,
    set_language,
    add_daily_reminder,
    add_periodic_reminder,
    handle_cancel_button,
    send_reminders_job,
)
from telegram_bot_calendar import DetailedTelegramCalendar
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from data.data_store import load_data, save_data
from data.localization import get_text
from dotenv import load_dotenv
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Define the scheduler globally
scheduler = AsyncIOScheduler()

# Load data once at startup
user_data = load_data()


async def start(update, context):
    user_id = str(update.effective_user.id)
    if user_id not in user_data:
        user_data[user_id] = {"language": "he", "reminders": []}
        save_data(user_data)
    text = get_text("welcome", user_data[user_id]["language"])
    await update.message.reply_text(text)


def setup_scheduler(application):
    scheduler.add_job(send_reminders_job, "interval", seconds=60, args=[application])
    scheduler.start()


def setup_handlers(application):
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CommandHandler("cancel", cancel_reminder))
    application.add_handler(CommandHandler("lang", set_language))
    application.add_handler(CommandHandler("daily", add_daily_reminder))
    application.add_handler(CommandHandler("periodic", add_periodic_reminder))
    application.add_handler(CallbackQueryHandler(handle_cancel_button, pattern="cancel_"))
    application.add_handler(CallbackQueryHandler(DetailedTelegramCalendar().process))


async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    setup_handlers(app)
    setup_scheduler(app)
    await app.run_polling()


if __name__ == "__main__":
    asyncio.run(main())
