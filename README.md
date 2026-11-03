# 🌙 Luna: a private period tracker on Telegram

Luna helps women track their period, know what is coming, and, if they want, keep a partner in the loop.
English and Persian (فارسی), Gregorian and Solar Hijri calendars. Everything is buttons, no commands.

## ✨ What it does

- 🩸 Log a period start and end in one tap (today, yesterday, or pick a date)
- 📅 Calendar: tap every past start day you remember, month by month
- 🌸 Today: cycle day, phase, next period, fertile window (optional), and tips for what helps now
- 📝 How I feel: flow, mood, body symptoms, energy
- 📊 Stats: average cycle and period, regularity, last 6 cycles, top symptoms, "worth asking a doctor" flags
- 🔔 Reminders: period soon, due today, late, PMS days, "has it ended?", optional daily check-in
- 💞 Partner: a one-time invite link; the partner sees only what she switches on, plus tips on how to help

## 🔐 Privacy and security

Privacy is the core of Luna, not an add-on.

| | How |
|---|---|
| Encrypted at rest | All personal data (name, periods, logs) is one blob per user, encrypted with Fernet (AES-128-CBC + HMAC-SHA256). |
| Per-user keys | Each user's key is derived with HKDF-SHA256 from a server master key and her Telegram id. A copied database alone is unreadable. |
| Strict scoping | Every handler reads only the caller's own record. A partner reads derived info (phase, dates) through an active link, filtered by her switches. Never raw logs or notes. |
| Invite links | Random 128-bit tokens, one-time, expire after 48 hours, stored only as an HMAC. |
| Instant revoke | Stop sharing deletes the link and the partner's record right away. |
| No third parties | No analytics, no ads, no AI services, no outside APIs except Telegram. |
| No sensitive logs | Logs never contain message text or health data. |
| User control | One tap to export all data as JSON, one tap to delete everything. |
| Discreet mode | Notifications hide their text on the lock screen until tapped. |

**Honest limits.** Encryption is at rest on the server, not end-to-end: whoever runs the server holds the master key. Telegram stores the chat on the user's devices and Telegram's servers. Luna is not a medical device and not a birth control method.

## 🧮 Prediction method

- Cycle length: median of the last 6 cycles (15 to 90 days). Before one full cycle, the length she gives at setup ("rough estimate").
- Ovulation: next period minus 14 days. Fertile window: 5 days before to 1 day after.
- PMS window: the 5 days before the next period.
- Late alerts start after her normal variation. Doctor flags follow FIGO and ACOG ranges.

## 🛠 Run it

```bash
python3 -m venv venv && ./venv/bin/pip install -r requirements.txt
cp .env.example .env                    # add BOT_TOKEN
./venv/bin/python scripts/gen_key.py    # put the result in .env as MASTER_KEY, back it up separately
./venv/bin/python main.py
```

Docker: `docker compose up -d --build` (data in `./data`).

Tests: `./venv/bin/pip install pytest && ./venv/bin/pytest -q` (unit tests plus a full simulated chat against a fake Telegram API).

Stack: Python 3.12, python-telegram-bot 21, SQLite, cryptography, jdatetime.

## License

MIT
