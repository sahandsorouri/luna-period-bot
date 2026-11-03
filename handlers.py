"""All Telegram update handling. Tap driven: reply keyboard + inline buttons.

Privacy rule for this file: every handler loads ONLY the caller's own row
(update.effective_user.id). The one place another person's data is read is the
partner view, which goes through the active link and filters by its flags.
"""
from __future__ import annotations

import html
import io
import json
import logging
import re
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup as IKM
from telegram import ReplyKeyboardRemove, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, Forbidden
from telegram.ext import ContextTypes

import cycle
import dates
import keyboards as kb
from config import INVITE_TTL_HOURS, REPO_URL
from i18n import (LABEL_TO_ACTION, NUDGES, SYMPTOM_TIPS, TZS, days, flag_label, in_days,
                  item_label, opt, phase_desc, phase_name, t, tips)
from storage import DEFAULT_FLAGS, FLAG_KEYS, Store, User

log = logging.getLogger("luna")
HTML = ParseMode.HTML
STORE: Store | None = None   # set by main.py


def S() -> Store:
    assert STORE is not None
    return STORE


# ---------------------------------------------------------------- helpers

def today_for(u: User) -> date:
    return datetime.now(ZoneInfo(u.tz)).date()


def get_ps(u: User) -> list[cycle.Period]:
    return cycle.parse(u.data.get("periods", []))


def put_ps(u: User, ps: list[cycle.Period]) -> None:
    u.data["periods"] = cycle.dump(ps)


def status_of(u: User, day: date | None = None) -> cycle.Status:
    return cycle.status(get_ps(u), day or today_for(u),
                        u.data.get("cycle_hint"), u.data.get("period_hint"))


def name_of(u: User | None, lang: str) -> str:
    if u and u.data.get("name"):
        return html.escape(u.data["name"])
    return t(lang, "someone")


def fd(u: User, d: date, weekday: bool = False) -> str:
    return dates.fmt(d, u.lang, u.cal, weekday=weekday)


def menu_for(u: User):
    if u.role == "partner":
        return kb.partner_kb(u.lang)
    return kb.main_kb(u.lang, status_of(u).awaiting_end)


def touch_name(u: User, update: Update) -> None:
    n = (update.effective_user.first_name or "").strip()[:40]
    if n and u.data.get("name") != n:
        u.data["name"] = n


_ARABIC = re.compile(r"[\u0600-\u06FF]")


def rtl(text: str) -> str:
    """Persian text: start every line with a right-to-left mark, so a Latin name,
    number or link at the start of a line can't flip it to left-to-right."""
    if not _ARABIC.search(text or ""):
        return text
    return "\n".join(line if line.startswith("\u200f") else "\u200f" + line
                     for line in text.split("\n"))


async def send(bot, chat_id: int, text: str, markup=None):
    """Returns the sent Message, or None."""
    text = rtl(text)
    try:
        return await bot.send_message(chat_id, text, parse_mode=HTML, reply_markup=markup,
                                      disable_web_page_preview=True)
    except (Forbidden, BadRequest) as e:
        log.info("send failed: %s", type(e).__name__)
        return None


async def drop(bot, chat_id: int, message_id: int) -> None:
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:  # too old, already gone: fine
        pass


async def screen(context, chat: int, text: str, markup=None, bot=None):
    """Send a view (Today, Stats, Settings...) and remove the previous view,
    so the chat shows one live screen instead of a pile of old ones.
    Confirmations and reminders are never removed (see keep())."""
    bot = bot or context.bot
    ud = context.user_data if context is not None else None
    m = await send(bot, chat, text, markup)
    # the new screen must arrive first; only then the old one goes
    if m is not None and ud is not None:
        prev = ud.get("screen")
        ud["screen"] = m.message_id
        if prev:
            await drop(bot, chat, prev)
    return m


def keep(context, q) -> None:
    """This message turned into a record (a logged period, a saved log). Never auto-remove it."""
    if context is not None and q.message is not None and \
            context.user_data.get("screen") == q.message.message_id:
        context.user_data.pop("screen", None)


async def edit(q, text: str, markup=None) -> None:
    text = rtl(text)
    try:
        await q.edit_message_text(text, parse_mode=HTML, reply_markup=markup,
                                  disable_web_page_preview=True)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


async def edit_markup(q, markup) -> None:
    try:
        await q.edit_message_reply_markup(markup)
    except BadRequest as e:
        if "not modified" not in str(e).lower():
            raise


def welcome_kb(lang: str) -> IKM:
    return IKM([[B(t(lang, "btn_privacy"), callback_data="privacy:w")],
                [B(t(lang, "btn_continue"), callback_data="onb:go")]])


def privacy_text(lang: str) -> str:
    return t(lang, "privacy", repo=REPO_URL)


# ---------------------------------------------------------------- entry points

async def on_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    uid = update.effective_user.id
    payload = context.args[0] if context.args else ""
    u = S().get(uid)
    if payload.startswith("inv_"):
        token = payload[4:]
        if u is None:
            await update.message.reply_text(t("en", "lang_pick"),
                                            reply_markup=kb.lang_kb(f"pl:{token}"))
            return
        await show_invite(update, context, u, token)
        return
    if u is None:
        await update.message.reply_text(t("en", "lang_pick"), reply_markup=kb.lang_kb())
        return
    await resume(update, context, u)


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_chat.type != "private":
        return
    uid = update.effective_user.id
    u = S().get(uid)
    if u is None:
        await update.message.reply_text(t("en", "lang_pick"), reply_markup=kb.lang_kb())
        return
    if not u.onboarded:
        await resume(update, context, u)
        return
    touch_name(u, update)
    S().save(u)
    action = LABEL_TO_ACTION.get((update.message.text or "").strip())
    if u.role == "partner":
        fn = {"p_today": partner_today, "p_coming": partner_coming,
              "p_help": partner_help, "settings": show_settings}.get(action)
    else:
        fn = {"start": ask_start, "end": ask_end, "today": show_today, "log": show_log_today,
              "calendar": show_calendar, "stats": show_stats, "partner": show_partner,
              "settings": show_settings}.get(action)
    if fn is None:
        await update.message.reply_text(t(u.lang, "use_buttons"), reply_markup=menu_for(u))
        return
    await fn(update.message.chat_id, context, u)
    try:
        await update.message.delete()   # after the reply is there, her button tap is just noise
    except Exception:
        pass


async def resume(update: Update, context, u: User) -> None:
    """Re-show where she left off in onboarding, or the main menu."""
    chat = update.effective_chat.id
    if u.onboarded:
        await send(context.bot, chat, t(u.lang, "onb_done"), menu_for(u))
        return
    step = u.data.get("onb", "welcome")
    await onb_step(context.bot, chat, u, step)


def onb_view(u: User, step: str) -> tuple[str, IKM]:
    L = u.lang
    if step == "tz":
        return t(L, "ask_tz"), kb.tz_kb(L, "onb", back="ob:welcome")
    if step == "last":
        return t(L, "ask_last"), kb.when_kb(
            L, "ol", [[B(t(L, "btn_dont_remember"), callback_data="ol:skip")]], back="ob:tz")
    if step == "cycle":
        return t(L, "ask_cycle"), kb.choice_kb(L, "oc", [24, 26, 28, 30, 32, 35], back="ob:last")
    if step == "plen":
        return t(L, "ask_plen"), kb.choice_kb(L, "op", [3, 4, 5, 6, 7, 8], per_row=3, back="ob:cycle")
    if step == "past":
        return t(L, "ask_past"), IKM([[B(t(L, "btn_add_past"), callback_data="oa:add")],
                                      [B(t(L, "btn_later"), callback_data="oa:later")]]
                                     + kb.back_row(L, "ob:plen"))
    return t(L, "welcome"), welcome_kb(L)


async def onb_step(bot, chat: int, u: User, step: str) -> None:
    text, markup = onb_view(u, step)
    await send(bot, chat, text, markup)


async def finish_onboarding(bot, chat: int, u: User, open_calendar: bool, context=None) -> None:
    u.onboarded = True
    u.data.pop("onb", None)
    S().save(u)
    await send(bot, chat, t(u.lang, "onb_done"), menu_for(u))
    if open_calendar:
        await show_calendar(chat, context, u, bot=bot)
    else:
        await show_today(chat, context, u, bot=bot)


# ---------------------------------------------------------------- tracker screens

def today_view(u: User) -> tuple[str, IKM]:
    s = status_of(u)
    L = u.lang
    lines = [t(L, "today_title", d=fd(u, s.today, weekday=True)), ""]
    if not s.has_data or s.stale:
        lines.append(t(L, "no_data" if not s.has_data else "stale"))
        return "\n".join(lines), kb.today_kb(L, add_past=True)
    if s.in_period:
        lines.append(t(L, "period_day", n=s.period_day))
    lines.append(t(L, "cycle_day", n=s.cycle_day))
    lines.append(t(L, "phase_line", p=phase_name(L, s.phase), desc=phase_desc(L, s.phase)))
    lines.append("")
    if s.days_until > 0:
        lines.append(t(L, "next_line", d=fd(u, s.next_start), rel=in_days(L, s.days_until)))
    elif s.days_until == 0:
        lines.append(t(L, "due_line"))
    else:
        lines.append(t(L, "late_line", n=days(L, s.days_late)))
        if s.days_late <= s.margin:
            lines.append(t(L, "late_normal"))
    if u.show_fertile and s.days_until > 0 and s.today <= s.fertile_end and not s.in_period:
        lines.append(t(L, "fertile_line", a=fd(u, s.fertile_start), b=fd(u, s.fertile_end)))
    n_cycles = len(cycle.usable(get_ps(u))[-6:])
    if s.quality == "good":
        lines += ["", t(L, "based_on", n=n_cycles)]
    else:
        lines += ["", t(L, f"q_{s.quality}")]
    return "\n".join(lines), kb.today_kb(L, add_past=len(get_ps(u)) < 3)


async def show_today(chat: int, context, u: User, bot=None) -> None:
    text, markup = today_view(u)
    await screen(context, chat, text, markup, bot=bot)


def helps_text(u: User) -> str:
    s = status_of(u)
    L = u.lang
    ph = s.phase if s.has_data and not s.stale else "follicular"
    out = [t(L, "helps_title", p=phase_name(L, ph)), "", tips(L, ph)]
    entry = u.data.get("logs", {}).get(today_for(u).isoformat(), {})
    sym = [k for k in entry.get("sym", []) if k in SYMPTOM_TIPS]
    if sym:
        out.append("")
        out += ["• " + SYMPTOM_TIPS[k][1 if L == "fa" else 0] for k in sym]
    out += ["", t(L, "red_flags")]
    return "\n".join(out)


def start_view(u: User) -> tuple[str, IKM]:
    L = u.lang
    s = status_of(u)
    if s.awaiting_end:
        return (t(L, "already_started", d=fd(u, s.last_start)),
                IKM([[B(t(L, "btn_it_ended"), callback_data="goend")],
                     [B(t(L, "btn_remove_start"), callback_data=f"un:s:{dates.ymd(s.last_start)}:0")],
                     [B(t(L, "cancel"), callback_data="close")]]))
    return t(L, "ask_start"), kb.when_kb(L, "ps", cancel=True)


def end_view(u: User) -> tuple[str, IKM]:
    L = u.lang
    if not status_of(u).awaiting_end:
        return t(L, "no_open"), IKM([[B(t(L, "btn_log_start"), callback_data="gostart")],
                                     [B(t(L, "cancel"), callback_data="close")]])
    return t(L, "ask_end"), kb.when_kb(L, "pe", cancel=True)


async def ask_start(chat: int, context, u: User) -> None:
    await screen(context, chat, *start_view(u))


async def ask_end(chat: int, context, u: User) -> None:
    await screen(context, chat, *end_view(u))


def calendar_marks(u: User, today: date) -> dict[date, str]:
    ps = get_ps(u)
    marks = {d: "•" for d in cycle.period_days(ps, u.data.get("period_hint"), today)}
    for p in ps:
        marks[p.start] = "🩸"
    s = status_of(u)
    if s.has_data and not s.stale and s.next_start and s.next_start > today:
        marks[s.next_start] = "✨"
    return marks


def calendar_view(u: User, anchor: date | None = None) -> tuple[str, IKM]:
    today = today_for(u)
    return t(u.lang, "cal_past"), kb.calendar_kb(u.lang, u.cal, "past", anchor or today, today,
                                                calendar_marks(u, today), True)


async def show_calendar(chat: int, context, u: User, bot=None) -> None:
    await screen(context, chat, *calendar_view(u), bot=bot)


async def show_log_today(chat: int, context, u: User) -> None:
    day = today_for(u)
    await screen(context, chat, log_text(u, day), log_markup(u, day))


def log_text(u: User, day: date) -> str:
    return t(u.lang, "log_title", d=fd(u, day, weekday=True))


def log_markup(u: User, day: date) -> IKM:
    entry = u.data.get("logs", {}).get(day.isoformat(), {})
    s = status_of(u, day)
    show_flow = s.in_period or s.phase in ("due", "late", "pms") or "flow" in entry
    return kb.log_kb(u.lang, day, entry, show_flow, S().link_by_owner(u.id) is not None)


def entry_items(u: User, entry: dict, lang: str) -> list[str]:
    items = []
    if entry.get("flow"):
        items.append(opt(lang, "flow", entry["flow"]))
    items += [item_label(lang, k) for k in entry.get("mood", []) + entry.get("sym", [])]
    if entry.get("energy"):
        items.append(opt(lang, "energy", entry["energy"]))
    return items


async def show_stats(chat: int, context, u: User) -> None:
    L = u.lang
    ps = get_ps(u)
    st = cycle.stats(ps, u.data.get("period_hint"))
    if len(ps) < 2:
        await screen(context, chat, t(L, "stats_none"),
                     IKM([[B(t(L, "btn_add_past"), callback_data="opencal")]]))
        return
    out = [t(L, "stats_title"), "", t(L, "st_periods", n=st.periods)]
    if st.avg_cycle:
        out.append(t(L, "st_cycle", a=days(L, st.avg_cycle), mn=days(L, st.min_cycle),
                     mx=days(L, st.max_cycle)))
    if st.avg_period:
        out.append(t(L, "st_period", a=days(L, st.avg_period)))
    if st.regularity:
        out.append(t(L, f"st_reg_{st.regularity}", s=days(L, st.spread)))
    else:
        out.append(t(L, "st_reg_none"))
    s = status_of(u)
    if s.has_data and not s.stale and s.days_until >= 0:
        out.append(t(L, "st_next", d=fd(u, s.next_start)))
    if st.recent:
        out += ["", t(L, "st_recent")]
        top = max(n for _, n in st.recent)
        for start, n in st.recent:
            bar = "▇" * max(1, round(10 * n / top))
            out.append(f"{fd(u, start)}  {bar} {dates.num(L, n)}")
    logs = u.data.get("logs", {})
    c = cycle.symptom_counts(logs, today_for(u))
    if c:
        items = "، ".join if L == "fa" else ", ".join
        out += ["", t(L, "st_top", items=items(f"{item_label(L, k)} ({dates.num(L, n)})"
                                               for k, n in c.most_common(4)))]
    pc = cycle.pms_counts(logs, ps)
    if pc:
        items = "، ".join if L == "fa" else ", ".join
        out += ["", t(L, "st_pms", items=items(item_label(L, k) for k, _ in pc.most_common(3)))]
    if st.flags:
        out += [""] + [t(L, f"flag_{f}") for f in st.flags]
    await screen(context, chat, "\n".join(out))


# ---------------------------------------------------------------- partner (owner side)

def flags_view(u: User) -> tuple[str, IKM]:
    L = u.lang
    link = S().link_by_owner(u.id)
    if link:
        p = S().get(link.partner_id)
        return (t(L, "pt_linked", name=name_of(p, L)),
                kb.flags_kb(L, link.flags, True, False))
    flags = u.data.get("invite_flags") or dict(DEFAULT_FLAGS)
    text = t(L, "pt_intro")
    return text, kb.flags_kb(L, flags, False, S().has_invite(u.id))


async def show_partner(chat: int, context, u: User) -> None:
    text, markup = flags_view(u)
    await screen(context, chat, text, markup)


def shared_list(lang: str, flags: dict) -> str:
    return "\n".join(f"• {flag_label(lang, k)}" for k in FLAG_KEYS if flags.get(k))


# ---------------------------------------------------------------- partner (partner side)

def partner_ctx(u: User):
    link = S().link_by_partner(u.id)
    if not link:
        return None, None
    owner = S().get(link.owner_id)
    if not owner:
        return None, None
    return link, owner


async def lost_access(chat: int, bot, u: User) -> None:
    S().delete(u.id)
    await send(bot, chat, t(u.lang, "partner_restart"), ReplyKeyboardRemove())


def partner_today_view(u: User):
    link, owner = partner_ctx(u)
    if not link:
        return None
    L = u.lang
    f = link.flags
    s = status_of(owner)
    out = [t(L, "p_today_title", name=name_of(owner, L)), ""]
    shown = False
    if s.has_data and not s.stale:
        if f.get("phase"):
            if s.in_period:
                out.append(t(L, "p_period_day", n=s.period_day))
            out.append(t(L, "p_phase", p=phase_name(L, s.phase), desc=phase_desc(L, s.phase)))
            if s.days_until > 0:
                out.append(t(L, "p_next", d=fd(u, s.next_start), rel=in_days(L, s.days_until)))
            shown = True
        if f.get("late") and s.days_late > 0 and not s.in_period:
            out.append(t(L, "p_late", n=days(L, s.days_late)))
            shown = True
    if f.get("mood"):
        entry = owner.data.get("logs", {}).get(today_for(owner).isoformat())
        if entry:
            sep = "، " if L == "fa" else ", "
            out += ["", t(L, "p_mood", items=sep.join(entry_items(owner, entry, L)))]
            shown = True
    if not shown:
        out.append(t(L, "p_nothing"))
    return "\n".join(out), IKM([[B(t(L, "btn_helps"), callback_data="phelps")]])


async def partner_today(chat: int, context, u: User) -> None:
    view = partner_today_view(u)
    if view is None:
        return await lost_access(chat, context.bot, u)
    await screen(context, chat, *view)


async def partner_coming(chat: int, context, u: User) -> None:
    link, owner = partner_ctx(u)
    if not link:
        return await lost_access(chat, context.bot, u)
    L = u.lang
    f = link.flags
    s = status_of(owner)
    out = [t(L, "p_coming_title"), ""]
    if not s.has_data or s.stale:
        out.append(t(L, "p_no_data"))
    else:
        today = today_for(owner)
        any_line = False
        if f.get("pms") and s.pms_start > today:
            out.append(t(L, "p_c_pms", d=fd(u, s.pms_start), rel=in_days(L, (s.pms_start - today).days)))
            any_line = True
        if f.get("phase") and s.days_until > 0:
            out.append(t(L, "p_c_period", d=fd(u, s.next_start), rel=in_days(L, s.days_until)))
            any_line = True
        if f.get("fertile") and s.days_until > 0 and today <= s.fertile_end:
            out.append(t(L, "p_c_fertile", a=fd(u, s.fertile_start), b=fd(u, s.fertile_end)))
            any_line = True
        if f.get("late") and s.days_late > 0 and not s.in_period:
            out.append(t(L, "p_late", n=days(L, s.days_late)))
            any_line = True
        if not any_line:
            out.append(t(L, "p_nothing"))
    await screen(context, chat, "\n".join(out))


def partner_help_text(u: User, owner: User, flags: dict) -> str:
    L = u.lang
    s = status_of(owner)
    ph = s.phase if (flags.get("phase") and s.has_data and not s.stale) else None
    if ph is None:
        # without the phase flag, give the general list
        body = tips(L, "pms", "partner") + "\n" + tips(L, "period", "partner")
        return "\n".join([t(L, "helps_partner_title", p="💞"), "", body, "", t(L, "partner_footer")])
    return "\n".join([t(L, "helps_partner_title", p=phase_name(L, ph)), "",
                      tips(L, ph, "partner"), "", t(L, "partner_footer")])


async def partner_help(chat: int, context, u: User) -> None:
    link, owner = partner_ctx(u)
    if not link:
        return await lost_access(chat, context.bot, u)
    await screen(context, chat, partner_help_text(u, owner, link.flags))


def landing_view(u: User, token: str) -> tuple[str, IKM | None]:
    L = u.lang
    inv = S().peek_invite(token)
    if not inv:
        return t(L, "inv_invalid"), None
    owner_id, flags = inv
    if owner_id == u.id:
        return t(L, "inv_self"), None
    if u.role == "tracker" and (u.onboarded or u.data.get("periods")):
        return t(L, "inv_is_tracker"), None
    other = S().link_by_partner(u.id)
    if other and other.owner_id != owner_id:
        return t(L, "inv_has_other"), None
    owner = S().get(owner_id)
    return (t(L, "inv_landing", name=name_of(owner, L), items=shared_list(L, flags)),
            IKM([kb._rtl(L, [B(t(L, "btn_accept"), callback_data=f"inv:a:{token}"),
                             B(t(L, "btn_decline"), callback_data=f"inv:d:{token}")]),
                 [B(t(L, "btn_privacy"), callback_data=f"privacy:i:{token}")]]))


async def show_invite(update: Update, context, u: User, token: str) -> None:
    text, markup = landing_view(u, token)
    await send(context.bot, update.effective_chat.id, text, markup)


# ---------------------------------------------------------------- settings

def settings_view(u: User) -> tuple[str, IKM]:
    L = u.lang
    onoff = lambda v: t(L, "on" if v else "off")  # noqa: E731
    rows = [[B(t(L, "s_lang"), callback_data="st:lang")],
            [B(t(L, "s_cal_j" if u.cal == "j" else "s_cal_g"), callback_data="st:cal")],
            [B(t(L, "s_hour", h=u.notify_hour), callback_data="st:hourmenu")],
            [B(t(L, "s_tz", z=tz_short(u)), callback_data="st:tzmenu")],
            [B(t(L, "s_discreet", v=onoff(u.discreet)), callback_data="st:discreet")]]
    if u.role == "partner":
        rows.append([B(t(L, "s_leave"), callback_data="st:leave")])
    else:
        rows += [[B(t(L, "s_daily", v=onoff(u.daily_reminder)), callback_data="st:daily")],
                 [B(t(L, "s_fertile", v=onoff(u.show_fertile)), callback_data="st:fertile")],
                 [B(cycle_label(u), callback_data="st:cyclemenu")],
                 [B(plen_label(u), callback_data="st:plenmenu")],
                 [B(t(L, "s_export"), callback_data="st:export")]]
    rows.append([B(t(L, "btn_privacy"), callback_data="privacy:s")])
    rows.append([B(t(L, "s_delete"), callback_data="st:delete")])
    return t(L, "settings_title"), IKM(rows)


def data_cycle(u: User) -> int | None:
    ps = get_ps(u)
    return cycle.est_cycle(ps, None)[0] if cycle.usable(ps) else None


def data_plen(u: User) -> int | None:
    ps = get_ps(u)
    return cycle.est_period(ps, None) if cycle.period_lengths(ps) else None


def cycle_label(u: User) -> str:
    n = data_cycle(u)
    if n:
        return t(u.lang, "s_cycle_data", n=days(u.lang, n))
    return t(u.lang, "s_cycle", n=days(u.lang, u.data.get("cycle_hint") or 28))


def plen_label(u: User) -> str:
    n = data_plen(u)
    if n:
        return t(u.lang, "s_plen_data", n=days(u.lang, n))
    return t(u.lang, "s_plen", n=days(u.lang, u.data.get("period_hint") or 5))


def tz_short(u: User) -> str:
    from i18n import tz_label
    return tz_label(u.lang, u.tz)


async def show_settings(chat: int, context, u: User) -> None:
    text, markup = settings_view(u)
    await screen(context, chat, text, markup)


# ---------------------------------------------------------------- notifications (shared with notify.py)

def partner_note(owner: User, partner: User, event: str, k: int = 0) -> str:
    L = partner.lang
    s = status_of(owner)
    name = name_of(owner, L)
    if event == "p_pms":
        return t(L, "np_pms", name=name) + "\n\n" + tips(L, "pms", "partner")
    if event == "p_soon":
        return t(L, "np_soon", name=name) + "\n\n" + tips(L, "period", "partner")
    if event == "p_start":
        d = s.last_start or today_for(owner)
        rel = t(L, "today_word") if d == today_for(owner) else fd(partner, d)
        return t(L, "np_start", name=name, d=rel) + "\n\n" + tips(L, "period", "partner")
    if event == "p_late":
        return t(L, "np_late", name=name, n=days(L, max(k, s.days_late))) + "\n\n" + tips(L, "late", "partner")
    return ""


def her_note(u: User, event: str, k: int = 0) -> tuple[str, IKM | None]:
    L = u.lang
    s = status_of(u)
    if event == "soon":
        return t(L, "n_soon", d=fd(u, s.next_start)), None
    if event == "due":
        return t(L, "n_due"), IKM([kb._rtl(L, [B(t(L, "btn_yes_started"), callback_data="ps:t"),
                                              B(t(L, "btn_not_yet"), callback_data="due:no")])])
    if event == "late":
        return (t(L, "n_late", n=days(L, max(k, s.days_late))) + "\n\n" + tips(L, "late"),
                IKM([[B(t(L, "btn_yes_started"), callback_data="ps:pick")]]))
    if event == "endq":
        return t(L, "n_endq"), IKM([kb._rtl(L, [B(t(L, "btn_ended_today"), callback_data="pe:t"),
                                               B(t(L, "btn_ended_yesterday"), callback_data="pe:y")]),
                                    [B(t(L, "btn_not_yet"), callback_data="endq:no")]])
    if event == "pms":
        return t(L, "n_pms") + "\n\n" + tips(L, "pms"), None
    if event == "fertile":
        return t(L, "n_fertile"), None
    if event == "daily":
        return t(L, "n_daily"), IKM([[B(t(L, "btn_log"), callback_data="lgnow")]])
    return "", None


async def deliver(bot, receiver: User, text: str, markup, event: str, k: int = 0) -> bool:
    """Send a reminder, hidden behind a Show button in discreet mode."""
    if receiver.discreet:
        return await send(bot, receiver.id, t(receiver.lang, "n_discreet"),
                          IKM([[B(t(receiver.lang, "btn_show"), callback_data=f"rv:{event}:{k}")]]))
    return await send(bot, receiver.id, text, markup)


async def notify_partner_start(bot, owner: User) -> bool:
    link = S().link_by_owner(owner.id)
    if not link or not link.flags.get("start"):
        return False
    s = status_of(owner)
    if not s.last_start or (today_for(owner) - s.last_start).days > 1:
        return False
    partner = S().get(link.partner_id)
    if not partner:
        return False
    return await deliver(bot, partner, partner_note(owner, partner, "p_start"), None, "p_start")


# ---------------------------------------------------------------- callbacks

async def on_cb(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    q = update.callback_query
    data = q.data or ""
    uid = q.from_user.id
    chat = q.message.chat_id if q.message else uid
    parts = data.split(":")
    head = parts[0]
    bot = context.bot

    if data == "noop":
        await q.answer()
        return

    # language choice before an account exists
    if head == "lang":
        u = S().get(uid)
        lang = parts[1] if parts[1] in ("en", "fa") else "en"
        if u is None:
            u = S().create(uid, lang)
            u.data["name"] = (q.from_user.first_name or "")[:40]
            u.data["onb"] = "welcome"
            S().save(u)
            await q.answer()
            await edit(q, t(lang, "welcome"),
                       welcome_kb(lang))
        else:
            u.lang = lang
            u.cal = "j" if lang == "fa" else "g"
            S().save(u)
            await q.answer()
            await edit(q, t(lang, "saved"))
            await send(bot, chat, t(lang, "onb_done") if u.onboarded else t(lang, "saved"),
                       menu_for(u) if u.onboarded else None)
            if not u.onboarded:
                await onb_step(bot, chat, u, u.data.get("onb", "welcome"))
        return

    if head == "pl":   # partner arriving with an invite, picks language
        token, lang = parts[1], parts[2]
        u = S().get(uid)
        if u is None:
            u = S().create(uid, lang if lang in ("en", "fa") else "en", role="partner")
            u.data["name"] = (q.from_user.first_name or "")[:40]
            S().save(u)
        await q.answer()
        await edit(q, t(u.lang, "saved"))
        await show_invite(update, context, u, token)
        return

    u = S().get(uid)
    if u is None:
        await q.answer()
        await send(bot, chat, t("en", "lang_pick"), kb.lang_kb())
        return
    L = u.lang

    if head == "close":
        await q.answer()
        keep(context, q)
        try:
            await q.message.delete()
        except Exception:
            await edit(q, t(L, "cancel"))
        return

    if head == "privacy":
        await q.answer()
        where = parts[1] if len(parts) > 1 else ""
        if where == "w":
            back, extra = "ob:welcome", [[B(t(L, "btn_continue"), callback_data="onb:go")]]
        elif where == "s":
            back, extra = "st:menu", []
        elif where == "i":
            back, extra = f"inv:v:{parts[2]}", []
        else:
            back, extra = None, []
        await edit(q, privacy_text(L), IKM(kb.back_row(L, back) + extra) if (back or extra) else None)
        return

    if head == "ob":   # onboarding back button
        step = parts[1]
        if step == "last":
            u.data["periods"] = []      # the start picked on this step is undone
        u.data["onb"] = step
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, step))
        return

    if head == "tdy":
        await q.answer()
        await edit(q, *today_view(u))
        return
    if head == "opencal":
        await q.answer()
        await edit(q, *calendar_view(u))
        return
    if head == "gostart":
        await q.answer()
        await edit(q, *start_view(u))
        return
    if head == "goend":
        await q.answer()
        await edit(q, *end_view(u))
        return
    if head == "un":
        await handle_undo(q, context, u, parts[1], dates.parse_ymd(parts[2]),
                          parts[3] if len(parts) > 3 else "0")
        return
    if head == "lgd":
        d = dates.parse_ymd(parts[1])
        await q.answer()
        await edit(q, log_text(u, d), log_markup(u, d))
        return
    if head == "ndu":
        await handle_unsend(q, context, u)
        return

    if head == "inv":
        if parts[1] == "v":
            await q.answer()
            await edit(q, *landing_view(u, parts[2]))
            return
        await handle_invite(q, context, u, parts[1], parts[2])
        return

    # ---------- onboarding
    if head == "onb":
        u.data["onb"] = "tz"
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, "tz"))
        return
    if head == "tz":
        ctx, idx = parts[1], int(parts[2])
        u.tz = TZS[idx][0] if 0 <= idx < len(TZS) else "UTC"
        if ctx == "onb":
            u.data["onb"] = "last"
            S().save(u)
            await q.answer()
            await edit(q, *onb_view(u, "last"))
        else:
            S().save(u)
            await q.answer(t(L, "saved"))
            text, markup = settings_view(u)
            await edit(q, text, markup)
        return
    if head == "ol":
        today = today_for(u)
        if parts[1] == "pick":
            await q.answer()
            await edit(q, t(L, "cal_start"), kb.calendar_kb(L, u.cal, "onb", today, today))
            return
        if parts[1] in ("t", "y"):
            ps = []                     # onboarding sets exactly one start, picking again replaces it
            cycle.add_start(ps, today - timedelta(days=0 if parts[1] == "t" else 1))
            put_ps(u, ps)
        u.data["onb"] = "cycle"
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, "cycle"))
        return
    if head == "oc":
        v = int(parts[1])
        u.data["cycle_hint"] = v or 28
        u.data["onb"] = "plen"
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, "plen"))
        return
    if head == "op":
        v = int(parts[1])
        u.data["period_hint"] = v or 5
        u.data["onb"] = "past"
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, "past"))
        return
    if head == "oa":
        await q.answer()
        try:
            await q.message.delete()    # setup questions are done, keep the chat clean
        except Exception:
            await edit_markup(q, None)
        await finish_onboarding(bot, chat, u, parts[1] == "add", context)
        return

    # ---------- calendar
    if head == "cal":
        await handle_calendar(q, context, u, parts[1], parts[2], parts[3] if len(parts) > 3 else "")
        return

    # ---------- period start / end
    if head == "ps":
        today = today_for(u)
        if parts[1] == "pick":
            await q.answer()
            await edit(q, t(L, "cal_start"), kb.calendar_kb(L, u.cal, "start", today, today))
            return
        await q.answer()
        await log_start(q, context, u, today - timedelta(days=0 if parts[1] == "t" else 1))
        return
    if head == "pe":
        today = today_for(u)
        if parts[1] == "pick":
            await q.answer()
            await edit(q, t(L, "cal_end"), kb.calendar_kb(L, u.cal, "end", today, today))
            return
        await q.answer()
        await log_end(q, context, u, today - timedelta(days=0 if parts[1] == "t" else 1))
        return
    if head == "due":
        await q.answer()
        await edit(q, t(L, "ok_wait"))
        return
    if head == "endq":
        ps = get_ps(u)
        if ps and not ps[-1].end:
            ps[-1].ongoing = True
            put_ps(u, ps)
            S().save(u)
        await q.answer()
        await edit(q, t(L, "ok_noted"))
        return

    # ---------- today / helps
    if head == "helps":
        await q.answer()
        await edit(q, helps_text(u), IKM(kb.back_row(L, "tdy")))
        return
    if head == "phelps":
        link, owner = partner_ctx(u)
        await q.answer()
        if link:
            await edit(q, partner_help_text(u, owner, link.flags), IKM(kb.back_row(L, "ptdy")))
        return
    if head == "ptdy":
        await q.answer()
        view = partner_today_view(u)
        if view:
            await edit(q, *view)
        return

    # ---------- daily log
    if head == "lgnow":
        await q.answer()
        day = today_for(u)
        await edit(q, log_text(u, day), log_markup(u, day))
        return
    if head == "lgday":
        today = today_for(u)
        await q.answer()
        await edit(q, t(L, "cal_log"), kb.calendar_kb(L, u.cal, "log", today, today))
        return
    if head == "lg":
        await handle_log(q, context, u, dates.parse_ymd(parts[1]), parts[2],
                         parts[3] if len(parts) > 3 else "")
        return

    # ---------- partner (owner side)
    if head == "pt":
        await handle_partner_owner(q, context, u, parts[1], parts[2] if len(parts) > 2 else "")
        return
    if head == "nd":
        link = S().link_by_owner(u.id)
        await q.answer()
        if not link:
            await edit(q, t(L, "no_partner_yet"))
            return
        partner = S().get(link.partner_id)
        key = parts[1]
        sent = None
        for k, en, fa in NUDGES:
            if k == key and partner:
                txt = fa if partner.lang == "fa" else en
                sent = await send(bot, partner.id, t(partner.lang, "np_nudge",
                                                     name=name_of(u, partner.lang), text=txt))
        if sent is not None:
            u.data["last_nudge"] = [partner.id, sent.message_id]
            S().save(u)
        keep(context, q)
        await edit(q, t(L, "nudge_sent"),
                   IKM([[B(t(L, "btn_unsend"), callback_data="ndu")]]) if sent is not None else None)
        return

    # ---------- discreet reveal
    if head == "rv":
        event, k = parts[1], int(parts[2] or 0)
        await q.answer()
        if event.startswith("p_"):
            link, owner = partner_ctx(u)
            if not link:
                await edit(q, t(L, "p_nothing"))
                return
            await edit(q, partner_note(owner, u, event, k))
        else:
            text, markup = her_note(u, event, k)
            await edit(q, text or t(L, "saved"), markup)
        return

    # ---------- settings
    if head == "st":
        await handle_settings(q, context, u, parts[1], parts[2] if len(parts) > 2 else "")
        return
    if head == "del":
        await q.answer()
        if parts[1] == "yes":
            await delete_everything(bot, u)
            await edit(q, t(L, "deleted"))
            await send(bot, chat, "🌙", ReplyKeyboardRemove())
        else:
            text, markup = settings_view(u)
            await edit(q, text, markup)
        return

    await q.answer()


async def handle_calendar(q, context, u: User, mode: str, action: str, arg: str) -> None:
    L = u.lang
    today = today_for(u)
    bot = context.bot
    chat = q.message.chat_id
    if action == "nav":
        anchor = dates.parse_ymd(arg)
        marks = calendar_marks(u, today) if mode == "past" else None
        await q.answer()
        await edit_markup(q, kb.calendar_kb(L, u.cal, mode, anchor, today, marks, mode == "past"))
        return
    if action == "sw":   # switch Gregorian / Solar Hijri right on the picker
        u.cal = "g" if u.cal == "j" else "j"
        S().save(u)
        anchor = dates.parse_ymd(arg)
        marks = calendar_marks(u, today) if mode == "past" else None
        await q.answer(t(L, "saved"))
        await edit_markup(q, kb.calendar_kb(L, u.cal, mode, anchor, today, marks, mode == "past"))
        return
    if action == "x":
        await q.answer()
        if mode == "past":
            await edit(q, *today_view(u))
        elif mode == "onb":
            await edit(q, *onb_view(u, "last"))
        elif mode == "start":
            await edit(q, *start_view(u))
        elif mode == "end":
            await edit(q, *end_view(u))
        else:
            day = today_for(u)
            await edit(q, log_text(u, day), log_markup(u, day))
        return
    d = dates.parse_ymd(arg)
    if d > today:
        await q.answer(t(L, "future_day"), show_alert=True)
        return
    if mode == "past":
        ps = get_ps(u)
        if cycle.remove_start(ps, d):
            msg = t(L, "removed", d=fd(u, d))
        else:
            ok, other = cycle.add_start(ps, d)
            if not ok:
                await q.answer(t(L, "too_close", d=fd(u, other)), show_alert=True)
                return
            msg = t(L, "added", d=fd(u, d))
        put_ps(u, ps)
        S().save(u)
        await q.answer(msg)
        await edit_markup(q, kb.calendar_kb(L, u.cal, "past", d, today, calendar_marks(u, today), True))
        return
    if mode == "onb":
        ps = []
        cycle.add_start(ps, d)
        put_ps(u, ps)
        u.data["onb"] = "cycle"
        S().save(u)
        await q.answer()
        await edit(q, *onb_view(u, "cycle"))
        return
    if mode == "start":
        await q.answer()
        await log_start(q, context, u, d)
        return
    if mode == "end":
        await q.answer()
        await log_end(q, context, u, d)
        return
    if mode == "log":
        await q.answer()
        await edit(q, log_text(u, d), log_markup(u, d))
        return


async def log_start(q, context, u: User, d: date) -> None:
    L = u.lang
    ps = get_ps(u)
    ok, other = cycle.add_start(ps, d)
    if not ok:
        await edit(q, t(L, "too_close", d=fd(u, other)),
                   IKM([[B(t(L, "back"), callback_data="gostart")]]))
        return
    put_ps(u, ps)
    S().save(u)
    told = await notify_partner_start(context.bot, u)
    text = t(L, "logged_start", d=fd(u, d, weekday=True)) + "\n\n" + tips(L, "period")
    if told:
        text += "\n\n" + t(L, "partner_told")
    keep(context, q)
    await edit(q, text, IKM([[B(t(L, "undo"), callback_data=f"un:s:{dates.ymd(d)}:{1 if told else 0}")]]))


async def log_end(q, context, u: User, d: date) -> None:
    L = u.lang
    ps = get_ps(u)
    res, p = cycle.set_end(ps, d)
    if res in ("no_period", "too_long"):
        await edit(q, t(L, "no_open" if res == "no_period" else "end_too_long"),
                   IKM([[B(t(L, "back"), callback_data="goend")]]))
        return
    put_ps(u, ps)
    S().save(u)
    n = (p.end - p.start).days + 1
    keep(context, q)
    await edit(q, t(L, "logged_end", d=fd(u, d, weekday=True), n=days(L, n)),
               IKM([[B(t(L, "undo"), callback_data=f"un:e:{dates.ymd(d)}")]]))


async def handle_undo(q, context, u: User, kind: str, d: date, told: str) -> None:
    """Undo a period start or end that was logged by mistake."""
    L = u.lang
    ps = get_ps(u)
    if kind == "s":
        removed = cycle.remove_start(ps, d)
        if removed:
            put_ps(u, ps)
            S().save(u)
            link = S().link_by_owner(u.id)
            if told == "1" and link:
                partner = S().get(link.partner_id)
                if partner:
                    await send(context.bot, partner.id,
                               t(partner.lang, "np_undo", name=name_of(u, partner.lang)))
        await q.answer(t(L, "undone"))
        text, markup = start_view(u)
        await edit(q, t(L, "undone") + "\n\n" + text, markup)
        return
    if kind == "e":
        for p in ps:
            if p.end == d:
                p.end = None
        put_ps(u, ps)
        S().save(u)
        await q.answer(t(L, "undone"))
        text, markup = end_view(u)
        await edit(q, t(L, "undone") + "\n\n" + text, markup)
        return
    await q.answer()


async def handle_unsend(q, context, u: User) -> None:
    L = u.lang
    last = u.data.pop("last_nudge", None)
    link = S().link_by_owner(u.id)
    await q.answer()
    if not last or not link or last[0] != link.partner_id:
        await edit(q, t(L, "unsend_late"))
        return
    try:
        await context.bot.delete_message(last[0], last[1])
        S().save(u)
        await edit(q, t(L, "unsent"))
    except Exception:
        await edit(q, t(L, "unsend_late"))


async def handle_log(q, context, u: User, day: date, field: str, value: str) -> None:
    L = u.lang
    today = today_for(u)
    if day > today:
        await q.answer(t(L, "future_day"), show_alert=True)
        return
    logs = u.data.setdefault("logs", {})
    key = day.isoformat()
    entry = logs.get(key, {})
    if field == "done":
        await q.answer()
        items = entry_items(u, entry, L)
        if not items:
            await edit(q, t(L, "log_empty", d=fd(u, day)))
            return
        sep = "، " if L == "fa" else ", "
        out = [t(L, "log_saved", d=fd(u, day)), sep.join(items)]
        sym = [k for k in entry.get("sym", []) if k in SYMPTOM_TIPS]
        if sym:
            out.append("")
            out += ["• " + SYMPTOM_TIPS[k][1 if L == "fa" else 0] for k in sym]
        keep(context, q)
        await edit(q, "\n".join(out), IKM([[B(t(L, "btn_edit"), callback_data=f"lgd:{dates.ymd(day)}")]]))
        return
    if field == "tell":
        link = S().link_by_owner(u.id)
        partner = S().get(link.partner_id) if link else None
        items_p = entry_items(u, entry, partner.lang) if partner else []
        if not partner or not items_p:
            await q.answer(t(L, "log_empty", d=fd(u, day)), show_alert=True)
            return
        sep = "، " if partner.lang == "fa" else ", "
        await send(context.bot, partner.id,
                   t(partner.lang, "np_mood", name=name_of(u, partner.lang), items=sep.join(items_p)))
        await q.answer(t(L, "told_partner"), show_alert=True)
        return
    if field in ("mood", "sym"):
        cur = entry.setdefault(field, [])
        if value in cur:
            cur.remove(value)
        else:
            cur.append(value)
        if not cur:
            entry.pop(field)
    elif field in ("flow", "energy"):
        if entry.get(field) == value:
            entry.pop(field)
        else:
            entry[field] = value
    if entry:
        logs[key] = entry
    else:
        logs.pop(key, None)
    S().save(u)
    await q.answer()
    await edit_markup(q, log_markup(u, day))


async def handle_invite(q, context, u: User, action: str, token: str) -> None:
    L = u.lang
    bot = context.bot
    inv = S().peek_invite(token)
    await q.answer()
    if not inv:
        await edit(q, t(L, "inv_invalid"))
        return
    owner_id, flags = inv
    owner = S().get(owner_id)
    if owner is None or owner_id == u.id:
        await edit(q, t(L, "inv_invalid"))
        return
    if u.role == "tracker" and (u.onboarded or u.data.get("periods")):
        await edit(q, t(L, "inv_is_tracker"))
        return
    if action == "d":
        S().drop_invite(token)
        if u.role == "partner" and not S().link_by_partner(u.id):
            S().delete(u.id)
        await edit(q, t(L, "inv_declined_partner"))
        await send(bot, owner.id, t(owner.lang, "inv_declined_owner", name=name_of(u, owner.lang)))
        return
    if S().link_by_owner(owner_id):
        await edit(q, t(L, "inv_owner_busy"))
        return
    if S().link_by_partner(u.id):
        await edit(q, t(L, "inv_has_other"))
        return
    S().drop_invite(token)
    u.role = "partner"
    u.onboarded = True
    u.tz = owner.tz
    u.data["name"] = (q.from_user.first_name or "")[:40]
    S().save(u)
    S().create_link(owner_id, u.id, flags)
    await edit(q, t(L, "inv_accepted_partner", name=name_of(owner, L)))
    await send(bot, u.id, t(L, "onb_done"), kb.partner_kb(L))
    await send(bot, owner.id, t(owner.lang, "inv_accepted_owner", name=name_of(u, owner.lang)))


async def handle_partner_owner(q, context, u: User, action: str, arg: str) -> None:
    L = u.lang
    bot = context.bot
    link = S().link_by_owner(u.id)
    if action == "flag" and arg in FLAG_KEYS:
        if link:
            link.flags[arg] = not link.flags.get(arg)
            S().set_flags(u.id, link.flags)
        else:
            flags = u.data.get("invite_flags") or dict(DEFAULT_FLAGS)
            flags[arg] = not flags.get(arg)
            u.data["invite_flags"] = flags
            S().save(u)
        await q.answer(t(L, "saved"))
        text, markup = flags_view(u)
        await edit(q, text, markup)
        return
    if action == "menu":
        await q.answer()
        text, markup = flags_view(u)
        await edit(q, text, markup)
        return
    if action == "create":
        await q.answer()
        if link:
            text, markup = flags_view(u)
            await edit(q, text, markup)
            return
        flags = u.data.get("invite_flags") or dict(DEFAULT_FLAGS)
        token = S().create_invite(u.id, flags, INVITE_TTL_HOURS)
        url = f"https://t.me/{bot.username}?start=inv_{token}"
        await edit(q, t(L, "invite_made", link=url),
                   IKM([[B(t(L, "btn_cancel_invite"), callback_data="pt:cancel")]]
                       + kb.back_row(L, "pt:menu")))
        return
    if action == "cancel":
        S().cancel_invites(u.id)
        await q.answer(t(L, "invite_cancelled"), show_alert=True)
        text, markup = flags_view(u)
        await edit(q, text, markup)
        return
    if action == "nudge":
        await q.answer()
        if not link:
            await edit(q, t(L, "no_partner_yet"))
            return
        partner = S().get(link.partner_id)
        await edit(q, t(L, "nudge_pick", name=name_of(partner, L)), kb.nudge_kb(L))
        return
    if action == "stop":
        await q.answer()
        if not link:
            text, markup = flags_view(u)
            await edit(q, text, markup)
            return
        partner = S().get(link.partner_id)
        await edit(q, t(L, "stop_confirm", name=name_of(partner, L)),
                   kb.confirm_kb(L, "btn_yes_stop", "pt:stop!", "pt:menu"))
        return
    if action == "stop!":
        await q.answer()
        if link:
            partner = S().get(link.partner_id)
            S().delete_link(u.id)
            if partner:
                await send(bot, partner.id, t(partner.lang, "partner_lost", name=name_of(u, partner.lang)),
                           ReplyKeyboardRemove())
                S().delete(partner.id)
            await edit(q, t(L, "stopped", name=name_of(partner, L)))
        else:
            text, markup = flags_view(u)
            await edit(q, text, markup)
        return
    await q.answer()


async def handle_settings(q, context, u: User, action: str, arg: str) -> None:
    L = u.lang
    bot = context.bot
    chat = q.message.chat_id

    async def refresh(note: str | None = None):
        await q.answer(note or "")
        text, markup = settings_view(u)
        await edit(q, text, markup)

    if action == "menu":
        return await refresh()
    if action == "lang":
        u.lang = "en" if u.lang == "fa" else "fa"
        u.cal = "j" if u.lang == "fa" else "g"
        S().save(u)
        await refresh(t(u.lang, "saved"))
        await send(bot, chat, t(u.lang, "lang_changed"), menu_for(u))  # new language on the keyboard
        return
    if action == "cal":
        u.cal = "g" if u.cal == "j" else "j"
        S().save(u)
        return await refresh(t(L, "saved"))
    if action in ("discreet", "daily", "fertile"):
        attr = {"discreet": "discreet", "daily": "daily_reminder", "fertile": "show_fertile"}[action]
        setattr(u, attr, not getattr(u, attr))
        S().save(u)
        return await refresh(t(L, "saved"))
    if action == "hourmenu":
        await q.answer()
        await edit(q, t(L, "pick_hour"), kb.hour_kb(L))
        return
    if action == "hour":
        u.notify_hour = int(arg)
        S().save(u)
        return await refresh(t(L, "saved"))
    if action == "tzmenu":
        await q.answer()
        await edit(q, t(L, "ask_tz"), kb.tz_kb(L, "set", back="st:menu"))
        return
    if action == "cyclemenu":
        await q.answer()
        n = data_cycle(u)
        note = ("\n\n" + t(L, "note_cycle_data", n=days(L, n))) if n else ""
        await edit(q, t(L, "ask_cycle") + note,
                   kb.choice_kb(L, "st:cycle", [24, 26, 28, 30, 32, 35], back="st:menu"))
        return
    if action == "cycle":
        u.data["cycle_hint"] = int(arg) or 28
        S().save(u)
        return await refresh(t(L, "saved"))
    if action == "plenmenu":
        await q.answer()
        n = data_plen(u)
        note = ("\n\n" + t(L, "note_plen_data", n=days(L, n))) if n else ""
        await edit(q, t(L, "ask_plen") + note,
                   kb.choice_kb(L, "st:plen", [3, 4, 5, 6, 7, 8], per_row=3, back="st:menu"))
        return
    if action == "plen":
        u.data["period_hint"] = int(arg) or 5
        S().save(u)
        return await refresh(t(L, "saved"))
    if action == "export":
        await q.answer()
        payload = {
            "exported_at": datetime.now(ZoneInfo(u.tz)).isoformat(timespec="seconds"),
            "settings": {"language": u.lang, "calendar": u.cal, "time_zone": u.tz,
                         "reminder_hour": u.notify_hour},
            "periods": u.data.get("periods", []),
            "daily_logs": u.data.get("logs", {}),
            "usual_cycle_length": u.data.get("cycle_hint"),
            "usual_period_length": u.data.get("period_hint"),
        }
        buf = io.BytesIO(json.dumps(payload, ensure_ascii=False, indent=2).encode())
        buf.name = "luna-my-data.json"
        await bot.send_document(chat, buf, caption=t(L, "export_caption"))
        return
    if action == "delete":
        await q.answer()
        await edit(q, t(L, "del_confirm"), kb.confirm_kb(L, "btn_yes_delete", "del:yes", "del:no"))
        return
    if action == "leave":
        link, owner = partner_ctx(u)
        await q.answer()
        if not link:
            await edit(q, t(L, "p_nothing"))
            return
        await edit(q, t(L, "leave_confirm", name=name_of(owner, L)),
                   kb.confirm_kb(L, "btn_yes_leave", "st:leave!", "st:menu"))
        return
    if action == "leave!":
        link, owner = partner_ctx(u)
        await q.answer()
        name = name_of(owner, L)
        if link:
            S().delete_link(link.owner_id)
            if owner:
                await send(bot, owner.id, t(owner.lang, "partner_left_owner", name=name_of(u, owner.lang)))
        S().delete(u.id)
        await edit(q, t(L, "left", name=name))
        await send(bot, chat, t(L, "partner_restart"), ReplyKeyboardRemove())
        return
    await q.answer()


async def delete_everything(bot, u: User) -> None:
    link = S().link_by_owner(u.id)
    if link:
        partner = S().get(link.partner_id)
        if partner:
            await send(bot, partner.id, t(partner.lang, "partner_lost", name=name_of(u, partner.lang)),
                       ReplyKeyboardRemove())
            S().delete(partner.id)
    plink = S().link_by_partner(u.id)
    if plink:
        owner = S().get(plink.owner_id)
        if owner:
            await send(bot, owner.id, t(owner.lang, "partner_left_owner", name=name_of(u, owner.lang)))
    S().delete(u.id)


async def on_other(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Stickers, photos, voice: just show the menu again."""
    if update.effective_chat.type != "private":
        return
    u = S().get(update.effective_user.id)
    if u is None:
        await update.message.reply_text(t("en", "lang_pick"), reply_markup=kb.lang_kb())
        return
    if not u.onboarded:
        await resume(update, context, u)
        return
    await update.message.reply_text(t(u.lang, "use_buttons"), reply_markup=menu_for(u))


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    # never log update content, only the error type and place
    err = context.error
    tb = err.__traceback__
    while tb and tb.tb_next:
        tb = tb.tb_next
    where = f"{tb.tb_frame.f_code.co_filename.rsplit('/', 1)[-1]}:{tb.tb_lineno}" if tb else "?"
    log.error("handler error %s at %s: %s", type(err).__name__, where, str(err)[:200])
