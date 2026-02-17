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

# قراءة التوكن من متغير البيئة
TOKEN = os.getenv("BOT_TOKEN")

# إعدادات
COOLDOWN = 10
SUPPORTED = ["tiktok.com", "instagram.com", "youtu", "facebook.com"]

# تخزين روابط المستخدمين وحماية سبام
user_links = {}
user_last_request = {}
cache = {}

# ===== رسالة البداية =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 اهلاً بك في بوت التحميل الاحترافي!\n\n"
        "📥 أرسل رابط من أي منصة:\n"
        "TikTok — Instagram — YouTube — Facebook\n"
        "⚠️ ملاحظة: ستوري إنستغرام يجب أن يكون عام."
    )

# ===== التحقق من الرابط =====
def is_supported(url: str):
    return any(site in url for site in SUPPORTED)

# ===== استقبال الرابط =====
async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    now = time.time()
    url = update.message.text.strip()

    # فلترة روابط غير مدعومة
    if not is_supported(url):
        await update.message.reply_text("❌ الرابط غير مدعوم")
        return

    # حماية سبام
    if user_id in user_last_request:
        if now - user_last_request[user_id] < COOLDOWN:
            wait = int(COOLDOWN - (now - user_last_request[user_id]))
            await update.message.reply_text(f"⏳ انتظر {wait} ثانية قبل طلب جديد")
            return

    user_last_request[user_id] = now
    user_links[user_id] = url

    # أزرار الفيديو / MP3
    keyboard = [[
        InlineKeyboardButton("📹 فيديو", callback_data="video"),
        InlineKeyboardButton("🎵 MP3", callback_data="audio"),
    ]]

    await update.message.reply_text(
        "اختر نوع التحميل:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

# ===== التعامل مع الأزرار =====
async def buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    url = user_links.get(user_id)

    if not url:
        await query.message.reply_text("❌ أرسل الرابط أولاً")
        return

    # إنشاء مفتاح فريد للكاش
    key = hashlib.md5((url + query.data).encode()).hexdigest()

    # إرسال الملف من الكاش إذا موجود
    if key in cache and os.path.exists(cache[key]):
        if query.data == "video":
            await query.message.reply_video(video=open(cache[key], "rb"))
        else:
            await query.message.reply_audio(audio=open(cache[key], "rb"))
        return

    msg = await query.message.reply_text("⏳ جاري التحميل...")

    try:
        if query.data == "video":
            ydl_opts = {"format": "best", "outtmpl": f"{key}.%(ext)s"}
        else:
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": f"{key}.%(ext)s",
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}],
            }

        # تحميل الفيديو أو الصوت
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # البحث عن الملف وإرساله
        for f in os.listdir():
            if f.startswith(key):
                cache[key] = f
                if query.data == "video":
                    await query.message.reply_video(video=open(f, "rb"))
                else:
                    await query.message.reply_audio(audio=open(f, "rb"))
                break

        await msg.delete()

    except Exception as e:
        await msg.edit_text("❌ فشل التحميل أو الرابط خاص/غير مدعوم")

# ===== تشغيل البوت =====
app = ApplicationBuilder().token(TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))
app.add_handler(CallbackQueryHandler(buttons))

app.run_polling()
