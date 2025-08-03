def get_text(key, lang="he"):
    texts = {
        "welcome": {
            "he": "ברוך הבא לבוט התזכורות! 🍼\nהשתמש בפקודה /help כדי להתחיל.",
            "en": "Welcome to the BabyCareBot! 🍼\nUse /help to get started.",
        },
        "help": {
            "he": "📌 הפקודות הזמינות:\n"
                  "/daily - הוסף תזכורת יומית\n"
                  "/periodic - הוסף תזכורת מחזורית\n"
                  "/list - רשימת התזכורות\n"
                  "/cancel - ביטול תזכורת\n"
                  "/lang - שינוי שפה\n"
                  "/help - עזרה",
            "en": "📌 Available commands:\n"
                  "/daily - Add daily reminder\n"
                  "/periodic - Add periodic reminder\n"
                  "/list - List reminders\n"
                  "/cancel - Cancel a reminder\n"
                  "/lang - Change language\n"
                  "/help - Help",
        },
        "no_reminders": {
            "he": "אין תזכורות כרגע.",
            "en": "No reminders currently.",
        },
        "choose_reminder_to_cancel": {
            "he": "בחר תזכורת לביטול:",
            "en": "Choose a reminder to cancel:",
        },
        "reminder_added": {
            "he": "✔️ תזכורת נוספה בהצלחה!",
            "en": "✔️ Reminder added successfully!",
        },
        "reminder_cancelled": {
            "he": "❌ התזכורת בוטלה.",
            "en": "❌ Reminder cancelled.",
        },
        "language_changed": {
            "he": "השפה עודכנה לעברית 🇮🇱",
            "en": "Language changed to English 🇺🇸",
        },
        "ask_language": {
            "he": "בחר שפה:\n🇮🇱 עברית\n🇺🇸 English",
            "en": "Choose a language:\n🇮🇱 Hebrew\n🇺🇸 English",
        },
        "invalid_time_format": {
            "he": "⛔ פורמט זמן לא תקין. השתמש בפורמט HH:MM (למשל 08:30)",
            "en": "⛔ Invalid time format. Use HH:MM (e.g. 08:30)",
        },
        "invalid_interval_format": {
            "he": "⛔ פורמט לא תקין. כתוב כך: כל 3 שעות או כל 30 דקות.",
            "en": "⛔ Invalid format. Write like: every 3 hours or every 30 minutes.",
        },
    }

    return texts.get(key, {}).get(lang, "❗ טקסט לא נמצא / Text not found.")
