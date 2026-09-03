from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from kino_bot.database.db import Database
from kino_bot.keyboards.user_kb import get_movie_action_kb, get_sub_channels_kb
from kino_bot.keyboards.admin_kb import get_admin_reply_kb
from kino_bot.middlewares.check_sub import is_user_subscribed

router = Router(name="user_start")

async def send_ad_if_enabled(bot, chat_id: int, setting_key: str, db: Database):
    val = await db.get_setting(setting_key, "0")
    if val == "1":
        ad = await db.get_active_ad()
        if ad:
            kb = None
            if ad.get("button_text") and ad.get("button_url"):
                kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text=ad["button_text"], url=ad["button_url"])]
                ])
            try:
                if ad["content_type"] == "photo":
                    await bot.send_photo(chat_id=chat_id, photo=ad["file_id"], caption=ad["text"], reply_markup=kb, parse_mode="HTML")
                elif ad["content_type"] == "video":
                    await bot.send_video(chat_id=chat_id, video=ad["file_id"], caption=ad["text"], reply_markup=kb, parse_mode="HTML")
                elif ad["content_type"] == "animation":
                    await bot.send_animation(chat_id=chat_id, animation=ad["file_id"], caption=ad["text"], reply_markup=kb, parse_mode="HTML")
                else:
                    await bot.send_message(chat_id=chat_id, text=ad["text"], reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass


async def deliver_movie(bot, chat_id: int, user_id: int, movie: dict, db: Database):
    await db.record_download(user_id, movie["id"])
    bot_info = await bot.get_me()

    raw_caption = await db.get_bot_text("movie_caption")
    try:
        caption = raw_caption.format(
            title=movie['title'],
            code=movie['code'],
            quality=movie.get('quality', '720p HD'),
            language=movie.get('language', 'O‘zbekcha'),
            bot_username=bot_info.username
        )
    except Exception:
        caption = (
            f"🎬 <b>Nomi:</b> {movie['title']}\n"
            f"🔢 <b>Kodi:</b> <code>{movie['code']}</code>\n"
            f"💾 <b>Sifati:</b> {movie.get('quality', '720p HD')}\n"
            f"🌐 <b>Tili:</b> {movie.get('language', 'O‘zbekcha')}\n\n"
            f"🤖 <b>Bot:</b> @{bot_info.username}"
        )
    
    user = await db.get_user(user_id)
    is_prem = bool(user and user.get("is_premium") == 1)

    if is_prem:
        protect = (await db.get_setting("protect_content_premium", "1")) == "1"
    else:
        protect = (await db.get_setting("protect_content_regular", "1")) == "1"

    kb = get_movie_action_kb(movie["code"], bot_info.username)

    if movie.get("file_type") == "video":
        await bot.send_video(
            chat_id=chat_id, 
            video=movie["file_id"], 
            caption=caption, 
            reply_markup=kb, 
            protect_content=protect,
            parse_mode="HTML"
        )
    else:
        await bot.send_document(
            chat_id=chat_id, 
            document=movie["file_id"], 
            caption=caption, 
            reply_markup=kb, 
            protect_content=protect,
            parse_mode="HTML"
        )

    # Send movie ad if enabled
    await send_ad_if_enabled(bot, chat_id, "ad_on_movie", db)


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject, db: Database, bot, is_admin: bool = False, state: FSMContext = None):
    user = message.from_user
    args = command.args

    if state:
        await state.clear()

    # Check for direct movie link: /start m_123 or /start 123
    if args:
        movie_code = None
        if args.startswith("m_"):
            movie_code = args.replace("m_", "").strip()
        elif args.isdigit():
            movie_code = args.strip()

        if movie_code:
            movie = await db.get_movie_by_code(movie_code)
            if movie:
                # Check subscription first
                channels = await db.get_channels(active_only=True)
                unsubbed = []
                redis_client = None
                for ch in channels:
                    if ch.get("channel_type") == "external":
                        continue
                    if not await is_user_subscribed(bot, user.id, ch["channel_id"]):
                        unsubbed.append(ch)

                if unsubbed:
                    text = await db.get_bot_text("channels_msg")
                    return await message.answer(text, reply_markup=get_sub_channels_kb(unsubbed), parse_mode="HTML")

                return await deliver_movie(bot, message.chat.id, user.id, movie, db)

    # Standard Welcome Message from dynamic text
    bot_info = await bot.get_me()
    raw_welcome = await db.get_bot_text("welcome")
    try:
        welcome_text = raw_welcome.format(
            full_name=user.full_name,
            username=user.username or "",
            bot_username=bot_info.username
        )
    except Exception:
        welcome_text = (
            f"👋 Assalomu alaykum, <b>{user.full_name}</b>!\n\n"
            "🎬 <b>Kino Bot</b>imizga xush kelibsiz!\n\n"
            "🔢 Kino kodini yuboring:"
        )

    # For admin, attach the single '🕹️ Boshqaruv' button
    if is_admin:
        await message.answer(welcome_text, reply_markup=get_admin_reply_kb(), parse_mode="HTML")
    else:
        await message.answer(welcome_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")

    # Send start ad if enabled
    await send_ad_if_enabled(bot, message.chat.id, "ad_on_start", db)


@router.callback_query(F.data == "check_sub")
async def cb_check_sub(call: CallbackQuery, db: Database, bot, is_admin: bool = False):
    user = call.from_user
    channels = await db.get_channels(active_only=True)
    unsubbed = []

    for ch in channels:
        if ch.get("channel_type") == "external":
            continue
        if not await is_user_subscribed(bot, user.id, ch["channel_id"]):
            unsubbed.append(ch)

    if unsubbed:
        await call.answer("❌ Hamma kanallarga a'zo bo'lmadingiz!", show_alert=True)

    else:
        await call.answer("✅ Obuna tasdiqlandi!")
        try:
            await call.message.delete()
        except Exception:
            pass

        bot_info = await bot.get_me()
        raw_welcome = await db.get_bot_text("welcome")
        try:
            welcome_text = raw_welcome.format(
                full_name=user.full_name,
                username=user.username or "",
                bot_username=bot_info.username
            )
        except Exception:
            welcome_text = (
                f"🎉 <b>Tabriklaymiz!</b> Obuna muvaffaqiyatli tekshirildi.\n\n"
                f"👋 Assalomu alaykum, <b>{user.full_name}</b>!\n\n"
                "🔢 Kino kodini yuboring:"
            )

        if is_admin:
            await call.message.answer(welcome_text, reply_markup=get_admin_reply_kb(), parse_mode="HTML")
        else:
            await call.message.answer(welcome_text, reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
        
        await send_ad_if_enabled(bot, call.message.chat.id, "ad_on_start", db)
