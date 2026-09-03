from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.keyboards.admin_kb import get_users_menu_kb, get_users_pagination_kb, get_cancel_fsm_kb
from aiogram.fsm.state import State, StatesGroup

router = Router(name="admin_users")

class AdminFindUser(StatesGroup):
    waiting_for_user_id = State()


def format_user_date(date_val) -> str:
    if not date_val:
        return datetime.now().strftime("%Y.%m.%d")
    if isinstance(date_val, datetime):
        return date_val.strftime("%Y.%m.%d")
    date_str = str(date_val)
    try:
        dt = datetime.strptime(date_str.split(".")[0], "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%Y.%m.%d")
    except Exception:
        return date_str[:10].replace("-", ".")


def get_user_status_emoji(user: dict) -> str:
    if user.get("status") == "banned":
        return "🚫"
    if user.get("status") == "blocked":
        return "🔴"
    if user.get("is_premium"):
        return "💎"
    return "🟢"


# ================= FOYDALANUVCHILAR ASOSIY MENYUSI =================
@router.callback_query(F.data == "admin:users")
async def cb_admin_users(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    stats = await db.get_users_overview_stats()
    text = (
        "👥 <b>Foydalanuvchilar bo'limi</b>\n\n"
        f"📊 Jami: {stats['total']} ta\n"
        f"🟢 Faol: {stats['active']} ta\n"
        f"🔴 Tark etgan: {stats['left']} ta\n"
        f"🚫 Bloklangan: {stats['banned']} ta\n"
        f"💎 Premium: {stats['premium']} ta"
    )
    await call.message.edit_text(text, reply_markup=get_users_menu_kb(), parse_mode="HTML")
    await call.answer()


# ================= FOYDALANUVCHILAR RO'YXATI =================
@router.callback_query(F.data.startswith("users:list:"))
async def cb_users_list(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    page = int(call.data.split(":")[2])
    users, total_count, total_pages = await db.get_users_list(page=page, limit=10)

    if not users:
        text = "📋 <b>Foydalanuvchilar ro'yxati</b>\n\nHozircha foydalanuvchilar mavjud emas."
        return await call.message.edit_text(text, reply_markup=get_users_pagination_kb(1, 1, mode="all"), parse_mode="HTML")

    lines = [
        "📋 <b>Foydalanuvchilar ro'yxati</b>",
        f"📊 Jami: {total_count} ta | Sahifa: {page} / {total_pages}\n"
    ]

    for idx, u in enumerate(users, (page - 1) * 10 + 1):
        username_str = f"@{u['username']}" if u.get('username') else "username yo'q"
        emoji = get_user_status_emoji(u)
        date_formatted = format_user_date(u.get('joined_at', ''))
        
        lines.append(f"{idx}. {u['full_name']} ({username_str}) {emoji}")
        lines.append(f"🆔 <code>{u['user_id']}</code> | 📅 {date_formatted}\n")

    text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=get_users_pagination_kb(page, total_pages, mode="all"), parse_mode="HTML")
    await call.answer()


# ================= BLOKLANGAN FOYDALANUVCHILAR =================
@router.callback_query(F.data.startswith("users:blocked:"))
async def cb_users_blocked(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    page = int(call.data.split(":")[2])
    users, total_count, total_pages = await db.get_users_list(page=page, limit=10, filter_status="blocked")

    if not users:
        text = "🚫 <b>Bloklangan foydalanuvchilar ro'yxati</b>\n\nHozircha bloklangan foydalanuvchilar mavjud emas."
        return await call.message.edit_text(text, reply_markup=get_users_pagination_kb(1, 1, mode="blocked"), parse_mode="HTML")

    lines = [
        "🚫 <b>Bloklangan foydalanuvchilar ro'yxati</b>",
        f"📊 Jami: {total_count} ta | Sahifa: {page} / {total_pages}\n"
    ]

    for idx, u in enumerate(users, (page - 1) * 10 + 1):
        username_str = f"@{u['username']}" if u.get('username') else "username yo'q"
        emoji = get_user_status_emoji(u)
        date_formatted = format_user_date(u.get('joined_at', ''))
        
        lines.append(f"{idx}. {u['full_name']} ({username_str}) {emoji}")
        lines.append(f"🆔 <code>{u['user_id']}</code> | 📅 {date_formatted}\n")

    text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=get_users_pagination_kb(page, total_pages, mode="blocked"), parse_mode="HTML")
    await call.answer()


# ================= FOYDALANUVCHI QIDIRISH =================
@router.callback_query(F.data == "users:search")
async def cb_user_search_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminFindUser.waiting_for_user_id)
    text = (
        "🔎 <b>Foydalanuvchi ID sini kiriting:</b>\n\n"
        "Masalan: <code>123456789</code>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:users")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminFindUser.waiting_for_user_id)
async def process_user_search(message: Message, state: FSMContext, db: Database):
    text = message.text.strip()
    if not text.isdigit():
        return await message.answer(
            "❌ Iltimos, faqat sonlardan iborat ID kiriting:\n\nMasalan: <code>123456789</code>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:users")]
            ]),
            parse_mode="HTML"
        )

    user_id = int(text)
    user = await db.get_user(user_id)
    await state.clear()

    if not user:
        return await message.answer(
            f"❌ <code>{user_id}</code> IDli foydalanuvchi bot bazasida topilmadi.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Ortga", callback_data="admin:users")]
            ]),
            parse_mode="HTML"
        )

    ref_count = await db.get_referral_count(user_id)
    status_emoji = "🟢 Faol" if user["status"] == "active" else ("🔴 Tark etgan" if user["status"] == "blocked" else "🚫 Bloklangan")
    premium_emoji = "💎 Faol" if user["is_premium"] else "Yo'q"
    joined_date = format_user_date(user.get("joined_at", ""))

    info_text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"• ID: <code>{user['user_id']}</code>\n"
        f"• Ism: <b>{user['full_name']}</b>\n"
        f"• Username: @{user['username'] if user['username'] else 'mavjud emas'}\n"
        f"• Holat: {status_emoji}\n"
        f"• Premium: {premium_emoji}\n"
        f"• Taklif qilgan do'stlari: {ref_count} ta\n"
        f"• Ro'yxatdan o'tgan: {joined_date}\n"
        f"• So'nggi faollik: {user['last_active_at']}"
    )

    ban_btn_text = "✅ Blokdan chiqarish" if user["status"] == "banned" else "🚫 Bloklash"
    prem_btn_text = "❌ Premium bekor qilish" if user["is_premium"] else "💎 Premium berish"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=ban_btn_text, callback_data=f"user:toggle_ban:{user_id}"),
            InlineKeyboardButton(text=prem_btn_text, callback_data=f"user:toggle_prem:{user_id}")
        ],
        [InlineKeyboardButton(text="◀️ Foydalanuvchilar bo'limiga", callback_data="admin:users")]
    ])
    await message.answer(info_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("user:toggle_ban:"))
async def cb_toggle_ban(call: CallbackQuery, db: Database):
    user_id = int(call.data.split(":")[2])
    new_status = await db.toggle_user_ban(user_id)
    await call.answer(f"Holat o'zgartirildi: {new_status}!", show_alert=True)
    
    user = await db.get_user(user_id)
    if not user:
        return
    ref_count = await db.get_referral_count(user_id)
    status_emoji = "🟢 Faol" if user["status"] == "active" else ("🔴 Tark etgan" if user["status"] == "blocked" else "🚫 Bloklangan")
    premium_emoji = "💎 Faol" if user["is_premium"] else "Yo'q"
    joined_date = format_user_date(user.get("joined_at", ""))

    info_text = (
        f"👤 <b>Foydalanuvchi ma'lumotlari:</b>\n\n"
        f"• ID: <code>{user['user_id']}</code>\n"
        f"• Ism: <b>{user['full_name']}</b>\n"
        f"• Username: @{user['username'] if user['username'] else 'mavjud emas'}\n"
        f"• Holat: {status_emoji}\n"
        f"• Premium: {premium_emoji}\n"
        f"• Taklif qilgan do'stlari: {ref_count} ta\n"
        f"• Ro'yxatdan o'tgan: {joined_date}\n"
        f"• So'nggi faollik: {user['last_active_at']}"
    )
    ban_btn_text = "✅ Blokdan chiqarish" if user["status"] == "banned" else "🚫 Bloklash"
    prem_btn_text = "❌ Premium bekor qilish" if user["is_premium"] else "💎 Premium berish"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=ban_btn_text, callback_data=f"user:toggle_ban:{user_id}"),
            InlineKeyboardButton(text=prem_btn_text, callback_data=f"user:toggle_prem:{user_id}")
        ],
        [InlineKeyboardButton(text="◀️ Foydalanuvchilar bo'limiga", callback_data="admin:users")]
    ])
    await call.message.edit_text(info_text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("user:toggle_prem:"))
async def cb_toggle_prem(call: CallbackQuery, db: Database):
    user_id = int(call.data.split(":")[2])
    new_prem = await db.toggle_user_premium(user_id)
    prem_msg = "Premium faollashtirildi!" if new_prem == 1 else "Premium bekor qilindi!"
    await call.answer(prem_msg, show_alert=True)

    user = await db.get_user(user_id)
    if not user:
        return
    ref_count = await db.get_referral_count(user_id)
    status_emoji = "🟢 Faol" if user["status"] == "active" else ("🔴 Tark etgan" if user["status"] == "blocked" else "🚫 Bloklangan")
    premium_emoji = "💎 Faol" if user["is_premium"] else "Yo'q"
    joined_date = format_user_date(user.get("joined_at", ""))

    info_text = (
        f"👤 <b>Foydalanuvchilar ma'lumotlari:</b>\n\n"
        f"• ID: <code>{user['user_id']}</code>\n"
        f"• Ism: <b>{user['full_name']}</b>\n"
        f"• Username: @{user['username'] if user['username'] else 'mavjud emas'}\n"
        f"• Holat: {status_emoji}\n"
        f"• Premium: {premium_emoji}\n"
        f"• Taklif qilgan do'stlari: {ref_count} ta\n"
        f"• Ro'yxatdan o'tgan: {joined_date}\n"
        f"• So'nggi faollik: {user['last_active_at']}"
    )
    ban_btn_text = "✅ Blokdan chiqarish" if user["status"] == "banned" else "🚫 Bloklash"
    prem_btn_text = "❌ Premium bekor qilish" if user["is_premium"] else "💎 Premium berish"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=ban_btn_text, callback_data=f"user:toggle_ban:{user_id}"),
            InlineKeyboardButton(text=prem_btn_text, callback_data=f"user:toggle_prem:{user_id}")
        ],
        [InlineKeyboardButton(text="◀️ Foydalanuvchilar bo'limiga", callback_data="admin:users")]
    ])
    await call.message.edit_text(info_text, reply_markup=kb, parse_mode="HTML")
