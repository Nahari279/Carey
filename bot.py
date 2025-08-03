import asyncio
import logging
import os
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
)
from reminders import (
    start,
    add_daily_reminder,
    add_cyclic_reminder,
    done_reminder,
    cancel_reminder,
    language_command,
    set_language,
    list_reminders,
)

# Load token from environment variable (Render best practice)
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN environment variable")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CommandHandler("list", list_reminders))

    # Callback handlers (menu buttons)
    app.add_handler(CallbackQueryHandler(add_daily_reminder, pattern="^add_daily$"))
    app.add_handler(CallbackQueryHandler(add_cyclic_reminder, pattern="^add_cyclic$"))
    app.add_handler(CallbackQueryHandler(done_reminder, pattern="^done$"))
    app.add_handler(CallbackQueryHandler(cancel_reminder, pattern="^cancel$"))
    app.add_handler(CallbackQueryHandler(set_language, pattern="^lang_(he|en)$"))

    # Start polling
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())
