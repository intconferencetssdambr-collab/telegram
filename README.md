# Free Autonomous Telegram AI Bot

A 24/7 Telegram bot that answers questions and searches the web — **completely free**, independent of Lovable credits.

- 🧠 **AI**: Google Gemini Flash (free tier resets daily, ~1,500 requests/day)
- 🔎 **Web search**: DuckDuckGo (no API key, unlimited)
- 📡 **Transport**: long polling — no public URL, no webhook setup needed
- 💾 **Memory**: last 12 turns per chat (in-memory)

---

## 1. Get free API keys

1. **Telegram token** — Open [@BotFather](https://t.me/BotFather) → `/newbot` (or `/revoke` your leaked one, then `/token`).
2. **Gemini API key** — Go to <https://aistudio.google.com/apikey> → *Create API key*. Free tier: ~1,500 req/day on `gemini-2.0-flash`, auto-resets daily.

## 2. Deploy on a free always-on host

Pick **one** of these. All run the bot 24/7 for free with long polling.

### Option A — Koyeb (recommended, simplest free always-on)
1. Push these files to a GitHub repo.
2. Sign up at <https://www.koyeb.com> (free "Eco" instance, no card required).
3. *Create Service* → GitHub → pick repo.
4. Builder: **Buildpack**. Run command: `python bot.py`. Instance: **Free (eco-nano)**. Type: **Worker** (no port).
5. Env vars: `TELEGRAM_TOKEN`, `GEMINI_API_KEY`.
6. Deploy. Done.

### Option B — Fly.io (free tier, requires card for verification)
```bash
fly launch --no-deploy           # accept defaults, no DB
fly secrets set TELEGRAM_TOKEN=xxx GEMINI_API_KEY=xxx
fly deploy
```

### Option C — Your own machine / Raspberry Pi / old laptop
```bash
pip install -r requirements.txt
export TELEGRAM_TOKEN=xxx
export GEMINI_API_KEY=xxx
python bot.py
```
Run under `systemd`, `pm2`, or `screen` for persistence.

### Option D — Render (free web service + cron ping)
Render's free worker tier was removed, but a free **web service** works if you add a tiny HTTP keepalive. Prefer Koyeb instead.

## 3. Test locally first

```bash
pip install -r requirements.txt
TELEGRAM_TOKEN=... GEMINI_API_KEY=... python bot.py
```
Open your bot in Telegram, send `/start`, ask anything.

## Commands
- `/start` — greeting
- `/reset` — clear chat memory

## Notes
- The Gemini free quota is **per Google account, per day**, and resets every 24h — so the bot keeps working forever without payment as long as usage stays under the daily limit.
- If you exceed quota, the bot replies with the error; it auto-recovers next day.
- Switch model via env: `GEMINI_MODEL=gemini-2.0-flash-lite` for even higher free limits.
- Memory is in-process; restarts clear it. Add SQLite if you want persistence.
