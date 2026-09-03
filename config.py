import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent

load_dotenv(BASE_DIR / ".env")

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMINS_RAW = os.getenv("ADMINS", "")
ADMINS = [int(admin_id.strip()) for admin_id in ADMINS_RAW.split(",") if admin_id.strip().isdigit()]

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "5432"))
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")
DB_NAME = os.getenv("DB_NAME", "kino_bot")

DB_PATH = BASE_DIR / os.getenv("DB_PATH", "data/kino_bot.db")

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)


REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", None) or None

REDIS_URL = os.getenv(
    "REDIS_URL",
    f"redis://{(':' + REDIS_PASSWORD + '@') if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/{REDIS_DB}"
)

WEB_PANEL_URL = os.getenv("WEB_PANEL_URL", "https://t.me")


DEFAULT_TEXTS = {
    "welcome": "👋 Assalomu alaykum, <b>{full_name}</b>!\n\n🎬 <b>Kino Bot</b>imizga xush kelibsiz!\n\n🔢 Kino kodini yuboring va kinoni yuklab oling.\nMasalan: <code>101</code> yoki <code>102</code>",
    "channels_msg": "⚠️ <b>Botdan foydalanish uchun quyidagi kanallarga a'zo bo'ling:</b>\n\nObuna bo'lgach, <b>«✅ Tekshirish»</b> tugmasini bosing.",
    "subscribe_btn": "➕ Obuna bo'lish",
    "check_btn": "✅ Tekshirish",
    "movie_caption": "🎬 <b>Nomi:</b> {title}\n🔢 <b>Kodi:</b> <code>{code}</code>\n💾 <b>Sifati:</b> {quality}\n🌐 <b>Tili:</b> {language}\n\n🤖 <b>Bot:</b> @{bot_username}",
    "share_btn": "↗️ Ulashish",
    "prem_movie_msg": "🔒 <b>Bu kino faqat Premium foydalanuvchilar uchun mavjud!</b>\n\nKinoni ko'rish uchun Premium obunani faollashtiring.",
    "prem_btn": "💎 Premium sotib olish",
    "series_title": "🎬 <b>{title}</b> serialining qismlari:\n\nQismni tanlang:",
    "wrong_code_msg": "😔 Kechirasiz, <b>{code}</b> kodli kino topilmadi.\n\nIltimos, kodni to'g'ri kiritganingizga ishonch hosil qiling yoki kino so'rovini yuboring.",
    "part_name": "{part}-qism",
    "movie_name_format": "🎬 {title}",
    "prem_active_page": "💎 <b>Sizda Premium obuna faol!</b>\n\nAmal qilish muddati: <b>{until}</b>\n\nBarcha kinolarni reklamasiz va cheklovlarsiz yuklab olishingiz mumkin.",
    "prem_offer_page": "💎 <b>Premium obuna afzalliklari:</b>\n\n• Kanallarga majburiy obuna yo'q\n• Reklamasiz tezkor yuklash\n• Eksklyuziv premyeralar\n\nTarifni tanlang:",
    "pay_select_msg": "💳 <b>To'lov tizimini tanlang:</b>",
    "manual_pay_info": "💳 <b>To'lov ma'lumotlari:</b>\n\nQuyidagi hisob raqamga to'lov qiling va to'lov chekini (skrinshot) shu yerga yuboring:\n\n<code>{card_details}</code>",
    "receipt_received_msg": "🧾 <b>To'lov chekingiz qabul qilindi!</b>\n\nAdminlarimiz to'lovni tekshirib, tez orada Premium obunangizni faollashtirishadi.",
    "pay_approved_msg": "✅ <b>Tabriklaymiz! To'lovingiz tasdiqlandi.</b>\n\nPremium obunangiz muvaffaqiyatli faollashtirildi!",
    "pay_rejected_msg": "❌ <b>Afsuski, to'lovingiz tasdiqlanmadi.</b>\n\nChek noto'g'ri yoki to'lov hisobga kelib tushmagan. Savollar bo'lsa adminga murojaat qiling.",
    "paid_movie_offer": "💰 <b>Ushbu kino pullik!</b>\n\nKinoni sotib olish narxi: <b>{price}</b>\nDavom etish uchun quyidagi tugmani bosing.",
    "paid_movie_pay_info": "💰 <b>Pullik kino uchun to'lov:</b>\n\nQuyidagi kartaga <b>{price}</b> o'tkazing va chekni yuboring:\n\n<code>{card_details}</code>",
    "request_success": "✅ Sizning so'rovingiz qabul qilindi! Adminlar ko'rib chiqib, tez orada botga yuklashadi.",
    "help": "ℹ️ <b>Yordam bo'limi:</b>\n\n• Kino yuklash uchun uning kodini yuboring.\n• Kinolarni nomi bo'yicha qidirishingiz mumkin.\n• Agar kino topilmasa, «📥 Kino so'rash» orqali buyurtma bering."
}

TEXT_LABELS = {
    "welcome": "👋 Start xabari",
    "channels_msg": "📢 Kanallar chiqadigan matn",
    "subscribe_btn": "➕ Obuna bo'lish tugmasi",
    "check_btn": "✅ Tekshirish tugmasi",
    "movie_caption": "🎬 Kino caption matni",
    "share_btn": "↗️ Ulashish tugmasi",
    "prem_movie_msg": "🔒 Premium kino xabari",
    "prem_btn": "💎 Premium tugmasi",
    "series_title": "🎬 Kino qismlari sarlavhasi",
    "wrong_code_msg": "❌ Noto'g'ri kod xabari",
    "part_name": "🗃 Qism nomi (masalan: 1-qism)",
    "movie_name_format": "🎬 Kino nomi matni",
    "prem_active_page": "💎 Premium faol — obuna sahifasi",
    "prem_offer_page": "💎 Premium taklifi sahifasi",
    "pay_select_msg": "💳 To'lov tizimini tanlash",
    "manual_pay_info": "💳 Qo'lda to'lov ma'lumotlari",
    "receipt_received_msg": "🧾 Chek qabul qilindi xabari",
    "pay_approved_msg": "✅ To'lov tasdiqlandi xabari",
    "pay_rejected_msg": "❌ To'lov bekor qilindi xabari",
    "paid_movie_offer": "💰 Pullik kino taklifi",
    "paid_movie_pay_info": "💰 Pullik kino — to'lov ma'lumotlari",
}
