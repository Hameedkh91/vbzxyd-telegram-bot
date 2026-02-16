import os
import time
import hashlib
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

TOKEN = os.getenv("BOT_TOKEN")

COOLDOWN = 10
SUPPORTED = ["tiktok.com","instagram.com","youtu","facebook.com"]

user_links = {}
user_last_request = {}
cache = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 اهلاً بك في بوت التحميل الاحترافي\n"
        "📥 ارسل رابط من السوشال"
    )

def is_supported(url: str):
    return any(site in url for site in SUPPORTED)

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    url = update.message.text.strip()

    if not is_supported(url):
        await update.message.reply_text("❌ الرابط غير مدعوم")
        return

    if user_id in user_last_request:
        if now - user_last_request[user_id] < COOLDOWN:
            wait = int(COOLDOWN - (now - user_last_request[user_id]))
            await update.message.reply_text(f"⏳ انتظر {wait} ثانية")
            return

    user_last_request[user_id] = now
    user_links[user_id] = url

    keyboard = [[
        InlineKeyboardButton("📹 فيديو", callback_data="video"),
        InlineKeyboardButton("🎵 MP3", callback_data="audio"),
    ]]

    await update.message.reply_text(
        "اختر نوع التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.message.reply_text("❌ ارسل الرابط اولاً")
        return

    key = hashlib.md5((url + query.data).encode()).hexdigest()

    if key in cache and os.path.exists(cache[key]):
        if query.data == "video":
            await query.message.reply_video(video=open(cache[key], "rb"))
        else:
            await query.message.reply_audio(audio=open(cache[key], "rb"))
        return

    msg = await query.message.reply_text("⏳ جاري التحميل...")

    try:
        if query.data == "video":
            ydl_opts = {"format": "best","outtmpl": f"{key}.%(ext)s"}
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{key}.%(ext)s",
                "postprocessors":[{"key":"FFmpegExtractAudio","preferredcodec":"mp3"}],
            }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        for f in os.listdir():
            if f.startswith(key):
                cache[key] = f
                if query.data == "video":
                    await query.message.reply_video(video=open(f,"rb"))
                else:
                    await query.message.reply_audio(audio=open(f,"rb"))
                break

        await msg.delete()

    except Exception as e:
        await msg.edit_text("❌ فشل التحميل")

app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
