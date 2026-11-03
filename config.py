import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", BASE / "data"))
DB_PATH = DATA_DIR / "luna.db"
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
MASTER_KEY = os.getenv("MASTER_KEY", "")
INVITE_TTL_HOURS = 48
REPO_URL = os.getenv("REPO_URL", "https://github.com/sahandsorouri/luna-period-bot")
