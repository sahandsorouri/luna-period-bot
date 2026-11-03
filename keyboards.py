from __future__ import annotations

from datetime import date, timedelta

from telegram import InlineKeyboardButton as B
from telegram import InlineKeyboardMarkup as IKM
from telegram import ReplyKeyboardMarkup

import dates
from i18n import NUDGES, OPTS, TZS, flag_label, menu, opt, t
from storage import FLAG_KEYS

BLANK = "⠀"


def main_kb(lang: str, awaiting_end: bool = False) -> ReplyKeyboardMarkup:
    # static on purpose: both buttons always there, so the keyboard never needs a refresh message
    rows = [[menu(lang, "start"), menu(lang, "end")],
            [menu(lang, "today"), menu(lang, "log")],
            [menu(lang, "calendar"), menu(lang, "stats")],
            [menu(lang, "partner"), menu(lang, "settings")]]
    if lang == "fa":
        rows = [list(reversed(r)) for r in rows]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def partner_kb(lang: str) -> ReplyKeyboardMarkup:
    rows = [[menu(lang, "p_today"), menu(lang, "p_coming")],
            [menu(lang, "p_help"), menu(lang, "settings")]]
    if lang == "fa":
        rows = [list(reversed(r)) for r in rows]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, is_persistent=True)


def _rtl(lang: str, row: list) -> list:
    return list(reversed(row)) if lang == "fa" else row


def lang_kb(prefix: str = "lang") -> IKM:
    return IKM([[B("English", callback_data=f"{prefix}:en"),
                 B("فارسی", callback_data=f"{prefix}:fa")]])


def back_row(lang: str, data: str | None) -> list:
    return [[B(t(lang, "back"), callback_data=data)]] if data else []


def tz_kb(lang: str, ctx: str, back: str | None = None) -> IKM:
    rows, row = [], []
    for i, (_, en, fa) in enumerate(TZS):
        row.append(B(fa if lang == "fa" else en, callback_data=f"tz:{ctx}:{i}"))
        if len(row) == 2:
            rows.append(_rtl(lang, row))
            row = []
    if row:
        rows.append(row)
    return IKM(rows + back_row(lang, back))


def when_kb(lang: str, prefix: str, extra: list | None = None, back: str | None = None,
            cancel: bool = False) -> IKM:
    """Today / Yesterday / Pick a date. prefix like 'ps' (period start) or 'pe'."""
    rows = [_rtl(lang, [B(t(lang, "btn_today"), callback_data=f"{prefix}:t"),
                        B(t(lang, "btn_yesterday"), callback_data=f"{prefix}:y")]),
            [B(t(lang, "btn_pick"), callback_data=f"{prefix}:pick")]]
    if extra:
        rows.extend(extra)
    rows += back_row(lang, back)
    if cancel:
        rows.append([B(t(lang, "cancel"), callback_data="close")])
    return IKM(rows)


def choice_kb(lang: str, prefix: str, values: list[int], per_row: int = 4,
              not_sure: bool = True, back: str | None = None) -> IKM:
    rows, row = [], []
    for v in values:
        row.append(B(dates.num(lang, v), callback_data=f"{prefix}:{v}"))
        if len(row) == per_row:
            rows.append(_rtl(lang, row))
            row = []
    if row:
        rows.append(_rtl(lang, row))
    if not_sure:
        rows.append([B(t(lang, "not_sure"), callback_data=f"{prefix}:0")])
    return IKM(rows + back_row(lang, back))


def calendar_kb(lang: str, cal: str, mode: str, anchor: date, today: date,
                marks: dict[date, str] | None = None, allow_future_view: bool = False) -> IKM:
    marks = marks or {}
    first, last = dates.month_bounds(anchor, cal)
    prev_anchor = first - timedelta(days=1)
    next_anchor = last + timedelta(days=1)
    limit = today + timedelta(days=45 if allow_future_view else 0)
    prev_b = B("◀", callback_data=f"cal:{mode}:nav:{dates.ymd(prev_anchor)}")
    next_b = (B("▶", callback_data=f"cal:{mode}:nav:{dates.ymd(next_anchor)}")
              if next_anchor <= limit else B(BLANK, callback_data="noop"))
    title = B(dates.month_title(anchor, lang, cal), callback_data="noop")
    if lang == "fa":
        # right to left: older months on the right
        nav = [B("◀", callback_data=next_b.callback_data) if next_b.text != BLANK else next_b,
               title, B("▶", callback_data=prev_b.callback_data)]
    else:
        nav = [prev_b, title, next_b]
    rows = [nav, _rtl(lang, [B(w, callback_data="noop") for w in dates.weekday_header(lang)])]
    for week in dates.month_weeks(anchor, lang, cal):
        row = []
        for d in week:
            if d is None:
                row.append(B(BLANK, callback_data="noop"))
                continue
            dn = dates.day_num(d, lang, cal)
            label = marks.get(d, "") + dn
            if d == today and not marks.get(d):
                label = f"[{dn}]"
            if d > today:
                row.append(B(label if marks.get(d) else dn, callback_data="noop"))
            else:
                row.append(B(label, callback_data=f"cal:{mode}:d:{dates.ymd(d)}"))
        rows.append(_rtl(lang, row))
    other = "cal_switch_g" if cal == "j" else "cal_switch_j"
    rows.append([B(t(lang, other), callback_data=f"cal:{mode}:sw:{dates.ymd(anchor)}")])
    rows.append([B(t(lang, "btn_done") if mode == "past" else t(lang, "back"),
                   callback_data=f"cal:{mode}:x")])
    return IKM(rows)


def log_kb(lang: str, day: date, entry: dict, show_flow: bool, has_partner: bool) -> IKM:
    k = dates.ymd(day)
    rows = []

    def section(kind: str, title_key: str, per_row: int, multi: bool):
        rows.append([B(t(lang, title_key), callback_data="noop")])
        row = []
        cur = entry.get(kind)
        for key, _, _ in OPTS[kind]:
            on = (key in (cur or [])) if multi else (cur == key)
            label = ("✓ " if on else "") + opt(lang, kind, key)
            row.append(B(label, callback_data=f"lg:{k}:{kind}:{key}"))
            if len(row) == per_row:
                rows.append(_rtl(lang, row))
                row = []
        if row:
            rows.append(_rtl(lang, row))

    if show_flow:
        section("flow", "sec_flow", 2, False)
    section("mood", "sec_mood", 2, True)
    section("sym", "sec_sym", 2, True)
    section("energy", "sec_energy", 3, False)
    last = [B(t(lang, "btn_other_day"), callback_data="lgday"),
            B(t(lang, "btn_done"), callback_data=f"lg:{k}:done")]
    rows.append(_rtl(lang, last))
    if has_partner:
        rows.append([B(t(lang, "btn_tell_partner"), callback_data=f"lg:{k}:tell")])
    return IKM(rows)


def today_kb(lang: str, add_past: bool = False) -> IKM:
    rows = [_rtl(lang, [B(t(lang, "btn_helps"), callback_data="helps"),
                        B(t(lang, "btn_log"), callback_data="lgnow")])]
    if add_past:
        rows.append([B(t(lang, "btn_add_past"), callback_data="opencal")])
    return IKM(rows)


def flags_kb(lang: str, flags: dict, linked: bool, invite_open: bool) -> IKM:
    rows = []
    for k in FLAG_KEYS:
        mark = "✅" if flags.get(k) else "⬜"
        rows.append([B(f"{mark} {flag_label(lang, k)}", callback_data=f"pt:flag:{k}")])
    if linked:
        rows.append([B(t(lang, "btn_nudge"), callback_data="pt:nudge")])
        rows.append([B(t(lang, "btn_stop_sharing"), callback_data="pt:stop")])
    elif invite_open:  # noqa: SIM114
        rows.append([B(t(lang, "btn_create_invite"), callback_data="pt:create")])
        rows.append([B(t(lang, "btn_cancel_invite"), callback_data="pt:cancel")])
    else:
        rows.append([B(t(lang, "btn_create_invite"), callback_data="pt:create")])
    return IKM(rows)


def nudge_kb(lang: str) -> IKM:
    rows = [[B(fa if lang == "fa" else en, callback_data=f"nd:{k}")] for k, en, fa in NUDGES]
    rows.append([B(t(lang, "cancel"), callback_data="pt:menu")])
    return IKM(rows)


def confirm_kb(lang: str, yes_key: str, yes_data: str, no_data: str) -> IKM:
    return IKM([_rtl(lang, [B(t(lang, yes_key), callback_data=yes_data),
                            B(t(lang, "cancel"), callback_data=no_data)])])


def hour_kb(lang: str) -> IKM:
    hours = [7, 8, 9, 10, 12, 14, 17, 19, 20, 21, 22]
    rows, row = [], []
    for h in hours:
        row.append(B(f"{dates.num(lang, h)}:{dates.num(lang, '00')}", callback_data=f"st:hour:{h}"))
        if len(row) == 4:
            rows.append(_rtl(lang, row))
            row = []
    if row:
        rows.append(_rtl(lang, row))
    rows.append([B(t(lang, "back"), callback_data="st:menu")])
    return IKM(rows)
