from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.keyboards.admin_kb import (
    get_admin_main_kb, 
    get_stats_refresh_kb, 
    get_back_to_admin_kb, 
    get_content_protection_kb,
    get_design_menu_kb,
    get_design_button_detail_kb,
    get_color_picker_kb,
    get_cancel_fsm_kb
)
from kino_bot.utils.states import AdminDesignEdit

router = Router(name="admin_main")

DESIGN_BTN_NAMES = {
    "subscribe": "➕ Obuna bo'lish",
    "check": "✅ Tekshirish",
    "premium": "💎 Premium",
    "share": "↗️ Ulashish",
    "tariffs": "📦 Tarif tugmalari",
    "payments": "💳 To'lov tugmalari"
}

async def format_stats_text(db: Database) -> str:
    s = await db.get_full_statistics()
    e_chart = '<tg-emoji emoji-id="5431577498364158238">📊</tg-emoji>'
    e_growth = '<tg-emoji emoji-id="5373001317042101552">📈</tg-emoji>'
    e_inbox = '<tg-emoji emoji-id="5433811242135331842">📥</tg-emoji>'
    e_movie = '<tg-emoji emoji-id="5375464961822695044">🎬</tg-emoji>'
    text = (
        f"{e_chart} <b>Statistika</b>\n"
        f"• Obunachilar soni: <b>{s['total_users']:,} ta</b>\n"
        f"• Faol obunachilar: <b>{s['active_users']:,} ta</b>\n"
        f"• Tark etganlar: <b>{s['blocked_users']:,} ta</b>\n\n"
        f"{e_growth} <b>Obunachilar qo'shilishi</b>\n"
        f"• Oxirgi 24 soat: <b>+{s['new_24h']} obunachi</b>\n"
        f"• Oxirgi 7 kun: <b>+{s['new_7d']} obunachi</b>\n"
        f"• Oxirgi 30 kun: <b>+{s['new_30d']} obunachi</b>\n\n"
        f"{e_chart} <b>Faollik</b>\n"
        f"• Oxirgi 24 soatda faol: <b>{s['active_24h']:,} ta</b>\n"
        f"• Oxirgi 7 kun faol: <b>{s['active_7d']:,} ta</b>\n"
        f"• Oxirgi 30 kun faol: <b>{s['active_30d']:,} ta</b>\n\n"
        f"{e_inbox} <b>Yuklanishlar</b>\n"
        f"• Oxirgi 24 soat: <b>{s['downloads_24h']:,} ta</b>\n"
        f"• Oxirgi 7 kun: <b>{s['downloads_7d']:,} ta</b>\n"
        f"• Oxirgi 30 kun: <b>{s['downloads_30d']:,} ta</b>\n\n"
        f"{e_movie} <b>Kinolar soni:</b> <b>{s['total_movies']:,} ta</b>"
    )
    return text


@router.message(Command("admin"))
@router.message(F.text.in_(["🕹️ Boshqaruv", "🕹️Boshqaruv"]))
async def open_admin_panel(message: Message, is_admin: bool, state: FSMContext):
    if not is_admin:
        return
    await state.clear()
    text = "👋 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"
    await message.answer(text, reply_markup=get_admin_main_kb(), parse_mode="HTML")


@router.callback_query(F.data == "admin:main")
async def cb_admin_main(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat berilmagan!", show_alert=True)
    await state.clear()
    text = "👋 <b>Admin panel</b>\n\nKerakli bo'limni tanlang:"
    try:
        await call.message.edit_text(text, reply_markup=get_admin_main_kb(), parse_mode="HTML")
    except Exception:
        await call.message.answer(text, reply_markup=get_admin_main_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:stats")
async def cb_admin_stats(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    text = await format_stats_text(db)
    await call.message.edit_text(text, reply_markup=get_stats_refresh_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:stats:refresh")
async def cb_admin_stats_refresh(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    text = await format_stats_text(db)
    try:
        await call.message.edit_text(text, reply_markup=get_stats_refresh_kb(), parse_mode="HTML")
        await call.answer("🔄 Statistika yangilandi!")
    except Exception:
        await call.answer("ℹ️ O'zgarish yo'q.")


@router.callback_query(F.data == "cancel_action")
async def cb_cancel_action(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.clear()
    await call.message.edit_text("❌ Amaliyot bekor qilindi.", reply_markup=get_back_to_admin_kb(), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:close")
async def cb_admin_close(call: CallbackQuery):
    try:
        await call.message.delete()
    except Exception:
        await call.message.edit_text("🔒 Admin panel yopildi.")
    await call.answer()


# ================= ULASHISH / KONTENTNI HIMOYALASH =================
@router.callback_query(F.data == "admin:share")
async def cb_admin_share(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    protect_reg = (await db.get_setting("protect_content_regular", "1")) == "1"
    protect_prem = (await db.get_setting("protect_content_premium", "1")) == "1"

    reg_status = "🔴 Taqiqlangan" if protect_reg else "🟢 Ruxsat berilgan"
    prem_status = "🔴 Taqiqlangan" if protect_prem else "🟢 Ruxsat berilgan"

    text = (
        "↗️ <b>Kontentni himoya qilish sozlamalari</b>\n\n"
        "Ushbu bo'lim orqali foydalanuvchilar kinolarni boshqalarga yuborishi (Forward) yoki saqlab olishini nazorat qilasiz.\n\n"
        "👥 <b>Oddiy foydalanuvchilar:</b>\n"
        f"└ Holat: {reg_status}\n\n"
        "🌟 <b>Premium foydalanuvchilar:</b>\n"
        f"└ Holat: {prem_status}\n\n"
        "<i>Tugmani bosish orqali ruxsatni o'zgartirishingiz mumkin:</i>"
    )
    kb = get_content_protection_kb(protect_reg, protect_prem)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("protect:toggle:"))
async def cb_toggle_protection(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    target = call.data.split(":")[2]
    setting_key = f"protect_content_{target}"
    
    cur_val = await db.get_setting(setting_key, "1")
    new_val = "0" if cur_val == "1" else "1"
    await db.set_setting(setting_key, new_val)
    
    await cb_admin_share(call, is_admin, db)


# ================= DIZAYN BOSHQARUVI =================
@router.callback_query(F.data == "admin:design")
async def cb_admin_design(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    if state:
        await state.clear()

    colors = {}
    for k in DESIGN_BTN_NAMES.keys():
        colors[k] = await db.get_setting(f"btn_color_{k}", "⚪")

    text = (
        "🎨 <b>Dizayn boshqaruvi</b>\n\n"
        "Tugmani tanlang — rangi, custom emojisi va matnini o'zgartirishingiz mumkin. "
        "Bot xabarlarining matnlari « 📝 Matnlar» bo'limida.\n\n"
        "<blockquote>⚠️ Custom emoji faqat bot egasida faol Telegram Premium bo'lsa ishlaydi. "
        "Tugma ranglari hamma botda ishlaydi.</blockquote>"
    )
    kb = get_design_menu_kb(colors)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("design:btn:"))
async def cb_design_btn_detail(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer()
    if state:
        await state.clear()

    btn_key = call.data.split(":")[2]
    name = DESIGN_BTN_NAMES.get(btn_key, btn_key)
    cur_color = await db.get_setting(f"btn_color_{btn_key}", "⚪")
    cur_text = await db.get_setting(f"btn_text_{btn_key}", name)
    custom_emoji = await db.get_setting(f"btn_emoji_{btn_key}", "Yo'q")

    text = (
        f"🎨 <b>«{name}» tugmasi dizaynini sozlash:</b>\n\n"
        f"• <b>Tugma rangi:</b> {cur_color}\n"
        f"• <b>Tugma matni:</b> <code>{cur_text}</code>\n"
        f"• <b>Custom Emoji:</b> <code>{custom_emoji}</code>\n\n"
        "<i>Quyidagi amallardan birini tanlang:</i>"
    )
    kb = get_design_button_detail_kb(btn_key)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("design:color:"))
async def cb_design_color(call: CallbackQuery, is_admin: bool):
    if not is_admin:
        return await call.answer()
    btn_key = call.data.split(":")[2]
    name = DESIGN_BTN_NAMES.get(btn_key, btn_key)

    text = f"🎨 <b>«{name}» uchun rangni tanlang:</b>"
    kb = get_color_picker_kb(btn_key)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("design:set_color:"))
async def cb_design_set_color(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    parts = call.data.split(":")
    btn_key = parts[2]
    color = parts[3]

    await db.set_setting(f"btn_color_{btn_key}", color)
    await call.answer(f"🎨 Rang {color} ga o'zgartirildi!")
    
    call.data = f"design:btn:{btn_key}"
    await cb_design_btn_detail(call, is_admin, db)


@router.callback_query(F.data.startswith("design:text:"))
async def cb_design_text_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    btn_key = call.data.split(":")[2]
    name = DESIGN_BTN_NAMES.get(btn_key, btn_key)

    await state.update_data(btn_key=btn_key, name=name)
    await state.set_state(AdminDesignEdit.waiting_for_text)

    await call.message.edit_text(
        f"✏️ <b>«{name}» tugmasi uchun yangi matnni kiriting:</b>",
        reply_markup=get_cancel_fsm_kb(f"design:btn:{btn_key}"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminDesignEdit.waiting_for_text)
async def process_design_text(message: Message, state: FSMContext, db: Database):
    new_text = message.text.strip()
    data = await state.get_data()
    btn_key = data.get("btn_key", "subscribe")
    name = data.get("name", "Tugma")

    await db.set_setting(f"btn_text_{btn_key}", new_text)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Tugma sozlamalariga qaytish", callback_data=f"design:btn:{btn_key}")],
        [InlineKeyboardButton(text="🎨 Barcha dizaynlar", callback_data="admin:design")]
    ])
    await message.answer(
        f"✅ <b>«{name}»</b> tugmasi matni <code>{new_text}</code> ga o'zgartirildi!",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("design:emoji:"))
async def cb_design_emoji_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    btn_key = call.data.split(":")[2]
    name = DESIGN_BTN_NAMES.get(btn_key, btn_key)

    await state.update_data(btn_key=btn_key, name=name)
    await state.set_state(AdminDesignEdit.waiting_for_custom_emoji)

    await call.message.edit_text(
        f"✨ <b>«{name}»</b> uchun Telegram Premium Custom Emoji ID sini yuboring:\n(Masalan: <code>5368324170671202286</code>):",
        reply_markup=get_cancel_fsm_kb(f"design:btn:{btn_key}"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminDesignEdit.waiting_for_custom_emoji)
async def process_design_emoji(message: Message, state: FSMContext, db: Database):
    emoji_id = message.text.strip()
    data = await state.get_data()
    btn_key = data.get("btn_key", "subscribe")
    name = data.get("name", "Tugma")

    await db.set_setting(f"btn_emoji_{btn_key}", emoji_id)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Tugma sozlamalariga qaytish", callback_data=f"design:btn:{btn_key}")],
        [InlineKeyboardButton(text="🎨 Barcha dizaynlar", callback_data="admin:design")]
    ])
    await message.answer(
        f"✅ <b>«{name}»</b> uchun custom emoji muvaffaqiyatli saqlandi!",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("design:reset:"))
async def cb_design_reset(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    btn_key = call.data.split(":")[2]
    await db.set_setting(f"btn_color_{btn_key}", "⚪")
    default_text = DESIGN_BTN_NAMES.get(btn_key, btn_key)
    await db.set_setting(f"btn_text_{btn_key}", default_text)
    await db.set_setting(f"btn_emoji_{btn_key}", "Yo'q")

    await call.answer("🔄 Tugma dizayni asliga qaytarildi!", show_alert=True)
    call.data = f"design:btn:{btn_key}"
    await cb_design_btn_detail(call, is_admin, db)
