# CLAUDE.md: Luna (period tracker bot)

## What it is
A private Telegram bot for women to track their period, in English or Persian (user picks).
She can invite one partner with a one-time link. The partner sees only what she turns on.

## Stack
- Python 3.12, python-telegram-bot 21.6 (async, job-queue), SQLite, cryptography (Fernet), jdatetime
- Docker on the Hetzner box (server ~/luna-bot, container `luna`) (same pattern as Hokm and Poker Ledger bots)
- Vault doc: `Build/Builds/Period Tracker Bot.md`

## Files
- `cycle.py`: pure cycle logic (predictions, phases, stats, health flags). No I/O. Tested.
- `storage.py`: SQLite. Health data lives in one encrypted blob per user.
- `crypto.py`: per-user Fernet key derived (HKDF) from MASTER_KEY. Invite tokens stored as HMAC only.
- `i18n.py`: every string in `en` and `fa`. Add a key to both, the test fails otherwise.
- `dates.py`: Gregorian and Solar Hijri formatting, Persian digits, month grids.
- `keyboards.py`: reply keyboards and inline keyboards (calendar picker).
- `handlers.py`: all update handling. `notify.py`: hourly reminder job.

## Rules
- Tap driven. No slash commands except Telegram's own Start. Command menu is cleared at boot.
- Privacy: every read is scoped to the caller's own Telegram id. A partner reads only derived
  info (phase, dates) through the active link, and only the flags she turned on. Never raw logs.
- Never log message text, dates or health data. httpx logs are muted (they contain the token).
- MASTER_KEY lost = all data unreadable. Back it up apart from the database.
- Not a medical device, not birth control. Keep that line in the welcome text.
- Persian strings: no line starts with a Latin word, code or URL. Persian digits in Persian UI.
- No em dashes anywhere.

## Run
```
cp .env.example .env   # BOT_TOKEN, MASTER_KEY
./venv/bin/python scripts/gen_key.py
./venv/bin/python main.py
./venv/bin/pytest -q
```
