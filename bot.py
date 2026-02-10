import asyncio
import logging
import json
import os
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, Command
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, WebAppInfo,
    InlineKeyboardMarkup, InlineKeyboardButton
)

logging.basicConfig(level=logging.INFO)

# ====== НАСТРОЙКИ (из ENV) ======
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise RuntimeError("❌ BOT_TOKEN не найден. Добавь переменную окружения BOT_TOKEN.")

BOT_USERNAME = os.getenv("BOT_USERNAME", "THE_KINGS_Bot").replace("@", "")  # без @
ADMIN_ID = int(os.getenv("ADMIN_ID", "6013591658"))
CHANNEL_ID = os.getenv("CHANNEL_ID", "@THEKINGS_BARBERSHOP")

# ✅ ВАЖНО: для GitHub Pages project page лучше index.html
WEBAPP_URL = os.getenv(
    "WEBAPP_URL",
    "https://tahirovdd-lang.github.io/TheKINGS/index.html?v=1"
)

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

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
BTN_OPEN_MULTI = "Записаться • Book • Ro‘yxatdan o‘tish"

def kb_webapp_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=BTN_OPEN_MULTI, web_app=WebAppInfo(url=WEBAPP_URL))]],
        resize_keyboard=True
    )

def kb_channel_deeplink() -> InlineKeyboardMarkup:
    deeplink = f"https://t.me/{BOT_USERNAME}?startapp=booking"
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=BTN_OPEN_MULTI, url=deeplink)]]
    )

# ====== ТЕКСТ ======
def welcome_text() -> str:
    return (
        "👑 <b>THE KINGS Barbershop</b>\n\n"
        "🇷🇺 Добро пожаловать! Нажмите кнопку ниже, чтобы открыть онлайн-запись.\n\n"
        "🇺🇿 Xush kelibsiz! Pastdagi tugmani bosib, online yoziling.\n\n"
        "🇬🇧 Welcome! Tap the button below to book an appointment."
    )

# ====== /start ======
@dp.message(CommandStart())
async def start(message: types.Message):
    if not allow_start(message.from_user.id):
        return
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

@dp.message(Command("startapp"))
async def startapp(message: types.Message):
    if not allow_start(message.from_user.id):
        return
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

# ====== ПОСТ В КАНАЛ ======
@dp.message(Command("post_booking"))
async def post_booking(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return await message.answer("⛔️ Нет доступа.")

    text = (
        "👑 <b>THE KINGS Barbershop</b>\n\n"
        "🇷🇺 Нажмите кнопку ниже, чтобы открыть онлайн-запись.\n\n"
        "🇺🇿 Pastdagi tugma orqali online yoziling.\n\n"
        "🇬🇧 Tap the button below to book an appointment."
    )

    try:
        sent = await bot.send_message(CHANNEL_ID, text, reply_markup=kb_channel_deeplink())
        try:
            await bot.pin_chat_message(CHANNEL_ID, sent.message_id, disable_notification=True)
            await message.answer("✅ Пост отправлен и закреплён.")
        except Exception:
            await message.answer(
                "✅ Пост отправлен.\n"
                "⚠️ Не удалось закрепить — дай боту право «Закреплять сообщения» или закрепи вручную."
            )
    except Exception as e:
        logging.exception("CHANNEL POST ERROR")
        await message.answer(f"❌ Ошибка отправки в канал: <code>{e}</code>")

# ====== ВСПОМОГАТЕЛЬНЫЕ ======
def fmt_sum(n: int) -> str:
    try:
        n = int(n)
    except Exception:
        n = 0
    return f"{n:,}".replace(",", " ")

def tg_label(u: types.User) -> str:
    return f"@{u.username}" if u.username else u.full_name

def clean_str(v) -> str:
    return ("" if v is None else str(v)).strip()

def safe_int(v, default=0) -> int:
    try:
        if v is None:
            return default
        if isinstance(v, bool):
            return default
        if isinstance(v, (int, float)):
            return int(v)
        s = str(v).strip().replace(" ", "")
        if s == "":
            return default
        return int(float(s))
    except Exception:
        return default

def build_services_lines(data: dict) -> list[str]:
    raw_items = data.get("items")
    raw_services = data.get("services") or data.get("order") or data.get("cart")

    lines: list[str] = []

    if isinstance(raw_items, list) and raw_items:
        for it in raw_items:
            if not isinstance(it, dict):
                continue
            name = clean_str(it.get("name")) or clean_str(it.get("title")) or clean_str(it.get("id")) or "—"
            qty = safe_int(it.get("qty"), 0)
            if qty <= 0:
                continue
            price = safe_int(it.get("price"), 0)
            ssum = safe_int(it.get("sum"), 0)
            if ssum > 0:
                lines.append(f"• {name} × {qty} = {fmt_sum(ssum)} сум")
            elif price > 0:
                lines.append(f"• {name} × {qty} = {fmt_sum(price * qty)} сум")
            else:
                lines.append(f"• {name} × {qty}")

    if not lines and isinstance(raw_services, dict):
        for k, v in raw_services.items():
            q = safe_int(v, 0)
            if q > 0:
                lines.append(f"• {k} × {q}")

    if not lines:
        lines = ["⚠️ Услуги не выбраны"]

    return lines

# ====== ДАННЫЕ ИЗ WEBAPP ======
@dp.message(F.web_app_data)
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

    lines = build_services_lines(data)

    booking_id = clean_str(data.get("booking_id") or data.get("order_id") or data.get("id")) or "—"
    phone = clean_str(data.get("phone")) or "—"
    comment = clean_str(data.get("comment"))

    master = clean_str(data.get("master") or data.get("barber")) or "—"
    date = clean_str(data.get("date")) or "—"
    time_slot = clean_str(data.get("time") or data.get("slot")) or "—"
    branch = clean_str(data.get("branch") or data.get("location")) or "—"

    payment = clean_str(data.get("payment")) or "—"
    pay_label = {
        "cash": "💵 Наличные",
        "click": "💳 Безнал (CLICK)",
        "payme": "💳 Payme",
        "card": "💳 Карта",
    }.get(payment, payment)

    total_num = safe_int(data.get("total_num"), 0)
    total_str = clean_str(data.get("total")) or (fmt_sum(total_num) if total_num > 0 else "—")

    admin_text = (
        "👑 <b>НОВАЯ ЗАПИСЬ — THE KINGS Barbershop</b>\n"
        f"🆔 <b>{booking_id}</b>\n\n"
        "<b>Услуги:</b>\n" + "\n".join(lines) +
        f"\n\n✂️ <b>Барбер:</b> {master}"
        f"\n📅 <b>Дата:</b> {date}"
        f"\n🕒 <b>Время:</b> {time_slot}"
        f"\n📍 <b>Филиал:</b> {branch}"
        f"\n💳 <b>Оплата:</b> {pay_label}"
        f"\n💰 <b>Сумма:</b> {total_str}"
        f"\n📞 <b>Телефон:</b> {phone}"
        f"\n👤 <b>Telegram:</b> {tg_label(message.from_user)}"
    )
    if comment:
        admin_text += f"\n💬 <b>Комментарий:</b> {comment}"

    await bot.send_message(ADMIN_ID, admin_text)

    client_text = (
        "✅ <b>Запись отправлена!</b>\n"
        "🙏 Спасибо! Мы скоро подтвердим запись.\n\n"
        f"🆔 <b>{booking_id}</b>\n\n"
        "<b>Вы выбрали:</b>\n" + "\n".join(lines) +
        f"\n\n✂️ <b>Барбер:</b> {master}"
        f"\n📅 <b>Дата:</b> {date}"
        f"\n🕒 <b>Время:</b> {time_slot}"
        f"\n📍 <b>Филиал:</b> {branch}"
        f"\n💳 <b>Оплата:</b> {pay_label}"
        f"\n💰 <b>Сумма:</b> {total_str}"
        f"\n📞 <b>Телефон:</b> {phone}"
    )
    if comment:
        client_text += f"\n💬 <b>Комментарий:</b> {comment}"

    await message.answer(client_text, reply_markup=kb_webapp_reply())

# ====== ЗАПУСК ======
async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
