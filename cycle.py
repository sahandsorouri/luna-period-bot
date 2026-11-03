"""Pure cycle logic. No I/O, no Telegram. Everything here is unit tested.

Method (same family as Apple Cycle Tracking, Clue and drip):
- cycle length = median of the last 6 usable cycles (15 to 90 days); robust to one odd month
- before 1 full cycle is logged we use the length she told us at onboarding ("rough")
- ovulation = next period - 14 days, fertile window = ovulation - 5 .. ovulation + 1
- PMS window = the 5 days before the next period
- uncertainty margin grows with how much her cycles vary
Health flags follow FIGO 2018 / ACOG ranges, worded as "worth asking a doctor", never a diagnosis.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from statistics import mean, median

MIN_GAP = 10          # two period starts closer than this are rejected
MIN_CYCLE, MAX_CYCLE = 15, 90
LUTEAL = 14
PMS_DAYS = 5
MAX_OPEN = 10         # an unclosed period counts as "maybe still going" up to this day
MAX_PERIOD = 15


@dataclass
class Period:
    start: date
    end: date | None = None
    ongoing: bool = False   # she said "not yet ended" when asked


def parse(raw: list[dict]) -> list[Period]:
    out = []
    for r in raw or []:
        out.append(Period(
            date.fromisoformat(r["s"]),
            date.fromisoformat(r["e"]) if r.get("e") else None,
            bool(r.get("o")),
        ))
    return sorted(out, key=lambda p: p.start)


def dump(ps: list[Period]) -> list[dict]:
    out = []
    for p in sorted(ps, key=lambda p: p.start):
        r = {"s": p.start.isoformat(), "e": p.end.isoformat() if p.end else None}
        if p.ongoing and not p.end:
            r["o"] = 1
        out.append(r)
    return out


def _round(x: float) -> int:
    return int(x + 0.5)


def lengths(ps: list[Period]) -> list[int]:
    s = [p.start for p in ps]
    return [(b - a).days for a, b in zip(s, s[1:])]


def usable(ps: list[Period]) -> list[int]:
    return [n for n in lengths(ps) if MIN_CYCLE <= n <= MAX_CYCLE]


def period_lengths(ps: list[Period]) -> list[int]:
    out = []
    for p in ps:
        if p.end:
            n = (p.end - p.start).days + 1
            if 1 <= n <= MAX_PERIOD:
                out.append(n)
    return out


def est_cycle(ps: list[Period], hint: int | None) -> tuple[int, str]:
    u = usable(ps)[-6:]
    if not u:
        return (hint or 28), "rough"
    return _round(median(u)), ("good" if len(u) >= 3 else "early")


def est_period(ps: list[Period], hint: int | None) -> int:
    pl = period_lengths(ps)[-6:]
    return _round(median(pl)) if pl else (hint or 5)


def margin(ps: list[Period]) -> int:
    u = usable(ps)[-6:]
    if len(u) < 3:
        return 3
    spread = max(u) - min(u)
    return 1 if spread <= 3 else 2 if spread <= 7 else 3


@dataclass
class Status:
    has_data: bool = False
    today: date | None = None
    last_start: date | None = None
    last_end: date | None = None      # logged end, or None
    cycle_day: int = 0
    cycle_len: int = 28
    period_len: int = 5
    quality: str = "rough"
    margin: int = 3
    in_period: bool = False
    period_day: int = 0
    awaiting_end: bool = False
    next_start: date | None = None
    days_until: int = 0               # negative means late
    days_late: int = 0
    ovulation: date | None = None
    fertile_start: date | None = None
    fertile_end: date | None = None
    pms_start: date | None = None
    phase: str = "unknown"
    stale: bool = False               # nothing logged for a long time


def status(ps: list[Period], today: date, cycle_hint: int | None = 28,
           period_hint: int | None = 5) -> Status:
    s = Status(today=today)
    past = [p for p in ps if p.start <= today]
    if not past:
        return s
    cur = past[-1]
    L, q = est_cycle(past, cycle_hint)
    P = est_period(past, period_hint)
    s.has_data = True
    s.last_start, s.last_end = cur.start, cur.end
    s.cycle_len, s.period_len, s.quality, s.margin = L, P, q, margin(past)
    day = (today - cur.start).days + 1
    s.cycle_day = day
    if cur.end:
        s.in_period = today <= cur.end
    else:
        s.awaiting_end = day <= MAX_OPEN
        s.in_period = day <= P or (cur.ongoing and day <= MAX_OPEN)
    if s.in_period:
        s.period_day = day
    n = cur.start + timedelta(days=L)
    s.next_start = n
    s.days_until = (n - today).days
    s.days_late = max(0, -s.days_until)
    o = n - timedelta(days=LUTEAL)
    s.ovulation = o
    s.fertile_start = o - timedelta(days=5)
    s.fertile_end = o + timedelta(days=1)
    s.pms_start = n - timedelta(days=PMS_DAYS)
    s.stale = s.days_late > 60
    if s.in_period:
        s.phase = "period"
    elif s.days_until == 0:
        s.phase = "due"
    elif s.days_until < 0:
        s.phase = "late"
    elif today >= s.pms_start:
        s.phase = "pms"
    elif today == o:
        s.phase = "ovulation"
    elif s.fertile_start <= today <= s.fertile_end:
        s.phase = "fertile"
    elif today < s.fertile_start:
        s.phase = "follicular"
    else:
        s.phase = "luteal"
    return s


def late_thresholds(s: Status) -> tuple[int, int, int]:
    base = max(3, s.margin + 1)
    return base, base + 4, base + 11


def period_days(ps: list[Period], period_hint: int | None, today: date) -> set[date]:
    """Every bleeding day we know or assume, for the calendar view."""
    P = est_period(ps, period_hint)
    out: set[date] = set()
    for p in ps:
        if p.end:
            end = p.end
        else:
            end = p.start + timedelta(days=P - 1)
            if p.ongoing:
                end = max(end, min(today, p.start + timedelta(days=MAX_OPEN - 1)))
        d = p.start
        while d <= end:
            out.add(d)
            d += timedelta(days=1)
    return out


# ---- editing -------------------------------------------------------------

def add_start(ps: list[Period], d: date) -> tuple[bool, date | None]:
    """Returns (ok, conflicting_start)."""
    for p in ps:
        if abs((p.start - d).days) < MIN_GAP:
            return False, p.start
    ps.append(Period(d))
    ps.sort(key=lambda p: p.start)
    return True, None


def remove_start(ps: list[Period], d: date) -> bool:
    for p in ps:
        if p.start == d:
            ps.remove(p)
            return True
    return False


def set_end(ps: list[Period], d: date) -> tuple[str, Period | None]:
    """Close the period that contains d. Returns (result, period)."""
    cands = [p for p in ps if p.start <= d]
    if not cands:
        return "no_period", None
    cur = cands[-1]
    n = (d - cur.start).days + 1
    if n > MAX_PERIOD:
        return "too_long", cur
    cur.end = d
    cur.ongoing = False
    return "ok", cur


# ---- stats ---------------------------------------------------------------

@dataclass
class Stats:
    periods: int = 0
    cycles: int = 0
    avg_cycle: int | None = None
    min_cycle: int | None = None
    max_cycle: int | None = None
    spread: int | None = None
    avg_period: int | None = None
    regularity: str | None = None     # regular / variable / irregular
    recent: list[tuple[date, int]] | None = None
    flags: list[str] | None = None


def stats(ps: list[Period], period_hint: int | None = 5) -> Stats:
    st = Stats(periods=len(ps), recent=[], flags=[])
    pairs = []
    for a, b in zip(ps, ps[1:]):
        n = (b.start - a.start).days
        if MIN_CYCLE <= n <= MAX_CYCLE:
            pairs.append((a.start, n))
    st.cycles = len(pairs)
    recent = [n for _, n in pairs[-6:]]
    st.recent = pairs[-6:]
    if recent:
        st.avg_cycle = _round(mean(recent))
        st.min_cycle, st.max_cycle = min(recent), max(recent)
        st.spread = st.max_cycle - st.min_cycle
    pl = period_lengths(ps)[-6:]
    if pl:
        st.avg_period = _round(mean(pl))
    if len(recent) >= 3:
        st.regularity = ("regular" if st.spread <= 7
                         else "variable" if st.spread <= 16 else "irregular")
    if len(recent) >= 4 and st.spread >= 17:
        st.flags.append("irregular")
    if sum(n < 21 for n in recent) >= 2:
        st.flags.append("short")
    if sum(n > 35 for n in recent) >= 2:
        st.flags.append("long")
    if sum(n > 8 for n in pl) >= 2:
        st.flags.append("prolonged")
    return st


def symptom_counts(logs: dict, today: date, days: int = 90) -> Counter:
    c: Counter = Counter()
    since = today - timedelta(days=days)
    for k, v in (logs or {}).items():
        d = date.fromisoformat(k)
        if since <= d <= today:
            for item in v.get("sym", []) + v.get("mood", []):
                c[item] += 1
    return c


def pms_counts(logs: dict, ps: list[Period]) -> Counter:
    """What she logs most in the 5 days before a period starts."""
    c: Counter = Counter()
    for p in ps:
        for i in range(1, PMS_DAYS + 1):
            v = (logs or {}).get((p.start - timedelta(days=i)).isoformat())
            if v:
                for item in v.get("sym", []) + v.get("mood", []):
                    c[item] += 1
    return c
