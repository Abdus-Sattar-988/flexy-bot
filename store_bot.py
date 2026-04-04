import telebot
from telebot import types
import os, re, unicodedata, datetime, threading, random, string, logging, functools, time, queue
from flask import Flask, request
import psycopg2
from psycopg2.extras import RealDictCursor

TOKEN                = "8799605089:AAEitRruRKPCCg-ZRuL-r_IpRlnqkNm-6bw"
OWNER_ID             = int(os.getenv("OWNER_ID", "7286057617"))
DATABASE_URL         = "postgresql://flexybot_user:25dGFamQqxa00PZgpwKhUsQMb6chhgLr@dpg-d73sgfkr85hc73fh7log-a/flexybot"
EXCHANGE_RATE        = float(os.getenv("EXCHANGE_RATE", "1"))
WITHDRAW_FEE         = float(os.getenv("WITHDRAW_FEE", "0.0"))
MAX_ATTEMPTS         = int(os.getenv("MAX_ATTEMPTS", "5"))
BAN_DURATION         = int(os.getenv("BAN_DURATION", "5"))
MIN_WITHDRAW         = int(os.getenv("MIN_WITHDRAW", "500"))
FLASK_PORT           = int(os.getenv("PORT", "5000"))
SUPPORT_USER         = os.getenv("SUPPORT_USER", "support")
DEFAULT_CHARGE_PHONE = os.getenv("CHARGE_PHONE", "0555 123 456")
TARGET_SENDER        = os.getenv("TARGET_SENDER", "Mobilis")
SMS_TIME_WINDOW_MIN  = int(os.getenv("SMS_TIME_WINDOW", "60"))
SMS_TIME_OFFSET_MIN  = int(os.getenv("SMS_TIME_OFFSET", "60"))  # فرق ساعة محول الرسائل

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger(__name__)

bot = telebot.TeleBot(TOKEN, parse_mode=None)
app = Flask(__name__)

@app.route("/")
def home():
    return "OK"
    
# ── طابور معالجة رسائل SMS ──────────────────────────────────────
sms_queue = queue.Queue()

def sms_worker():
    """يعمل في background — يعالج رسائل SMS واحدة تلو الأخرى."""
    log.info("SMS worker started.")
    while True:
        try:
            item = sms_queue.get()
            if item is None:
                break
            process_sms(item["amount"], item["sms_time"], item.get("sms_date", ""), item["raw_text"])
        except Exception as e:
            log.error(f"SMS worker error: {e}", exc_info=True)
        finally:
            sms_queue.task_done()

def process_sms(amount, sms_time, sms_date, raw_text):
    """المعالجة الفعلية لكل رسالة SMS من الطابور."""
    sms_datetime = f"{sms_date} {sms_time}".strip()
    try:
        with get_conn() as conn:
            # حفظ الرسالة في sms_vault — نخزن التاريخ+الوقت في حقل time
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO sms_vault (amount, time, sms_time, raw) VALUES (%s, %s, %s, %s)",
                    (amount, sms_datetime, sms_time, raw_text[:200])
                )
            conn.commit()
            log.info(f"SMS saved: {amount} DA at {sms_datetime}")

            # البحث بالمبلغ + الوقت — خلال آخر 24 ساعة
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT * FROM transactions
                    WHERE amount = %s
                      AND send_time = %s
                      AND status = 'unconfirmed'
                      AND created_at >= NOW() - INTERVAL '24 hours'
                    ORDER BY created_at DESC
                    LIMIT 1
                """, (amount, sms_time))
                tx = cur.fetchone()

            if not tx:
                log.info(f"process_sms: no pending tx for {amount} DA — saved as unused")
                for adm in get_admins():
                    try:
                        bot.send_message(
                            adm,
                            f"📥 رسالة شحن جديدة\n"
                            f"💰 المبلغ: {amount} DA\n"
                            f"📅 التاريخ: {sms_date}\n"
                            f"🕒 الوقت: {sms_time}\n"
                            f"⚠️ لم يتم إيجاد معاملة مطابقة — محفوظة في sms_vault"
                        )
                    except Exception as e:
                        log.error(f"Admin notify error: {e}")
                return

            tx = dict(tx)
            uid = tx["user_id"]

            # تأكيد المعاملة وتحديث sms_vault
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE transactions SET status='confirmed', confirmed_by='bot_auto' WHERE id=%s",
                    (tx["id"],)
                )
                cur.execute("""
                    UPDATE sms_vault SET status='used', used_by=%s, used_at=NOW()
                    WHERE id = (
                        SELECT id FROM sms_vault WHERE amount = %s AND status = 'unused'
                        ORDER BY received_at ASC LIMIT 1
                    )
                """, (uid, amount))
            conn.commit()
            log.info(f"process_sms: TX #{tx['id']} auto-confirmed for {uid} — {amount} DA")

        # إشعار المستخدم والأدمن خارج الـ connection
        user = get_user(uid)
        net = round(amount * EXCHANGE_RATE, 2)
        new_bal = round(user["balance"] + net, 2)
        update_user(
            uid,
            balance=new_bal,
            total_charged=round(user["total_charged"] + amount, 2),
            current_tx_attempts=0,
            in_process=False
        )

        try:
            bot.send_message(
                int(uid),
                f"✅ تم تأكيد معاملتك تلقائياً!\n\n"
                f"💰 المبلغ: {amount} DA\n"
                f"📅 التاريخ: {sms_date}\n"
                f"🕒 الوقت: {sms_time}\n"
                f"💳 رصيد أضيف: {net} DA\n"
                f"💳 رصيدك الحالي: {new_bal} DA"
            )
        except Exception as e:
            log.error(f"process_sms notify user error: {e}")

        for adm in get_admins():
            try:
                bot.send_message(
                    adm,
                    f"✅ تأكيد تلقائي\n"
                    f"👤 المستخدم: {uid}\n"
                    f"💰 المبلغ: {amount} DA\n"
                    f"📅 التاريخ: {sms_date}\n"
                    f"🕒 الوقت: {sms_time}"
                )
            except Exception as e:
                log.error(f"Admin notify error: {e}")

    except Exception as e:
        log.error(f"process_sms error: {e}", exc_info=True)


def safe_md(text):
    """يهرّب أي نص قبل إرساله بـ Markdown لمنع كسر التنسيق."""
    if not text:
        return ""
    escape_chars = r"\_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", str(text))


def fmt(text, **kwargs):
    """إرسال رسالة مُنسَّقة — يستخدم Markdown فقط على النصوص الآمنة."""
    return text.format(**kwargs)


def build_username(from_user):
    if from_user.username:
        return "@" + from_user.username
    name = (from_user.first_name or "").strip()
    return name if name else str(from_user.id)


def normalize_text(text):
    """يزيل الـ accents الفرنسية: reçu → recu, rechargé → recharge"""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode("ascii")


def get_conn():
    return psycopg2.connect(DATABASE_URL, sslmode="require")


def init_db():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                );
                CREATE TABLE IF NOT EXISTS admins (
                    user_id BIGINT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT DEFAULT '',
                    balance FLOAT DEFAULT 0,
                    total_charged FLOAT DEFAULT 0,
                    total_withdrawn FLOAT DEFAULT 0,
                    current_tx_attempts INT DEFAULT 0,
                    in_process BOOLEAN DEFAULT FALSE,
                    join_date DATE DEFAULT CURRENT_DATE
                );
                CREATE TABLE IF NOT EXISTS active_codes (
                    code TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS banned (
                    user_id TEXT PRIMARY KEY,
                    unban_time TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS sms_vault (
                    id SERIAL PRIMARY KEY,
                    amount INT,
                    time TEXT,
                    sms_time TEXT,
                    status TEXT DEFAULT 'unused',
                    received_at TIMESTAMP DEFAULT NOW(),
                    used_by TEXT,
                    used_at TIMESTAMP,
                    raw TEXT
                );
                CREATE TABLE IF NOT EXISTS withdrawals (
                    id TEXT PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    gross FLOAT,
                    fee FLOAT,
                    net FLOAT,
                    method TEXT,
                    address TEXT,
                    status TEXT DEFAULT 'pending',
                    date TIMESTAMP DEFAULT NOW(),
                    paid_by TEXT,
                    paid_at TIMESTAMP
                );
                CREATE TABLE IF NOT EXISTS transactions (
                    id SERIAL PRIMARY KEY,
                    user_id TEXT,
                    username TEXT,
                    amount INT,
                    send_time TEXT,
                    status TEXT DEFAULT 'unconfirmed',
                    confirmed_by TEXT DEFAULT 'bot',
                    created_at TIMESTAMP DEFAULT NOW()
                );
            """)
            cur.execute(
                "INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                (OWNER_ID,)
            )
            cur.execute(
                "INSERT INTO settings (key, value) VALUES ('charge_phone', %s) ON CONFLICT DO NOTHING",
                (DEFAULT_CHARGE_PHONE,)
            )
            # FIX: reset in_process للجميع عند إعادة التشغيل
            cur.execute("UPDATE users SET in_process = FALSE WHERE in_process = TRUE")
            # إضافة عمود sms_time إذا لم يكن موجوداً
            cur.execute("""
                ALTER TABLE sms_vault ADD COLUMN IF NOT EXISTS sms_time TEXT
            """)
        conn.commit()
    log.info("Database initialized.")


def is_admin(uid):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM admins WHERE user_id = %s", (int(uid),))
            return cur.fetchone() is not None


def is_owner(uid):
    return int(uid) == int(OWNER_ID)


def is_activated(uid):
    if is_admin(uid):
        return True
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE user_id = %s", (str(uid),))
            return cur.fetchone() is not None


def check_banned(uid):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT unban_time FROM banned WHERE user_id = %s", (str(uid),))
            row = cur.fetchone()
            if row:
                unban_time = row[0]
                if datetime.datetime.now() < unban_time:
                    rem = unban_time - datetime.datetime.now()
                    mins = rem.seconds // 60
                    secs = rem.seconds % 60
                    return True, f"{mins}:{secs:02d}"
                cur.execute("DELETE FROM banned WHERE user_id = %s", (str(uid),))
                conn.commit()
    return False, 0


def get_user(uid):
    uid = str(uid)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "INSERT INTO users (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (uid,)
                )
                conn.commit()
                cur.execute("SELECT * FROM users WHERE user_id = %s", (uid,))
                row = cur.fetchone()
            return dict(row)


def update_user(uid, **kwargs):
    uid = str(uid)
    if not kwargs:
        return
    cols = ", ".join(f"{k} = %s" for k in kwargs)
    vals = list(kwargs.values()) + [uid]
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(f"UPDATE users SET {cols} WHERE user_id = %s", vals)
        conn.commit()


def get_setting(key):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM settings WHERE key = %s", (key,))
            row = cur.fetchone()
            return row[0] if row else None


def set_setting(key, value):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO settings (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = %s",
                (key, value, value)
            )
        conn.commit()


def get_admins():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM admins")
            return [row[0] for row in cur.fetchall()]


def validate_time(t):
    """يتحقق أن الوقت صيغته صحيحة وأرقامه منطقية."""
    m = re.match(r"^(\d{1,2}):(\d{2})$", t)
    if not m:
        return False
    h, mn = int(m.group(1)), int(m.group(2))
    return 0 <= h <= 23 and 0 <= mn <= 59


def time_in_window(sms_time_str, window_minutes=None):
    """يتحقق أن وقت الرسالة ضمن نافذة زمنية من الآن."""
    if window_minutes is None:
        window_minutes = SMS_TIME_WINDOW_MIN
    try:
        now = datetime.datetime.now()
        h, m = map(int, sms_time_str.split(":"))
        sms_dt = now.replace(hour=h, minute=m, second=0, microsecond=0)
        # إذا الوقت في المستقبل، ربما الرسالة من أمس
        if sms_dt > now:
            sms_dt -= datetime.timedelta(days=1)
        diff = abs((now - sms_dt).total_seconds()) / 60
        return diff <= window_minutes
    except Exception:
        return False


def get_candidate_times(user_time):
    """يولّد قائمة أوقات للبحث: الوقت المدخل و +1 دقيقة فقط."""
    try:
        h, m = map(int, user_time.split(":"))
        base = datetime.datetime(2000, 1, 1, h, m)
        times = set()
        for delta in [0, 1]:
            t = base + datetime.timedelta(minutes=delta)
            times.add(f"{t.hour:02d}:{t.minute:02d}")
        return list(times)
    except Exception:
        return [user_time]


def find_sms_match(cur, amount, candidate_times):
    """
    البحث الذكي في sms_vault:
    1. رسالة واحدة بالمبلغ الكامل ضمن الأوقات المرشحة
    2. رسالتان مجموعهما = المبلغ ضمن نفس الأوقات المرشحة
    يرجع: (نوع, قائمة IDs, الوقت المطابق) أو (None, [], "")
    """
    from itertools import combinations

    placeholders = ", ".join(["%s"] * len(candidate_times))

    # المرحلة 1: رسالة واحدة بالمبلغ الكامل
    cur.execute(f"""
        SELECT id, sms_time FROM sms_vault
        WHERE amount = %s
          AND sms_time IN ({placeholders})
          AND status = 'unused'
          AND received_at >= NOW() - INTERVAL '24 hours'
        ORDER BY received_at ASC
        LIMIT 1
        FOR UPDATE SKIP LOCKED
    """, [amount] + candidate_times)
    row = cur.fetchone()
    if row:
        return ("single", [row["id"]], row["sms_time"])

    # المرحلة 2: رسالتان مجموعهما = المبلغ
    cur.execute(f"""
        SELECT id, amount, sms_time FROM sms_vault
        WHERE sms_time IN ({placeholders})
          AND status = 'unused'
          AND received_at >= NOW() - INTERVAL '24 hours'
        ORDER BY received_at ASC
        FOR UPDATE SKIP LOCKED
    """, candidate_times)
    rows = cur.fetchall()

    if len(rows) >= 2:
        for r1, r2 in combinations(rows, 2):
            if r1["amount"] + r2["amount"] == amount:
                return ("split", [r1["id"], r2["id"]], r1["sms_time"])

    return (None, [], "")


def main_keyboard(uid):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        types.KeyboardButton("➕ انشاء معاملة"),
        types.KeyboardButton("💸 سحب الأموال")
    )
    markup.add(
        types.KeyboardButton("📜 سجل السحوبات"),
        types.KeyboardButton("📱 رقم الشحن")
    )
    markup.add(types.KeyboardButton("🎧 الدعم الفني"))
    if is_admin(uid):
        markup.add(
            types.KeyboardButton("📋 سجل المعاملات"),
            types.KeyboardButton("🔑 توليد كود")
        )
        markup.add(types.KeyboardButton("⚙️ لوحة الإدارة"))
    return markup


def cancel_markup():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("❌ إلغاء العملية"))
    return markup


def admin_panel_markup(caller_uid):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("👥 المستخدمون", callback_data="adm_users"),
        types.InlineKeyboardButton("📊 الاحصائيات", callback_data="adm_stats"),
        types.InlineKeyboardButton("📋 طلبات السحب", callback_data="adm_pending_withdrawals"),
        types.InlineKeyboardButton("📱 تغيير رقم الشحن", callback_data="adm_change_phone"),
        types.InlineKeyboardButton("📢 رسالة جماعية", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("✅ تأكيد معاملة", callback_data="adm_confirm_tx"),
        types.InlineKeyboardButton("📥 SMS غير مؤكدة", callback_data="adm_unmatched_sms"),
        types.InlineKeyboardButton("🔄 مسح اليوزرات", callback_data="adm_reset_usernames"),
    )
    if is_owner(caller_uid):
        markup.add(types.InlineKeyboardButton("➕ اضافة ادمن", callback_data="adm_add_admin"))
    return markup


def withdraw_methods_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🏦 بريدي موب (RIP)", callback_data="w_baridi"),
        types.InlineKeyboardButton("🆔 Binance ID", callback_data="w_binance")
    )
    markup.add(types.InlineKeyboardButton("❌ الغاء", callback_data="w_cancel"))
    return markup


def require_activation(func):
    @functools.wraps(func)
    def wrapper(message):
        if not is_activated(message.chat.id):
            bot.send_message(message.chat.id, "❌ غير مفعّل. ارسل /start للتفعيل.")
            return
        banned, rem = check_banned(str(message.chat.id))
        if banned:
            bot.send_message(
                message.chat.id,
                f"🚫 انت محظور مؤقتاً!\nالوقت المتبقي: {rem} دقيقة"
            )
            return
        return func(message)
    return wrapper


@bot.message_handler(commands=["start"])
def cmd_start(message):
    uid = str(message.chat.id)
    user_id = message.chat.id
    username = build_username(message.from_user)

    if is_admin(user_id):
        get_user(uid)
        update_user(uid, username=username)
        bot.send_message(
            user_id,
            f"👋 اهلاً {message.from_user.first_name}\n\n💎 FlexyBot Pro\nانت مسجّل كـ مسؤول ✅",
            reply_markup=main_keyboard(user_id)
        )
        return

    if is_activated(user_id):
        update_user(uid, username=username)
        bot.send_message(
            user_id,
            f"👋 مرحباً بعودتك {message.from_user.first_name}\nاختر احد الخيارات 👇",
            reply_markup=main_keyboard(user_id)
        )
        return

    msg = bot.send_message(
        user_id,
        "🔑 مرحباً بك في FlexyBot Pro!\n\n"
        "هذا النظام للمستخدمين المصرح لهم فقط.\n"
        "📩 ارسل كود التفعيل للمتابعة:"
    )
    bot.register_next_step_handler(msg, step_activate)


def step_activate(message):
    uid = str(message.chat.id)
    code = message.text.strip() if message.text else ""

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM active_codes WHERE code = %s", (code,))
            valid = cur.fetchone()
            if valid:
                cur.execute("DELETE FROM active_codes WHERE code = %s", (code,))
                conn.commit()

    if valid:
        username = build_username(message.from_user)
        get_user(uid)
        update_user(uid, username=username)
        bot.send_message(
            message.chat.id,
            "✅ تم التفعيل بنجاح!\nمرحباً بك في النظام 🎉",
            reply_markup=main_keyboard(message.chat.id)
        )
        log.info(f"New user activated: {uid}")
    else:
        msg = bot.send_message(
            message.chat.id,
            "❌ الكود غير صحيح او منتهي الصلاحية.\n"
            "تواصل مع الادمن للحصول على كود.\n\nاعد ارسال الكود:"
        )
        bot.register_next_step_handler(msg, step_activate)


@bot.message_handler(func=lambda m: m.text == "📱 رقم الشحن")
@require_activation
def show_charge_phone(message):
    phone = get_setting("charge_phone") or DEFAULT_CHARGE_PHONE
    bot.send_message(
        message.chat.id,
        f"📱 رقم الشحن الحالي\n\n{phone}\n\n"
        "يرجى تحويل المبلغ الى هذا الرقم عبر Flexy.\n"
        "بعد التحويل اضغط على ➕ انشاء معاملة"
    )


@bot.message_handler(func=lambda m: m.text == "➕ انشاء معاملة")
@require_activation
def charge_init(message):
    update_user(str(message.chat.id), current_tx_attempts=0, in_process=True)
    msg = bot.send_message(
        message.chat.id,
        "💰 انشاء معاملة جديدة\n\n"
        "📌 تاكد من ارسال الفليكسي للرقم المحدد اولاً.\n\n"
        "🔢 ادخل المبلغ الذي ارسلته (بالدينار):",
        reply_markup=cancel_markup()
    )
    bot.register_next_step_handler(msg, step_charge_amount)


def step_charge_amount(message):
    if message.text == "❌ إلغاء العملية":
        _cancel_process(message)
        return
    if not message.text or not message.text.strip().isdigit():
        msg = bot.send_message(
            message.chat.id,
            "⚠️ يرجى ادخال رقم صحيح فقط (مثال: 1000):"
        )
        bot.register_next_step_handler(msg, step_charge_amount)
        return
    amount = int(message.text.strip())
    if amount <= 0:
        msg = bot.send_message(message.chat.id, "⚠️ المبلغ يجب ان يكون اكبر من 0:")
        bot.register_next_step_handler(msg, step_charge_amount)
        return
    msg = bot.send_message(
        message.chat.id,
        f"✅ المبلغ: {amount} DA\n\n"
        "🕒 ادخل وقت الرسالة بالصيغة HH:MM (مثال: 14:20):"
    )
    bot.register_next_step_handler(msg, step_charge_verify, amount)


def step_charge_verify(message, amount):
    uid = str(message.chat.id)
    if message.text == "❌ إلغاء العملية":
        _cancel_process(message)
        return

    user_time = message.text.strip() if message.text else ""

    if not validate_time(user_time):
        msg = bot.send_message(
            message.chat.id,
            "⚠️ وقت غير صحيح. ادخله بالشكل HH:MM مثال 14:20 او 09:05:"
        )
        bot.register_next_step_handler(msg, step_charge_verify, amount)
        return

    # normalize: 2:50 → 02:50
    h, m = user_time.split(":")
    user_time = f"{int(h):02d}:{int(m):02d}"

    user = get_user(uid)
    username = build_username(message.from_user)

    # أوقات البحث: الوقت المدخل ± دقيقة
    candidate_times = get_candidate_times(user_time)

    match_type = None
    matched_ids = []
    matched_time = ""

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            match_type, matched_ids, matched_time = find_sms_match(cur, amount, candidate_times)

            if match_type:
                # تعليم كل الرسائل المطابقة كـ used
                for sms_id in matched_ids:
                    cur.execute(
                        "UPDATE sms_vault SET status='used', used_by=%s, used_at=NOW() WHERE id=%s",
                        (uid, sms_id)
                    )
                cur.execute(
                    "INSERT INTO transactions (user_id, username, amount, send_time, status, confirmed_by) "
                    "VALUES (%s, %s, %s, %s, 'confirmed', 'bot')",
                    (uid, username, amount, matched_time)
                )
                conn.commit()
            else:
                cur.execute(
                    "INSERT INTO transactions (user_id, username, amount, send_time, status) "
                    "VALUES (%s, %s, %s, %s, 'unconfirmed')",
                    (uid, username, amount, user_time)
                )
                conn.commit()

    if match_type:
        net = round(amount * EXCHANGE_RATE, 2)
        new_bal = round(user["balance"] + net, 2)
        new_charged = round(user["total_charged"] + amount, 2)
        update_user(uid, balance=new_bal, total_charged=new_charged,
                    current_tx_attempts=0, in_process=False)

        # رسالة مختلفة إذا تم دمج رسائل مقسّمة
        if match_type == "split":
            extra = f"🔀 تم دمج {len(matched_ids)} رسائل مقسّمة تلقائياً\n"
        else:
            extra = ""

        bot.send_message(
            message.chat.id,
            f"✅ تمت عملية الشحن بنجاح!\n\n"
            f"💵 المبلغ المرسل: {amount} DA\n"
            f"🕒 الوقت المطابق: {matched_time}\n"
            f"{extra}"
            f"📉 خصم النظام: {round(amount * (1 - EXCHANGE_RATE), 2)} DA\n"
            f"💰 رصيد اضيف: {net} DA\n"
            f"💳 رصيدك الان: {new_bal} DA",
            reply_markup=main_keyboard(message.chat.id)
        )
        log.info(f"Charge success ({match_type}): {uid} - {amount} DA at {matched_time} ids={matched_ids}")

    else:
        update_user(uid, current_tx_attempts=0, in_process=False)
        bot.send_message(
            message.chat.id,
            f"⏳ رسالة الشحن لم تصل بعد!\n\n"
            f"💰 المبلغ: {amount} DA\n"
            f"🕒 الوقت: {user_time}\n\n"
            f"📋 تم حفظ طلبك — سيتم تأكيده تلقائياً فور وصول رسالة الشحن ✅",
            reply_markup=main_keyboard(message.chat.id)
        )
        log.info(f"TX saved as unconfirmed: {uid} - {amount} DA at {user_time}")


def _cancel_process(message):
    update_user(str(message.chat.id), in_process=False)
    bot.send_message(
        message.chat.id,
        "🏠 تم الغاء العملية.",
        reply_markup=main_keyboard(message.chat.id)
    )


@bot.message_handler(func=lambda m: m.text == "💸 سحب الأموال")
@require_activation
def withdraw_init(message):
    uid = str(message.chat.id)
    user = get_user(uid)
    bal = user["balance"]
    if bal < MIN_WITHDRAW:
        bot.send_message(
            message.chat.id,
            f"❌ لا يمكن السحب!\n\n"
            f"💳 رصيدك الحالي: {bal:.2f} DA\n"
            f"📌 الحد الادنى للسحب: {MIN_WITHDRAW} DA"
        )
        return
    fee = round(bal * WITHDRAW_FEE, 2)
    net = round(bal - fee, 2)
    bot.send_message(
        message.chat.id,
        f"💸 طلب سحب جديد\n\n"
        f"💳 رصيدك: {bal:.2f} DA\n"
        f"✅ الصافي: {net:.2f} DA\n\n"
        "اختر وسيلة السحب:",
        reply_markup=withdraw_methods_markup()
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("w_"))
def withdraw_method_callback(call):
    bot.answer_callback_query(call.id)
    if call.data == "w_cancel":
        try:
            bot.edit_message_reply_markup(
                call.message.chat.id, call.message.message_id, reply_markup=None
            )
        except Exception:
            pass
        bot.send_message(
            call.message.chat.id,
            "🏠 تم الغاء طلب السحب.",
            reply_markup=main_keyboard(call.message.chat.id)
        )
        return
    method = "بريدي موب (RIP)" if call.data == "w_baridi" else "Binance ID"
    placeholder = "رقم CCP / RIP" if call.data == "w_baridi" else "Binance Pay ID / UID"
    try:
        bot.edit_message_reply_markup(
            call.message.chat.id, call.message.message_id, reply_markup=None
        )
    except Exception:
        pass
    msg = bot.send_message(
        call.message.chat.id,
        f"📝 {method}\n\nارسل {placeholder} الخاص بك:",
        reply_markup=cancel_markup()
    )
    bot.register_next_step_handler(msg, step_process_withdrawal, method)


def step_process_withdrawal(message, method):
    uid = str(message.chat.id)
    if message.text == "❌ إلغاء العملية":
        bot.send_message(
            message.chat.id,
            "🏠 تم الالغاء.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    user = get_user(uid)
    bal = user["balance"]
    if bal < MIN_WITHDRAW:
        bot.send_message(
            message.chat.id,
            "❌ رصيد غير كافٍ.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    fee = round(bal * WITHDRAW_FEE, 2)
    net = round(bal - fee, 2)
    # FIX: wid قصير لضمان عدم تجاوز 64 بايت في callback_data
    wid = "W" + "".join(random.choices(string.digits, k=6))
    address = message.text.strip()
    username = build_username(message.from_user)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO withdrawals (id, user_id, username, gross, fee, net, method, address)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (wid, uid, username, bal, fee, net, method, address))
        conn.commit()

    update_user(uid, balance=0.0, total_withdrawn=round(user["total_withdrawn"] + net, 2))

    bot.send_message(
        message.chat.id,
        f"✅ تم ارسال طلب السحب بنجاح!\n\n"
        f"🔖 رقم الطلب: {wid}\n"
        f"💰 المبلغ الصافي: {net:.2f} DA\n"
        f"🛠 الوسيلة: {method}\n"
        f"📍 العنوان: {address}\n\n"
        "سيتم معالجة طلبك خلال 24 ساعة.",
        reply_markup=main_keyboard(message.chat.id)
    )

    # FIX: callback_data يحتوي فقط على wid (الـ uid يجلب من DB عند الحاجة)
    admin_markup = types.InlineKeyboardMarkup()
    admin_markup.add(
        types.InlineKeyboardButton("✅ تم الدفع", callback_data=f"pay_done_{wid}"),
        types.InlineKeyboardButton("❌ رفض الطلب", callback_data=f"pay_reject_{wid}")
    )
    for adm in get_admins():
        try:
            bot.send_message(
                adm,
                f"🔔 طلب سحب جديد #{wid}\n\n"
                f"👤 المستخدم: {uid} ({username})\n"
                f"💰 الصافي: {net:.2f} DA\n"
                f"🛠 الوسيلة: {method}\n"
                f"📍 العنوان: {address}",
                reply_markup=admin_markup
            )
        except Exception as e:
            log.error(f"Failed to notify admin {adm}: {e}")


@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_"))
def admin_payment_decision(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    bot.answer_callback_query(call.id)

    parts = call.data.split("_")
    action = parts[1]
    wid = parts[2]

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT * FROM withdrawals WHERE id = %s", (wid,))
            req = cur.fetchone()

    if not req:
        bot.edit_message_text(
            "⚠️ الطلب غير موجود.",
            call.message.chat.id,
            call.message.message_id
        )
        return

    req = dict(req)
    uid = req["user_id"]

    if req["status"] != "pending":
        bot.answer_callback_query(call.id, "⚠️ هذا الطلب تمت معالجته مسبقاً.")
        return

    if action == "done":
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE withdrawals SET status='paid', paid_by=%s, paid_at=NOW() WHERE id=%s",
                    (str(call.from_user.id), wid)
                )
            conn.commit()
        try:
            bot.edit_message_text(
                f"✅ تم تاكيد الدفع #{wid}\nبواسطة: {call.from_user.first_name}",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception:
            pass
        try:
            bot.send_message(
                int(uid),
                f"✅ تم صرف طلبك بنجاح!\n"
                f"رقم الطلب: {wid}\n"
                f"المبلغ: {req['net']:.2f} DA"
            )
        except Exception as e:
            log.error(f"User notify error: {e}")

    elif action == "reject":
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("UPDATE withdrawals SET status='rejected' WHERE id=%s", (wid,))
            conn.commit()
        user = get_user(uid)
        update_user(uid, balance=round(user["balance"] + req["gross"], 2))
        try:
            bot.edit_message_text(
                f"❌ تم رفض الطلب #{wid}",
                call.message.chat.id,
                call.message.message_id
            )
        except Exception:
            pass
        try:
            bot.send_message(
                int(uid),
                f"❌ تم رفض طلب السحب #{wid}\n"
                f"تم اعادة رصيدك {req['gross']:.2f} DA"
            )
        except Exception as e:
            log.error(f"User notify error: {e}")


@bot.message_handler(func=lambda m: m.text == "📜 سجل السحوبات")
@require_activation
def withdrawal_history(message):
    uid = str(message.chat.id)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT id, net, date, method, status FROM withdrawals
                WHERE user_id = %s ORDER BY date DESC LIMIT 10
            """, (uid,))
            rows = cur.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📜 لا توجد عمليات سحب سابقة بعد.")
        return

    status_icons = {"pending": "⌛", "paid": "✅", "rejected": "❌"}
    text = "📜 آخر 10 عمليات سحب:\n\n"
    for w in rows:
        icon = status_icons.get(w["status"], "?")
        date_str = w["date"].strftime("%Y-%m-%d %H:%M") if w["date"] else "-"
        text += f"{icon} {w['id']} | {w['net']:.2f} DA\n   📅 {date_str} - {w['method']}\n\n"

    if is_admin(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المنتهية", callback_data="clear_w_done"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_w_all"),
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "🎧 الدعم الفني")
@require_activation
def support(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📩 تواصل مع الدعم", url=f"https://t.me/{SUPPORT_USER}")
    )
    bot.send_message(
        message.chat.id,
        "🎧 الدعم الفني\n\nهل تواجه مشكلة؟ تواصل مع الدعم مباشرةً.",
        reply_markup=markup
    )


@bot.message_handler(func=lambda m: m.text == "❌ إلغاء العملية")
def global_cancel(message):
    uid = str(message.chat.id)
    if is_activated(uid):
        update_user(uid, in_process=False)
    bot.send_message(
        message.chat.id,
        "🏠 تم الالغاء والعودة للقائمة الرئيسية.",
        reply_markup=main_keyboard(message.chat.id)
    )


@bot.message_handler(func=lambda m: m.text == "📋 سجل المعاملات")
@require_activation
def view_transactions(message):
    uid = str(message.chat.id)
    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if is_admin(message.chat.id):
                cur.execute("""
                    SELECT user_id, username, amount, send_time, status, created_at
                    FROM transactions ORDER BY created_at DESC LIMIT 20
                """)
            else:
                cur.execute("""
                    SELECT user_id, username, amount, send_time, status, created_at
                    FROM transactions WHERE user_id = %s ORDER BY created_at DESC LIMIT 20
                """, (uid,))
            rows = cur.fetchall()

    if not rows:
        bot.send_message(message.chat.id, "📋 لا توجد معاملات بعد.")
        return

    confirmed = [r for r in rows if r["status"] == "confirmed"]
    unconfirmed = [r for r in rows if r["status"] == "unconfirmed"]

    text = "📋 سجل المعاملات\n\n"
    text += f"✅ المعاملات المؤكدة ({len(confirmed)}):\n"
    for r in confirmed[:10]:
        date_str = r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "-"
        display_name = r["username"] if r["username"] else r["user_id"]
        text += f"  👤 {display_name}\n  💰 {r['amount']} DA | 🕒 {r['send_time']} | 📅 {date_str}\n\n"
    if not confirmed:
        text += "  لا توجد\n\n"

    text += f"❌ المعاملات غير المؤكدة ({len(unconfirmed)}):\n"
    for r in unconfirmed[:10]:
        date_str = r["created_at"].strftime("%Y-%m-%d") if r["created_at"] else "-"
        display_name = r["username"] if r["username"] else r["user_id"]
        text += f"  👤 {display_name}\n  💰 {r['amount']} DA | 🕒 {r['send_time']} | 📅 {date_str}\n\n"
    if not unconfirmed:
        text += "  لا توجد\n"

    if is_admin(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المؤكدة", callback_data="clear_tx_confirmed"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_tx_all"),
        )
        bot.send_message(message.chat.id, text, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, text)


@bot.message_handler(func=lambda m: m.text == "🔑 توليد كود" and is_admin(m.chat.id))
def generate_code(message):
    code = "".join(random.choices(string.ascii_uppercase + string.digits, k=10))
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO active_codes (code) VALUES (%s) ON CONFLICT DO NOTHING",
                (code,)
            )
        conn.commit()
    bot.send_message(
        message.chat.id,
        f"🎫 كود تفعيل جديد:\n\n{code}\n\nاعطِ هذا الكود للمستخدم الجديد.\nصالح للاستخدام مرة واحدة فقط."
    )


@bot.message_handler(func=lambda m: m.text == "⚙️ لوحة الإدارة" and is_admin(m.chat.id))
def admin_panel(message):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM users")
            users_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM active_codes")
            codes_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM withdrawals WHERE status='pending'")
            pending = cur.fetchone()[0]
    bot.send_message(
        message.chat.id,
        f"⚙️ لوحة الادارة\n\n"
        f"👥 المستخدمون: {users_count}\n"
        f"🎫 الاكواد المتاحة: {codes_count}\n"
        f"⌛ طلبات السحب المعلقة: {pending}\n\n"
        "اختر اجراءً:",
        reply_markup=admin_panel_markup(message.chat.id)
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    bot.answer_callback_query(call.id)

    if call.data == "adm_stats":
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM users")
                users_count = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(amount),0) FROM sms_vault WHERE status='used'")
                total_charged = cur.fetchone()[0]
                cur.execute("SELECT COALESCE(SUM(net),0) FROM withdrawals WHERE status='paid'")
                total_withdrawn = cur.fetchone()[0]
                cur.execute("SELECT COUNT(*) FROM sms_vault WHERE status='unused'")
                unused = cur.fetchone()[0]
        bot.send_message(
            call.message.chat.id,
            f"📊 احصائيات النظام\n\n"
            f"👥 اجمالي المستخدمين: {users_count}\n"
            f"📥 اجمالي الشحن: {total_charged:.2f} DA\n"
            f"📤 اجمالي السحب: {total_withdrawn:.2f} DA\n"
            f"📦 رسائل متاحة: {unused}"
        )

    elif call.data == "adm_users":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT user_id, username, balance, total_charged
                    FROM users ORDER BY total_charged DESC LIMIT 10
                """)
                rows = cur.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "👥 لا يوجد مستخدمون بعد.")
            return
        for r in rows:
            # FIX: عرض الـ username مع معالجة الحالات الثلاث: @username / الاسم / الـ ID
            raw_uname = r["username"] or ""
            if raw_uname.startswith("@"):
                display = raw_uname
            elif raw_uname:
                display = raw_uname
            else:
                display = f"ID: {r['user_id']}"

            text = (
                f"👤 مستخدم\n"
                f"🆔 {r['user_id']}\n"
                f"👤 {display}\n"
                f"💳 الرصيد: {r['balance']:.2f} DA\n"
                f"📥 اجمالي الشحن: {r['total_charged']:.2f} DA"
            )
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🗑 حذف", callback_data=f"del_user_{r['user_id']}"),
                types.InlineKeyboardButton("💰 تعديل رصيده", callback_data=f"edit_bal_{r['user_id']}")
            )
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == "adm_pending_withdrawals":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT id, user_id, username, net, method, address FROM withdrawals WHERE status='pending'"
                )
                rows = cur.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "✅ لا توجد طلبات سحب معلقة.")
            return
        for w in rows:
            display = w["username"] if w["username"] else w["user_id"]
            text = (
                f"🔔 طلب سحب #{w['id']}\n"
                f"👤 {display}\n"
                f"💰 {w['net']:.2f} DA | {w['method']}\n"
                f"📍 {w['address']}"
            )
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("✅ تم الدفع", callback_data=f"pay_done_{w['id']}"),
                types.InlineKeyboardButton("❌ رفض", callback_data=f"pay_reject_{w['id']}")
            )
            bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == "adm_clear_tx":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المؤكدة فقط", callback_data="clear_tx_confirmed"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_tx_all"),
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="clear_cancel"))
        bot.send_message(call.message.chat.id, "⚠️ ماذا تريد حذف من سجل المعاملات؟", reply_markup=markup)

    elif call.data == "adm_clear_withdrawals":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المدفوعة/المرفوضة", callback_data="clear_w_done"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_w_all"),
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="clear_cancel"))
        bot.send_message(call.message.chat.id, "⚠️ ماذا تريد حذف من سجل السحوبات؟", reply_markup=markup)

    elif call.data == "adm_clear_sms":
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المستخدمة فقط", callback_data="clear_sms_used"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_sms_all"),
        )
        markup.add(types.InlineKeyboardButton("❌ إلغاء", callback_data="clear_cancel"))
        bot.send_message(call.message.chat.id, "⚠️ ماذا تريد حذف من SMS Vault؟", reply_markup=markup)

    elif call.data == "adm_broadcast":
        msg = bot.send_message(
            call.message.chat.id,
            "📢 ارسال رسالة جماعية\n\nارسل النص الذي تريد ارساله لجميع المستخدمين:",
            reply_markup=cancel_markup()
        )
        bot.register_next_step_handler(msg, step_broadcast)

    elif call.data == "adm_confirm_tx":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, user_id, username, amount, send_time, created_at
                    FROM transactions WHERE status = 'unconfirmed'
                    ORDER BY created_at DESC LIMIT 10
                """)
                rows = cur.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "✅ لا توجد معاملات غير مؤكدة.")
            return
        text = "المعاملات غير المؤكدة:\n\n"
        for r in rows:
            date_str = r["created_at"].strftime("%Y-%m-%d %H:%M") if r["created_at"] else "-"
            # FIX: عرض الـ username بشكل صحيح
            display = r["username"] if r["username"] else r["user_id"]
            text += (
                f"🔢 رقم: {r['id']}\n"
                f"👤 {display}\n"
                f"💰 {r['amount']} DA | 🕒 {r['send_time']}\n"
                f"📅 {date_str}\n\n"
            )
        text += "---\nارسل رقم المعاملة التي تريد تأكيدها:"
        msg = bot.send_message(
            call.message.chat.id, text, reply_markup=cancel_markup()
        )
        bot.register_next_step_handler(msg, step_confirm_tx_id)

    elif call.data == "adm_unmatched_sms":
        with get_conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT id, amount, time, received_at, raw
                    FROM sms_vault WHERE status = 'unused'
                    ORDER BY received_at DESC LIMIT 15
                """)
                rows = cur.fetchall()
        if not rows:
            bot.send_message(call.message.chat.id, "✅ لا توجد رسائل SMS غير مؤكدة.")
            return
        text = f"📥 رسائل SMS بدون معاملة مطابقة ({len(rows)}):\n\n"
        for r in rows:
            date_str = r["received_at"].strftime("%Y-%m-%d %H:%M") if r["received_at"] else "-"
            text += (
                f"🔢 #{r['id']} | 💰 {r['amount']} DA | 🕒 {r['time']}\n"
                f"📅 {date_str}\n\n"
            )
        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🗑 حذف المستخدمة", callback_data="clear_sms_used"),
            types.InlineKeyboardButton("🗑 حذف الكل", callback_data="clear_sms_all"),
        )
        bot.send_message(call.message.chat.id, text, reply_markup=markup)

    elif call.data == "adm_reset_usernames":
        # FIX: كان يمسح أسماء المستخدمين الذين ليس عندهم @ وهو خطأ
        # الصح: مسح فقط السجلات الفارغة أو التي تحتوي أرقام بدون @
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users SET username = ''
                    WHERE username != ''
                    AND username NOT LIKE '@%'
                    AND username ~ '^[0-9]+$'
                """)
                count = cur.rowcount
            conn.commit()
        bot.send_message(
            call.message.chat.id,
            f"✅ تم مسح {count} username قديم (أرقام فقط).\n"
            "سيتحدث كل مستخدم عند ضغطه /start"
        )

    elif call.data == "adm_change_phone":
        msg = bot.send_message(
            call.message.chat.id,
            "📱 ارسل رقم الشحن الجديد:",
            reply_markup=cancel_markup()
        )
        bot.register_next_step_handler(msg, step_save_new_phone)

    elif call.data == "adm_add_admin":
        # FIX: is_owner يتحقق من المستدعي الحقيقي وليس OWNER_ID الثابت
        if not is_owner(call.from_user.id):
            bot.send_message(call.message.chat.id, "❌ هذا الاجراء للمالك فقط.")
            return
        msg = bot.send_message(
            call.message.chat.id,
            "📩 ارسل Telegram ID الادمن الجديد:"
        )
        bot.register_next_step_handler(msg, step_add_admin)


def step_save_new_phone(message):
    if message.text == "❌ إلغاء العملية":
        bot.send_message(
            message.chat.id, "🏠 تم الالغاء.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    new_phone = message.text.strip()
    old_phone = get_setting("charge_phone")
    set_setting("charge_phone", new_phone)
    bot.send_message(
        message.chat.id,
        f"✅ تم تغيير رقم الشحن!\nالقديم: {old_phone}\nالجديد: {new_phone}"
    )
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users")
            users = [row[0] for row in cur.fetchall()]
    count = 0
    for uid_str in users:
        try:
            bot.send_message(
                int(uid_str),
                f"📢 تم تغيير رقم الشحن الى:\n{new_phone}"
            )
            count += 1
            time.sleep(0.05)  # FIX: rate limiting لمنع حظر Telegram
        except Exception as e:
            log.error(f"Broadcast error for {uid_str}: {e}")
    bot.send_message(
        message.chat.id,
        f"✅ تم ارسال الاشعار الى {count} مستخدم."
    )


def step_add_admin(message):
    try:
        new_id = int(message.text.strip())
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO admins (user_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    (new_id,)
                )
            conn.commit()
        bot.send_message(message.chat.id, f"✅ تمت اضافة {new_id} كادمن.")
        try:
            bot.send_message(new_id, "🎉 تمت ترقيتك كمسؤول في FlexyBot Pro!")
        except Exception:
            pass
    except ValueError:
        bot.send_message(message.chat.id, "❌ ID غير صحيح. يجب ان يكون رقماً.")


def step_broadcast(message):
    if message.text == "❌ إلغاء العملية":
        bot.send_message(
            message.chat.id, "🏠 تم الالغاء.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    broadcast_text = message.text
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM users")
            users = [row[0] for row in cur.fetchall()]
    success, failed = 0, 0
    for uid_str in users:
        try:
            bot.send_message(
                int(uid_str),
                f"📢 اشعار من الادارة\n\n{broadcast_text}"
            )
            success += 1
            time.sleep(0.05)  # FIX: rate limiting
        except Exception as e:
            log.error(f"Broadcast error {uid_str}: {e}")
            failed += 1
    bot.send_message(
        message.chat.id,
        f"📢 تم ارسال الرسالة الجماعية\n\n"
        f"✅ وصلت لـ: {success} مستخدم\n"
        f"❌ فشل: {failed} مستخدم",
        reply_markup=main_keyboard(message.chat.id)
    )


@bot.callback_query_handler(func=lambda c: c.data == "clear_cancel")
def clear_cancel(call):
    bot.answer_callback_query(call.id, "تم الإلغاء")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("clear_"))
def clear_records_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    bot.answer_callback_query(call.id)

    with get_conn() as conn:
        with conn.cursor() as cur:
            if call.data == "clear_tx_confirmed":
                cur.execute("DELETE FROM transactions WHERE status = 'confirmed'")
            elif call.data == "clear_tx_all":
                cur.execute("DELETE FROM transactions")
            elif call.data == "clear_w_done":
                cur.execute("DELETE FROM withdrawals WHERE status IN ('paid', 'rejected')")
            elif call.data == "clear_w_all":
                cur.execute("DELETE FROM withdrawals")
            elif call.data == "clear_sms_used":
                cur.execute("DELETE FROM sms_vault WHERE status = 'used'")
            elif call.data == "clear_sms_all":
                cur.execute("DELETE FROM sms_vault")
            else:
                return
            deleted = cur.rowcount
        conn.commit()

    labels = {
        "clear_tx_confirmed": "المعاملات المؤكدة",
        "clear_tx_all": "جميع المعاملات",
        "clear_w_done": "السحوبات المنتهية",
        "clear_w_all": "جميع السحوبات",
        "clear_sms_used": "رسائل SMS المستخدمة",
        "clear_sms_all": "جميع رسائل SMS",
    }
    label = labels.get(call.data, "السجلات")
    try:
        bot.edit_message_text(
            f"✅ تم حذف {deleted} سجل من {label}.",
            call.message.chat.id,
            call.message.message_id
        )
    except Exception:
        bot.send_message(call.message.chat.id, f"✅ تم حذف {deleted} سجل من {label}.")
    log.info(f"Admin {call.from_user.id} cleared {deleted} records: {call.data}")


@bot.callback_query_handler(func=lambda c: c.data.startswith("del_user_"))
def delete_user_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    uid = call.data.replace("del_user_", "")
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("✅ نعم، احذف", callback_data=f"confirm_del_{uid}"),
        types.InlineKeyboardButton("❌ الغاء", callback_data="cancel_del")
    )
    bot.answer_callback_query(call.id)
    bot.send_message(
        call.message.chat.id,
        f"⚠️ هل تريد حذف المستخدم {uid} نهائياً؟",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("confirm_del_"))
def confirm_delete_user(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    uid = call.data.replace("confirm_del_", "")
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE user_id = %s", (uid,))
        conn.commit()
    bot.answer_callback_query(call.id, "✅ تم الحذف")
    bot.edit_message_text(
        f"🗑 تم حذف المستخدم {uid} بنجاح.",
        call.message.chat.id,
        call.message.message_id
    )
    log.info(f"User {uid} deleted by admin {call.from_user.id}")


@bot.callback_query_handler(func=lambda c: c.data == "cancel_del")
def cancel_delete(call):
    bot.answer_callback_query(call.id, "تم الالغاء")
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception:
        pass


@bot.callback_query_handler(func=lambda c: c.data.startswith("edit_bal_"))
def edit_balance_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ غير مصرح لك.")
        return
    uid = call.data.replace("edit_bal_", "")
    bot.answer_callback_query(call.id)
    user = get_user(uid)
    msg = bot.send_message(
        call.message.chat.id,
        f"💰 تعديل رصيد المستخدم {uid}\n"
        f"💳 رصيده الحالي: {user['balance']:.2f} DA\n\n"
        "ارسل المبلغ (موجب للاضافة، سالب للخصم):\n"
        "مثال: 500 او -200"
    )
    bot.register_next_step_handler(msg, step_edit_balance, uid)


def step_edit_balance(message, uid):
    try:
        amount = float(message.text.strip())
    except (ValueError, AttributeError):
        bot.send_message(message.chat.id, "❌ ارسل رقماً صحيحاً.")
        return
    user = get_user(uid)
    old_bal = user["balance"]
    new_bal = round(old_bal + amount, 2)
    if new_bal < 0:
        bot.send_message(
            message.chat.id,
            f"❌ الرصيد سيصبح سالباً ({new_bal} DA). العملية ملغاة."
        )
        return
    update_user(uid, balance=new_bal)
    op = f"+{amount}" if amount >= 0 else str(amount)
    bot.send_message(
        message.chat.id,
        f"✅ تم تعديل الرصيد بنجاح!\n\n"
        f"👤 المستخدم: {uid}\n"
        f"💳 القديم: {old_bal:.2f} DA\n"
        f"📊 التعديل: {op} DA\n"
        f"💰 الجديد: {new_bal:.2f} DA"
    )
    try:
        bot.send_message(
            int(uid),
            f"💰 تم تعديل رصيدك\nرصيدك الحالي: {new_bal:.2f} DA"
        )
    except Exception as e:
        log.error(f"User notify error: {e}")


def step_confirm_tx_id(message):
    if message.text == "❌ إلغاء العملية":
        bot.send_message(
            message.chat.id, "🏠 تم الالغاء.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    try:
        tx_id = int(message.text.strip())
    except (ValueError, AttributeError):
        bot.send_message(message.chat.id, "❌ ارسل رقم المعاملة فقط (مثال: 5).")
        return

    with get_conn() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT * FROM transactions WHERE id = %s AND status = 'unconfirmed'",
                (tx_id,)
            )
            tx = cur.fetchone()

    if not tx:
        bot.send_message(message.chat.id, "❌ المعاملة غير موجودة او مؤكدة مسبقاً.")
        return

    tx = dict(tx)
    display = tx["username"] if tx["username"] else tx["user_id"]
    info = (
        f"📋 تفاصيل المعاملة #{tx['id']}\n\n"
        f"👤 {display}\n"
        f"💰 المبلغ: {tx['amount']} DA\n"
        f"🕒 وقت الارسال: {tx['send_time']}\n\n"
        "ارسل المبلغ للتاكيد:"
    )
    msg = bot.send_message(message.chat.id, info)
    bot.register_next_step_handler(msg, step_confirm_tx_amount, tx)


def step_confirm_tx_amount(message, tx):
    if message.text == "❌ إلغاء العملية":
        bot.send_message(
            message.chat.id, "🏠 تم الالغاء.",
            reply_markup=main_keyboard(message.chat.id)
        )
        return
    try:
        entered_amount = int(message.text.strip())
    except (ValueError, AttributeError):
        bot.send_message(message.chat.id, "❌ ارسل رقماً صحيحاً.")
        return

    if entered_amount != tx["amount"]:
        bot.send_message(
            message.chat.id,
            f"❌ المبلغ غير متطابق!\n"
            f"المبلغ في المعاملة: {tx['amount']} DA\n"
            f"المبلغ الذي ادخلته: {entered_amount} DA"
        )
        return

    uid = tx["user_id"]
    amount = tx["amount"]
    net = round(amount * EXCHANGE_RATE, 2)
    admin_id = str(message.chat.id)

    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE transactions SET status='confirmed', confirmed_by=%s WHERE id=%s",
                (f"admin:{admin_id}", tx["id"])
            )
        conn.commit()

    user = get_user(uid)
    new_bal = round(user["balance"] + net, 2)
    update_user(
        uid,
        balance=new_bal,
        total_charged=round(user["total_charged"] + amount, 2)
    )

    bot.send_message(
        message.chat.id,
        f"✅ تم تاكيد المعاملة #{tx['id']} بنجاح!\n\n"
        f"👤 المستخدم: {uid}\n"
        f"💰 المبلغ: {amount} DA\n"
        f"💳 رصيد اضيف: {net} DA",
        reply_markup=main_keyboard(message.chat.id)
    )
    try:
        bot.send_message(
            int(uid),
            f"✅ تم تاكيد معاملتك من الادارة!\n\n"
            f"💰 المبلغ: {amount} DA\n"
            f"💳 رصيد اضيف: {net} DA\n"
            f"💳 رصيدك الحالي: {new_bal} DA"
        )
    except Exception as e:
        log.error(f"User notify error: {e}")
    log.info(f"TX #{tx['id']} confirmed by admin {admin_id}")



@app.route("/webhook", methods=["POST"])
def sms_webhook():
    try:
        data = request.get_json(force=True, silent=True) or {}
        raw_text = str(data.get("content", data.get("text", data.get("message", data.get("sms", "")))))
        sender = str(data.get("from", ""))

        sender_ok = (
            TARGET_SENDER in raw_text or
            TARGET_SENDER in sender or
            sender.endswith(TARGET_SENDER)
        )
        if not sender_ok:
            return "IGNORED", 200

        full_text = normalize_text(raw_text)
        log.info(f"SMS received from {sender}: {full_text[:150]}")

        patterns = [
    # للرسالة الأولى: Vous avez rechargé 500.00 DZD DA
    r"recharg[eé]\s+([\d,.]+)\s*dzd\s*da", 
    # للرسالة الثانية: Vous avez reçu un montant de 500.00 DZD
    r"montant\s+de\s+([\d,.]+)\s*dzd",
    # أنماط احتياطية عامة
    r"([\d,.]+)\s*dzd",
    r"([\d,.]+)\s*da",
]

        amount = None
        for pattern in patterns:
            match = re.search(pattern, full_text, re.IGNORECASE)
            if match:
                amount = int(float(match.group(1)))  # 500.00 → 500
                log.info(f"Pattern matched: {pattern} → {amount} DA")
                break

        if amount:
            raw_datetime = str(data.get("time", "")).strip()
            dt_match = re.match(r"(\d{1,2})-(\d{1,2})-(\d{2,4})\s*-\s*(\d{1,2})[.:](\d{2})", raw_datetime)
            if dt_match:
                day, month, year, hour, minute = dt_match.groups()
                year = int(year)
                if year < 100:
                    year += 2000
                sms_date = f"{int(day):02d}/{int(month):02d}/{year}"
                # تعويض فرق الساعة: محول الرسائل ينقص ساعة فنزيدها
                raw_dt = datetime.datetime(year, int(month), int(day), int(hour), int(minute))
                corrected_dt = raw_dt + datetime.timedelta(minutes=SMS_TIME_OFFSET_MIN)
                sms_time = f"{corrected_dt.hour:02d}:{corrected_dt.minute:02d}"
            else:
                time_only = re.sub(r"[^\d.:]", "", raw_datetime.split("-")[-1]).strip().replace(".", ":")
                sms_time = time_only if validate_time(time_only) else datetime.datetime.now().strftime("%H:%M")
                sms_date = datetime.datetime.now().strftime("%d/%m/%Y")
                log.warning(f"Could not parse datetime '{raw_datetime}', fallback: {sms_date} {sms_time}")

            sms_queue.put({"amount": amount, "sms_time": sms_time, "sms_date": sms_date, "raw_text": raw_text})
            log.info(f"SMS queued: {amount} DA at {sms_date} {sms_time} — queue size: {sms_queue.qsize()}")
        else:
            log.warning(f"SMS not matched! Full text: {full_text}")

        return "OK", 200
    except Exception as e:
        log.error(f"Webhook error: {e}", exc_info=True)
        return "OK", 200


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "bot": "FlexyBot Pro"}, 200


def start_polling():
    """يشغّل polling في thread منفصل."""
    log.info("Bot polling started...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10, none_stop=True)


def cleanup_worker():
    """يعمل كل ساعة — يحذف المعاملات غير المؤكدة التي مضى عليها أكثر من 24 ساعة."""
    log.info("Cleanup worker started.")
    while True:
        try:
            time.sleep(3600)  # ينتظر ساعة
            with get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        DELETE FROM transactions
                        WHERE status = 'unconfirmed'
                          AND created_at < NOW() - INTERVAL '24 hours'
                    """)
                    deleted = cur.rowcount
                conn.commit()
            if deleted > 0:
                log.info(f"Cleanup: deleted {deleted} unconfirmed transaction(s) older than 24h")
        except Exception as e:
            log.error(f"Cleanup worker error: {e}", exc_info=True)


def startup():
    """يُشغَّل مرة واحدة عند بدء التطبيق."""
    log.info("Starting FlexyBot Pro...")
    init_db()
    bot.remove_webhook()
    # تشغيل SMS worker
    worker_thread = threading.Thread(target=sms_worker, daemon=True)
    worker_thread.start()
    log.info("SMS worker thread started.")
    # تشغيل Cleanup worker
    cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
    cleanup_thread.start()
    log.info("Cleanup worker thread started.")
    # تشغيل Bot polling
    polling_thread = threading.Thread(target=start_polling, daemon=True)
    polling_thread.start()
    log.info("Polling thread started.")


# يعمل سواء شغّلنا بـ python مباشرة أو بـ gunicorn على Render
startup()

if __name__ == "__main__":
    log.info(f"Flask running on port {FLASK_PORT}")
    app.run(host="0.0.0.0", port=FLASK_PORT, debug=False)
