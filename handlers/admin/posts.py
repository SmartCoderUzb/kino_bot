from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.utils.states import AdminPostMaker
from kino_bot.keyboards.admin_kb import get_back_to_admin_kb

router = Router(name="admin_posts")

# ================= 1. POSTLAR BO'LIMI ASOSIY OYNA =================
@router.callback_query(F.data == "admin:posts")
async def cb_admin_posts_main(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()

    text = (
        "📬 <b>Postlar bo'limi</b>\n\n"
        "Kanal yoki guruhga post yuborish uchun quyidagi tugmani bosing."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✍️ Yangi post yaratish", callback_data="posts:new")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ================= 2. KANAL YOKI GURUHNI TANLASH =================
@router.callback_query(F.data == "posts:new")
async def cb_posts_new(call: CallbackQuery, is_admin: bool, state: FSMContext, db: Database):
    if not is_admin:
        return await call.answer()
    await state.clear()

    channels = await db.get_channels(active_only=False)
    
    keyboard = []
    for ch in channels:
        keyboard.append([
            InlineKeyboardButton(text=f"📢 {ch['name']}", callback_data=f"posts:sel_chan:{ch['channel_id']}")
        ])
    
    keyboard.append([
        InlineKeyboardButton(text="✏️ ID/username/forward - kiritish", callback_data="posts:input_channel")
    ])
    keyboard.append([
        InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:posts")
    ])

    text = (
        "📢 <b>Kanal yoki guruhni tanlang:</b>\n\n"
        "Yoki o'zingiz kiriting."
    )
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="HTML")
    await call.answer()


# ================= 3. KANALNI QO'LDA KIRITISH =================
@router.callback_query(F.data == "posts:input_channel")
async def cb_posts_input_channel(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminPostMaker.waiting_for_channel)
    text = (
        "✏️ <b>Kanal yoki guruhni kiriting:</b>\n\n"
        "Quyidagi usullardan birini tanlang:\n\n"
        "🔹 <b>1. Username orqali</b>\n"
        "@kanalUsername\n\n"
        "🔹 <b>2. ID orqali</b>\n"
        "-1001234567890\n\n"
        "🔹 <b>3. Kanaldan xabar forward qilib yuboring</b>"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="posts:new")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminPostMaker.waiting_for_channel)
async def process_channel_input(message: Message, state: FSMContext):
    target_channel = None

    if message.forward_from_chat:
        target_channel = str(message.forward_from_chat.id)
    elif message.text:
        text = message.text.strip()
        target_channel = text

    if not target_channel:
        return await message.answer(
            "❌ Noto'g'ri kanal kiritildi. Qaytadan urinib ko'ring:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="posts:new")]
            ])
        )

    await state.update_data(target_channel=target_channel)
    await state.set_state(AdminPostMaker.waiting_for_movie_code)

    await message.answer(
        f"✅ Kanal qabul qilindi: <code>{target_channel}</code>\n\n"
        "🎬 Endi kanalga joylamoqchi bo'lgan <b>kino kodi</b>ni yuboring (masalan: <code>101</code>):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="posts:new")]
        ]),
        parse_mode="HTML"
    )


@router.callback_query(F.data.startswith("posts:sel_chan:"))
async def cb_select_existing_channel(call: CallbackQuery, state: FSMContext):
    channel_id = call.data.split(":")[2]
    await state.update_data(target_channel=channel_id)
    await state.set_state(AdminPostMaker.waiting_for_movie_code)

    await call.message.edit_text(
        f"✅ Kanal tanlandi: <code>{channel_id}</code>\n\n"
        "🎬 Endi kanalga joylamoqchi bo'lgan <b>kino kodi</b>ni yuboring (masalan: <code>101</code>):",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Orqaga", callback_data="posts:new")]
        ]),
        parse_mode="HTML"
    )
    await call.answer()


# ================= 4. KINO KODINI QABUL QILISH VA PREVIEW =================
@router.message(AdminPostMaker.waiting_for_movie_code)
async def process_post_movie_code(message: Message, state: FSMContext, db: Database, bot):
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)

    if not movie:
        return await message.answer(
            f"❌ <b>{code}</b> kodli kino topilmadi. Qaytadan kod kiriting:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="posts:new")]
            ]),
            parse_mode="HTML"
        )

    data = await state.get_data()
    target_channel = data.get("target_channel")
    await state.update_data(movie_id=movie["id"], code=movie["code"])

    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=m_{movie['code']}"

    post_caption = (
        f"🎬 <b>{movie['title']}</b>\n\n"
        f"🔢 <b>Kino kodi:</b> <code>{movie['code']}</code>\n"
        f"💾 <b>Sifati:</b> {movie.get('quality', '720p HD')}\n"
        f"🌐 <b>Tili:</b> {movie.get('language', 'O‘zbekcha')}\n\n"
        f"📥 <b>Kinoni yuklab olish uchun bot:</b>\n"
        f"👉 @{bot_info.username}"
    )

    action_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🚀 Kanalga yuborish", callback_data="post:publish")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:posts")]
    ])

    await message.answer("👁 <b>Post namunasi (Preview):</b>", parse_mode="HTML")
    
    link_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kinoni yuklab olish", url=deep_link)]
    ])

    try:
        if movie.get("file_type") == "video":
            await bot.send_video(
                chat_id=message.chat.id,
                video=movie["file_id"],
                caption=post_caption,
                reply_markup=link_btn,
                parse_mode="HTML"
            )
        else:
            await bot.send_document(
                chat_id=message.chat.id,
                document=movie["file_id"],
                caption=post_caption,
                reply_markup=link_btn,
                parse_mode="HTML"
            )
    except Exception:
        await message.answer(post_caption, reply_markup=link_btn, parse_mode="HTML")

    await message.answer(
        f"📢 Tanlangan kanal: <code>{target_channel}</code>\n\nPostni kanalga yuborasizmi?",
        reply_markup=action_kb,
        parse_mode="HTML"
    )


# ================= 5. KANALGA POSTNI YUBORISH =================
@router.callback_query(F.data == "post:publish")
async def cb_post_publish(call: CallbackQuery, state: FSMContext, db: Database, bot):
    data = await state.get_data()
    target_channel = data.get("target_channel")
    movie_id = data.get("movie_id")
    await state.clear()

    if not target_channel or not movie_id:
        return await call.message.edit_text("❌ Ma'lumotlar topilmadi.", reply_markup=get_back_to_admin_kb())

    movie = await db.get_movie_by_id(movie_id)
    if not movie:
        return await call.message.edit_text("❌ Kino topilmadi.", reply_markup=get_back_to_admin_kb())

    bot_info = await bot.get_me()
    deep_link = f"https://t.me/{bot_info.username}?start=m_{movie['code']}"

    post_caption = (
        f"🎬 <b>{movie['title']}</b>\n\n"
        f"🔢 <b>Kino kodi:</b> <code>{movie['code']}</code>\n"
        f"💾 <b>Sifati:</b> {movie.get('quality', '720p HD')}\n"
        f"🌐 <b>Tili:</b> {movie.get('language', 'O‘zbekcha')}\n\n"
        f"📥 <b>Kinoni yuklab olish uchun bot:</b>\n"
        f"👉 @{bot_info.username}"
    )

    channel_btn = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎬 Kinoni yuklab olish", url=deep_link)]
    ])

    try:
        if movie.get("file_type") == "video":
            await bot.send_video(
                chat_id=target_channel,
                video=movie["file_id"],
                caption=post_caption,
                reply_markup=channel_btn,
                parse_mode="HTML"
            )
        else:
            await bot.send_document(
                chat_id=target_channel,
                document=movie["file_id"],
                caption=post_caption,
                reply_markup=channel_btn,
                parse_mode="HTML"
            )
        
        await call.message.edit_text(
            f"🎉 <b>Post muvaffaqiyatli kanalga yuborildi!</b>\n\n"
            f"📢 Kanal: <code>{target_channel}</code>\n"
            f"🎬 Kino: <b>{movie['title']}</b> (Kod: <code>{movie['code']}</code>)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✍️ Yana post yaratish", callback_data="posts:new")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
            ]),
            parse_mode="HTML"
        )
    except Exception as e:
        await call.message.edit_text(
            f"❌ <b>Xatolik yuz berdi:</b>\n\n<code>{e}</code>\n\n"
            "<i>Iltimos, bot ushbu kanalda admin ekanligiga va xabar yuborish huquqiga ega ekanligiga ishonch hosil qiling.</i>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Qaytadan urinish", callback_data="posts:new")],
                [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:main")]
            ]),
            parse_mode="HTML"
        )
    await call.answer()
