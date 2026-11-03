"""Date display in Gregorian or Solar Hijri, with Persian digits for Persian UI."""
from __future__ import annotations

from datetime import date, timedelta

import jdatetime

_FA = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")

J_MONTHS_FA = ["فروردین", "اردیبهشت", "خرداد", "تیر", "مرداد", "شهریور",
               "مهر", "آبان", "آذر", "دی", "بهمن", "اسفند"]
J_MONTHS_EN = ["Farvardin", "Ordibehesht", "Khordad", "Tir", "Mordad", "Shahrivar",
               "Mehr", "Aban", "Azar", "Dey", "Bahman", "Esfand"]
G_MONTHS_EN = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
               "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
G_MONTHS_EN_FULL = ["January", "February", "March", "April", "May", "June", "July",
                    "August", "September", "October", "November", "December"]
G_MONTHS_FA = ["ژانویه", "فوریه", "مارس", "آوریل", "مه", "ژوئن",
               "ژوئیه", "اوت", "سپتامبر", "اکتبر", "نوامبر", "دسامبر"]
# indexed by date.weekday(): Monday = 0
WD_EN = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
WD_FA = ["دوشنبه", "سه‌شنبه", "چهارشنبه", "پنجشنبه", "جمعه", "شنبه", "یکشنبه"]
WD_FA_SHORT = ["د", "س", "چ", "پ", "ج", "ش", "ی"]
WD_EN_SHORT = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]


def num(lang: str, n) -> str:
    s = str(n)
    return s.translate(_FA) if lang == "fa" else s


def fmt(d: date, lang: str, cal: str, weekday: bool = False, year: bool = False) -> str:
    if cal == "j":
        jd = jdatetime.date.fromgregorian(date=d)
        months = J_MONTHS_FA if lang == "fa" else J_MONTHS_EN
        s = f"{num(lang, jd.day)} {months[jd.month - 1]}"
        if year:
            s += f" {num(lang, jd.year)}"
    else:
        months = G_MONTHS_FA if lang == "fa" else G_MONTHS_EN
        s = f"{num(lang, d.day)} {months[d.month - 1]}"
        if year:
            s += f" {num(lang, d.year)}"
    if weekday:
        s = f"{(WD_FA if lang == 'fa' else WD_EN)[d.weekday()]} {s}"
    return s


def month_bounds(anchor: date, cal: str) -> tuple[date, date]:
    """First and last Gregorian dates of the month (in the chosen calendar) holding anchor."""
    if cal == "j":
        ja = jdatetime.date.fromgregorian(date=anchor)
        first = jdatetime.date(ja.year, ja.month, 1).togregorian()
        if ja.month == 12:
            nxt = jdatetime.date(ja.year + 1, 1, 1).togregorian()
        else:
            nxt = jdatetime.date(ja.year, ja.month + 1, 1).togregorian()
    else:
        first = anchor.replace(day=1)
        nxt = (first.replace(year=first.year + 1, month=1) if first.month == 12
               else first.replace(month=first.month + 1))
    return first, nxt - timedelta(days=1)


def month_title(anchor: date, lang: str, cal: str) -> str:
    if cal == "j":
        ja = jdatetime.date.fromgregorian(date=anchor)
        months = J_MONTHS_FA if lang == "fa" else J_MONTHS_EN
        return f"{months[ja.month - 1]} {num(lang, ja.year)}"
    months = G_MONTHS_FA if lang == "fa" else G_MONTHS_EN_FULL
    return f"{months[anchor.month - 1]} {num(lang, anchor.year)}"


def week_col(d: date, lang: str) -> int:
    # Persian weeks start on Saturday, English on Monday
    return (d.weekday() + 2) % 7 if lang == "fa" else d.weekday()


def weekday_header(lang: str) -> list[str]:
    if lang == "fa":
        order = [5, 6, 0, 1, 2, 3, 4]
        return [WD_FA_SHORT[i] for i in order]
    return WD_EN_SHORT[:]


def month_weeks(anchor: date, lang: str, cal: str) -> list[list[date | None]]:
    first, last = month_bounds(anchor, cal)
    weeks: list[list[date | None]] = []
    row: list[date | None] = [None] * week_col(first, lang)
    d = first
    while d <= last:
        row.append(d)
        if len(row) == 7:
            weeks.append(row)
            row = []
        d += timedelta(days=1)
    if row:
        weeks.append(row + [None] * (7 - len(row)))
    return weeks


def day_num(d: date, lang: str, cal: str) -> str:
    """Day of month in the chosen calendar."""
    n = jdatetime.date.fromgregorian(date=d).day if cal == "j" else d.day
    return num(lang, n)


def ymd(d: date) -> str:
    return d.strftime("%Y%m%d")


def parse_ymd(s: str) -> date:
    return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
