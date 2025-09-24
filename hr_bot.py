# -*- coding: utf-8 -*-
import os, re, sqlite3
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, CallbackQueryHandler,
    ConversationHandler, ContextTypes, filters
)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))

# Состояния
LANG, NAME, PHONE, POSITION, CV = range(5)

# Приветствие
WELCOME_3 = (
    "🇷🇺 Добро пожаловать! Станьте частью нашей международной команды в Holiday Inn Tashkent City.\n\n"
    "🇬🇧 Welcome! Join our international team at Holiday Inn Tashkent City.\n\n"
    "🇺🇿 Xush kelibsiz! Holiday Inn Tashkent City’dagi xalqaro jamoamizga qo‘shiling."
)

# Тексты
T = {
    "en": {
        "choose_lang": "Please choose your language:",
        "ask_name": "Please enter your full name (e.g., John Smith).",
        "ask_phone": "Send your phone number in international format (e.g., +9989X xxx xx xx).",
        "bad_phone": "This number looks invalid. Use format +9989X xxx xx xx.",
        "ask_position": "Which position are you applying for? (e.g., Front Desk Agent, Waiter).",
        "ask_cv": "Upload your CV as a PDF/DOC/DOCX file (max 20 MB). Photos are not accepted.",
        "bad_cv": "Please send a document file (PDF/DOC/DOCX) up to 20 MB (no images).",
        "thanks": (
            "Thank you! Your CV has been received successfully.\n"
            "The HR Department of Holiday Inn Tashkent City will carefully review your application.\n"
            "If your profile matches an open vacancy, we will contact you.\n"
            "We appreciate your interest and patience."
        ),
        "change_lang": "Choose a language:",
    },
    "ru": {
        "choose_lang": "Пожалуйста, выберите язык:",
        "ask_name": "Введите ваше ФИО (например: Иванов Иван Иванович).",
        "ask_phone": "Укажите номер телефона в международном формате (например: +9989X xxx xx xx).",
        "bad_phone": "Похоже, номер некорректный. Используйте формат +9989X xxx xx xx.",
        "ask_position": "На какую позицию вы хотите откликнуться? (например: Front Desk Agent, Официант).",
        "ask_cv": "Загрузите резюме как документ в формате PDF/DOC/DOCX (до 20 МБ). Фото не принимаются.",
        "bad_cv": "Нужен файл-документ (PDF/DOC/DOCX) до 20 МБ (не изображение).",
        "thanks": (
            "Спасибо! Ваше резюме успешно получено.\n"
            "HR-отдел Holiday Inn Tashkent City рассмотрит вашу заявку.\n"
            "Если ваш профиль будет соответствовать открытой вакансии, мы обязательно свяжемся.\n"
            "Благодарим за интерес и терпение."
        ),
        "change_lang": "Выберите язык:",
    },
    "uz": {
        "choose_lang": "Iltimos, tilni tanlang:",
        "ask_name": "Iltimos, to‘liq ismingizni kiriting (masalan: Aliyev Ali).",
        "ask_phone": "Telefon raqamingizni xalqaro formatda yuboring (masalan: +9989X xxx xx xx).",
        "bad_phone": "Raqam noto‘g‘ri ko‘rinadi. +9989X xxx xx xx kabi formatdan foydalaning.",
        "ask_position": "Qaysi lavozimga murojaat qilyapsiz? (masalan: Front Desk Agent, Waiter).",
        "ask_cv": "Rezyumeyingizni PDF/DOC/DOCX hujjat sifatida yuboring (maks. 20 MB). Rasm qabul qilinmaydi.",
        "bad_cv": "Faqat hujjat fayli kerak (PDF/DOC/DOCX), 20 MB gacha (rasm emas).",
        "thanks": (
            "Rahmat! Sizning rezyumeyingiz muvaffaqiyatli qabul qilindi.\n"
            "Holiday Inn Tashkent City HR bo‘limi arizangizni diqqat bilan ko‘rib chiqadi.\n"
            "Profilingiz ochiq bo‘sh ish o‘rinlariga mos kelsa, biz albatta bog‘lanamiz.\n"
            "Kompaniyamizga bo‘lgan qiziqishingiz va sabringiz uchun rahmat."
        ),
        "change_lang": "Tilni tanlang:",
    }
}

LANG_KEYS = ["en", "ru", "uz"]
PHONE_RE = re.compile(r"^\+?\d{7,15}$")
DOC_MIMES = {
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

# --- DB ---
def db():
    conn = sqlite3.connect("hrbot.db")
    conn.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tg_user_id INTEGER,
        lang TEXT,
        full_name TEXT,
        phone TEXT,
        position TEXT,
        cv_file_id TEXT,
        created_at TEXT
    )""")
    return conn

# --- Keyboards ---
def lang_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("English", callback_data="lang_en")],
        [InlineKeyboardButton("Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("O‘zbekcha", callback_data="lang_uz")],
    ])

def get_lang(ctx: ContextTypes.DEFAULT_TYPE) -> str:
    return ctx.user_data.get("lang", "ru")

# --- Handlers ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = WELCOME_3 + "\n\n" + T["ru"]["choose_lang"]
    await update.effective_chat.send_message(text, reply_markup=lang_buttons())
    return LANG

async def on_lang_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    data = q.data
    if data.startswith("lang_"):
        chosen = data.split("_")[1]
        if chosen in LANG_KEYS:
            context.user_data["lang"] = chosen
            await q.edit_message_text(T[chosen]["ask_name"])
            return NAME
    return LANG

async def ask_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data["full_name"] = (update.message.text or "").strip()
    await update.message.reply_text(T[lang]["ask_phone"])
    return PHONE

async def ask_phone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    phone = (update.message.text or "").strip().replace(" ", "")
    if not PHONE_RE.match(phone):
        await update.message.reply_text(T[lang]["bad_phone"])
        return PHONE
    context.user_data["phone"] = phone
    await update.message.reply_text(T[lang]["ask_position"])
    return POSITION

async def ask_position(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    context.user_data["position"] = (update.message.text or "").strip()
    await update.message.reply_text(T[lang]["ask_cv"])
    return CV

async def ask_cv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = get_lang(context)
    doc = update.message.document
    if not doc:
        await update.message.reply_text(T[lang]["bad_cv"])
        return CV

    mime = doc.mime_type or ""
    size_ok = (doc.file_size or 0) <= 20 * 1024 * 1024
    if mime not in DOC_MIMES or not size_ok:
        await update.message.reply_text(T[lang]["bad_cv"])
        return CV

    conn = db()
    with conn:
        conn.execute(
            """INSERT INTO applications
               (tg_user_id, lang, full_name, phone, position, cv_file_id, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                update.effective_user.id,
                lang,
                context.user_data.get("full_name"),
                context.user_data.get("phone"),
                context.user_data.get("position"),
                doc.file_id,
                datetime.utcnow().isoformat(),
            ),
        )
    conn.close()

    try:
        if ADMIN_CHAT_ID and ADMIN_CHAT_ID != update.effective_chat.id:
            caption = (
                "📥 New application\n"
                f"Lang: {lang}\n"
                f"Name: {context.user_data.get('full_name')}\n"
                f"Phone: {context.user_data.get('phone')}\n"
                f"Position: {context.user_data.get('position')}\n"
                f"TG: @{update.effective_user.username or '—'} (id {update.effective_user.id})"
            )
            await context.bot.send_document(
                chat_id=ADMIN_CHAT_ID,
                document=doc.file_id,
                caption=caption
            )
    except Exception as e:
        print("Admin forward error:", e)

    await update.message.reply_text(T[lang]["thanks"])
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cancelled. /start")
    return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing in .env")
    app = Application.builder().token(BOT_TOKEN).build()

    conv = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            LANG: [CallbackQueryHandler(on_lang_choice)],
            NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            POSITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_position)],
            CV: [MessageHandler(filters.Document.ALL & ~filters.COMMAND, ask_cv)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True,
    )

    app.add_handler(conv)
    app.add_handler(CommandHandler("cancel", cancel))

    print("HITC Careers Bot is running (polling). Press Ctrl+C to stop.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
