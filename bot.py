"""
Free autonomous Telegram bot.
- Chat: Google Gemini (free tier, refreshes daily)
- Web search: DuckDuckGo (no key, free, unlimited)
- Transport: long polling (no public URL needed -> works on any free host)
"""
import os
import logging
import asyncio
from collections import defaultdict, deque

import google.generativeai as genai
from ddgs import DDGS
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, MessageHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bot")

TELEGRAM_TOKEN = os.environ["TELEGRAM_TOKEN"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(
    GEMINI_MODEL,
    system_instruction=(
        "You are a helpful, concise assistant in a Telegram chat. "
        "When the user asks about recent events, news, prices, or anything time-sensitive, "
        "call the `web_search` tool. Always cite sources as short markdown links "
        "when you used search results. Keep answers under 400 words unless asked."
    ),
    tools=[{
        "function_declarations": [{
            "name": "web_search",
            "description": "Search the public web via DuckDuckGo and return top results.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {"type": "integer", "description": "1-8"},
                },
                "required": ["query"],
            },
        }]
    }],
)

# Per-chat short memory (last N turns)
HISTORY_LEN = 12
histories: dict[int, deque] = defaultdict(lambda: deque(maxlen=HISTORY_LEN))
locks: dict[int, asyncio.Lock] = defaultdict(asyncio.Lock)


def web_search(query: str, max_results: int = 5) -> dict:
    max_results = max(1, min(int(max_results or 5), 8))
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=max_results))
        return {"results": [
            {"title": r.get("title"), "url": r.get("href"), "snippet": r.get("body")}
            for r in results
        ]}
    except Exception as e:
        log.exception("search failed")
        return {"error": str(e), "results": []}


async def generate(chat_id: int, user_text: str) -> str:
    history = list(histories[chat_id])
    chat = model.start_chat(history=history)
    resp = await asyncio.to_thread(chat.send_message, user_text)

    # Handle tool calls (loop in case the model chains them)
    for _ in range(4):
        call = None
        try:
            call = resp.candidates[0].content.parts[0].function_call
        except Exception:
            call = None
        if not call or not getattr(call, "name", None):
            break
        args = {k: v for k, v in (call.args or {}).items()}
        log.info("tool call: %s %s", call.name, args)
        if call.name == "web_search":
            result = web_search(**args)
        else:
            result = {"error": f"unknown tool {call.name}"}
        resp = await asyncio.to_thread(
            chat.send_message,
            genai.protos.Content(parts=[genai.protos.Part(
                function_response=genai.protos.FunctionResponse(
                    name=call.name, response=result
                )
            )]),
        )

    text = (resp.text or "").strip() or "…"
    histories[chat_id] = deque(chat.history[-HISTORY_LEN:], maxlen=HISTORY_LEN)
    return text


async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Hi! I'm a free AI bot powered by Gemini + web search.\n"
        "Just ask me anything. /reset to clear memory."
    )


async def reset(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    histories.pop(update.effective_chat.id, None)
    await update.message.reply_text("Memory cleared.")


async def on_message(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text or ""
    async with locks[chat_id]:
        await ctx.bot.send_chat_action(chat_id, "typing")
        try:
            answer = await generate(chat_id, text)
        except Exception as e:
            log.exception("generation failed")
            answer = f"⚠️ Error: {e}"
        # Telegram message limit ~4096
        for i in range(0, len(answer), 4000):
            await update.message.reply_text(answer[i:i+4000], parse_mode=None)


def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_message))
    log.info("Bot starting (long polling)…")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
