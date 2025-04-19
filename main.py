import re
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")

user_modes = {}
user_quiz_data = {}

def clean_question_for_json(text):
    return re.sub(r'\[.*?\]', '', text).strip()

def clean_explanation_for_json(text):
    text = re.sub(r'https?://\S+', '', text)
    return text.strip()

def replace_brackets(text):
    if '[' in text and ']' in text:
        return re.sub(r'\[.*?\]', '[Dopamine Admission]\n', text)
    else:
        return f"[Dopamine Admission]\n{text}"

def sanitize_explanation(text):
    return re.sub(r'https://t\.me/\S+', 'https://t.me/Dopamine_Admission', text)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Quiz Mode")], [KeyboardButton("JSON Mode")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Please choose a mode:", reply_markup=reply_markup)

async def handle_mode_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text

    if text == "Quiz Mode":
        user_modes[user_id] = "quiz"
        await update.message.reply_text("Quiz Mode enabled.")
    elif text == "JSON Mode":
        user_modes[user_id] = "json"
        user_quiz_data[user_id] = []
        keyboard = [[KeyboardButton("Make JSON")], [KeyboardButton("Back to Menu")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("JSON Mode enabled. Send quizzes now.", reply_markup=reply_markup)
    elif text == "Back to Menu":
        user_modes[user_id] = None
        keyboard = [[KeyboardButton("Quiz Mode")], [KeyboardButton("JSON Mode")]]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
        await update.message.reply_text("Back to main menu.", reply_markup=reply_markup)
    elif text == "Make JSON":
        quizzes = user_quiz_data.get(user_id, [])
        if not quizzes:
            await update.message.reply_text("No quizzes added yet.")
        else:
            filename = f"quizzes_{user_id}.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(quizzes, f, indent=2, ensure_ascii=False)
            await update.message.reply_document(document=InputFile(filename))
            os.remove(filename)

async def handle_poll_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    poll = update.message.poll
    user_id = update.message.from_user.id
    mode = user_modes.get(user_id)

    if not poll:
        return

    question = poll.question
    options = [opt.text for opt in poll.options]
    is_anonymous = poll.is_anonymous
    correct_option_id = poll.correct_option_id if poll.type == "quiz" else None
    explanation = poll.explanation if hasattr(poll, "explanation") else ""

    if mode == "quiz":
        question = replace_brackets(question)
        if explanation:
            explanation = sanitize_explanation(explanation)
        await update.message.reply_poll(
            question=question,
            options=options,
            type="quiz",
            correct_option_id=correct_option_id,
            is_anonymous=is_anonymous,
            explanation=explanation
        )
    elif mode == "json":
        clean_q = clean_question_for_json(question)
        clean_exp = clean_explanation_for_json(explanation or "")
        quiz_data = {
            "question": clean_q,
            "options": options,
            "correctOption": str(correct_option_id + 1) if correct_option_id is not None else "0",
            "explanation": clean_exp
        }
        user_quiz_data.setdefault(user_id, []).append(quiz_data)
        await update.message.reply_text("Quiz saved for JSON export.")

app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mode_selection))
app.add_handler(MessageHandler(filters.POLL, handle_poll_message))
app.run_polling()
