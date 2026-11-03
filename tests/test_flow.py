"""End to end: real handlers, real Application, fake Telegram API.

Covers onboarding, logging, past periods, partner invite, partner views,
privacy boundaries, notifications, discreet mode and delete-all.
"""
import asyncio
import base64
import itertools
import time
from datetime import date, timedelta

import pytest
from telegram import InlineKeyboardMarkup, Update
from telegram.ext import Application, ExtBot

import cycle
import dates
import handlers
import main as app_main
import notify
from crypto import Crypto
from storage import Store

OWNER, PARTNER, STRANGER = 111, 222, 333
_ids = itertools.count(1)


class FakeBot(ExtBot):
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        object.__setattr__(self, "calls", [])

    async def _post(self, endpoint, data=None, *args, **kwargs):
        data = data or {}
        self.calls.append((endpoint, data))
        if endpoint == "getMe":
            return {"id": 999, "is_bot": True, "first_name": "Luna", "username": "luna_test_bot"}
        if endpoint in ("sendMessage", "editMessageText", "editMessageReplyMarkup", "sendDocument"):
            chat = data.get("chat_id", OWNER)
            return {"message_id": next(_ids), "date": int(time.time()),
                    "chat": {"id": chat, "type": "private"}, "text": str(data.get("text", ""))}
        return True


def msgs(bot, chat=None):
    out = []
    for ep, d in bot.calls:
        if ep in ("sendMessage", "editMessageText") and (chat is None or d.get("chat_id", chat) == chat):
            out.append(d)
    return out


def last_text(bot, chat=None):
    m = msgs(bot, chat)
    return m[-1]["text"] if m else ""


def last_buttons(bot):
    for ep, d in reversed(bot.calls):
        rm = d.get("reply_markup")
        if isinstance(rm, InlineKeyboardMarkup):
            return [b.callback_data for row in rm.inline_keyboard for b in row]
    return []


@pytest.fixture
def env(tmp_path):
    handlers.STORE = Store(str(tmp_path / "t.db"), Crypto(b"k" * 32))
    bot = FakeBot(token="123:ABC")
    app = Application.builder().bot(bot).build()
    app_main.register(app)
    asyncio.run(app.initialize())
    return app, bot


def run(app, upd):
    asyncio.run(app.process_update(Update.de_json(upd, app.bot)))


def user(uid, name):
    return {"id": uid, "is_bot": False, "first_name": name}


def text(app, uid, txt, name="Sara"):
    m = {"message_id": next(_ids), "date": int(time.time()),
         "chat": {"id": uid, "type": "private"}, "from": user(uid, name), "text": txt}
    if txt.startswith("/"):
        m["entities"] = [{"type": "bot_command", "offset": 0, "length": len(txt.split()[0])}]
    run(app, {"update_id": next(_ids), "message": m})


def tap(app, uid, data, name="Sara"):
    run(app, {"update_id": next(_ids), "callback_query": {
        "id": str(next(_ids)), "from": user(uid, name), "chat_instance": "x", "data": data,
        "message": {"message_id": next(_ids), "date": int(time.time()),
                    "chat": {"id": uid, "type": "private"}, "from": user(999, "Luna"),
                    "text": "old"}}})


def onboard(app, bot, lang="en", uid=OWNER):
    text(app, uid, "/start")
    tap(app, uid, f"lang:{lang}")
    tap(app, uid, "onb:go")
    tap(app, uid, "tz:onb:1")          # UAE
    tap(app, uid, "ol:y")              # last period started yesterday
    tap(app, uid, "oc:28")
    tap(app, uid, "op:5")
    tap(app, uid, "oa:later")


def test_onboarding_and_today(env):
    app, bot = env
    onboard(app, bot)
    u = handlers.S().get(OWNER)
    assert u.onboarded and u.tz == "Asia/Dubai" and u.data["cycle_hint"] == 28
    assert len(u.data["periods"]) == 1
    assert "Day 2 of your period" in last_text(bot)
    # main keyboard now shows "period ended" because the period is open
    text(app, OWNER, "🌸 Today")
    assert "Cycle day 2" in last_text(bot)
    errors = [d for ep, d in bot.calls if ep == "sendMessage" and "error" in str(d.get("text", "")).lower()]
    assert not errors


def test_no_slash_commands_needed(env):
    app, bot = env
    onboard(app, bot)
    text(app, OWNER, "hello")
    assert "tap a button below" in last_text(bot).lower()


def test_persian_onboarding(env):
    app, bot = env
    onboard(app, bot, "fa")
    text(app, OWNER, "🌸 امروز")
    out = last_text(bot)
    assert "روز ۲ پریودت" in out and out.startswith("‏")


def test_end_period_and_log(env):
    app, bot = env
    onboard(app, bot)
    text(app, OWNER, "✅ My period ended")
    tap(app, OWNER, "pe:t")
    assert "It lasted 2 days" in " ".join(m["text"] for m in msgs(bot))
    u = handlers.S().get(OWNER)
    day = dates.ymd(handlers.today_for(u))
    tap(app, OWNER, f"lg:{day}:sym:cramps")
    tap(app, OWNER, f"lg:{day}:mood:irritable")
    tap(app, OWNER, f"lg:{day}:mood:irritable")   # toggle off
    tap(app, OWNER, f"lg:{day}:done")
    assert "Cramps" in last_text(bot) and "heat on the belly" in last_text(bot)
    u = handlers.S().get(OWNER)
    assert u.data["logs"][handlers.today_for(u).isoformat()] == {"sym": ["cramps"]}


def test_past_periods_calendar(env):
    app, bot = env
    onboard(app, bot)
    u = handlers.S().get(OWNER)
    today = handlers.today_for(u)
    for back in (29, 57, 85):
        tap(app, OWNER, f"cal:past:d:{dates.ymd(today - timedelta(days=back))}")
    tap(app, OWNER, f"cal:past:d:{dates.ymd(today - timedelta(days=60))}")   # too close, rejected
    u = handlers.S().get(OWNER)
    assert len(u.data["periods"]) == 4
    tap(app, OWNER, f"cal:past:d:{dates.ymd(today - timedelta(days=85))}")   # remove
    assert len(handlers.S().get(OWNER).data["periods"]) == 3
    tap(app, OWNER, f"cal:past:d:{dates.ymd(today + timedelta(days=3))}")    # future rejected
    assert len(handlers.S().get(OWNER).data["periods"]) == 3
    text(app, OWNER, "📊 Stats")
    out = last_text(bot)
    assert "Periods logged: <b>3</b>" in out and "Average cycle" in out


def make_partner(app, bot):
    onboard(app, bot)
    text(app, OWNER, "💞 Partner")
    tap(app, OWNER, "pt:flag:mood")       # turn mood sharing on before inviting
    tap(app, OWNER, "pt:create")
    link_text = last_text(bot)
    token = link_text.split("start=inv_")[1].split()[0]
    text(app, PARTNER, f"/start inv_{token}", name="Ali")
    tap(app, PARTNER, f"pl:{token}:en", name="Ali")
    assert "invited you" in last_text(bot)
    tap(app, PARTNER, f"inv:a:{token}", name="Ali")
    return token


def test_partner_invite_and_views(env):
    app, bot = env
    token = make_partner(app, bot)
    link = handlers.S().link_by_owner(OWNER)
    assert link and link.partner_id == PARTNER and link.flags["mood"] is True
    assert any("Ali accepted" in m["text"] for m in msgs(bot))
    # link is single use
    text(app, STRANGER, f"/start inv_{token}", name="Eve")
    tap(app, STRANGER, f"pl:{token}:en", name="Eve")
    assert "expired or was already used" in last_text(bot)
    # partner sees derived info only
    text(app, PARTNER, "🌸 How she's doing", name="Ali")
    out = last_text(bot)
    assert "Sara today" in out and "day 2 of her period" in out
    # owner logs a mood, partner sees it because mood flag is on
    u = handlers.S().get(OWNER)
    day = dates.ymd(handlers.today_for(u))
    tap(app, OWNER, f"lg:{day}:mood:sad")
    text(app, PARTNER, "🌸 How she's doing", name="Ali")
    assert "Sad" in last_text(bot)
    # owner turns mood off: partner no longer sees it
    tap(app, OWNER, "pt:flag:mood")
    text(app, PARTNER, "🌸 How she's doing", name="Ali")
    assert "Sad" not in last_text(bot)
    text(app, PARTNER, "📅 What's coming", name="Ali")
    assert "Next period" in last_text(bot)
    # nudge
    tap(app, OWNER, "nd:hug")
    assert "I could use a hug" in last_text(bot, PARTNER)


def test_partner_start_alert(env):
    app, bot = env
    make_partner(app, bot)
    u = handlers.S().get(OWNER)
    # replace history so a new period can start today
    today = handlers.today_for(u)
    u.data["periods"] = [{"s": (today - timedelta(days=28)).isoformat(),
                          "e": (today - timedelta(days=24)).isoformat()}]
    handlers.S().save(u)
    text(app, OWNER, "🩸 My period started")
    tap(app, OWNER, "ps:t")
    assert any("period started today" in m["text"] for m in msgs(bot, PARTNER))
    assert "partner got a short note" in last_text(bot, OWNER)


def test_stranger_cannot_reach_owner_data(env):
    app, bot = env
    onboard(app, bot)
    text(app, STRANGER, "/start", name="Eve")
    tap(app, STRANGER, "lang:en", name="Eve")
    # crafted callbacks from a stranger act only on the stranger's own (empty) account
    tap(app, STRANGER, "pt:stop!", name="Eve")
    tap(app, STRANGER, "nd:hug", name="Eve")
    tap(app, STRANGER, "rv:p_late:3", name="Eve")
    assert handlers.S().get(OWNER).data["periods"]
    assert all(d.get("chat_id") != OWNER for ep, d in bot.calls[-6:] if ep == "sendMessage")


def test_late_alert_reaches_both_and_discreet(env):
    app, bot = env
    make_partner(app, bot)
    owner = handlers.S().get(OWNER)
    today = handlers.today_for(owner)
    k = 4                                         # 1 cycle logged: margin 3, first alert on day 4
    start = today - timedelta(days=28 + k)
    owner.data["periods"] = [{"s": (start - timedelta(days=28)).isoformat(), "e": None},
                             {"s": start.isoformat(), "e": (start + timedelta(days=4)).isoformat()}]
    handlers.S().save(owner)
    ev = notify.her_events(owner, today)
    assert any(e[1] == "late" for e in ev)
    link = handlers.S().link_by_owner(OWNER)
    pev = notify.partner_events(owner, link.flags, today)
    assert any(e[1] == "p_late" for e in pev)
    # make both "due" this hour and run the job
    from datetime import datetime
    from zoneinfo import ZoneInfo
    for uid in (OWNER, PARTNER):
        x = handlers.S().get(uid)
        x.notify_hour = datetime.now(ZoneInfo(x.tz)).hour
        x.discreet = uid == PARTNER
        handlers.S().save(x)

    class Ctx:
        pass
    ctx = Ctx()
    ctx.bot = bot
    asyncio.run(notify.tick(ctx))
    assert "later than expected" in last_text(bot, OWNER)
    assert "new note from Luna" in last_text(bot, PARTNER)     # discreet
    assert "rv:p_late" in " ".join(last_buttons(bot))
    tap(app, PARTNER, "rv:p_late:4", name="Ali")
    assert "later than expected" in last_text(bot, PARTNER)
    # job is idempotent within the cycle
    n = len(bot.calls)
    asyncio.run(notify.tick(ctx))
    assert len(bot.calls) == n


def test_stop_sharing_and_delete(env):
    app, bot = env
    make_partner(app, bot)
    tap(app, OWNER, "pt:stop!")
    assert handlers.S().link_by_owner(OWNER) is None
    assert handlers.S().get(PARTNER) is None          # partner row removed, nothing kept
    assert "stopped sharing" in last_text(bot, PARTNER)
    tap(app, OWNER, "st:export")
    assert any(ep == "sendDocument" for ep, _ in bot.calls)
    tap(app, OWNER, "del:yes")
    assert handlers.S().get(OWNER) is None


def test_settings_toggles(env):
    app, bot = env
    onboard(app, bot)
    tap(app, OWNER, "st:lang")
    assert handlers.S().get(OWNER).lang == "fa"
    tap(app, OWNER, "st:hour:21")
    tap(app, OWNER, "st:discreet")
    tap(app, OWNER, "st:cal")
    u = handlers.S().get(OWNER)
    assert u.notify_hour == 21 and u.discreet and u.cal == "g"
    text(app, OWNER, "⚙️ تنظیمات")
    assert "تنظیمات" in last_text(bot)


def test_privacy_screen(env):
    app, bot = env
    text(app, OWNER, "/start")
    tap(app, OWNER, "lang:en")
    assert "privacy:w" in last_buttons(bot)
    tap(app, OWNER, "privacy:w")
    out = last_text(bot)
    assert "AES" in out and "github.com/sahandsorouri/luna-period-bot" in out
    # the privacy page itself keeps a way forward and a way back
    assert last_buttons(bot) == ["ob:welcome", "onb:go"]
    tap(app, OWNER, "ob:welcome")
    assert "Hi, I'm Luna" in last_text(bot)


def test_onboarding_back_buttons(env):
    app, bot = env
    text(app, OWNER, "/start")
    tap(app, OWNER, "lang:en")
    tap(app, OWNER, "onb:go")
    assert "ob:welcome" in last_buttons(bot)
    tap(app, OWNER, "tz:onb:1")
    tap(app, OWNER, "ol:t")
    assert "ob:last" in last_buttons(bot)
    tap(app, OWNER, "ob:last")          # went back: the start picked is undone
    assert handlers.S().get(OWNER).data["periods"] == []
    tap(app, OWNER, "ol:y")
    assert len(handlers.S().get(OWNER).data["periods"]) == 1


def test_undo_start_and_end(env):
    app, bot = env
    make_partner(app, bot)
    u = handlers.S().get(OWNER)
    today = handlers.today_for(u)
    u.data["periods"] = [{"s": (today - timedelta(days=28)).isoformat(),
                          "e": (today - timedelta(days=24)).isoformat()}]
    handlers.S().save(u)
    tap(app, OWNER, "ps:t")
    assert any(b.startswith("un:s:") for b in last_buttons(bot))
    undo = [b for b in last_buttons(bot) if b.startswith("un:s:")][0]
    assert undo.endswith(":1")              # partner was told
    tap(app, OWNER, undo)
    assert len(handlers.S().get(OWNER).data["periods"]) == 1
    assert "didn't start after all" in last_text(bot, PARTNER)
    assert "Undone" in last_text(bot, OWNER)
    # end: log a start, end it, undo the end
    tap(app, OWNER, "ps:y")
    tap(app, OWNER, "pe:t")
    undo = [b for b in last_buttons(bot) if b.startswith("un:e:")][0]
    tap(app, OWNER, undo)
    assert handlers.S().get(OWNER).data["periods"][-1]["e"] is None


def test_calendar_switch_and_back(env):
    app, bot = env
    onboard(app, bot, "fa")
    u = handlers.S().get(OWNER)
    assert u.cal == "j"
    today = dates.ymd(handlers.today_for(u))
    tap(app, OWNER, "ps:pick")
    assert f"cal:start:sw:{today}" in last_buttons(bot)
    tap(app, OWNER, f"cal:start:sw:{today}")
    assert handlers.S().get(OWNER).cal == "g"
    tap(app, OWNER, "cal:start:x")          # back to the Today/Yesterday picker
    assert "ps:t" in last_buttons(bot) or "goend" in last_buttons(bot)


def test_menu_tap_deleted_and_old_screen_replaced(env):
    app, bot = env
    onboard(app, bot)
    n_del = sum(ep == "deleteMessage" for ep, _ in bot.calls)
    text(app, OWNER, "📊 Stats")
    text(app, OWNER, "⚙️ Settings")
    dels = [d for ep, d in bot.calls if ep == "deleteMessage"][n_del:]
    assert len(dels) >= 3      # two taps + the previous screen


def test_settings_show_data_based_lengths(env):
    app, bot = env
    onboard(app, bot)
    u = handlers.S().get(OWNER)
    today = handlers.today_for(u)
    u.data["periods"] = [{"s": (today - timedelta(days=d)).isoformat(),
                          "e": (today - timedelta(days=d - 3)).isoformat()} for d in (93, 62, 31)]
    u.data["cycle_hint"] = 35
    handlers.S().save(u)
    text(app, OWNER, "⚙️ Settings")
    rm = [d for ep, d in bot.calls if ep == "sendMessage"][-1]["reply_markup"]
    labels = [b.text for row in rm.inline_keyboard for b in row]
    assert any("31 days (from your data)" in x for x in labels)
    tap(app, OWNER, "st:cyclemenu")
    assert "your cycle is about <b>31 days</b>" in last_text(bot)
    assert handlers.status_of(handlers.S().get(OWNER)).cycle_len == 31   # data wins over the 35 hint


def test_nudge_unsend(env):
    app, bot = env
    make_partner(app, bot)
    tap(app, OWNER, "nd:hug")
    assert "ndu" in last_buttons(bot)
    tap(app, OWNER, "ndu")
    assert any(ep == "deleteMessage" and d.get("chat_id") == PARTNER for ep, d in bot.calls)
    assert "Unsent" in last_text(bot, OWNER)


def test_partner_help_has_back(env):
    app, bot = env
    make_partner(app, bot)
    text(app, PARTNER, "🌸 How she's doing", name="Ali")
    tap(app, PARTNER, "phelps", name="Ali")
    assert last_buttons(bot) == ["ptdy"]
    tap(app, PARTNER, "ptdy", name="Ali")
    assert "Sara today" in last_text(bot, PARTNER)
