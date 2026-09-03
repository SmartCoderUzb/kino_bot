import secrets
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.keyboards.admin_kb import (
    get_back_to_admin_kb, 
    get_cancel_fsm_kb,
    get_premium_menu_kb,
    get_premium_tariffs_kb,
    get_premium_users_pagination_kb,
    get_premium_user_actions_kb,
    get_texts_menu_kb,
    get_text_edit_kb,
    get_referral_menu_kb,
    get_referral_list_pagination_kb
)
from kino_bot.utils.states import (
    AdminAddPayment, 
    AdminManageAdmin, 
    AdminSetText,
    AdminPremiumTariffEdit,
    AdminPremiumUserManage,
    AdminCreateReferralLink
)
from kino_bot.config import ADMINS, TEXT_LABELS, DEFAULT_TEXTS

router = Router(name="admin_settings")

# ================= TO'LOV TIZIMLAR =================
@router.callback_query(F.data == "admin:payments")
async def cb_admin_payments(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    systems = await db.get_payment_systems()
    text = "💳 <b>To'lov tizimlari va hisob raqamlari:</b>\n\n"
    if not systems:
        text += "<i>Hozircha to'lov usullari qo'shilmagan.</i>\n"
    else:
        for s in systems:
            text += f"• <b>{s['name']}:</b> <code>{s['details']}</code>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi karta / to'lov qo'shish", callback_data="pay:add")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "pay:add")
async def cb_pay_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminAddPayment.waiting_for_name)
    await call.message.edit_text(
        "💳 <b>To'lov tizimi nomini kiriting:</b>\n(Masalan: <i>Uzcard / Humo / Click / Payme</i>):",
        reply_markup=get_cancel_fsm_kb("admin:payments"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminAddPayment.waiting_for_name)
async def process_pay_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await state.update_data(name=name)
    await state.set_state(AdminAddPayment.waiting_for_details)
    await message.answer(
        f"💳 <b>{name}</b> uchun hisob yoki karta raqami va egasining ismini kiriting:\n(Masalan: <code>8600 0000 0000 0000 (Eshmat T.)</code>):",
        reply_markup=get_cancel_fsm_kb("admin:payments"),
        parse_mode="HTML"
    )


@router.message(AdminAddPayment.waiting_for_details)
async def process_pay_details(message: Message, state: FSMContext, db: Database):
    details = message.text.strip()
    data = await state.get_data()
    await db.add_payment_system(data["name"], details)
    await state.clear()

    await message.answer(
        f"✅ <b>{data['name']}</b> muvaffaqiyatli saqlandi!",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="HTML"
    )


# ================= PREMIUM SOZLAMALAR =================
@router.callback_query(F.data == "admin:premium")
async def cb_admin_premium(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    if state:
        await state.clear()
    
    prem_enabled = (await db.get_setting("premium_enabled", "0")) == "1"
    prem_count = await db.get_premium_users_count()
    
    status_str = "✅ Yoqiq" if prem_enabled else "⛔ O'chiq"

    text = (
        "⚙️ <b>Premium sozlamalar bo'limidasiz:</b>\n\n"
        f"🔹 <b>Premium holati:</b> {status_str}\n"
        f"👥 <b>Jami Premium foydalanuvchilar:</b> {prem_count} ta\n\n"
        "📌 Quyidagi tugmalardan foydalanib Premium sozlamalarini boshqaring."
    )
    kb = get_premium_menu_kb()
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "prem:toggle_status")
async def cb_prem_toggle_status(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    cur_val = await db.get_setting("premium_enabled", "0")
    new_val = "0" if cur_val == "1" else "1"
    await db.set_setting("premium_enabled", new_val)
    
    await cb_admin_premium(call, is_admin, db)


@router.callback_query(F.data.startswith("prem:users_list:"))
async def cb_prem_users_list(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    parts = call.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    
    users, total_count, total_pages = await db.get_premium_users_list(page=page, limit=10)
    
    if not users:
        text = (
            "👥 <b>Premium foydalanuvchilar ro'yxati:</b>\n\n"
            "<i>Hozircha Premium foydalanuvchilar mavjud emas.</i>"
        )
    else:
        text = f"👥 <b>Premium foydalanuvchilar ro'yxati</b> (Jami: {total_count} ta) | {page}/{total_pages}-sahifa:\n\n"
        for idx, u in enumerate(users, start=(page - 1) * 10 + 1):
            name = u.get("full_name") or u.get("username") or "Noma'lum"
            u_id = u["user_id"]
            until = u.get("premium_until")
            until_str = f"gacha: <code>{until}</code>" if until else "Muddatsiz"
            text += f"{idx}. 👤 <b>{name}</b> (<code>{u_id}</code>)\n    ⏳ Muddat: {until_str}\n\n"

    kb = get_premium_users_pagination_kb(page, total_pages)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "prem:tariffs")
async def cb_prem_tariffs(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer()
    if state:
        await state.clear()
    
    prem_1m = await db.get_setting("prem_1m_price", "15 000 so'm")
    prem_3m = await db.get_setting("prem_3m_price", "35 000 so'm")
    prem_1y = await db.get_setting("prem_1y_price", "99 000 so'm")

    text = (
        "📋 <b>Premium tariflar sozlamalari:</b>\n\n"
        f"• <b>1 oylik:</b> <code>{prem_1m}</code>\n"
        f"• <b>3 oylik:</b> <code>{prem_3m}</code>\n"
        f"• <b>1 yillik:</b> <code>{prem_1y}</code>\n\n"
        "<i>Narxni o'zgartirish uchun kerakli tarif tugmasini bosing:</i>"
    )
    kb = get_premium_tariffs_kb()
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("prem:edit:"))
async def cb_prem_edit_tariff_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    tariff_key = call.data.split(":")[2]
    tariff_names = {
        "1m": "1 oylik",
        "3m": "3 oylik",
        "1y": "1 yillik"
    }
    name = tariff_names.get(tariff_key, tariff_key)
    
    await state.update_data(tariff_key=tariff_key, tariff_name=name)
    await state.set_state(AdminPremiumTariffEdit.waiting_for_price)
    
    await call.message.edit_text(
        f"✏️ <b>{name}</b> tarif uchun yangi narxni kiriting:\n(Masalan: <code>20 000 so'm</code> yoki <code>1.5 $</code>):",
        reply_markup=get_cancel_fsm_kb("prem:tariffs"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminPremiumTariffEdit.waiting_for_price)
async def process_prem_tariff_price(message: Message, state: FSMContext, db: Database):
    price = message.text.strip()
    data = await state.get_data()
    tariff_key = data.get("tariff_key", "1m")
    tariff_name = data.get("tariff_name", "Tarif")
    
    setting_key = f"prem_{tariff_key}_price"
    await db.set_setting(setting_key, price)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Tariflar bo'limiga qaytish", callback_data="prem:tariffs")],
        [InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:main")]
    ])
    await message.answer(
        f"✅ <b>{tariff_name}</b> narxi muvaffaqiyatli <code>{price}</code> ga o'zgartirildi!",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data == "prem:manage_user")
async def cb_prem_manage_user_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    await state.set_state(AdminPremiumUserManage.waiting_for_user_id)
    await call.message.edit_text(
        "➕ Premium berish yoki muddatini boshqarish uchun foydalanuvchining <b>Telegram ID</b>sini kiriting:",
        reply_markup=get_cancel_fsm_kb("admin:premium"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminPremiumUserManage.waiting_for_user_id)
async def process_prem_manage_user_id(message: Message, state: FSMContext, db: Database):
    text = message.text.strip()
    if not text.isdigit():
        return await message.answer("❌ Faqat sonlardan iborat Telegram ID kiriting:", reply_markup=get_cancel_fsm_kb("admin:premium"))
    
    user_id = int(text)
    user = await db.get_user(user_id)
    if not user:
        return await message.answer(
            f"❌ <code>{user_id}</code> IDli foydalanuvchi bazada topilmadi.\n\nFoydalanuvchi botga kamida bir marta <b>/start</b> bosgan bo'lishi kerak.",
            reply_markup=get_cancel_fsm_kb("admin:premium"),
            parse_mode="HTML"
        )
    
    await state.clear()
    name = user.get("full_name") or user.get("username") or "Noma'lum"
    is_prem = user.get("is_premium") == 1
    prem_status = "✅ Faol" if is_prem else "❌ O'chiq"
    until = user.get("premium_until") or "Muddatsiz / Yo'q"
    
    caption = (
        "👤 <b>Foydalanuvchi Premium boshqaruvi:</b>\n\n"
        f"• <b>Ism:</b> {name}\n"
        f"• <b>ID:</b> <code>{user_id}</code>\n"
        f"• <b>Premium holati:</b> {prem_status}\n"
        f"• <b>Amal qilish muddati:</b> <code>{until}</code>\n\n"
        "<i>Kerakli amalni tanlang:</i>"
    )
    kb = get_premium_user_actions_kb(user_id, is_prem)
    await message.answer(caption, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("prem:grant:"))
async def cb_prem_grant(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    parts = call.data.split(":")
    user_id = int(parts[2])
    duration = parts[3]
    
    days = None if duration == "unlimited" else int(duration)
    success = await db.grant_premium(user_id, days=days)
    
    if success:
        dur_text = "muddatsiz (cheksiz)" if days is None else f"{days} kunga"
        text = f"🎉 <code>{user_id}</code> IDli foydalanuvchiga Premium <b>{dur_text}</b> muvaffaqiyatli berildi! ✅"
    else:
        text = f"❌ <code>{user_id}</code> foydalanuvchiga Premium berishda xatolik yuz berdi."

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Premium menyusiga qaytish", callback_data="admin:premium")],
        [InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("prem:revoke:"))
async def cb_prem_revoke(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    user_id = int(call.data.split(":")[2])
    await db.revoke_premium(user_id)
    
    text = f"❌ <code>{user_id}</code> IDli foydalanuvchidan Premium muvaffaqiyatli olib tashlandi!"
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Premium menyusiga qaytish", callback_data="admin:premium")],
        [InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ================= MATNLAR (TEXTS) =================
@router.callback_query(F.data == "admin:texts")
async def cb_admin_texts(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    if state:
        await state.clear()

    text = (
        "📝 <b>Matnlar bo'limi</b>\n\n"
        "O'zgartirmoqchi bo'lgan matnni tanlang:"
    )
    kb = get_texts_menu_kb()
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("text:edit:"))
async def cb_text_edit_start(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    text_key = call.data.split(":")[2]
    label = TEXT_LABELS.get(text_key, text_key)
    cur_text = await db.get_bot_text(text_key)

    await state.update_data(text_key=text_key, label=label)
    await state.set_state(AdminSetText.waiting_for_value)

    prompt = (
        f"📝 <b>«{label}»</b> matnini tahrirlash:\n\n"
        f"<b>Hozirgi matn:</b>\n"
        f"<blockquote>{cur_text}</blockquote>\n\n"
        "<i>Yangi matnni yuboring (HTML teglari qo'llab-quvvatlanadi):</i>"
    )
    kb = get_text_edit_kb(text_key)
    await call.message.edit_text(prompt, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminSetText.waiting_for_value)
async def process_text_value(message: Message, state: FSMContext, db: Database):
    new_text = message.html_text or message.text or ""
    data = await state.get_data()
    text_key = data.get("text_key", "welcome")
    label = data.get("label", "Matn")

    await db.set_bot_text(text_key, new_text)
    await state.clear()

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Matnlar bo'limiga qaytish", callback_data="admin:texts")],
        [InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:main")]
    ])
    await message.answer(
        f"✅ <b>«{label}»</b> matni muvaffaqiyatli saqlandi!\n\n"
        f"<b>Yangi matn:</b>\n<blockquote>{new_text}</blockquote>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("text:reset:"))
async def cb_text_reset_single(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    await state.clear()
    text_key = call.data.split(":")[2]
    label = TEXT_LABELS.get(text_key, text_key)
    await db.reset_bot_text(text_key)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Matnlar bo'limiga qaytish", callback_data="admin:texts")],
        [InlineKeyboardButton(text="◀️ Asosiy panel", callback_data="admin:main")]
    ])
    await call.message.edit_text(
        f"🔄 <b>«{label}»</b> matni standart holatiga qaytarildi!",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.callback_query(F.data == "text:reset_all")
async def cb_text_reset_all(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    await db.reset_all_bot_texts()
    await call.answer("🔄 Barcha bot matnlari standart holatiga qaytarildi!", show_alert=True)
    await cb_admin_texts(call, is_admin, db)


# ================= REFERAL =================
@router.callback_query(F.data == "admin:referral")
async def cb_admin_referral(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext = None):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    if state:
        await state.clear()
    
    links_count, users_count = await db.get_total_referral_stats()
    text = (
        "🔗 <b>Referal bo'limi</b>\n\n"
        f"📊 <b>Jami havolalar:</b> {links_count} ta\n"
        f"👥 <b>Jami kelgan foydalanuvchilar:</b> {users_count} ta"
    )
    kb = get_referral_menu_kb()
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "ref:create")
async def cb_ref_create_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    
    await state.set_state(AdminCreateReferralLink.waiting_for_name)
    await call.message.edit_text(
        "➕ <b>Yangi referal havola yaratish:</b>\n\n"
        "Havola uchun nom kiriting (masalan: <i>Instagram reklama</i> yoki <i>Kanal 1 post</i>):",
        reply_markup=get_cancel_fsm_kb("admin:referral"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminCreateReferralLink.waiting_for_name)
async def process_ref_create_name(message: Message, state: FSMContext, db: Database, bot):
    name = message.text.strip()
    code = f"ref_{secrets.token_hex(3)}"
    
    await db.create_referral_link(name=name, code=code)
    await state.clear()

    bot_info = await bot.get_me()
    link = f"https://t.me/{bot_info.username}?start={code}"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📋 Barcha havolalar", callback_data="ref:list:1")],
        [InlineKeyboardButton(text="➕ Yana havola yaratish", callback_data="ref:create")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:referral")]
    ])
    await message.answer(
        f"🎉 <b>Yangi referal havola yaratildi!</b>\n\n"
        f"📌 <b>Nomi:</b> <b>{name}</b>\n"
        f"🔗 <b>Havola:</b> <code>{link}</code>\n"
        f"👥 <b>Kelganlar:</b> 0 ta\n\n"
        f"<i>Ushbu havolani nusxalab, reklama yoki postlaringizga joylashingiz mumkin.</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("ref:list:"))
async def cb_ref_list(call: CallbackQuery, is_admin: bool, db: Database, bot):
    if not is_admin:
        return await call.answer()
    
    parts = call.data.split(":")
    page = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
    
    links, total_count, total_pages = await db.get_referral_links(page=page, limit=5)
    bot_info = await bot.get_me()

    if not links:
        text = (
            "📋 <b>Referal havolalar ro'yxati:</b>\n\n"
            "<i>Hozircha hech qanday havola yaratilmagan.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Havola yaratish", callback_data="ref:create")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:referral")]
        ])
    else:
        text = f"📋 <b>Referal havolalar ro'yxati</b> (Jami: {total_count} ta) | {page}/{total_pages}-sahifa:\n\n"
        for idx, l in enumerate(links, start=(page - 1) * 5 + 1):
            link_url = f"https://t.me/{bot_info.username}?start={l['code']}"
            created = str(l.get('created_at', ''))[:10]
            text += (
                f"{idx}. 📌 <b>{l['name']}</b>\n"
                f"    🔗 Havola: <code>{link_url}</code>\n"
                f"    👥 Kelganlar: <b>{l['joined']} ta</b> (Sana: {created})\n\n"
            )
        kb = get_referral_list_pagination_kb(page, total_pages, links)

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data.startswith("ref:del:"))
async def cb_ref_del(call: CallbackQuery, is_admin: bool, db: Database, bot):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    
    link_id = int(call.data.split(":")[2])
    await db.delete_referral_link(link_id)
    await call.answer("🗑 Havola muvaffaqiyatli o'chirildi!", show_alert=True)
    
    links, total_count, total_pages = await db.get_referral_links(page=1, limit=5)
    bot_info = await bot.get_me()

    if not links:
        text = (
            "📋 <b>Referal havolalar ro'yxati:</b>\n\n"
            "<i>Hozircha hech qanday havola yaratilmagan.</i>"
        )
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Havola yaratish", callback_data="ref:create")],
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:referral")]
        ])
    else:
        text = f"📋 <b>Referal havolalar ro'yxati</b> (Jami: {total_count} ta) | 1/{total_pages}-sahifa:\n\n"
        for idx, l in enumerate(links, start=1):
            link_url = f"https://t.me/{bot_info.username}?start={l['code']}"
            created = str(l.get('created_at', ''))[:10]
            text += (
                f"{idx}. 📌 <b>{l['name']}</b>\n"
                f"    🔗 Havola: <code>{link_url}</code>\n"
                f"    👥 Kelganlar: <b>{l['joined']} ta</b> (Sana: {created})\n\n"
            )
        kb = get_referral_list_pagination_kb(1, total_pages, links)

    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ================= ADMINLAR =================
@router.callback_query(F.data == "admin:admins")
async def cb_admin_admins(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    db_admins = await db.get_admins()
    all_admin_ids = list(set(ADMINS + db_admins))
    
    text = "👮‍♂️ <b>Bot Adminlari ro'yxati:</b>\n\n"
    for a_id in all_admin_ids:
        text += f"• <code>{a_id}</code>\n"

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Yangi admin qo'shish", callback_data="admin:add_new")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.callback_query(F.data == "admin:add_new")
async def cb_add_admin_start(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminManageAdmin.waiting_for_user_id)
    await call.message.edit_text(
        "👮‍♂️ Yangi adminning <b>Telegram ID</b>sini kiriting:",
        reply_markup=get_cancel_fsm_kb("admin:admins"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminManageAdmin.waiting_for_user_id)
async def process_add_admin(message: Message, state: FSMContext, db: Database):
    text = message.text.strip()
    if not text.isdigit():
        return await message.answer("❌ Faqat sonlardan iborat Telegram ID kiriting:", reply_markup=get_cancel_fsm_kb("admin:admins"))

    new_admin_id = int(text)
    await db.add_admin(new_admin_id)
    await state.clear()

    await message.answer(
        f"✅ <code>{new_admin_id}</code> IDli foydalanuvchi muvaffaqiyatli admin etib tayinlandi!",
        reply_markup=get_back_to_admin_kb(),
        parse_mode="HTML"
    )
