"""Hourly job: each person gets reminders at their own local reminder hour.

Dedupe keys live in each receiver's encrypted blob ("sent"), keyed by the
predicted date, so one cycle never sends the same note twice.
"""
from __future__ import annotations

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import cycle
import handlers as h

log = logging.getLogger("luna.notify")


def her_events(u, today):
    s = h.status_of(u, today)
    ev = []
    if not s.has_data or s.stale:
        if u.daily_reminder:
            ev.append((f"daily:{today}", "daily", 0))
        return ev
    n = s.next_start.isoformat()
    if not s.in_period:
        if s.days_until == 2:
            ev.append((f"soon:{n}", "soon", 0))
        if s.days_until == 0:
            ev.append((f"due:{n}", "due", 0))
        for k in cycle.late_thresholds(s):
            if s.days_late == k:
                ev.append((f"late{k}:{n}", "late", k))
        if s.days_until == cycle.PMS_DAYS:
            ev.append((f"pms:{n}", "pms", 0))
        if u.show_fertile and today == s.fertile_start and s.days_until > 0:
            ev.append((f"fert:{n}", "fertile", 0))
    if s.awaiting_end and not s.last_end:
        for day in (s.period_len + 1, s.period_len + 4):
            if s.cycle_day == day and day <= cycle.MAX_OPEN:
                ev.append((f"endq{day}:{s.last_start}", "endq", 0))
    if u.daily_reminder:
        ev.append((f"daily:{today}", "daily", 0))
    return ev


def partner_events(owner, flags, today):
    s = h.status_of(owner, today)
    if not s.has_data or s.stale or s.in_period:
        return []
    n = s.next_start.isoformat()
    ev = []
    if flags.get("pms") and s.days_until == cycle.PMS_DAYS + 1:
        ev.append((f"p_pms:{n}", "p_pms", 0))
    if flags.get("phase") and s.days_until == 1:
        ev.append((f"p_soon:{n}", "p_soon", 0))
    if flags.get("late"):
        for k in cycle.late_thresholds(s)[:2]:
            if s.days_late == k:
                ev.append((f"p_late{k}:{n}", "p_late", k))
    return ev


def _prune(sent: dict) -> dict:
    if len(sent) <= 80:
        return sent
    return dict(sorted(sent.items(), key=lambda kv: kv[1])[-60:])


async def tick(context) -> None:
    store = h.S()
    bot = context.bot
    for uid in store.all_ids():
        try:
            u = store.get(uid)
            if not u:
                continue
            now = datetime.now(ZoneInfo(u.tz))
            if now.hour != u.notify_hour:
                continue
            sent = u.data.setdefault("sent", {})
            if u.role == "partner":
                link, owner = h.partner_ctx(u)
                if not link:
                    continue
                events = partner_events(owner, link.flags, h.today_for(owner))
            else:
                events = her_events(u, now.date())
            changed = False
            for key, event, k in events:
                if key in sent:
                    continue
                if u.role == "partner":
                    text, markup = h.partner_note(owner, u, event, k), None
                else:
                    text, markup = h.her_note(u, event, k)
                if text and await h.deliver(bot, u, text, markup, event, k):
                    sent[key] = now.date().isoformat()
                    changed = True
            if changed:
                u.data["sent"] = _prune(sent)
                store.save(u)
        except Exception as e:  # one bad row must not stop the others
            log.error("notify failed for a user: %s", type(e).__name__)
