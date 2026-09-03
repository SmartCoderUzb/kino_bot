from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.utils.states import AdminAddChannelTelegram, AdminAddChannelExternal
from kino_bot.keyboards.admin_kb import get_channels_main_kb, get_channels_type_select_kb, get_cancel_fsm_kb

router = Router(name="admin_channels")

# ================= 1. ASOSIY MAJBURIY OBUNA MENYUSI =================
@router.callback_query(F.data == "admin:channels")
async def cb_admin_channels_main(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()

    text = "🔐 <b>Majburiy obuna kanallar:</b>"
    await call.message.edit_text(text, reply_markup=get_channels_main_kb(), parse_mode="HTML")
    await call.answer()


# ================= 2. TURINI TANLASH =================
@router.callback_query(F.data == "channels:type_select")
async def cb_channels_type_select(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.clear()

    text = (
        "⚙️ <b>Majburiy obuna turini tanlang:</b>\n\n"
        "Quyida majburiy obunani qo'shishning 3 ta turi mavjud:\n\n"
        "🔷 <b>Ommaviy / Shaxsiy (Kanal · Guruh)</b>\n"
        "Har qanday kanal yoki guruhni (ommaviy yoki shaxsiy) majburiy obunaga ulash.\n\n"
        "🔷 <b>Shaxsiy / So'rovli havola</b>\n"
        "Shaxsiy yoki so'rovli kanal/guruh havolasi orqali o'tganlarni kuzatish.\n\n"
        "🔷 <b>🌐 Oddiy havola</b>\n"
        "Majburiy tekshiruvsiz oddiy havolani ko'rsatish (Instagram, sayt va boshqalar)."
    )
    await call.message.edit_text(text, reply_markup=get_channels_type_select_kb(), parse_mode="HTML")
    await call.answer()


# ================= 3. TELEGRAM KANAL / SO'ROVLI QO'SHISH =================
@router.callback_query(F.data.startswith("chadd:type:"))
async def cb_chadd_type(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    ch_type = call.data.split(":")[2]

    if ch_type == "external":
        await state.set_state(AdminAddChannelExternal.waiting_for_name)
        text = (
            "🌐 <b>Oddiy havola qo'shish (Instagram, YouTube, Sayt va h.k.):</b>\n\n"
            "1️⃣ Havola uchun <b>tugma nomi</b>ni kiriting:\n"
            "(Masalan: <i>📸 Instagram sahifamiz</i> yoki <i>🔴 YouTube kanalimiz</i>)"
        )
        await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("channels:type_select"), parse_mode="HTML")
        return await call.answer()

    # For telegram & join_request
    await state.set_state(AdminAddChannelTelegram.waiting_for_forward_or_id)
    await state.update_data(channel_type=ch_type)

    type_title = "Ommaviy / Shaxsiy (Kanal · Guruh)" if ch_type == "telegram" else "Shaxsiy / So'rovli havola"
    text = (
        f"🔐 <b>{type_title} qo'shish:</b>\n\n"
        "1️⃣ Kanal ID sini yuboring (masalan: <code>-1001234567890</code>) yoki kanaldan biror postni bu yerga <b>Forward</b> qiling:\n\n"
        "<i>Eslatma: Bot ushbu kanalda admin bo'lishi kerak.</i>"
    )
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("channels:type_select"), parse_mode="HTML")
    await call.answer()


@router.message(AdminAddChannelTelegram.waiting_for_forward_or_id)
async def process_tg_channel_id(message: Message, state: FSMContext):
    channel_id = None
    channel_title = ""
    channel_username = ""

    if message.forward_from_chat:
        channel_id = str(message.forward_from_chat.id)
        channel_title = message.forward_from_chat.title or ""
        channel_username = message.forward_from_chat.username or ""
    elif message.text:
        text = message.text.strip()
        channel_id = text

    if not channel_id:
        return await message.answer(
            "❌ Noto'g'ri kanal ID yoki forward. Qaytadan urinib ko'ring:",
            reply_markup=get_cancel_fsm_kb("channels:type_select")
        )

    await state.update_data(channel_id=channel_id, channel_title=channel_title, channel_username=channel_username)
    await state.set_state(AdminAddChannelTelegram.waiting_for_name)

    prompt = f"✅ Kanal ID qabul qilindi: <code>{channel_id}</code>\n\n2️⃣ Kanal uchun <b>nom</b> kiriting:"
    if channel_title:
        prompt += f" (Masalan: <i>{channel_title}</i>)"
    await message.answer(prompt, reply_markup=get_cancel_fsm_kb("channels:type_select"), parse_mode="HTML")


@router.message(AdminAddChannelTelegram.waiting_for_name)
async def process_tg_channel_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AdminAddChannelTelegram.waiting_for_invite_link)
    await message.answer(
        f"3️⃣ Kanal uchun <b>taklif havolasi (link)</b>ni yuboring (masalan: <code>https://t.me/kanalingiz</code> yoki <code>https://t.me/+...</code>):",
        reply_markup=get_cancel_fsm_kb("channels:type_select"),
        parse_mode="HTML"
    )


@router.message(AdminAddChannelTelegram.waiting_for_invite_link)
async def process_tg_channel_link(message: Message, state: FSMContext, db: Database):
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://") or link.startswith("t.me/")):
        return await message.answer(
            "❌ Havola noto'g'ri. Iltimos to'liq https://t.me/... ko'rinishida yuboring:",
            reply_markup=get_cancel_fsm_kb("channels:type_select")
        )

    data = await state.get_data()
    channel_id = data["channel_id"]
    name = data["name"]
    username = data.get("channel_username", "")
    ch_type = data.get("channel_type", "telegram")

    await db.add_channel(
        channel_id=channel_id,
        name=name,
        invite_link=link,
        username=username,
        channel_type=ch_type
    )
    await state.clear()

    text = f"🎉 <b>{name}</b> kanali muvaffaqiyatli qo'shildi!"
    await message.answer(text, reply_markup=get_channels_main_kb(), parse_mode="HTML")


# ================= 4. ODDIY HAVOLA (INSTAGRAM/YOUTUBE) QO'SHISH =================
@router.message(AdminAddChannelExternal.waiting_for_name)
async def process_ext_channel_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AdminAddChannelExternal.waiting_for_url)
    await message.answer(
        f"2️⃣ <b>«{name}»</b> uchun <b>havola (URL)</b>ni yuboring:\n(Masalan: <code>https://instagram.com/profilingiz</code> yoki <code>https://youtube.com/@kanalingiz</code>)",
        reply_markup=get_cancel_fsm_kb("channels:type_select"),
        parse_mode="HTML"
    )


@router.message(AdminAddChannelExternal.waiting_for_url)
async def process_ext_channel_url(message: Message, state: FSMContext, db: Database):
    link = message.text.strip()
    if not (link.startswith("http://") or link.startswith("https://")):
        return await message.answer(
            "❌ Havola noto'g'ri. Iltimos to'liq https://... ko'rinishida yuboring:",
            reply_markup=get_cancel_fsm_kb("channels:type_select")
        )

    data = await state.get_data()
    name = data["name"]

    await db.add_channel(
        channel_id="",
        name=name,
        invite_link=link,
        username="",
        channel_type="external"
    )
    await state.clear()

    text = f"🎉 <b>{name}</b> havolasi muvaffaqiyatli qo'shildi!"
    await message.answer(text, reply_markup=get_channels_main_kb(), parse_mode="HTML")


# ================= 5. 📋 RO'YXATNI KO'RISH =================
@router.callback_query(F.data == "channels:list")
async def cb_channels_list(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    channels = await db.get_channels(active_only=False)
    if not channels:
        text = "📋 <b>Majburiy obuna kanallari:</b>\n\nHozircha kanallar qo'shilmagan."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channels:type_select")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:channels")]
        ])
        return await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    lines = ["📋 <b>Majburiy obuna kanallari ro'yxati:</b>\n"]
    for idx, ch in enumerate(channels, 1):
        status_emoji = "🟢 Faol" if ch.get("is_active") else "🔴 O'chiq"
        ch_type = ch.get("channel_type", "telegram")
        
        if ch_type == "external":
            type_tag = "🌐 Tashqi havola (Instagram/YouTube)"
        elif ch_type == "join_request":
            type_tag = "🔐 So'rovli havola"
        else:
            type_tag = "📢 Telegram kanal/guruh"

        lines.append(f"{idx}. <b>{ch['name']}</b> ({status_emoji})")
        lines.append(f"• Turi: {type_tag}")
        lines.append(f"• Havola: {ch['invite_link']}\n")

    text = "\n".join(lines)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="channels:type_select")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:channels")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ================= 6. 🗑 KANALNI O'CHIRISH =================
@router.callback_query(F.data == "channels:delete_menu")
async def cb_channels_delete_menu(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    channels = await db.get_channels(active_only=False)
    if not channels:
        text = "🗑 <b>Kanalni o'chirish:</b>\n\nO'chirish uchun kanallar mavjud emas."
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:channels")]
        ])
        return await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")

    keyboard = []
    for ch in channels:
        icon = "🌐" if ch.get("channel_type") == "external" else "📢"
        keyboard.append([
            InlineKeyboardButton(text=f"{icon} {ch['name']}", callback_data="noop"),
            InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"channels:del_id:{ch['id']}")
        ])

    keyboard.append([InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:channels")])

    text = "🗑 <b>Kanalni o'chirish:</b>\n\nO'chirmoqchi bo'lgan kanalni tanlang:"
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("channels:del_id:"))
async def cb_channel_delete_confirm(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    channel_id = int(call.data.split(":")[2])
    await db.delete_channel(channel_id)
    await call.answer("✅ Kanal o'chirildi!", show_alert=True)

    # Re-render delete menu
    await cb_channels_delete_menu(call, is_admin, db)
