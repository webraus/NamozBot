from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, ChatMember
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    ContextTypes, filters, CallbackQueryHandler
)
import requests
import json
import os
import config
from cities import cities

# === Foydalanuvchini saqlash ===
def save_user(user_id):
    if not os.path.exists("users.json"):
        with open("users.json", "w") as f:
            json.dump([], f)

    with open("users.json", "r") as f:
        users = json.load(f)

    if user_id not in users:
        users.append(user_id)
        with open("users.json", "w") as f:
            json.dump(users, f)

# === Majburiy obuna tekshiruvi ===
async def check_subscription(user_id, bot):
    try:
        member = await bot.get_chat_member(config.CHANNEL_USERNAME, user_id)
        return member.status in [ChatMember.MEMBER, ChatMember.ADMINISTRATOR, ChatMember.OWNER]
    except:
        return False

# === /start komandasi ===
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot = context.bot

    subscribed = await check_subscription(user_id, bot)
    if not subscribed:
        btn = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Obuna bo‘lish", url=f"https://t.me/{config.CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("🔄 Tekshirish", callback_data="check_subs")]
        ])
        await update.message.reply_text(
            "Botdan foydalanish uchun kanalga obuna bo‘ling:",
            reply_markup=btn
        )
        return

    save_user(user_id)

    keyboard = [[city] for city in cities]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("Shahringizni tanlang:", reply_markup=reply_markup)

# === Obuna tekshirish tugmasi ===
async def check_subs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    bot = context.bot

    subscribed = await check_subscription(user_id, bot)
    if subscribed:
        await query.message.delete()
        keyboard = [[city] for city in cities]
        reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
        await bot.send_message(chat_id=user_id, text="Shahringizni tanlang:", reply_markup=reply_markup)
        save_user(user_id)
    else:
        await query.message.reply_text("Iltimos, avval kanalga obuna bo‘ling!")

# === Shahar nomini yozganda ===
async def get_times(update: Update, context: ContextTypes.DEFAULT_TYPE):
    city = update.message.text
    if city not in cities:
        await update.message.reply_text("Iltimos, menyudan shahar tanlang.")
        return

    url = f"https://api.aladhan.com/v1/timingsByCity?city={city}&country=Uzbekistan&method=2"
    response = requests.get(url).json()
    timings = response['data']['timings']

    msg = f"""📿 {city} shahri uchun bugungi namoz vaqtlari:

🕓 Bomdod: {timings['Fajr']}
🌅 Quyosh: {timings['Sunrise']}
🕛 Peshin: {timings['Dhuhr']}
🕒 Asr: {timings['Asr']}
🌇 Shom: {timings['Maghrib']}
🌙 Xufton: {timings['Isha']}
"""
    await update.message.reply_text(msg)

# === Admin paneli ===
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != config.ADMIN_ID:
        await update.message.reply_text("Siz admin emassiz.")
        return

    btns = InlineKeyboardMarkup([
        [InlineKeyboardButton("👥 Obunachilar soni", callback_data="subs_count")],
        [InlineKeyboardButton("📢 Xabar yuborish", callback_data="send_message")]
    ])
    await update.message.reply_text("Admin paneliga xush kelibsiz!", reply_markup=btns)

# === Callbacklar ===
async def admin_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "subs_count":
        with open("users.json", "r") as f:
            users = json.load(f)
        await query.message.reply_text(f"Botda {len(users)} ta obunachi bor.")
    elif query.data == "send_message":
        context.user_data["sending_broadcast"] = True
        await query.message.reply_text("Foydalanuvchilarga yuboriladigan xabarni kiriting:")

# === Xabar yuborish admin uchun ===
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("sending_broadcast") and update.effective_user.id == config.ADMIN_ID:
        text = update.message.text
        with open("users.json", "r") as f:
            users = json.load(f)
        for user_id in users:
            try:
                await context.bot.send_message(chat_id=user_id, text=text)
            except:
                continue
        context.user_data["sending_broadcast"] = False
        await update.message.reply_text("Xabar yuborildi.")

# === Botni ishga tushurish ===
app = ApplicationBuilder().token(config.TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CommandHandler("admin", admin))
app.add_handler(CallbackQueryHandler(admin_buttons))
app.add_handler(CallbackQueryHandler(check_subs, pattern="check_subs"))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, get_times))
app.add_handler(MessageHandler(filters.TEXT & filters.User(config.ADMIN_ID), broadcast))

print("✅ Bot ishga tushdi.")
app.run_polling()
