import logging
import os

from telegram import MenuButtonDefault, Update
from telegram.ext import (Application, CallbackQueryHandler, CommandHandler, MessageHandler,
                          filters)

import config
import handlers
import notify
from i18n import t
from crypto import Crypto, decode_master
from storage import Store

logging.basicConfig(format="%(asctime)s %(levelname)s %(name)s %(message)s", level=logging.INFO)
for noisy in ("httpx", "httpcore", "telegram.ext.Application", "apscheduler"):
    logging.getLogger(noisy).setLevel(logging.WARNING)


def build_store() -> Store:
    if not config.MASTER_KEY:
        raise SystemExit("MASTER_KEY missing. Run scripts/gen_key.py and put it in .env")
    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    os.chmod(config.DATA_DIR, 0o700)
    return Store(str(config.DB_PATH), Crypto(decode_master(config.MASTER_KEY)))


async def post_init(app: Application) -> None:
    await app.bot.set_my_commands([])           # no slash menu, everything is buttons
    await app.bot.set_chat_menu_button(menu_button=MenuButtonDefault())
    # profile text people see before they tap Start
    for lang in ("en", "fa"):
        code = None if lang == "en" else "fa"
        try:
            await app.bot.set_my_description(t(lang, "bot_description"), language_code=code)
            await app.bot.set_my_short_description(t(lang, "bot_short"), language_code=code)
        except Exception as e:  # rate limits must not stop the bot
            logging.getLogger("luna").warning("profile text not set: %s", type(e).__name__)


def register(app: Application) -> None:
    private = filters.ChatType.PRIVATE
    app.add_handler(CommandHandler("start", handlers.on_start, filters=private))
    app.add_handler(MessageHandler(private & filters.TEXT & ~filters.COMMAND, handlers.on_text))
    app.add_handler(CallbackQueryHandler(handlers.on_cb))
    app.add_handler(MessageHandler(private & ~filters.TEXT, handlers.on_other))
    app.add_error_handler(handlers.on_error)


def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")
    handlers.STORE = build_store()
    app = Application.builder().token(config.BOT_TOKEN).post_init(post_init).build()
    register(app)
    app.job_queue.run_repeating(notify.tick, interval=3600, first=_seconds_to_next_hour() + 30)
    app.run_polling(allowed_updates=Update.ALL_TYPES)


def _seconds_to_next_hour() -> int:
    import time
    return 3600 - int(time.time()) % 3600


if __name__ == "__main__":
    main()
