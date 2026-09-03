from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.utils.states import AdminAddMovie, AdminBatchAddMovies, AdminEditMovie, AdminDeleteMovie
from kino_bot.keyboards.admin_kb import get_movies_mgmt_kb, get_movies_pagination_kb, get_cancel_fsm_kb

router = Router(name="admin_movies")

# ================= ASOSIY KINOLAR MENYUSI =================
@router.callback_query(F.data == "admin:movies")
async def cb_admin_movies(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()
    text = "🎬 <b>Kinolar bo'limi:</b>\n\nKerakli amalni tanlang:"
    await call.message.edit_text(text, reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")
    await call.answer()


# ================= 1. 📥 YAKKA KINO YUKLASH =================
@router.callback_query(F.data == "movies:add:single")
@router.callback_query(F.data == "movies:add")
async def cb_movies_add_single(call: CallbackQuery, is_admin: bool, state: FSMContext, db: Database):
    if not is_admin:
        return await call.answer()
    next_code = await db.get_next_available_code()
    await state.set_state(AdminAddMovie.waiting_for_video)
    await state.update_data(suggested_code=next_code)
    
    text = (
        "📥 <b>Yakka kino yuklash:</b>\n\n"
        "1️⃣ Iltimos, kino videosini (yoki faylini) yuboring.\n"
        f"💡 <i>Tavsiya etilgan keyingi kod: <code>{next_code}</code></i>"
    )
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminAddMovie.waiting_for_video, F.video | F.document)
async def process_single_video(message: Message, state: FSMContext):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    data = await state.get_data()
    suggested_code = data.get("suggested_code", "1")

    # If message has caption, suggest it as title
    caption_title = message.caption.strip() if message.caption else ""
    await state.update_data(file_id=file_id, file_type=file_type, caption_title=caption_title)
    await state.set_state(AdminAddMovie.waiting_for_code)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🔢 {suggested_code} kodini ishlatish", callback_data=f"use_code:{suggested_code}")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await message.answer(
        f"✅ Video qabul qilindi!\n\n2️⃣ Endi kino uchun <b>kod</b> kiriting (yoki quyidagi tavsiya etilgan kodni tanlang):",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminAddMovie.waiting_for_code, F.data.startswith("use_code:"))
async def cb_use_suggested_code(call: CallbackQuery, state: FSMContext):
    code = call.data.split(":")[1]
    await state.update_data(code=code)
    await state.set_state(AdminAddMovie.waiting_for_title)

    data = await state.get_data()
    caption_title = data.get("caption_title", "")
    prompt = f"🔢 Tanlangan kod: <b>{code}</b>\n\n3️⃣ Endi <b>Kino nomi</b>ni yuboring:"
    if caption_title:
        prompt += f"\n<i>(Izohdagi nom: {caption_title})</i>"

    await call.message.edit_text(prompt, reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminAddMovie.waiting_for_code)
async def process_movie_code(message: Message, state: FSMContext, db: Database):
    code = message.text.strip()
    existing = await db.get_movie_by_code(code)
    if existing:
        return await message.answer(
            f"⚠️ <b>{code}</b> kodli kino allaqachon mavjud!\nIltimos, boshqa kod kiriting:",
            reply_markup=get_cancel_fsm_kb("admin:movies"),
            parse_mode="HTML"
        )

    await state.update_data(code=code)
    await state.set_state(AdminAddMovie.waiting_for_title)
    await message.answer(
        f"🔢 Tanlangan kod: <b>{code}</b>\n\n3️⃣ Endi <b>Kino nomi</b>ni yuboring (masalan: <i>Forsaj 10</i>):",
        reply_markup=get_cancel_fsm_kb("admin:movies"),
        parse_mode="HTML"
    )


@router.message(AdminAddMovie.waiting_for_title)
async def process_movie_title(message: Message, state: FSMContext):
    title = message.text.strip()
    await state.update_data(title=title)
    await state.set_state(AdminAddMovie.waiting_for_quality)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="HD 720p", callback_data="qual:720p"), InlineKeyboardButton(text="Full HD 1080p", callback_data="qual:1080p")],
        [InlineKeyboardButton(text="480p", callback_data="qual:480p"), InlineKeyboardButton(text="4K Ultra", callback_data="qual:4K")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await message.answer(
        f"🎬 Kino nomi: <b>{title}</b>\n\n4️⃣ <b>Kino sifati</b>ni tanlang yoki qo'lda yozing:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminAddMovie.waiting_for_quality, F.data.startswith("qual:"))
async def cb_quality_choice(call: CallbackQuery, state: FSMContext):
    quality = call.data.split(":")[1]
    await state.update_data(quality=quality)
    await state.set_state(AdminAddMovie.waiting_for_language)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:Uzbek")],
        [InlineKeyboardButton(text="🇷🇺 Ruscha", callback_data="lang:Russian")],
        [InlineKeyboardButton(text="🇬🇧 Inglizcha", callback_data="lang:English")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await call.message.edit_text(
        f"💾 Sifat: <b>{quality}</b>\n\n5️⃣ <b>Kino tili</b>ni tanlang yoki qo'lda yozing:",
        reply_markup=kb,
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminAddMovie.waiting_for_quality)
async def process_quality_text(message: Message, state: FSMContext):
    quality = message.text.strip()
    await state.update_data(quality=quality)
    await state.set_state(AdminAddMovie.waiting_for_language)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇺🇿 O‘zbekcha", callback_data="lang:Uzbek")],
        [InlineKeyboardButton(text="🇷🇺 Ruscha", callback_data="lang:Russian")],
        [InlineKeyboardButton(text="🇬🇧 Inglizcha", callback_data="lang:English")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await message.answer(
        f"💾 Sifat: <b>{quality}</b>\n\n5️⃣ <b>Kino tili</b>ni tanlang yoki qo'lda yozing:",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminAddMovie.waiting_for_language, F.data.startswith("lang:"))
async def cb_language_choice(call: CallbackQuery, state: FSMContext, db: Database, bot):
    lang_map = {"Uzbek": "O‘zbekcha", "Russian": "Ruscha", "English": "Inglizcha"}
    lang_key = call.data.split(":")[1]
    language = lang_map.get(lang_key, "O‘zbekcha")
    
    data = await state.get_data()
    await db.add_movie(
        code=data["code"],
        title=data["title"],
        file_id=data["file_id"],
        file_type=data.get("file_type", "video"),
        quality=data.get("quality", "720p HD"),
        language=language
    )
    await state.clear()
    
    bot_info = await bot.get_me()
    text = (
        "🎉 <b>Kino muvaffaqiyatli saqlandi!</b>\n\n"
        f"🎬 <b>Nomi:</b> {data['title']}\n"
        f"🔢 <b>Kodi:</b> <code>{data['code']}</code>\n"
        f"💾 <b>Sifati:</b> {data.get('quality', '720p HD')}\n"
        f"🌐 <b>Tili:</b> {language}\n\n"
        f"🔗 <b>To'g'ridan-to'g'ri havola:</b> https://t.me/{bot_info.username}?start=m_{data['code']}"
    )
    await call.message.edit_text(text, reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")
    await call.answer()


@router.message(AdminAddMovie.waiting_for_language)
async def process_language_text(message: Message, state: FSMContext, db: Database, bot):
    language = message.text.strip()
    data = await state.get_data()
    
    await db.add_movie(
        code=data["code"],
        title=data["title"],
        file_id=data["file_id"],
        file_type=data.get("file_type", "video"),
        quality=data.get("quality", "720p HD"),
        language=language
    )
    await state.clear()

    bot_info = await bot.get_me()
    text = (
        "🎉 <b>Kino muvaffaqiyatli saqlandi!</b>\n\n"
        f"🎬 <b>Nomi:</b> {data['title']}\n"
        f"🔢 <b>Kodi:</b> <code>{data['code']}</code>\n"
        f"💾 <b>Sifati:</b> {data.get('quality', '720p HD')}\n"
        f"🌐 <b>Tili:</b> {language}\n\n"
        f"🔗 <b>To'g'ridan-to'g'ri havola:</b> https://t.me/{bot_info.username}?start=m_{data['code']}"
    )
    await message.answer(text, reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")


# ================= 2. 📦 KO'P KINO YUKLASH =================
@router.callback_query(F.data == "movies:add:batch")
async def cb_movies_batch_start(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.set_state(AdminBatchAddMovies.waiting_for_videos)
    await state.update_data(uploaded_count=0, uploaded_list=[])

    text = (
        "📦 <b>Ko'p kino yuklash rejimi faollashdi!</b>\n\n"
        "Istalgancha kino videolarini ketma-ket yuboring yoki kanalingizdan bu yerga <b>Forward</b> qiling.\n"
        "• Kodlar avtomatik tartib bilan belgilanadi.\n"
        "• Video izohidagi matn kino nomi sifatida olinadi.\n\n"
        "Yuklashni tugatgach <b>«✅ Yakunlash»</b> tugmasini bosing."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yakunlash", callback_data="batch:finish")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminBatchAddMovies.waiting_for_videos, F.video | F.document)
async def process_batch_video(message: Message, state: FSMContext, db: Database):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    
    code = await db.get_next_available_code()
    
    # Title from caption or fallback
    title = message.caption.strip() if message.caption else f"Kino #{code}"
    if len(title) > 100:
        title = title[:97] + "..."

    await db.add_movie(
        code=code,
        title=title,
        file_id=file_id,
        file_type=file_type,
        quality="720p HD",
        language="O‘zbekcha"
    )

    data = await state.get_data()
    count = data.get("uploaded_count", 0) + 1
    u_list = data.get("uploaded_list", [])
    u_list.append(f"• <b>{title}</b> (Kod: <code>{code}</code>)")
    await state.update_data(uploaded_count=count, uploaded_list=u_list)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"✅ Yakunlash ({count} ta yuklandi)", callback_data="batch:finish")],
        [InlineKeyboardButton(text="❌ Bekor qilish", callback_data="admin:movies")]
    ])
    await message.answer(
        f"✅ <b>{count}-kino yuklandi!</b>\n🎬 <b>{title}</b> | Kod: <code>{code}</code>\n\n<i>Yana yuborishingiz mumkin...</i>",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminBatchAddMovies.waiting_for_videos, F.data == "batch:finish")
async def cb_batch_finish(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    count = data.get("uploaded_count", 0)
    u_list = data.get("uploaded_list", [])
    await state.clear()

    if count == 0:
        return await call.message.edit_text("ℹ️ Hech qanday kino yuklanmadi.", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")

    summary_text = (
        f"🎉 <b>Ko'p kino yuklash muvaffaqiyatli yakunlandi!</b>\n\n"
        f"📊 Jami yuklangan kinolar: <b>{count}</b> ta\n\n" +
        "\n".join(u_list[:15])
    )
    if len(u_list) > 15:
        summary_text += f"\n<i>...va yana {len(u_list) - 15} ta kino</i>"

    await call.message.edit_text(summary_text, reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")
    await call.answer()


# ================= 3. 📝 KINO TAHRIRLASH =================
@router.callback_query(F.data == "movies:edit")
async def cb_movies_edit(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.set_state(AdminEditMovie.waiting_for_target_code)
    text = (
        "📝 <b>Kino tahrirlash:</b>\n\n"
        "Tahrirlamoqchi bo'lgan <b>kino kodi</b>ni yuboring:"
    )
    await call.message.edit_text(text, reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminEditMovie.waiting_for_target_code)
async def process_edit_target_code(message: Message, state: FSMContext, db: Database):
    code = message.text.strip()
    movie = await db.get_movie_by_code(code)
    if not movie:
        return await message.answer(
            f"❌ <b>{code}</b> kodli kino topilmadi. Qaytadan kod kiriting:",
            reply_markup=get_cancel_fsm_kb("admin:movies"),
            parse_mode="HTML"
        )

    await state.update_data(movie_id=movie["id"], code=movie["code"])
    
    text = (
        f"🎬 <b>Kino ma'lumotlari:</b>\n\n"
        f"• Nomi: <b>{movie['title']}</b>\n"
        f"• Kodi: <code>{movie['code']}</code>\n"
        f"• Sifati: {movie.get('quality', '720p HD')}\n"
        f"• Tili: {movie.get('language', 'O‘zbekcha')}\n"
        f"• Yuklashlar: {movie['downloads']} ta\n\n"
        "Qaysi ma'lumotni o'zgartirmoqchisiz?"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Nomini o'zgartirish", callback_data=f"medit:title:{movie['id']}")],
        [InlineKeyboardButton(text="✏️ Kodini o'zgartirish", callback_data=f"medit:code:{movie['id']}")],
        [InlineKeyboardButton(text="🔄 Yangi video yuklash", callback_data=f"medit:video:{movie['id']}")],
        [InlineKeyboardButton(text="⬅️ Orqaga", callback_data="admin:movies")]
    ])
    await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("medit:title:"))
async def cb_edit_title(call: CallbackQuery, state: FSMContext):
    movie_id = int(call.data.split(":")[2])
    await state.set_state(AdminEditMovie.waiting_for_new_title)
    await state.update_data(edit_movie_id=movie_id)
    await call.message.edit_text("✏️ Kino uchun <b>yangi nom</b>ni yuboring:", reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminEditMovie.waiting_for_new_title)
async def process_new_title(message: Message, state: FSMContext, db: Database):
    new_title = message.text.strip()
    data = await state.get_data()
    movie_id = data["edit_movie_id"]
    await db.update_movie(movie_id, title=new_title)
    await state.clear()
    await message.answer(f"✅ Kino nomi <b>{new_title}</b> ga o'zgartirildi!", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("medit:code:"))
async def cb_edit_code(call: CallbackQuery, state: FSMContext):
    movie_id = int(call.data.split(":")[2])
    await state.set_state(AdminEditMovie.waiting_for_new_code)
    await state.update_data(edit_movie_id=movie_id)
    await call.message.edit_text("✏️ Kino uchun <b>yangi kod</b>ni kiriting:", reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminEditMovie.waiting_for_new_code)
async def process_new_code(message: Message, state: FSMContext, db: Database):
    new_code = message.text.strip()
    existing = await db.get_movie_by_code(new_code)
    if existing:
        return await message.answer(f"⚠️ <b>{new_code}</b> kodi allaqachon boshqa kinoda mavjud!", reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")

    data = await state.get_data()
    movie_id = data["edit_movie_id"]
    await db.update_movie(movie_id, code=new_code)
    await state.clear()
    await message.answer(f"✅ Kino kodi <code>{new_code}</code> ga o'zgartirildi!", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")


@router.callback_query(F.data.startswith("medit:video:"))
async def cb_edit_video(call: CallbackQuery, state: FSMContext):
    movie_id = int(call.data.split(":")[2])
    await state.set_state(AdminEditMovie.waiting_for_new_video)
    await state.update_data(edit_movie_id=movie_id)
    await call.message.edit_text("🔄 Yangi kino videosini yuboring:", reply_markup=get_cancel_fsm_kb("admin:movies"), parse_mode="HTML")
    await call.answer()


@router.message(AdminEditMovie.waiting_for_new_video, F.video | F.document)
async def process_new_video(message: Message, state: FSMContext, db: Database):
    file_id = message.video.file_id if message.video else message.document.file_id
    file_type = "video" if message.video else "document"
    data = await state.get_data()
    movie_id = data["edit_movie_id"]
    await db.update_movie(movie_id, file_id=file_id, file_type=file_type)
    await state.clear()
    await message.answer("✅ Kino videosi muvaffaqiyatli almashtirildi!", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")


# ================= 4. 🗑 KINO O‘CHIRISH =================
@router.callback_query(F.data == "movies:delete")
async def cb_movies_delete(call: CallbackQuery, is_admin: bool, state: FSMContext):
    if not is_admin:
        return await call.answer()
    await state.set_state(AdminDeleteMovie.waiting_for_code)
    await call.message.edit_text(
        "🗑 <b>Kino o'chirish:</b>\n\nO'chirmoqchi bo'lgan <b>kino kodi</b>ni kiriting:",
        reply_markup=get_cancel_fsm_kb("admin:movies"),
        parse_mode="HTML"
    )
    await call.answer()


@router.message(AdminDeleteMovie.waiting_for_code)
async def process_delete_code(message: Message, state: FSMContext, db: Database):
    code = message.text.strip()
    success = await db.delete_movie(code)
    await state.clear()
    if success:
        await message.answer(f"✅ <b>{code}</b> kodli kino muvaffaqiyatli o'chirildi.", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")
    else:
        await message.answer(f"❌ <b>{code}</b> kodli kino topilmadi.", reply_markup=get_movies_mgmt_kb(), parse_mode="HTML")


# ================= 5. 📋 KINOLAR RO'YXATI =================
@router.callback_query(F.data.startswith("movies:list:"))
async def cb_movies_list(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()
    
    page = int(call.data.split(":")[2])
    movies, total_count, total_pages = await db.get_movies_list(page=page, limit=10)

    if not movies:
        text = "📋 <b>Kinolar ro'yxati</b>\n\nHozircha botda kinolar mavjud emas."
        return await call.message.edit_text(text, reply_markup=get_movies_pagination_kb(1, 1), parse_mode="HTML")
    
    lines = [
        "📋 <b>Kinolar ro'yxati</b>",
        f"📊 Jami: {total_count} ta | Sahifa: {page} / {total_pages}\n"
    ]
    for idx, m in enumerate(movies, (page - 1) * 10 + 1):
        lines.append(f"{idx}. <b>{m['title']}</b>")
        lines.append(f"🔢 Kod: <code>{m['code']}</code> | 💾 {m.get('quality', '720p HD')} | 📥 {m['downloads']} ta\n")
    
    text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=get_movies_pagination_kb(page, total_pages), parse_mode="HTML")
    await call.answer()
