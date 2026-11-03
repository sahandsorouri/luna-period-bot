import base64
import re
from datetime import date

import dates
from crypto import Crypto
from i18n import T
from storage import Store

KEY = base64.urlsafe_b64encode(b"k" * 32).decode()


def test_all_keys_in_both_languages():
    assert set(T["en"]) == set(T["fa"])


def test_no_em_dashes():
    for lang in T:
        for k, v in T[lang].items():
            assert "—" not in v and "–" not in v, k


def test_persian_lines_do_not_start_latin():
    for k, v in T["fa"].items():
        if k == "lang_pick":
            continue
        for line in v.split("\n"):
            plain = re.sub(r"<[^>]+>", "", line).lstrip(" •·🌙🩸🔁📅✨📆⏳🌱ℹ️💡🩺📊💞🔗💌📝🌸🌍🗑📤🌐🕘🔕🚪✅❌ ️")
            assert not re.match(r"[A-Za-z]", plain), (k, line)


def test_jalali_format():
    assert dates.fmt(date(2026, 11, 3), "fa", "j") == "۱۲ آبان"
    assert dates.fmt(date(2026, 11, 3), "en", "g", weekday=True) == "Tue 3 Nov"
    first, last = dates.month_bounds(date(2026, 11, 3), "j")
    assert first == date(2026, 10, 23) and last == date(2026, 11, 21)


def test_month_weeks_layout():
    w = dates.month_weeks(date(2026, 11, 3), "en", "g")
    assert w[0][6] == date(2026, 11, 1)          # 1 Nov 2026 is a Sunday
    w = dates.month_weeks(date(2026, 11, 3), "fa", "j")
    assert w[0][dates.week_col(date(2026, 10, 23), "fa")] == date(2026, 10, 23)


def test_storage_encrypted_and_invites(tmp_path):
    db = tmp_path / "t.db"
    s = Store(str(db), Crypto(base64.urlsafe_b64decode(KEY)))
    u = s.create(1, "fa")
    u.data["periods"] = [{"s": "2026-10-01", "e": None}]
    u.data["name"] = "Sara"
    s.save(u)
    raw = db.read_bytes() + (tmp_path / "t.db-wal").read_bytes() if (tmp_path / "t.db-wal").exists() else db.read_bytes()
    assert b"2026-10-01" not in raw and b"Sara" not in raw
    assert s.get(1).data["periods"][0]["s"] == "2026-10-01"
    tok = s.create_invite(1, {"phase": True}, 48)
    assert tok.encode() not in raw
    assert s.peek_invite(tok) == (1, {"phase": True})
    assert s.peek_invite("nope") is None
    s.drop_invite(tok)
    assert s.peek_invite(tok) is None
    s.create_link(1, 2, {"phase": True})
    assert s.link_by_partner(2).owner_id == 1
    s.delete(1)
    assert s.get(1) is None and s.link_by_partner(2) is None


def test_rtl_mark_added_for_persian():
    from handlers import rtl
    out = rtl("Sara دعوتت کرده\nhttps://t.me/x")
    assert all(line.startswith("\u200f") for line in out.split("\n"))
    assert rtl("Hello\nworld") == "Hello\nworld"


def test_jalali_calendar_shows_jalali_days():
    import keyboards as kb
    m = kb.calendar_kb("fa", "j", "past", date(2026, 11, 3), date(2026, 11, 3), {}, True)
    texts = [b.text for row in m.inline_keyboard for b in row]
    assert "۱" in texts and "[۱۲]" in texts and "۳۰" in texts and "۳۱" not in texts
