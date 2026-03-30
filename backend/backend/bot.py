from __future__ import annotations

import logging

import httpx
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)

from backend.config import settings


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


BACKEND_BASE_URL = settings.backend_base_url_internal.rstrip("/")
BOT_TOKEN = settings.telegram_ai_bot_token
ALLOWED_CHAT_ID = settings.telegram_ai_allowed_chat_id


class BotAccessError(Exception):
    pass


def ensure_allowed(update: Update) -> None:
    chat = update.effective_chat
    if chat is None or ALLOWED_CHAT_ID is None or chat.id != ALLOWED_CHAT_ID:
        raise BotAccessError("Access denied")


async def post_json(path: str, payload: dict) -> str:
    url = f"{BACKEND_BASE_URL}{path}"
    async with httpx.AsyncClient(timeout=180) as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        data = response.json()
    return data["response"]


async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    text = (
        "Private AI bot is running.\n\n"
        "Commands:\n"
        "/chat <text>\n"
        "/task <idea>\n"
        "/metric <name> | <value> | <context>\n"
        "/help"
    )
    await update.message.reply_text(text)


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    text = (
        "Available commands:\n\n"
        "/chat <text>\n"
        "Free-form request through /ai/chat\n\n"
        "/task <idea>\n"
        "Convert an idea into a structured task\n\n"
        "/metric <name> | <value> | <context>\n"
        "Explain a metric using the provided context"
    )
    await update.message.reply_text(text)


async def chat_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    if update.message is None:
        return

    prompt = " ".join(context.args).strip()
    if not prompt:
        await update.message.reply_text("Usage: /chat <text>")
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response_text = await post_json(
            "/ai/chat",
            {"prompt": prompt},
        )
        await update.message.reply_text(response_text)
    except Exception as exc:
        logger.exception("chat_cmd failed")
        await update.message.reply_text(f"Error: {exc}")


async def task_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    if update.message is None:
        return

    idea = " ".join(context.args).strip()
    if not idea:
        await update.message.reply_text("Usage: /task <idea>")
        return

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response_text = await post_json(
            "/ai/task-from-idea",
            {"idea": idea},
        )
        await update.message.reply_text(response_text)
    except Exception as exc:
        logger.exception("task_cmd failed")
        await update.message.reply_text(f"Error: {exc}")


async def metric_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    if update.message is None:
        return

    raw = " ".join(context.args).strip()
    if not raw:
        await update.message.reply_text(
            "Usage: /metric <name> | <value> | <context>"
        )
        return

    parts = [part.strip() for part in raw.split("|")]
    if len(parts) < 1 or not parts[0]:
        await update.message.reply_text(
            "Usage: /metric <name> | <value> | <context>"
        )
        return

    metric_name = parts[0]
    metric_value = parts[1] if len(parts) > 1 and parts[1] else None
    context_text = parts[2] if len(parts) > 2 and parts[2] else None

    await update.message.chat.send_action(ChatAction.TYPING)

    try:
        response_text = await post_json(
            "/ai/explain-metric",
            {
                "metric_name": metric_name,
                "metric_value": metric_value,
                "context": context_text,
            },
        )
        await update.message.reply_text(response_text)
    except Exception as exc:
        logger.exception("metric_cmd failed")
        await update.message.reply_text(f"Error: {exc}")


async def unknown_private_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    try:
        ensure_allowed(update)
    except BotAccessError:
        return

    if update.message is None or not update.message.text:
        return

    await update.message.reply_text(
        "Use /chat, /task, /metric, /start, or /help."
    )


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_AI_BOT_TOKEN is not configured")
    if ALLOWED_CHAT_ID is None:
        raise RuntimeError("TELEGRAM_AI_ALLOWED_CHAT_ID is not configured")

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_cmd))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("chat", chat_cmd))
    application.add_handler(CommandHandler("task", task_cmd))
    application.add_handler(CommandHandler("metric", metric_cmd))

    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
