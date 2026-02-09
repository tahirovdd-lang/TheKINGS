import asyncio
import logging
import json
import os
import time

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, WebAppInfo

from db import init_db, slot_taken, create_appointment

logging.basicConfig(level=logging.INFO)

# ====== BOT TOKEN из окружения ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден. Добавь переменную окружения BOT_TOKEN.")

ADMIN_ID = 6013591658

# ✅ NEW WEBAPP URL (GitHub Pages репо TheKINGS)
WEBAPP_URL = "https://tahirovdd-lang.github.io/TheKINGS/?v=1"

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
router = Router()
dp.include_router(router)

# ====== АНТИ-ДУБЛЬ START ======
_last_start: dict[int, float] = {}

def allow_start(user_id: int, ttl: float = 2.0) -> bool:
    now = time.time()
    prev = _last_start.get(user_id, 0.0)
    if now - prev < ttl:
        return False
    _last_start[user_id] = now
    return True

# ====== КНОПКИ ======
BTN_OPEN_MULTI = "Записаться 👑💈"

def kb_webapp_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_OPEN_MULTI, web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )

# ====== ТЕКСТ ======
def welcome_text() -> str:
    return (
        "🇷🇺 Добро пожаловать в <b>THE KINGS BARBERSHOP</b> 👑💈\n"
        "Запишитесь на удобное время и выберите услуги — нажмите кнопку ниже.\n\n"
        "🇺🇿 <b>THE KINGS BARBERSHOP</b> 👑💈 ga xush kelibsiz!\n"
        "Qulay vaqtga yoziling va xizmatlarni tanlang — pastdagi tugmani bosing.\n\n"
        "🇬🇧 Welcome to <b>THE KINGS BARBERSHOP</b> 👑💈\n"
        "Book a time and choose services — tap the button below."
    )

# ====== /start ======
@router.message(CommandStart())
async def start(message: types.Message):
    if not allow_start(message.from_user.id):
        return
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

@router.message(Command("startapp"))
async def startapp(message: types.Message):
    if not allow_start(message.from_user.id):
        return
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

# ====== HELPERS ======
def clean_str(v) -> str:
    return ("" if v is None else str(v)).strip()

def safe_int(v, default=0) -> int:
    try:
        if v is None or isinstance(v, bool):
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip().replace(" ", "")
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def fmt_sum(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        n = 0
    return f"{n:,}".replace(",", " ")

def tg_label(u: types.User) -> str:
    return f"@{u.username}" if u.username else u.full_name

def build_services_lines(services) -> tuple[list[str], int, int]:
    lines = []
    total = 0
    dur = 0

    if isinstance(services, list):
        for s in services:
            if not isinstance(s, dict):
                continue
            name = clean_str(s.get("name")) or "—"
            price = safe_int(s.get("price"), 0)
            duration = safe_int(s.get("duration"), 0)
            total += max(0, price)
            dur += max(0, duration)

            if price > 0 and duration > 0:
                lines.append(f"• {name} — {fmt_sum(price)} сум • {duration} мин")
            elif price > 0:
                lines.append(f"• {name} — {fmt_sum(price)} сум")
            else:
                lines.append(f"• {name}")

    if not lines:
        lines = ["⚠️ Услуги не указаны"]

    return lines, total, dur

# ====== RECEIVING WEBAPP DATA ======
@router.message(F.web_app_data)
async def webapp_data(message: types.Message):
    raw = message.web_app_data.data
    logging.info(f"WEBAPP DATA RAW: {raw}")

    await message.answer("✅ <b>Заявка получена.</b> Обрабатываю…")

    try:
        data = json.loads(raw) if raw else {}
    except Exception:
        data = {}
    if not isinstance(data, dict):
        data = {}

    # Extract fields from payload (app.js)
    user_name = clean_str(data.get("name")) or message.from_user.full_name
    user_phone = clean_str(data.get("phone"))
    comment = clean_str(data.get("comment"))

    master_id = safe_int(data.get("master_id"), 0)
    master_name = clean_str(data.get("master_name")) or "—"
    date_str = clean_str(data.get("date"))
    time_str = clean_str(data.get("time"))

    services = data.get("services", [])
    lines, calc_total, calc_dur = build_services_lines(services)

    total_price = safe_int(data.get("total_price"), calc_total)
    duration_min = safe_int(data.get("duration_min"), calc_dur)

    # Basic validation
    if master_id <= 0 or not date_str or not time_str:
        await message.answer("⚠️ Данные неполные. Откройте WebApp и отправьте снова.")
        return

    # Check if time slot is taken
    if slot_taken(master_id, date_str, time_str):
        await message.answer(
            "⛔️ <b>Это время уже занято.</b>\n"
            "Пожалуйста, выберите другое время и отправьте заявку снова."
        )
        return

    # Save to DB
    appt_id = create_appointment({
        "user_id": message.from_user.id,
        "user_name": user_name,
        "user_phone": user_phone,
        "master_id": master_id,
        "master_name": master_name,
        "date": date_str,
        "time": time_str,
        "duration_min": duration_min,
        "total_price": total_price,
        "services_json": json.dumps(services, ensure_ascii=False),
        "comment": comment,
        "status": "pending",
    })

    # ADMIN message
    admin_text = (
        "🚨 <b>НОВАЯ ЗАПИСЬ — THE KINGS BARBERSHOP</b>\n"
        f"🆔 <b>#{appt_id}</b>\n\n"
        "<b>Услуги:</b>\n" + "\n".join(lines) +
        f"\n\n💰 <b>Сумма:</b> {fmt_sum(total_price)} сум"
        f"\n⏱ <b>Длительность:</b> {duration_min} мин"
        f"\n💈 <b>Мастер:</b> {master_name}"
        f"\n🗓 <b>Дата:</b> {date_str}"
        f"\n⏰ <b>Время:</b> {time_str}"
        f"\n📞 <b>Телефон:</b> {user_phone or '—'}"
        f"\n👤 <b>Клиент:</b> {user_name}"
        f"\n👤 <b>Telegram:</b> {tg_label(message.from_user)}"
    )
    if comment:
        admin_text += f"\n💬 <b>Комментарий:</b> {comment}"

    await bot.send_message(ADMIN_ID, admin_text)

    # CLIENT confirmation
    client_text = (
        "✅ <b>Ваша запись принята!</b>\n"
        "Мы скоро свяжемся для подтверждения.\n\n"
        f"🆔 <b>#{appt_id}</b>\n"
        f"💈 <b>Мастер:</b> {master_name}\n"
        f"🗓 <b>Дата:</b> {date_str}\n"
        f"⏰ <b>Время:</b> {time_str}\n\n"
        "<b>Услуги:</b>\n" + "\n".join(lines) +
        f"\n\n💰 <b>Сумма:</b> {fmt_sum(total_price)} сум"
        f"\n⏱ <b>Длительность:</b> {duration_min} мин"
    )
    if comment:
        client_text += f"\n💬 <b>Комментарий:</b> {comment}"

    await message.answer(client_text)

# ====== LAUNCH ======
async def main():
    init_db()
    logging.info("✅ Bot started polling…")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
