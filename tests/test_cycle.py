from datetime import date, timedelta

import cycle
from cycle import Period


def P(*starts, plen=5):
    return [Period(date.fromisoformat(s), date.fromisoformat(s) + timedelta(days=plen - 1)) for s in starts]


def test_no_data():
    assert not cycle.status([], date(2026, 11, 3)).has_data


def test_rough_uses_hint():
    ps = [Period(date(2026, 10, 20))]
    s = cycle.status(ps, date(2026, 11, 3), cycle_hint=30)
    assert s.quality == "rough" and s.cycle_len == 30
    assert s.next_start == date(2026, 11, 19)
    assert s.cycle_day == 15


def test_median_is_robust():
    ps = P("2026-05-01", "2026-05-29", "2026-06-26", "2026-08-10", "2026-09-07", "2026-10-05")
    # lengths 28, 28, 45, 28, 28 -> median 28
    s = cycle.status(ps, date(2026, 10, 20))
    assert s.cycle_len == 28 and s.quality == "good"


def test_phases():
    ps = P("2026-09-07", "2026-10-05")  # 28-day cycle
    st = lambda d: cycle.status(ps, d).phase
    assert st(date(2026, 10, 6)) == "period"
    assert st(date(2026, 10, 12)) == "follicular"
    assert st(date(2026, 10, 17)) == "fertile"
    assert st(date(2026, 10, 19)) == "ovulation"
    assert cycle.status(ps, date(2026, 10, 19)).ovulation == date(2026, 10, 19)
    assert st(date(2026, 10, 25)) == "luteal"
    assert st(date(2026, 10, 29)) == "pms"
    assert st(date(2026, 11, 2)) == "due"
    assert st(date(2026, 11, 5)) == "late"
    assert cycle.status(ps, date(2026, 11, 5)).days_late == 3


def test_ovulation_phase_label():
    ps = P("2026-09-07", "2026-10-05")
    s = cycle.status(ps, date(2026, 10, 19))
    assert s.phase in ("ovulation", "fertile")


def test_open_period_and_end():
    ps = [Period(date(2026, 10, 30))]
    s = cycle.status(ps, date(2026, 11, 3), period_hint=5)
    assert s.in_period and s.awaiting_end and s.period_day == 5
    s = cycle.status(ps, date(2026, 11, 5), period_hint=5)
    assert not s.in_period and s.awaiting_end
    ps[0].ongoing = True
    assert cycle.status(ps, date(2026, 11, 5), period_hint=5).in_period
    res, p = cycle.set_end(ps, date(2026, 11, 4))
    assert res == "ok" and p.end == date(2026, 11, 4) and not p.ongoing
    assert cycle.set_end(ps, date(2026, 11, 30))[0] == "too_long"


def test_add_remove_gap():
    ps = []
    assert cycle.add_start(ps, date(2026, 10, 1))[0]
    ok, other = cycle.add_start(ps, date(2026, 10, 5))
    assert not ok and other == date(2026, 10, 1)
    assert cycle.add_start(ps, date(2026, 9, 3))[0]
    assert [p.start for p in ps] == [date(2026, 9, 3), date(2026, 10, 1)]
    assert cycle.remove_start(ps, date(2026, 9, 3)) and len(ps) == 1


def test_dump_roundtrip():
    ps = [Period(date(2026, 10, 1), date(2026, 10, 5)), Period(date(2026, 10, 29), None, True)]
    assert cycle.parse(cycle.dump(ps)) == ps


def test_stats_and_flags():
    ps = P("2026-01-01", "2026-01-19", "2026-02-07", "2026-03-20", "2026-05-01", "2026-05-19")
    st = cycle.stats(ps)
    assert st.cycles == 5
    assert "short" in st.flags and "long" in st.flags and "irregular" in st.flags
    assert st.regularity == "irregular"
    reg = cycle.stats(P("2026-01-01", "2026-01-29", "2026-02-27", "2026-03-27"))
    assert reg.regularity == "regular" and not reg.flags and reg.avg_cycle == 28


def test_margin_and_late_thresholds():
    reg = P("2026-01-01", "2026-01-29", "2026-02-26", "2026-03-26")
    s = cycle.status(reg, date(2026, 4, 1))
    assert s.margin == 1 and cycle.late_thresholds(s) == (3, 7, 14)


def test_period_days_for_calendar():
    ps = [Period(date(2026, 10, 1), date(2026, 10, 3)), Period(date(2026, 10, 29))]
    days = cycle.period_days(ps, 4, date(2026, 11, 3))
    assert date(2026, 10, 3) in days and date(2026, 10, 4) not in days
    # logged period lasted 3 days, so the open one is assumed 3 days too
    assert date(2026, 10, 31) in days and date(2026, 11, 1) not in days


def test_symptom_insights():
    ps = P("2026-10-05")
    logs = {"2026-10-02": {"sym": ["cramps"], "mood": ["irritable"]},
            "2026-10-03": {"sym": ["cramps"]}}
    assert cycle.pms_counts(logs, ps)["cramps"] == 2
    assert cycle.symptom_counts(logs, date(2026, 10, 10))["irritable"] == 1
