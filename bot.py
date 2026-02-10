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

# ✅ ГЛАВНОЕ ИЗМЕНЕНИЕ:
# GitHub Pages у тебя живой по адресу https://tahirovdd-lang.github.io/TheKINGS/
# поэтому НЕ используем /index.html (он может давать 404), а открываем корень.
WEBAPP_URL = os.getenv("WEBAPP_URL", "https://tahirovdd-lang.github.io/TheKINGS/?v=1")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ====== АНТИ-ДУБЛЬ START ======
_last_start: dict[int, float] = {}

def allow_start(user_id: int, ttl: float = 0.6) -> bool:
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
        return await message.answer("👑 Открывайте запись кнопкой ниже:", reply_markup=kb_webapp_reply())
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

@dp.message(Command("startapp"))
async def startapp(message: types.Message):
    if not allow_start(message.from_user.id):
        return await message.answer("👑 Открывайте запись кнопкой ниже:", reply_markup=kb_webapp_reply())
    await message.answer(welcome_text(), reply_markup=kb_webapp_reply())

# ====== Проверка ======
@dp.message(Command("ping"))
async def ping(message: types.Message):
    await message.answer("✅ <b>PONG</b>\nБот работает.", reply_markup=kb_webapp_reply())

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

def build_services_lines_from_services(services: list) -> list[str]:
    lines: list[str] = []
    for it in services:
        if not isinstance(it, dict):
            continue
        name = clean_str(it.get("name")) or "—"
        qty = safe_int(it.get("qty"), 1) or 1
        price = safe_int(it.get("price"), 0)
        dur = safe_int(it.get("duration"), 0)
        if price > 0:
            lines.append(f"• {name} × {qty} = {fmt_sum(price * qty)} сум ({dur} мин)")
        else:
            lines.append(f"• {name} × {qty} ({dur} мин)")
    return lines or ["⚠️ Услуги не выбраны"]

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

    booking_id = clean_str(data.get("booking_id") or data.get("id")) or "—"

    # поддерживаем оба варианта: client_name и name
    client_name = clean_str(
        data.get("client_name") or data.get("name") or data.get("client") or data.get("full_name")
    ) or "—"

    phone = clean_str(data.get("phone")) or "—"
    comment = clean_str(data.get("comment"))

    master_name = clean_str(data.get("master_name") or data.get("master") or data.get("barber")) or "—"
    date = clean_str(data.get("date")) or "—"
    time_slot = clean_str(data.get("time") or data.get("slot")) or "—"

    total = safe_int(data.get("total"), 0)
    duration_min = safe_int(data.get("duration_min"), 0)

    services = data.get("services") if isinstance(data.get("services"), list) else []
    lines = build_services_lines_from_services(services)

    admin_text = (
        "👑 <b>НОВАЯ ЗАПИСЬ — THE KINGS Barbershop</b>\n"
        f"🆔 <b>{booking_id}</b>\n\n"
        f"👤 <b>Клиент:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> {phone}\n"
        f"👤 <b>Telegram:</b> {tg_label(message.from_user)}\n\n"
        f"✂️ <b>Мастер:</b> {master_name}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"🕒 <b>Время:</b> {time_slot}\n\n"
        "<b>Услуги:</b>\n" + "\n".join(lines) +
        f"\n\n⏱ <b>Длительность:</b> {duration_min if duration_min else '—'} мин"
        f"\n💰 <b>Сумма:</b> {fmt_sum(total) if total else '—'} сум"
    )
    if comment:
        admin_text += f"\n💬 <b>Комментарий:</b> {comment}"

    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception:
        logging.exception("FAILED TO SEND ADMIN MESSAGE")

    client_text = (
        "✅ <b>Запись отправлена!</b>\n"
        "🙏 Спасибо! Мы скоро подтвердим запись.\n\n"
        f"🆔 <b>{booking_id}</b>\n"
        f"✂️ <b>Мастер:</b> {master_name}\n"
        f"📅 <b>Дата:</b> {date}\n"
        f"🕒 <b>Время:</b> {time_slot}\n\n"
        "<b>Услуги:</b>\n" + "\n".join(lines) +
        f"\n\n⏱ <b>Длительность:</b> {duration_min if duration_min else '—'} мин"
        f"\n💰 <b>Сумма:</b> {fmt_sum(total) if total else '—'} сум"
    )
    if comment:
        client_text += f"\n💬 <b>Комментарий:</b> {comment}"

    await message.answer(client_text, reply_markup=kb_webapp_reply())

# ====== ЗАПУСК ======
async def main():
    logging.info("✅ Bot starting…")
    logging.info(f"WEBAPP_URL = {WEBAPP_URL}")

    await bot.delete_webhook(drop_pending_updates=False)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
