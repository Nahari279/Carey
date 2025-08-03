import asyncio
import logging
import os
from telegram import Update
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
)
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from reminders import (
    start, help_command, set_daily_reminder, set_cyclic_reminder,
    cancel_reminder, list_reminders, handle_reminder_button
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Read token from environment variable
BOT_TOKEN = os.getenv("BOT_TOKEN")

async def main():
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(setup_scheduler)
        .build()
    )

    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("daily", set_daily_reminder))
    application.add_handler(CommandHandler("cyclic", set_cyclic_reminder))
    application.add_handler(CommandHandler("cancel", cancel_reminder))
    application.add_handler(CommandHandler("list", list_reminders))
    application.add_handler(CallbackQueryHandler(handle_reminder_button))

    await application.run_polling()

async def setup_scheduler(application):
    application.job_queue.scheduler = AsyncIOScheduler()
    application.job_queue.scheduler.start()

# Compatibility fix for Render
import nest_asyncio
nest_asyncio.apply()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
