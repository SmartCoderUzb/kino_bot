from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ChatJoinRequest, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.utils.states import AdminSetJoinPost
from kino_bot.keyboards.admin_kb import get_join_requests_menu_kb, get_cancel_fsm_kb, get_back_to_admin_kb
import logging

logger = logging.getLogger(__name__)
router = Router(name="admin_requests")


async def get_requests_dashboard_data(db: Database):
    auto_appr = (await db.get_setting("auto_approve_requests", "0")) == "1"
    post_text = await db.get_setting("join_post_text", "")
    has_post = bool(post_text)

    auto_status = "✅ Yoqiq" if auto_appr else "❌ O'chiq"
    post_status = "✅ Belgilangan" if has_post else "❌ Belgilanmagan"

    text = (
        "📩 <b>So'rovlar bo'limi</b>\n\n"
        f"⚡️ <b>Avto tasdiqlash:</b> {auto_status}\n"
        f"📨 <b>Yuborish posti:</b> {post_status}"
    )
    return text, auto_appr, has_post


# ================= 1. ASOSIY SO'ROVLAR OYNASI =================
@router.callback_query(F.data == "admin:requests")
async def cb_admin_requests_main(call: CallbackQuery, is_admin: bool, db: Database, state: FSMContext):
    if not is_admin:
        return await call.answer("❌ Ruxsat yo'q!", show_alert=True)
    await state.clear()

    text, auto_appr, has_post = await get_requests_dashboard_data(db)
    kb = get_join_requests_menu_kb(auto_appr, has_post)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


# ================= 2. AVTO TASDIQLASHNI YOQISH / O'CHIRISH =================
@router.callback_query(F.data == "requests:toggle_auto")
async def cb_toggle_auto_approve(call: CallbackQuery, is_admin: bool, db: Database):
    if not is_admin:
        return await call.answer()

    cur_val = await db.get_setting("auto_approve_requests", "0")
    new_val = "0" if cur_val == "1" else "1"
    await db.set_setting("auto_approve_requests", new_val)

    msg = "Avto tasdiqlash yoqildi!" if new_val == "1" else "Avto tasdiqlash o'chirildi!"
    await call.answer(msg)

    text, auto_appr, has_post = await get_requests_dashboard_data(db)
    kb = get_join_requests_menu_kb(auto_appr, has_post)
    try:
        await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    except Exception:
        pass


# ================= 3. 📨 POST BELGILASH =================
@router.callback_query(F.data == "requests:set_post")
async def cb_set_post_start(call: CallbackQuery, is_admin: bool, state: FSMContext, db: Database):
    if not is_admin:
        return await call.answer()
    await state.set_state(AdminSetJoinPost.waiting_for_content)

    post_text = await db.get_setting("join_post_text", "")
    if not post_text:
        header = "📭 <b>Post hali belgilanmagan!</b>"
    else:
        header = "📬 <b>Hozirgi post belgilangan!</b>\n<i>(Yangi post yuborsangiz, eskisi yangilanadi)</i>"

    text = (
        f"{header}\n\n"
        "Foydalanuvchi arizasi tasdiqlanganda unga yuborilishi kerak bo'lgan xabarni (rasm, tekst, video) yuboring:"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:requests")]
    ])
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminSetJoinPost.waiting_for_content)
async def process_join_post_content(message: Message, state: FSMContext):
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
    await state.set_state(AdminSetJoinPost.waiting_for_button_text)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⏭ Tugmasiz saqlash", callback_data="joinpost:skip_btn")],
        [InlineKeyboardButton(text="◀️ Orqaga", callback_data="admin:requests")]
    ])
    await message.answer(
        "2️⃣ Post ostidagi <b>tugma matni</b>ni kiriting (masalan: <i>🎬 Botga kirish</i>):",
        reply_markup=kb,
        parse_mode="HTML"
    )


@router.callback_query(AdminSetJoinPost.waiting_for_button_text, F.data == "joinpost:skip_btn")
async def cb_skip_join_post_btn(call: CallbackQuery, state: FSMContext, db: Database):
    data = await state.get_data()
    await db.set_setting("join_post_text", data.get("text", ""))
    await db.set_setting("join_post_type", data.get("content_type", "text"))
    await db.set_setting("join_post_file_id", data.get("file_id", ""))
    await db.set_setting("join_post_btn_text", "")
    await db.set_setting("join_post_btn_url", "")
    await state.clear()

    text, auto_appr, has_post = await get_requests_dashboard_data(db)
    kb = get_join_requests_menu_kb(auto_appr, has_post)
    await call.message.edit_text(f"🎉 <b>Post muvaffaqiyatli saqlandi!</b>\n\n{text}", reply_markup=kb, parse_mode="HTML")
    await call.answer()


@router.message(AdminSetJoinPost.waiting_for_button_text)
async def process_join_post_btn_text(message: Message, state: FSMContext):
    btn_text = message.text.strip()
    await state.update_data(btn_text=btn_text)
    await state.set_state(AdminSetJoinPost.waiting_for_button_url)

    await message.answer(
        f"3️⃣ <b>«{btn_text}»</b> tugmasi uchun <b>havola (URL)</b>ni kiriting (masalan: <code>https://t.me/bot_nomi</code>):",
        reply_markup=get_cancel_fsm_kb("admin:requests"),
        parse_mode="HTML"
    )


@router.message(AdminSetJoinPost.waiting_for_button_url)
async def process_join_post_btn_url(message: Message, state: FSMContext, db: Database):
    btn_url = message.text.strip()
    data = await state.get_data()
    
    await db.set_setting("join_post_text", data.get("text", ""))
    await db.set_setting("join_post_type", data.get("content_type", "text"))
    await db.set_setting("join_post_file_id", data.get("file_id", ""))
    await db.set_setting("join_post_btn_text", data.get("btn_text", ""))
    await db.set_setting("join_post_btn_url", btn_url)
    await state.clear()

    text, auto_appr, has_post = await get_requests_dashboard_data(db)
    kb = get_join_requests_menu_kb(auto_appr, has_post)
    await message.answer(f"🎉 <b>Tugmali post muvaffaqiyatli saqlandi!</b>\n\n{text}", reply_markup=kb, parse_mode="HTML")


# ================= 4. 🗑 POSTNI O'CHIRISH =================
@router.callback_query(F.data == "requests:clear_post")
async def cb_clear_join_post(call: CallbackQuery, db: Database):
    await db.set_setting("join_post_text", "")
    await db.set_setting("join_post_type", "")
    await db.set_setting("join_post_file_id", "")
    await db.set_setting("join_post_btn_text", "")
    await db.set_setting("join_post_btn_url", "")
    await call.answer("🗑 Yuborish posti o'chirildi!", show_alert=True)

    text, auto_appr, has_post = await get_requests_dashboard_data(db)
    kb = get_join_requests_menu_kb(auto_appr, has_post)
    await call.message.edit_text(text, reply_markup=kb, parse_mode="HTML")


# ================= 5. SO'ROV KELGANDA AVTO TASDIQLASH VA POST YUBORISH =================
@router.chat_join_request()
async def handle_chat_join_request(event: ChatJoinRequest, db: Database, bot):
    auto_appr = (await db.get_setting("auto_approve_requests", "0")) == "1"
    user_id = event.from_user.id

    # Track user
    await db.add_or_update_user(
        user_id=user_id,
        username=event.from_user.username,
        full_name=event.from_user.full_name
    )

    if auto_appr:
        try:
            await bot.approve_chat_join_request(chat_id=event.chat.id, user_id=user_id)
            logger.info(f"Avto tasdiqlandi: user {user_id} in {event.chat.id}")
        except Exception as e:
            logger.warning(f"Error approving join request for {user_id}: {e}")

    # Send join post if configured
    post_text = await db.get_setting("join_post_text", "")
    if post_text:
        post_type = await db.get_setting("join_post_type", "text")
        file_id = await db.get_setting("join_post_file_id", "")
        btn_text = await db.get_setting("join_post_btn_text", "")
        btn_url = await db.get_setting("join_post_btn_url", "")

        kb = None
        if btn_text and btn_url:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn_text, url=btn_url)]
            ])

        try:
            if post_type == "photo":
                await bot.send_photo(chat_id=user_id, photo=file_id, caption=post_text, reply_markup=kb, parse_mode="HTML")
            elif post_type == "video":
                await bot.send_video(chat_id=user_id, video=file_id, caption=post_text, reply_markup=kb, parse_mode="HTML")
            elif post_type == "animation":
                await bot.send_animation(chat_id=user_id, animation=file_id, caption=post_text, reply_markup=kb, parse_mode="HTML")
            else:
                await bot.send_message(chat_id=user_id, text=post_text, reply_markup=kb, parse_mode="HTML")
        except Exception as e:
            logger.warning(f"Could not send join post to user {user_id}: {e}")
