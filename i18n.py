"""Every user-facing string, in English and Persian.

Persian rule: no line starts with a Latin word, code or URL (Telegram flips it LTR).
Names passed in are HTML-escaped by the caller. Messages are sent with parse_mode=HTML.
"""
from __future__ import annotations

import dates

LANGS = ["en", "fa"]

T: dict[str, dict[str, str]] = {"en": {}, "fa": {}}


def _add(key: str, en: str, fa: str) -> None:
    T["en"][key] = en
    T["fa"][key] = fa


def t(lang: str, key: str, **kw) -> str:
    s = T.get(lang, T["en"]).get(key) or T["en"][key]
    if kw:
        kw = {k: (dates.num(lang, v) if isinstance(v, int) else v) for k, v in kw.items()}
        s = s.format(**kw)
    return s


def days(lang: str, n: int) -> str:
    if lang == "fa":
        return f"{dates.num(lang, n)} روز"
    return f"{n} day" if n == 1 else f"{n} days"


def in_days(lang: str, n: int) -> str:
    if n == 0:
        return t(lang, "today_word")
    if n == 1:
        return t(lang, "tomorrow_word")
    return t(lang, "in_n_days", n=n)


# ---------------------------------------------------------------- onboarding
_add("lang_pick", "🌙 Choose your language\nزبانت رو انتخاب کن",
     "🌙 Choose your language\nزبانت رو انتخاب کن")
_add("welcome",
     "🌙 <b>Hi, I'm Luna.</b>\n"
     "I help you track your period, know what is coming, and, if you want, keep your partner in the loop.\n\n"
     "🔒 <b>Your data is safe here</b>\n"
     "🔐 Everything you log is <b>encrypted</b> before it is saved. Each person has her own key.\n"
     "👤 <b>Only you</b> see your data. Your partner sees only what you switch on.\n"
     "🚫 <b>No ads, no trackers.</b> Your data is never sold or shared.\n"
     "🎛 <b>You're in control:</b> download or delete everything with one tap.\n"
     "🧩 <b>Open source:</b> anyone can check the code.\n\n"
     "<i>Luna is not a medical device and is not a birth control method.</i>",
     "🌙 <b>سلام، من لونا هستم.</b>\n"
     "کمکت می‌کنم پریودت رو ثبت کنی، بدونی چی در راهه و اگه خواستی، پارتنرت هم در جریان باشه.\n\n"
     "🔒 <b>اطلاعاتت اینجا امنه</b>\n"
     "🔐 هر چی ثبت کنی قبل از ذخیره <b>رمزنگاری</b> می‌شه. هر نفر کلید مخصوص خودش رو داره.\n"
     "👤 <b>فقط خودت</b> اطلاعاتت رو می‌بینی. پارتنرت فقط چیزی رو می‌بینه که خودت روشن کنی.\n"
     "🚫 <b>نه تبلیغ، نه ردیاب.</b> اطلاعاتت هیچ‌وقت فروخته یا به کسی داده نمی‌شه.\n"
     "🎛 <b>اختیارش دست خودته:</b> با یه دکمه همه‌چیز رو دانلود یا پاک کن.\n"
     "🧩 <b>متن‌باز:</b> هر کسی می‌تونه کد رو بررسی کنه.\n\n"
     "<i>لونا وسیله پزشکی نیست و روش پیشگیری از بارداری هم نیست.</i>")
_add("btn_privacy", "🔒 How your data is protected", "🔒 اطلاعاتم چطور محافظت می‌شه")
_add("privacy",
     "🔒 <b>How Luna protects your data</b>\n\n"
     "🔐 <b>Encrypted</b>\n"
     "Your periods, notes and name are locked with AES encryption, the same standard banks use, before they are saved. "
     "Every person gets her own key, so one person's key can never open another person's data.\n\n"
     "👤 <b>Only you</b>\n"
     "No other user can open your data, and we never look at it. The bot only answers you about your own account.\n\n"
     "💞 <b>Your partner sees only what you choose</b>\n"
     "You pick each item: phase, period start, PMS days, late period, mood, fertile window. "
     "They never see your notes or your full calendar. Stop sharing at any time and their access ends right away.\n\n"
     "🔗 <b>Safe invite links</b>\n"
     "Each link works one time only and expires after 48 hours.\n\n"
     "🚫 <b>No ads, no trackers, no selling</b>\n"
     "No analytics, no ad networks, no outside services. Your data is never sold or shared.\n\n"
     "🎛 <b>You're in control</b>\n"
     "In ⚙️ Settings you can download all your data as a file, or delete everything with one tap.\n\n"
     "🧩 <b>Open source</b>\n"
     "The code is public, so anyone can check how it works:\n{repo}\n\n"
     "💡 <b>Extra tip:</b> turn on a Telegram passcode (Settings, Privacy and Security, Passcode Lock) "
     "so no one can open your chats on your phone.",
     "🔒 <b>لونا چطور از اطلاعاتت محافظت می‌کنه</b>\n\n"
     "🔐 <b>رمزنگاری‌شده</b>\n"
     "پریودها، یادداشت‌ها و اسمت قبل از ذخیره با رمزنگاری AES قفل می‌شن، همون استانداردی که بانک‌ها استفاده می‌کنن. "
     "هر نفر کلید مخصوص خودش رو داره، پس کلید یه نفر هیچ‌وقت اطلاعات یه نفر دیگه رو باز نمی‌کنه.\n\n"
     "👤 <b>فقط خودت</b>\n"
     "هیچ کاربر دیگه‌ای نمی‌تونه اطلاعاتت رو باز کنه و ما هم هیچ‌وقت بهش نگاه نمی‌کنیم. ربات فقط درباره حساب خودت به خودت جواب می‌ده.\n\n"
     "💞 <b>پارتنرت فقط چیزی رو می‌بینه که خودت انتخاب کنی</b>\n"
     "تک‌تک موارد رو خودت انتخاب می‌کنی: فاز چرخه، شروع پریود، روزهای پی‌ام‌اس، تأخیر پریود، حال روحی، پنجره باروری. "
     "یادداشت‌ها و تقویم کاملت رو هیچ‌وقت نمی‌بینه. هر وقت بخوای اشتراک رو قطع می‌کنی و دسترسیش همون لحظه تموم می‌شه.\n\n"
     "🔗 <b>لینک دعوت امن</b>\n"
     "هر لینک فقط یک بار کار می‌کنه و بعد از ۴۸ ساعت باطل می‌شه.\n\n"
     "🚫 <b>نه تبلیغ، نه ردیاب، نه فروش</b>\n"
     "هیچ ابزار آمارگیری، شبکه تبلیغاتی یا سرویس بیرونی در کار نیست. اطلاعاتت هیچ‌وقت فروخته یا به کسی داده نمی‌شه.\n\n"
     "🎛 <b>اختیارش دست خودته</b>\n"
     "از ⚙️ تنظیمات می‌تونی همه اطلاعاتت رو به‌صورت فایل دانلود کنی یا با یه دکمه همه‌چیز رو پاک کنی.\n\n"
     "🧩 <b>متن‌باز</b>\n"
     "کد ربات عمومیه، پس هر کسی می‌تونه بررسی کنه چطور کار می‌کنه:\n{repo}\n\n"
     "💡 <b>یه پیشنهاد:</b> قفل رمز تلگرام رو روشن کن (تنظیمات، حریم خصوصی و امنیت، قفل رمز) "
     "تا کسی نتونه چت‌هات رو روی گوشیت باز کنه.")
_add("btn_continue", "Let's start 🌸", "بزن بریم 🌸")
_add("ask_tz", "🌍 Where do you live?\nI use this to send reminders at the right time.",
     "🌍 کجا زندگی می‌کنی؟\nبرای اینکه یادآوری‌ها سر وقت برسه.")
_add("ask_last", "🩸 When did your <b>last period</b> start?",
     "🩸 آخرین پریودت کی <b>شروع</b> شد؟")
_add("ask_cycle",
     "🔁 How long is your cycle usually?\n<i>From the first day of one period to the first day of the next.</i>",
     "🔁 معمولاً چرخه‌ات چند روزه‌ست؟\n<i>از روز اول یه پریود تا روز اول پریود بعدی.</i>")
_add("ask_plen", "🩸 How many days does your period usually last?",
     "🩸 پریودت معمولاً چند روز طول می‌کشه؟")
_add("ask_past",
     "📅 Do you remember earlier periods?\nAdding 2 or 3 past start dates makes predictions much better.",
     "📅 پریودهای قبلی یادته؟\nاگه تاریخ شروع ۲ یا ۳ پریود قبل رو اضافه کنی، پیش‌بینی‌ها خیلی دقیق‌تر می‌شه.")
_add("btn_add_past", "📅 Add past periods ✨", "📅 اضافه کردن پریودهای قبلی")
_add("btn_later", "⏰ Later", "⏰ بعداً")
_add("onb_done", "✨ All set! Use the buttons below any time 💕",
     "✨ همه‌چیز آماده‌ست! هر وقت خواستی از دکمه‌های پایین استفاده کن 💕")
_add("not_sure", "🤷‍♀️ Not sure", "🤷‍♀️ نمی‌دونم")
_add("btn_today", "☀️ Today", "☀️ امروز")
_add("btn_yesterday", "🌙 Yesterday", "🌙 دیروز")
_add("btn_pick", "📅 Pick a date", "📅 انتخاب از تقویم")
_add("btn_dont_remember", "🙈 I don't remember", "🙈 یادم نیست")
_add("days_suffix", "{n} days", "{n} روز")
_add("today_word", "today", "امروز")
_add("tomorrow_word", "tomorrow", "فردا")
_add("in_n_days", "in {n} days", "{n} روز دیگه")
_add("use_buttons", "🌸 Just tap a button below 👇", "🌸 کافیه یکی از دکمه‌های پایین رو بزنی 👇")
_add("cancel", "✖️ Cancel", "✖️ انصراف")
_add("back", "⬅️ Back", "بازگشت ↩️")
_add("saved", "💾 Saved ✓", "💾 ذخیره شد ✓")

TZS = [
    ("Asia/Tehran", "🇮🇷 Iran", "🇮🇷 ایران"),
    ("Asia/Dubai", "🇦🇪 UAE", "🇦🇪 امارات"),
    ("Europe/Istanbul", "🇹🇷 Turkey", "🇹🇷 ترکیه"),
    ("Europe/London", "🇬🇧 UK", "🇬🇧 انگلیس"),
    ("Europe/Berlin", "🇪🇺 Central Europe", "🇪🇺 اروپای مرکزی"),
    ("America/Toronto", "🇨🇦 Toronto / US East", "🇨🇦 تورنتو و شرق آمریکا"),
    ("America/Los_Angeles", "🇺🇸 US West", "🇺🇸 غرب آمریکا"),
    ("Australia/Sydney", "🇦🇺 Sydney", "🇦🇺 سیدنی"),
    ("UTC", "🌐 Other (UTC)", "🌐 جای دیگه (یو‌تی‌سی)"),
]


def tz_label(lang: str, tz: str) -> str:
    for z, en, fa in TZS:
        if z == tz:
            return fa if lang == "fa" else en
    return tz


# ---------------------------------------------------------------- menus
MENU = {
    "start": ("🩸 My period started", "🩸 پریودم شروع شد"),
    "end": ("✅ My period ended", "✅ پریودم تموم شد"),
    "today": ("🌸 Today", "🌸 امروز"),
    "log": ("📝 How I feel", "📝 حالم چطوره"),
    "calendar": ("📅 Calendar", "📅 تقویم"),
    "stats": ("📊 Stats", "📊 آمار"),
    "partner": ("💞 Partner", "💞 پارتنر"),
    "settings": ("⚙️ Settings", "⚙️ تنظیمات"),
    "p_today": ("🌸 How she's doing", "🌸 حالش چطوره"),
    "p_coming": ("📅 What's coming", "📅 روزهای پیش رو"),
    "p_help": ("💡 How to help", "💡 چطور کمک کنم"),
}


def menu(lang: str, key: str) -> str:
    en, fa = MENU[key]
    return fa if lang == "fa" else en


LABEL_TO_ACTION = {lbl: k for k, pair in MENU.items() for lbl in pair}

# ---------------------------------------------------------------- calendar
_add("cal_start", "🩸 Tap the day your period started.", "🩸 روزی که پریودت شروع شد رو بزن.")
_add("cal_end", "✅ Tap the day your period ended.", "✅ روزی که پریودت تموم شد رو بزن.")
_add("cal_log", "📝 Pick the day you want to log.", "📝 روزی که می‌خوای ثبت کنی رو انتخاب کن.")
_add("cal_past",
     "📅 <b>Your calendar</b>\n"
     "Tap a day to mark it as a period start. Tap a 🩸 day again to remove it.\n"
     "You can go back month by month and add all the periods you remember.\n\n"
     "🩸 period start   • period day   ✨ next period (estimate)",
     "📅 <b>تقویم تو</b>\n"
     "روی هر روز بزنی، به‌عنوان شروع پریود ثبت می‌شه. اگه دوباره روی 🩸 بزنی، پاک می‌شه.\n"
     "می‌تونی ماه به ماه برگردی عقب و همه پریودهایی که یادته رو اضافه کنی.\n\n"
     "🩸 شروع پریود   • روز پریود   ✨ پریود بعدی (تخمینی)")
_add("future_day", "🔮 That day is in the future.", "🔮 این روز هنوز نرسیده.")
_add("too_close", "🤏 Too close to another period start ({d}).", "🤏 خیلی به شروع یه پریود دیگه ({d}) نزدیکه.")
_add("added", "🩸 Added {d}", "🩸 {d} اضافه شد")
_add("removed", "🧽 Removed {d}", "🧽 {d} پاک شد")

# ---------------------------------------------------------------- start / end
_add("ask_start", "🩸 When did your period start?", "🩸 پریودت کی شروع شد؟")
_add("ask_end", "✅ When did your period end?", "✅ پریودت کی تموم شد؟")
_add("logged_start", "🩸 Logged: your period started {d}. Be gentle with yourself 💗", "🩸 ثبت شد: پریودت {d} شروع شد. با خودت مهربون باش 💗")
_add("partner_told", "💞 Your partner got a short note.", "💞 یه پیام کوتاه برای پارتنرت رفت.")
_add("logged_end", "✅ Logged: your period ended {d}. It lasted {n} 🌼",
     "✅ ثبت شد: پریودت {d} تموم شد. {n} طول کشید 🌼")
_add("end_too_long", "🤔 That would make the period longer than 15 days. Please pick another day.",
     "🤔 این‌طوری پریود بیشتر از ۱۵ روز می‌شه. لطفاً یه روز دیگه انتخاب کن.")
_add("no_open", "There is no period to close. Tap 🩸 when a new one starts.",
     "پریودی برای بستن نیست. هر وقت پریود جدید شروع شد، 🩸 رو بزن.")
_add("already_started", "You already logged a period that started {d}. 🩸",
     "یه پریود که {d} شروع شده قبلاً ثبت کردی. 🩸")
_add("ok_noted", "👌 OK, noted. I'll check again in a few days 🌷", "👌 باشه، یادم می‌مونه. چند روز دیگه دوباره می‌پرسم 🌷")
_add("ok_wait", "👌 OK. Tap 🩸 when it starts. Take care 💗", "👌 باشه. هر وقت شروع شد، 🩸 رو بزن. مراقب خودت باش 💗")

# ---------------------------------------------------------------- today
_add("today_title", "🌸 <b>Today, {d}</b>", "🌸 <b>امروز، {d}</b>")
_add("no_data",
     "🌱 You haven't logged a period yet.\nTap 🩸 when it starts, or add past periods in 📅 Calendar.",
     "🌱 هنوز پریودی ثبت نکردی.\nهر وقت شروع شد 🩸 رو بزن، یا از 📅 تقویم پریودهای قبلی رو اضافه کن.")
_add("stale",
     "🌙 No period logged in a long time. If one started, tap 🩸 or add it in 📅 Calendar.",
     "🌙 خیلی وقته پریودی ثبت نشده. اگه شروع شده، 🩸 رو بزن یا از 📅 تقویم اضافه‌اش کن.")
_add("period_day", "🩸 Day {n} of your period.", "🩸 روز {n} پریودت.")
_add("cycle_day", "🔁 Cycle day {n}.", "🔁 روز {n} چرخه.")
_add("phase_line", "Phase: <b>{p}</b>\n<i>{desc}</i>", "فاز: <b>{p}</b>\n<i>{desc}</i>")
_add("next_line", "📆 Next period: around <b>{d}</b> ({rel}).", "📆 پریود بعدی: حدود <b>{d}</b> ({rel}).")
_add("due_line", "📆 Your period is expected around today.", "📆 پریودت حدوداً امروز انتظار می‌ره.")
_add("late_line", "⏳ Your period is <b>{n}</b> later than expected.", "⏳ پریودت <b>{n}</b> از زمان پیش‌بینی‌شده عقب افتاده.")
_add("late_normal", "<i>Your cycles vary a bit, so a few days is normal.</i>",
     "<i>چرخه‌هات کمی متغیره، پس چند روز تأخیر عادیه.</i>")
_add("fertile_line", "🌱 Fertile window (estimate): {a} to {b}", "🌱 پنجره باروری (تخمینی): {a} تا {b}")
_add("q_rough", "ℹ️ This is a rough estimate. Log a few periods and it gets better.",
     "ℹ️ این یه تخمین اولیه‌ست. با ثبت چند پریود دقیق‌تر می‌شه.")
_add("q_early", "ℹ️ Predictions get better with every period you log.",
     "ℹ️ هر پریودی که ثبت کنی، پیش‌بینی‌ها دقیق‌تر می‌شه.")
_add("btn_helps", "💡 What helps now", "💡 الان چی کمک می‌کنه")
_add("btn_log", "📝 Log how I feel", "📝 ثبت حالم")

PHASES = {
    "period": (("Period", "Rest more if you can. Warmth and water help."),
               ("پریود", "اگه می‌تونی بیشتر استراحت کن. گرما و آب کمک می‌کنه.")),
    "follicular": (("Follicular phase", "Energy often goes up in these days."),
                   ("فاز فولیکولار", "این روزها معمولاً انرژی بالا می‌ره.")),
    "fertile": (("Fertile window", "Energy and mood are often at their best."),
                ("پنجره باروری", "معمولاً انرژی و حال روحی در بهترین حالته.")),
    "ovulation": (("Ovulation (estimate)", "Energy and mood are often at their best."),
                  ("تخمک‌گذاری (تخمینی)", "معمولاً انرژی و حال روحی در بهترین حالته.")),
    "luteal": (("Luteal phase", "Energy may slowly go down."),
               ("فاز لوتئال", "ممکنه انرژی کم‌کم پایین بیاد.")),
    "pms": (("PMS days", "Body and mood may feel more sensitive. Be gentle with yourself."),
            ("روزهای پیش از پریود (پی‌ام‌اس)", "ممکنه بدن و حال روحی حساس‌تر باشه. با خودت مهربون باش.")),
    "due": (("Period expected", "It may start any time now."),
            ("زمان پریود", "هر لحظه ممکنه شروع بشه.")),
    "late": (("Period late", "A few days late is common. Stress and sleep can delay it."),
             ("تأخیر پریود", "چند روز تأخیر رایجه. استرس و خواب می‌تونه عقبش بندازه.")),
    "unknown": (("Not enough data", ""), ("اطلاعات کافی نیست", "")),
}


def phase_name(lang: str, ph: str) -> str:
    return PHASES[ph][1 if lang == "fa" else 0][0]


def phase_desc(lang: str, ph: str) -> str:
    return PHASES[ph][1 if lang == "fa" else 0][1]


# ---------------------------------------------------------------- tips
TIPS_SELF = {
    "period": (
        "♨️ Heat on your belly or lower back (a heating pad or warm bath) eases cramps.\n"
        "💧 Drink water and warm drinks. Less salt and caffeine helps with bloating.\n"
        "🚶‍♀️ Gentle movement like walking or stretching can reduce pain.\n"
        "🥩 Iron-rich food (red meat, lentils, spinach) helps if your flow is heavy.\n"
        "💊 A pain reliever like ibuprofen works best taken early. Follow the label.",
        "♨️ گرما روی شکم یا کمر (کیسه آب گرم یا حموم گرم) دل‌درد رو کم می‌کنه.\n"
        "💧 آب و نوشیدنی گرم بخور. نمک و کافئین کمتر به نفخ کمک می‌کنه.\n"
        "🚶‍♀️ حرکت سبک مثل پیاده‌روی یا کشش می‌تونه درد رو کم کنه.\n"
        "🥩 اگه خونریزیت زیاده، غذای آهن‌دار (گوشت قرمز، عدس، اسفناج) کمک می‌کنه.\n"
        "💊 مسکنی مثل ایبوپروفن اگه زودتر خورده بشه بهتر اثر می‌کنه. طبق دستور مصرف کن."),
    "follicular": (
        "🚀 Good days to start new things and make plans.\n"
        "🏃‍♀️ Harder workouts often feel easier now.\n"
        "😴 Regular sleep keeps your energy steady.",
        "🚀 روزهای خوبی برای شروع کارهای جدید و برنامه‌ریزیه.\n"
        "🏃‍♀️ ورزش‌های سنگین‌تر الان معمولاً راحت‌تره.\n"
        "😴 خواب منظم انرژیت رو ثابت نگه می‌داره."),
    "fertile": (
        "✨ Energy and mood are often high. Enjoy it.\n"
        "🌀 A short pain on one side around ovulation is common.\n"
        "🛡 If you don't want to get pregnant, use contraception. This estimate is not birth control.",
        "✨ معمولاً انرژی و حال روحی بالاست. ازش لذت ببر.\n"
        "🌀 یه درد کوتاه یه‌طرفه حوالی تخمک‌گذاری رایجه.\n"
        "🛡 اگه نمی‌خوای باردار بشی، از روش پیشگیری استفاده کن. این تخمین روش پیشگیری نیست."),
    "luteal": (
        "🍽 Regular meals keep your energy and mood steady.\n"
        "🥜 Food with magnesium (nuts, seeds, dark chocolate, leafy greens) may help.\n"
        "🧘‍♀️ Lighter workouts like yoga or walking feel better for many people.",
        "🍽 وعده‌های منظم انرژی و حالت رو ثابت نگه می‌داره.\n"
        "🥜 غذاهای منیزیم‌دار (مغزها، دونه‌ها، شکلات تلخ، سبزیجات برگ‌سبز) ممکنه کمک کنه.\n"
        "🧘‍♀️ ورزش سبک‌تر مثل یوگا یا پیاده‌روی برای خیلی‌ها حس بهتری داره."),
    "pms": (
        "🗓 Plan a lighter schedule if you can.\n"
        "🧂 Less salt, sugar, caffeine and alcohol can ease bloating and mood swings.\n"
        "🌤 Sleep, a walk and daylight help your mood.\n"
        "👜 Keep pads or a cup in your bag.",
        "🗓 اگه می‌شه برنامه‌ات رو سبک‌تر بچین.\n"
        "🧂 نمک، قند، کافئین و الکل کمتر، نفخ و نوسان خلق رو کم می‌کنه.\n"
        "🌤 خواب، پیاده‌روی و نور روز به حالت کمک می‌کنه.\n"
        "👜 نوار بهداشتی یا کاپ رو توی کیفت داشته باش."),
    "late": (
        "🧳 Stress, travel, illness, weight change and poor sleep can delay a period.\n"
        "🧪 If pregnancy is possible, a home test is reliable from the first day of a missed period.\n"
        "🩺 If you miss 3 periods in a row, or you have pain, talk to a doctor.",
        "🧳 استرس، سفر، بیماری، تغییر وزن و کم‌خوابی می‌تونه پریود رو عقب بندازه.\n"
        "🧪 اگه احتمال بارداری هست، تست خانگی از روز اول تأخیر قابل اعتماده.\n"
        "🩺 اگه ۳ پریود پشت سر هم نیومد، یا درد داری، با پزشک صحبت کن."),
}
TIPS_SELF["ovulation"] = TIPS_SELF["fertile"]
TIPS_SELF["due"] = TIPS_SELF["pms"]

TIPS_PARTNER = {
    "period": (
        "♨️ Offer a heating pad or a hot water bottle.\n"
        "☕ Make her a warm drink or bring her favourite snack.\n"
        "🧺 Take over a chore or two today.\n"
        "👂 Ask \"What would help you right now?\" and listen.",
        "♨️ کیسه آب گرم یا پد گرمایی بهش پیشنهاد بده.\n"
        "☕ یه نوشیدنی گرم یا خوراکی موردعلاقه‌اش رو براش بیار.\n"
        "🧺 امروز یکی دو تا از کارها رو خودت انجام بده.\n"
        "👂 ازش بپرس «الان چی بهت کمک می‌کنه؟» و خوب گوش بده."),
    "follicular": (
        "⚡ Her energy is often higher now. A good time for plans and dates.\n"
        "🎈 Try something new together.",
        "⚡ این روزها معمولاً انرژیش بیشتره. وقت خوبیه برای برنامه و قرار.\n"
        "🎈 یه کار جدید رو با هم امتحان کنید."),
    "fertile": (
        "🥰 Energy and mood are often at their best. Enjoy time together.",
        "🥰 معمولاً انرژی و حالش در بهترین حالته. از وقت با هم بودن لذت ببرید."),
    "luteal": (
        "🌿 Her energy may slowly go down. Keep plans flexible.\n"
        "💌 Small kindness counts: a message, a snack, a walk together.",
        "🌿 ممکنه انرژیش کم‌کم پایین بیاد. برنامه‌ها رو منعطف نگه دار.\n"
        "💌 محبت‌های کوچیک مهمه: یه پیام، یه خوراکی، یه پیاده‌روی با هم."),
    "pms": (
        "🎢 Her mood may change fast. It is not about you, so try not to take it personally.\n"
        "🤍 Be patient. Leave heavy talks for later if they can wait.\n"
        "🍫 Keep snacks, chocolate or her favourite tea at home.\n"
        "🫂 Ask what she needs: some space, or company.",
        "🎢 ممکنه حالش زود عوض بشه. به تو ربطی نداره، سعی کن به خودت نگیری.\n"
        "🤍 صبور باش. اگه حرف‌های سنگین می‌تونه صبر کنه، بذارش برای بعد.\n"
        "🍫 خوراکی، شکلات یا چای موردعلاقه‌اش رو توی خونه داشته باش.\n"
        "🫂 ازش بپرس چی لازم داره: یکم تنهایی یا همراهی."),
    "late": (
        "🌀 Late periods are common. Stress, sleep and travel can cause them.\n"
        "🤗 Check in gently, without pressure.\n"
        "🧪 If you are both unsure, a home pregnancy test is reliable from the first missed day. Decide together, calmly.",
        "🌀 تأخیر پریود رایجه. استرس، خواب و سفر می‌تونه باعثش بشه.\n"
        "🤗 آروم و بدون فشار حالش رو بپرس.\n"
        "🧪 اگه هر دوتون مطمئن نیستید، تست بارداری خانگی از روز اول تأخیر قابل اعتماده. با آرامش با هم تصمیم بگیرید."),
}
TIPS_PARTNER["ovulation"] = TIPS_PARTNER["fertile"]
TIPS_PARTNER["due"] = TIPS_PARTNER["pms"]


def tips(lang: str, phase: str, who: str = "self") -> str:
    table = TIPS_PARTNER if who == "partner" else TIPS_SELF
    pair = table.get(phase) or table["follicular"]
    return pair[1 if lang == "fa" else 0]


_add("helps_title", "💡 <b>What helps now</b> ({p})", "💡 <b>الان چی کمک می‌کنه</b> ({p})")
_add("helps_partner_title", "💡 <b>How you can help</b> ({p})", "💡 <b>چطور می‌تونی کمک کنی</b> ({p})")
_add("partner_footer", "<i>Every person is different. The best tip: ask her.</i>",
     "<i>هر کسی فرق داره. بهترین راه: از خودش بپرس.</i>")
_add("red_flags",
     "🩺 <b>See a doctor if</b> pain stops your daily life, bleeding soaks a pad every hour for several hours, "
     "a period lasts more than 7 days, or you miss 3 periods and you are not pregnant.",
     "🩺 <b>به پزشک مراجعه کن اگه</b> درد جلوی کارهای روزمره‌ات رو می‌گیره، چند ساعت پشت سر هم هر ساعت یه نوار بهداشتی پر می‌شه، "
     "پریود بیشتر از ۷ روز طول می‌کشه، یا ۳ پریود نیومده و باردار نیستی.")

SYMPTOM_TIPS = {
    "cramps": ("Cramps: heat on the belly, gentle stretching, a pain reliever early.",
               "دل‌درد: گرما روی شکم، کشش سبک، مسکن زودهنگام."),
    "headache": ("Headache: water, rest in a dark room, regular meals.",
                 "سردرد: آب، استراحت توی اتاق تاریک، وعده‌های منظم."),
    "bloating": ("Bloating: less salt, more water, a short walk.",
                 "نفخ: نمک کمتر، آب بیشتر، یه پیاده‌روی کوتاه."),
    "backache": ("Back pain: heat on the lower back, gentle stretching.",
                 "کمردرد: گرما روی کمر، کشش سبک."),
    "tender": ("Tender breasts: a soft supportive bra, less caffeine.",
               "حساسیت سینه: سوتین نرم و راحت، کافئین کمتر."),
    "acne": ("Acne: a gentle cleanser, and try not to touch or pick.",
             "جوش: شوینده ملایم، و سعی کن دست نزنی."),
    "fatigue": ("Tiredness: an early night, iron-rich food, a short walk in daylight.",
                "خستگی: زود خوابیدن، غذای آهن‌دار، یه پیاده‌روی کوتاه توی نور روز."),
    "nausea": ("Nausea: small light meals, ginger tea.", "تهوع: وعده‌های کوچیک و سبک، چای زنجبیل."),
    "cravings": ("Cravings: normal. Pair sweets with protein to stay full.",
                 "هوس خوراکی: عادیه. شیرینی رو با پروتئین بخور که سیر بمونی."),
    "insomnia": ("Poor sleep: a cool dark room, no screens before bed.",
                 "بی‌خوابی: اتاق خنک و تاریک، قبل خواب گوشی نه."),
}

# ---------------------------------------------------------------- daily log
OPTS = {
    "flow": [("spotting", "💧 Spotting", "💧 لکه‌بینی"), ("light", "🩸 Light", "🩸 کم"),
             ("medium", "🩸🩸 Medium", "🩸🩸 متوسط"), ("heavy", "🩸🩸🩸 Heavy", "🩸🩸🩸 زیاد")],
    "mood": [("happy", "😊 Happy", "😊 خوشحال"), ("calm", "😌 Calm", "😌 آروم"),
             ("sensitive", "🥺 Sensitive", "🥺 حساس"), ("irritable", "😤 Irritable", "😤 عصبی"),
             ("anxious", "😰 Anxious", "😰 مضطرب"), ("sad", "😢 Sad", "😢 غمگین"),
             ("moody", "🎢 Mood swings", "🎢 نوسان خلق")],
    "sym": [("cramps", "🌀 Cramps", "🌀 دل‌درد"), ("headache", "🤕 Headache", "🤕 سردرد"),
            ("bloating", "🎈 Bloating", "🎈 نفخ"), ("backache", "💥 Back pain", "💥 کمردرد"),
            ("tender", "🫶 Tender breasts", "🫶 حساسیت سینه"), ("acne", "🔴 Acne", "🔴 جوش"),
            ("fatigue", "😴 Tired", "😴 خستگی"), ("nausea", "🤢 Nausea", "🤢 تهوع"),
            ("cravings", "🍫 Cravings", "🍫 هوس خوراکی"), ("insomnia", "🌙 Poor sleep", "🌙 بی‌خوابی")],
    "energy": [("low", "🪫 Low energy", "🪫 انرژی کم"), ("ok", "🔋 Okay", "🔋 معمولی"),
               ("high", "⚡ High energy", "⚡ انرژی زیاد")],
}
OPT_LABEL = {(kind, k): (en, fa) for kind, items in OPTS.items() for k, en, fa in items}


def opt(lang: str, kind: str, key: str) -> str:
    en, fa = OPT_LABEL[(kind, key)]
    return fa if lang == "fa" else en


def item_label(lang: str, key: str) -> str:
    for kind in ("sym", "mood"):
        if (kind, key) in OPT_LABEL:
            return opt(lang, kind, key)
    return key


_add("log_title", "📝 <b>How do you feel?</b> ({d})\nTap everything that fits. It saves as you tap.",
     "📝 <b>حالت چطوره؟</b> ({d})\nهر چی که صدق می‌کنه رو بزن. همون لحظه ذخیره می‌شه.")
_add("sec_flow", "🩸 Flow", "🩸 خونریزی")
_add("sec_mood", "💭 Mood", "💭 حال روحی")
_add("sec_sym", "🫧 Body", "🫧 بدن")
_add("sec_energy", "🔋 Energy", "🔋 انرژی")
_add("btn_other_day", "📅 Another day", "📅 یه روز دیگه")
_add("btn_done", "✅ Done", "✅ تمام")
_add("btn_tell_partner", "💌 Tell my partner", "💌 به پارتنرم بگو")
_add("log_saved", "📝 Saved for {d}.", "📝 برای {d} ذخیره شد.")
_add("log_empty", "📝 Nothing logged for {d}.", "📝 برای {d} چیزی ثبت نشد.")
_add("told_partner", "💌 Sent to your partner.", "💌 برای پارتنرت فرستاده شد.")

# ---------------------------------------------------------------- stats
_add("stats_none",
     "📊 Log at least 2 periods to see stats.\nTip: add past periods in 📅 Calendar.",
     "📊 برای دیدن آمار حداقل ۲ پریود ثبت کن.\nپیشنهاد: از 📅 تقویم پریودهای قبلی رو اضافه کن.")
_add("stats_title", "📊 <b>Your stats</b>", "📊 <b>آمار تو</b>")
_add("st_periods", "• Periods logged: <b>{n}</b>", "• تعداد پریودهای ثبت‌شده: <b>{n}</b>")
_add("st_cycle", "• Average cycle: <b>{a}</b> (shortest {mn}, longest {mx})",
     "• میانگین چرخه: <b>{a}</b> (کوتاه‌ترین {mn}، بلندترین {mx})")
_add("st_period", "• Average period: <b>{a}</b>", "• میانگین طول پریود: <b>{a}</b>")
_add("st_next", "• Next period: around <b>{d}</b>", "• پریود بعدی: حدود <b>{d}</b>")
_add("st_reg_regular", "• Pattern: <b>regular</b> ✅ (varies by {s})", "• الگو: <b>منظم</b> ✅ (اختلاف {s})")
_add("st_reg_variable", "• Pattern: <b>a bit variable</b> (varies by {s})", "• الگو: <b>کمی متغیر</b> (اختلاف {s})")
_add("st_reg_irregular", "• Pattern: <b>irregular</b> (varies by {s})", "• الگو: <b>نامنظم</b> (اختلاف {s})")
_add("st_reg_none", "• Pattern: log 3 cycles to see it", "• الگو: با ثبت ۳ چرخه معلوم می‌شه")
_add("st_recent", "<b>Last cycles</b>", "<b>چرخه‌های اخیر</b>")
_add("st_top", "<b>Most logged (last 3 months)</b>\n{items}", "<b>بیشترین موارد ثبت‌شده (۳ ماه اخیر)</b>\n{items}")
_add("st_pms", "<b>Before your period you often log</b>\n{items}", "<b>قبل از پریود معمولاً ثبت می‌کنی</b>\n{items}")
_add("flag_irregular", "🩺 Your cycle length changes a lot. That can be normal, but it is worth asking a doctor.",
     "🩺 طول چرخه‌ات خیلی تغییر می‌کنه. ممکنه عادی باشه، ولی ارزش داره از پزشک بپرسی.")
_add("flag_short", "🩺 Some cycles were shorter than 21 days. Worth checking with a doctor.",
     "🩺 بعضی چرخه‌هات کوتاه‌تر از ۲۱ روز بوده. بهتره با پزشک چک کنی.")
_add("flag_long", "🩺 Some cycles were longer than 35 days. Worth checking with a doctor.",
     "🩺 بعضی چرخه‌هات بلندتر از ۳۵ روز بوده. بهتره با پزشک چک کنی.")
_add("flag_prolonged", "🩺 Some periods lasted more than 8 days. Worth checking with a doctor.",
     "🩺 بعضی پریودهات بیشتر از ۸ روز طول کشیده. بهتره با پزشک چک کنی.")

# ---------------------------------------------------------------- partner (owner side)
FLAG_LABELS = {
    "phase": ("Cycle phase and next period", "فاز چرخه و پریود بعدی"),
    "start": ("When my period starts", "وقتی پریودم شروع می‌شه"),
    "pms": ("PMS heads-up with tips", "خبر روزهای پی‌ام‌اس با پیشنهاد"),
    "late": ("If my period is late", "اگه پریودم عقب بیفته"),
    "mood": ("My daily mood and symptoms", "حال و علائم روزانه‌ام"),
    "fertile": ("My fertile window", "پنجره باروری‌ام"),
}


def flag_label(lang: str, k: str) -> str:
    return FLAG_LABELS[k][1 if lang == "fa" else 0]


_add("pt_intro",
     "💞 <b>Partner sharing</b>\n"
     "Invite your partner so they know what is coming and how to help.\n"
     "They will never see your notes or your full calendar, only what you turn on below.\n\n"
     "Choose what to share, then create a one-time invite link.",
     "💞 <b>اشتراک با پارتنر</b>\n"
     "پارتنرت رو دعوت کن تا بدونه چی در راهه و چطور می‌تونه کمکت کنه.\n"
     "هیچ‌وقت یادداشت‌ها یا تقویم کاملت رو نمی‌بینه، فقط چیزهایی که پایین روشن کنی.\n\n"
     "انتخاب کن چی به اشتراک گذاشته بشه، بعد لینک دعوت یک‌بار مصرف بساز.")
_add("btn_create_invite", "🔗 Create invite link", "🔗 ساخت لینک دعوت")
_add("invite_made",
     "🔗 <b>Your invite link</b>\nOne-time, works for 48 hours:\n{link}\n\n"
     "Send it to your partner. When they open it, you will get a message here.",
     "🔗 <b>لینک دعوت تو</b>\nیک‌بار مصرفه و ۴۸ ساعت اعتبار داره:\n{link}\n\n"
     "برای پارتنرت بفرستش. وقتی بازش کنه، همین‌جا بهت خبر می‌دم.")
_add("btn_cancel_invite", "✖️ Cancel invite", "✖️ لغو دعوت")
_add("invite_cancelled", "✖️ Invite cancelled. The link no longer works.", "✖️ دعوت لغو شد. لینک دیگه کار نمی‌کنه.")
_add("pt_linked", "💞 <b>You share with {name}.</b>\nTap to turn each item on or off. Changes apply right away.",
     "💞 <b>با {name} به اشتراک گذاشتی.</b>\nروی هر مورد بزن تا روشن یا خاموش بشه. تغییرها همون لحظه اعمال می‌شه.")
_add("btn_nudge", "💌 Send a nudge", "💌 فرستادن یه پیام کوتاه")
_add("btn_stop_sharing", "❌ Stop sharing", "❌ قطع اشتراک")
_add("stop_confirm", "💔 Stop sharing with {name}? They lose access right away.",
     "💔 اشتراک با {name} قطع بشه؟ همون لحظه دسترسیش قطع می‌شه.")
_add("btn_yes_stop", "💔 Yes, stop", "💔 بله، قطع کن")
_add("stopped", "🔒 Done. {name} can't see anything now.", "🔒 انجام شد. {name} دیگه چیزی نمی‌بینه.")
_add("nudge_pick", "💌 What do you want to tell {name}?", "💌 می‌خوای به {name} چی بگی؟")
_add("nudge_sent", "💌 Sent.", "💌 فرستاده شد.")
_add("no_partner_yet", "💞 You don't have a partner linked yet.", "💞 هنوز پارتنری وصل نکردی.")

NUDGES = [
    ("hard", "I'm having a hard day 💛", "امروز روز سختیه برام 💛"),
    ("hug", "I could use a hug 🤗", "یه بغل لازم دارم 🤗"),
    ("snack", "Craving a snack, could you bring me something? 🍫", "هوس خوراکی کردم، یه چیزی برام میاری؟ 🍫"),
    ("heat", "Could you bring me a heating pad or a warm drink? ☕", "کیسه آب گرم یا یه نوشیدنی گرم برام میاری؟ ☕"),
    ("space", "I need some quiet time today 🌿", "امروز یکم آرامش و تنهایی لازم دارم 🌿"),
    ("talk", "Can we talk tonight? 💬", "امشب می‌تونیم با هم حرف بزنیم؟ 💬"),
]

# ---------------------------------------------------------------- partner (partner side)
_add("inv_landing",
     "💞 <b>{name} invited you</b> to follow her cycle on Luna.\n\n"
     "You will see:\n{items}\n\n"
     "You will not see her private notes. She can stop sharing at any time.",
     "💞 <b>{name} دعوتت کرده</b> که چرخه‌اش رو توی لونا دنبال کنی.\n\n"
     "چیزهایی که می‌بینی:\n{items}\n\n"
     "یادداشت‌های خصوصیش رو نمی‌بینی. هر وقت بخواد می‌تونه اشتراک رو قطع کنه.")
_add("btn_accept", "💞 Accept", "💞 قبول")
_add("btn_decline", "🙅 Decline", "🙅 رد کردن")
_add("inv_invalid", "⌛ This invite link has expired or was already used. Ask for a new one.",
     "⌛ این لینک دعوت منقضی شده یا قبلاً استفاده شده. یه لینک جدید بخواه.")
_add("inv_self", "😊 This is your own invite link. Send it to your partner.",
     "😊 این لینک دعوت خودته. برای پارتنرت بفرستش.")
_add("inv_is_tracker",
     "This account already tracks its own cycle, so it can't join as a partner. "
     "Your partner should open the link in their own Telegram.",
     "این حساب خودش چرخه رو ثبت می‌کنه، برای همین نمی‌تونه پارتنر بشه. "
     "پارتنرت باید لینک رو توی تلگرام خودش باز کنه.")
_add("inv_has_other", "You already follow someone. Leave first in ⚙️ Settings.",
     "الان چرخه یه نفر دیگه رو دنبال می‌کنی. اول از ⚙️ تنظیمات خارج شو.")
_add("inv_owner_busy", "She already shares with someone else.", "الان با یه نفر دیگه به اشتراک گذاشته.")
_add("inv_accepted_partner",
     "💞 You're in. Use the buttons below to see how {name} is doing and how you can help.",
     "💞 وصل شدی. با دکمه‌های پایین ببین {name} چطوره و چطور می‌تونی کمکش کنی.")
_add("inv_accepted_owner", "💞 {name} accepted your invite! 🥰", "💞 {name} دعوتت رو قبول کرد! 🥰")
_add("inv_declined_owner", "🙅 {name} declined your invite.", "🙅 {name} دعوتت رو رد کرد.")
_add("inv_declined_partner", "👌 OK. Nothing was shared.", "👌 باشه. چیزی به اشتراک گذاشته نشد.")
_add("partner_lost", "🔒 {name} stopped sharing. You no longer have access.",
     "🔒 {name} اشتراک رو قطع کرد. دیگه دسترسی نداری.")
_add("partner_left_owner", "👋 {name} stopped following your cycle.", "👋 {name} دیگه چرخه‌ات رو دنبال نمی‌کنه.")
_add("partner_restart", "🌸 Send any message if you want to start your own tracking.",
     "🌸 اگه خواستی خودت چرخه‌ات رو ثبت کنی، یه پیام بفرست.")
_add("p_today_title", "🌸 <b>{name} today</b>", "🌸 <b>{name} امروز</b>")
_add("p_period_day", "🩸 She is on day {n} of her period.", "🩸 روز {n} پریودشه.")
_add("p_phase", "Phase: <b>{p}</b>\n<i>{desc}</i>", "فاز: <b>{p}</b>\n<i>{desc}</i>")
_add("p_next", "📆 Next period: around <b>{d}</b> ({rel}).", "📆 پریود بعدی: حدود <b>{d}</b> ({rel}).")
_add("p_late", "⏳ Her period is <b>{n}</b> later than expected.", "⏳ پریودش <b>{n}</b> عقب افتاده.")
_add("p_mood", "📝 Today she logged: {items}", "📝 امروز ثبت کرده: {items}")
_add("p_nothing", "🤍 Nothing shared to show right now.", "🤍 الان چیزی برای نمایش به اشتراک گذاشته نشده.")
_add("p_coming_title", "📅 <b>What's coming</b>", "📅 <b>روزهای پیش رو</b>")
_add("p_c_period", "🩸 Next period: around <b>{d}</b> ({rel})", "🩸 پریود بعدی: حدود <b>{d}</b> ({rel})")
_add("p_c_pms", "🌧 PMS days may start: <b>{d}</b> ({rel})", "🌧 شروع احتمالی روزهای پی‌ام‌اس: <b>{d}</b> ({rel})")
_add("p_c_fertile", "🌱 Fertile window (estimate): {a} to {b}", "🌱 پنجره باروری (تخمینی): {a} تا {b}")
_add("p_no_data", "🌱 She hasn't logged enough yet.", "🌱 هنوز به اندازه کافی ثبت نکرده.")

# ---------------------------------------------------------------- notifications
_add("n_soon", "🌙 Your period may start in about 2 days ({d}).\nGood time to put pads or a cup in your bag.",
     "🌙 احتمالاً حدود ۲ روز دیگه ({d}) پریودت شروع می‌شه.\nوقت خوبیه که نوار بهداشتی یا کاپ رو توی کیفت بذاری.")
_add("n_due", "🌙 Your period is expected around today. Did it start?",
     "🌙 پریودت حدوداً امروز انتظار می‌ره. شروع شده؟")
_add("btn_yes_started", "🩸 Yes, it started", "🩸 آره، شروع شد")
_add("btn_not_yet", "⏳ Not yet", "⏳ هنوز نه")
_add("n_late", "🌙 Your period is {n} later than expected.", "🌙 پریودت {n} عقب افتاده.")
_add("n_endq", "🌙 Has your period ended?", "🌙 پریودت تموم شده؟")
_add("btn_ended_today", "☀️ Yes, today", "☀️ آره، امروز")
_add("btn_ended_yesterday", "🌙 Yes, yesterday", "🌙 آره، دیروز")
_add("n_pms", "🌙 Your PMS days may start now. Be kind to yourself.",
     "🌙 روزهای پی‌ام‌اس ممکنه از الان شروع بشه. با خودت مهربون باش.")
_add("n_fertile", "🌱 Your fertile window may start today. This is an estimate, not birth control.",
     "🌱 پنجره باروریت احتمالاً از امروز شروع می‌شه. این یه تخمینه، روش پیشگیری نیست.")
_add("n_daily", "🌙 How are you feeling today?", "🌙 امروز حالت چطوره؟")
_add("n_discreet", "🌙 You have a new note from Luna.", "🌙 یه پیام جدید از لونا داری.")
_add("btn_show", "👁 Show", "👁 نمایش")
_add("np_pms", "💞 Heads up: {name}'s PMS days may start tomorrow.",
     "💞 خبر: روزهای پی‌ام‌اس {name} احتمالاً از فردا شروع می‌شه.")
_add("np_soon", "💞 {name}'s period may start tomorrow.", "💞 پریود {name} احتمالاً فردا شروع می‌شه.")
_add("np_start", "💞 {name}'s period started {d}.", "💞 پریود {name} {d} شروع شد.")
_add("np_late", "💞 {name}'s period is {n} later than expected.", "💞 پریود {name} {n} عقب افتاده.")
_add("np_mood", "💌 {name} shared how she feels today:\n{items}", "💌 {name} حال امروزش رو فرستاد:\n{items}")
_add("np_nudge", "💌 <b>{name}:</b> {text}", "💌 <b>{name}:</b> {text}")

# ---------------------------------------------------------------- settings
_add("settings_title",
     "⚙️ <b>Settings</b>\n<i>Discreet notifications hide the text on your lock screen until you tap Show.</i>",
     "⚙️ <b>تنظیمات</b>\n<i>اعلان مخفی، متن پیام رو روی صفحه قفل نشون نمی‌ده تا وقتی «نمایش» رو بزنی.</i>")
_add("s_lang", "🌐 Language: English", "🌐 زبان: فارسی")
_add("s_cal_g", "📆 Calendar: Gregorian", "📆 تقویم: میلادی")
_add("s_cal_j", "📆 Calendar: Solar Hijri", "📆 تقویم: شمسی")
_add("s_hour", "🕘 Reminder time: {h}:00", "🕘 ساعت یادآوری: {h}:۰۰")
_add("s_tz", "🌍 Time zone: {z}", "🌍 منطقه زمانی: {z}")
_add("s_discreet", "🔕 Discreet notifications: {v}", "🔕 اعلان مخفی: {v}")
_add("s_daily", "📝 Daily check-in reminder: {v}", "📝 یادآوری روزانه ثبت حال: {v}")
_add("s_fertile", "🌱 Show fertile window: {v}", "🌱 نمایش پنجره باروری: {v}")
_add("s_plen", "🩸 Usual period length: {n}", "🩸 طول معمول پریود: {n}")
_add("s_cycle", "🔁 Usual cycle length: {n}", "🔁 طول معمول چرخه: {n}")
_add("s_export", "📤 Download my data", "📤 دانلود اطلاعاتم")
_add("s_delete", "🗑 Delete all my data", "🗑 پاک کردن همه اطلاعاتم")
_add("s_leave", "🚪 Stop following", "🚪 قطع دنبال کردن")
_add("on", "On", "روشن")
_add("off", "Off", "خاموش")
_add("pick_hour", "🕘 When should I send reminders?", "🕘 یادآوری‌ها چه ساعتی بیاد؟")
_add("pick_lang", "🌐 Choose your language", "🌐 زبانت رو انتخاب کن")
_add("del_confirm",
     "🗑 <b>Delete everything?</b>\nThis removes all your periods, logs and settings, and ends partner sharing. It can't be undone.",
     "🗑 <b>همه‌چیز پاک بشه؟</b>\nهمه پریودها، ثبت‌ها و تنظیماتت پاک می‌شه و اشتراک با پارتنر هم قطع می‌شه. قابل برگشت نیست.")
_add("btn_yes_delete", "🗑 Yes, delete everything", "🗑 بله، همه‌چیز پاک بشه")
_add("deleted", "🧹 Everything is deleted. Send any message if you want to start again.",
     "🧹 همه‌چیز پاک شد. اگه خواستی از اول شروع کنی، یه پیام بفرست.")
_add("export_caption", "📤 Your data. Only you received this file.",
     "📤 اطلاعات تو. این فایل فقط برای خودت فرستاده شد.")
_add("leave_confirm", "👋 Stop following {name}'s cycle?", "👋 دنبال کردن چرخه {name} قطع بشه؟")
_add("btn_yes_leave", "👋 Yes, stop", "👋 بله، قطع کن")
_add("left", "👋 Done. You no longer follow {name}.", "👋 انجام شد. دیگه چرخه {name} رو دنبال نمی‌کنی.")
_add("someone", "your partner", "پارتنرت")
