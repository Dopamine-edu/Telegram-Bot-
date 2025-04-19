import re
import json
import os
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Bot token
TELEGRAM_TOKEN = "7792624440:AAHJP9eeCssIISrkiirSMR4Rk4uC2qUV9SM"

# In-memory user data
user_modes = {}
user_quiz_data = {}

# Clean question for JSON output
def clean_question_for_json(text):
    return re.sub(r'\[.*?\]', '', text).strip()

# Clean explanation by removing any links
def clean_explanation_for_json(text):
    text = re.sub(r'https?://\S+', '', text)
    return text.strip()

# Replace [text] with [Dopamine Admission] for quiz display
def replace_brackets(text):
    if '[' in text and ']' in text:
        return re.sub(r'\[.*?\]', '[Dopamine Admission]\n', text)
    else:
        return f"[Dopamine Admission]\n{text}"

# Sanitize explanation for quiz display (replace t.me links)
def sanitize_explanation(text):
    return re.sub(r'https://t\.me/\S+', 'https://t.me/Dopamine_Admission', text)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[KeyboardButton("Quiz Mode")], [KeyboardButton("JSON Mode")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Please choose a mode:", reply_markup=reply_markup)

# Handle mode selection
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
            json_text = json.dumps(quizzes, indent=2, ensure_ascii=False)
            file_name = f"{user_id}_quizzes.json"
            with open(file_name, "w", encoding="utf-8") as f:
                f.write(json_text)

            await update.message.reply_document(document=open(file_name, "rb"), filename="quizzes.json")
            os.remove(file_name)

# Handle quizzes
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

# Setup the bot
app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_mode_selection))
app.add_handler(MessageHandler(filters.POLL, handle_poll_message))
app.run_polling()
