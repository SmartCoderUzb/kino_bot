from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.keyboards.admin_kb import get_ads_menu_kb, get_ads_pagination_kb, get_cancel_fsm_kb, get_back_to_admin_kb
from aiogram.fsm.state import State, StatesGroup

router = Router(name="admin_ads")

class AdminCreateAd(StatesGroup):
    waiting_for_content = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()


async def format_ads_main_text(db: Database) -> str:
    s = await db.get_ads_stats()
    start_status = "✅ Yoqiq" if s["start_enabled"] else "❌ O'chiq"
    movie_status = "✅ Yoqiq" if s["movie_enabled"] else "❌ O'chiq"

    text = (
        "📢 <b>Reklama bo'limi</b>\n\n"
        f"📊 Jami reklamalar: {s['total_ads']} ta\n"
        f"✅ Faol: {s['active_ads']} ta\n"
        f"👁 Jami ko'rishlar: {s['total_views']} ta\n\n"
        "⚙️ <b>Sozlamalar:</b>\n"
        f"🚀 Start da: {start_status}\n"
        f"🎬 Kino yuklaganda: {movie_status}"
    )
    return text


# ================= 1. ASOSIY REKLAMA MENYUSI =================
@router.callback_query(F.data == "admin:ads")
async def cb_admin_ads_main(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()

    s = await db.get_ads_stats()
    text = await format_ads_main_text(db)
    kb = get_ads_menu_kb(s["start_enabled"], s["movie_enabled"])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ================= 2. SOZLAMALARNI YOQISH / O'CHIRISH =================
@router.callback_query(F.data == "ads:toggle:start")
async def cb_toggle_start_ad(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    new_state = await db.toggle_ad_setting("ad_on_start")
    msg = "Start reklamasi yoqildi!" if new_state else "Start reklamasi o'chirildi!"
    await call.answer(msg)

    s = await db.get_ads_stats()
    text = await format_ads_main_text(db)
    kb = get_ads_menu_kb(s["start_enabled"], s["movie_enabled"])
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


@router.callback_query(F.data == "ads:toggle:movie")
async def cb_toggle_movie_ad(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    new_state = await db.toggle_ad_setting("ad_on_movie")
    msg = "Kino reklamasi yoqildi!" if new_state else "Kino reklamasi o'chirildi!"
    await call.answer(msg)

    s = await db.get_ads_stats()
    text = await format_ads_main_text(db)
    kb = get_ads_menu_kb(s["start_enabled"], s["movie_enabled"])
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# ================= 3. ➕ REKLAMA QO'SHISH =================
@router.callback_query(F.data == "ads:add")
async def cb_ads_add_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.set_state(AdminCreateAd.waiting_for_content)
    text = (
        "📢 <b>Yangi reklama qo'shish:</b>\n\n"
        "1️⃣ Reklama postini (matn, rasm yoki video) yuboring:"
    )
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("admin:ads"), parse_mode="HTML")
    await call.answer()


@router.message(AdminCreateAd.waiting_for_content)
async def process_ad_content(message: Message, state: FSMContext):
    content_type = "text"
    file_id = ""
    text = message.text or message.caption or ""

    if message.photo:
        content_type = "photo"
        file_id = message.photo[-1].file_id
    elif message.video:
        content_type = "video"
        file_id = message.video.file_id
    elif message.animation:
        content_type = "animation"
        file_id = message.animation.file_id

    await state.update_data(content_type=content_type, file_id=file_id, text=text)
    await state.set_state(AdminCreateAd.waiting_for_button_text)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Tugmasiz davom etish", callback_data="ad:skip_button")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:ads")]
    ])
    await message.answer(
        "2️⃣ Reklama ostidagi <b>tugma matni</b>ni kiriting (masalan: <i>Batafsil</i> yoki <i>Kanalga o'tish</i>):",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminCreateAd.waiting_for_button_text, F.data == "ad:skip_button")
async def cb_skip_ad_button(call: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await db.add_ad(
        text=data.get("text", ""),
        content_type=data.get("content_type", "text"),
        file_id=data.get("file_id", ""),
        button_text="",
        button_url=""
    )
    await state.clear()

    s = await db.get_ads_stats()
    text = f"🎉 <b>Reklama muvaffaqiyatli saqlandi!</b>\n\n{await format_ads_main_text(db)}"
    kb = get_ads_menu_kb(s["start_enabled"], s["movie_enabled"])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminCreateAd.waiting_for_button_text)
async def process_ad_btn_text(message: Message, state: FSMContext):
    btn_text = message.text.strip()
    await state.update_data(btn_text=btn_text)
    await state.set_state(AdminCreateAd.waiting_for_button_url)
    
    await message.answer(
        f"3️⃣ <b>«{btn_text}»</b> tugmasi uchun <b>havola (URL)</b>ni yuboring (masalan: <code>https://t.me/kanal_nomi</code>):",
        reply_markup=get_cancel_fsm_kb("admin:ads"),
        parse_mode="HTML"
    )


@router.message(AdminCreateAd.waiting_for_button_url)
async def process_ad_btn_url(message: Message, state: FSMContext, db: Database):
    btn_url = message.text.strip()
    data = await state.get_data()
    await state.clear()

    await db.add_ad(
        text=data.get("text", ""),
        content_type=data.get("content_type", "text"),
        file_id=data.get("file_id", ""),
        button_text=data.get("btn_text", ""),
        button_url=btn_url
    )

    s = await db.get_ads_stats()
    text = f"🎉 <b>Tugmali reklama muvaffaqiyatli saqlandi!</b>\n\n{await format_ads_main_text(db)}"
    kb = get_ads_menu_kb(s["start_enabled"], s["movie_enabled"])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


# ================= 4. 📋 REKLAMALAR RO'YXATI =================
@router.callback_query(F.data.startswith("ads:list:"))
async def cb_ads_list(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    page = int(call.data.split(":")[2])
    ads, total_count, total_pages = await db.get_ads_list(page=page, limit=5)

    if not ads:
        text = "📋 <b>Reklamalar ro'yxati</b>\n\nHozircha reklamalar mavjud emas."
        return await call.message.edit_text(text, reply_markup=get_ads_pagination_kb(1, 1), parse_mode="HTML")

    keyboard = []
    lines = [
        "📋 <b>Reklamalar ro'yxati</b>",
        f"📊 Jami: {total_count} ta | Sahifa: {page} / {total_pages}\n"
    ]

    for idx, a in enumerate(ads, (page - 1) * 5 + 1):
        status_txt = "🟢 Faol" if a["is_active"] else "🔴 O'chiq"
        ad_short = (a["text"][:30] + "...") if len(a["text"]) > 30 else (a["text"] or f"Reklama #{a['id']}")
        
        lines.append(f"{idx}. {ad_short}")
        lines.append(f"👁 Ko'rishlar: {a['views']} ta | Holat: {status_txt}\n")

        toggle_txt = "🔴 O'chirish" if a["is_active"] else "🟢 Yoqish"
        keyboard.append([
            InlineKeyboardButton(text=f"{idx}. {toggle_txt}", callback_data=f"ad:toggle:{a['id']}:{page}"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"ad:delete:{a['id']}:{page}")
        ])

    # Navigation buttons
    nav_row = []
    if page > 1:
        nav_row.append(InlineKeyboardButton(text="⬅️ Oldingi", callback_data=f"ads:list:{page-1}"))
    if page < total_pages:
        nav_row.append(InlineKeyboardButton(text="Keyingi ➡️", callback_data=f"ads:list:{page+1}"))

    if nav_row:
        keyboard.append(nav_row)
    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:ads")])

    text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ad:toggle:"))
async def cb_toggle_specific_ad(call: CallbackQuery, db: Database):
    parts = call.data.split(":")
    ad_id = int(parts[2])
    page = int(parts[3])

    new_act = await db.toggle_ad_active(ad_id)
    msg = "Reklama faollashtirildi!" if new_act == 1 else "Reklama o'chirildi!"
    await call.answer(msg, show_alert=True)

    # Re-render list
    call.data = f"ads:list:{page}"
    await cb_ads_list(call, True, db)


@router.callback_query(F.data.startswith("ad:delete:"))
async def cb_delete_specific_ad(call: CallbackQuery, db: Database):
    parts = call.data.split(":")
    ad_id = int(parts[2])
    page = int(parts[3])

    await db.delete_ad(ad_id)
    await call.answer("✅ Reklama o'chirildi!", show_alert=True)

    call.data = f"ads:list:{page}"
    await cb_ads_list(call, True, db)
