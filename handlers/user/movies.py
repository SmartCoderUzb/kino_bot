from aiogram import Router, F
from aiogram.types import Message
from kino_bot.database.db import Database
from kino_bot.handlers.user.start import deliver_movie

router = Router(name="user_movies")

@router.message(F.text)
async def process_movie_query(message: Message, db: Database, bot):
    text = message.text.strip()
    
    # Ignore bot commands
    if text.startswith("/"):
        return

    # Look up movie by code
    movie = await db.get_movie_by_code(text)
    if movie:
        return await deliver_movie(bot, message.chat.id, message.from_user.id, movie, db)

    # If code not found
    raw_wrong = await db.get_bot_text("wrong_code_msg")
    try:
        msg = raw_wrong.format(code=text)
    except Exception:
        msg = f"😔 Kechirasiz, <b>{text}</b> kodli kino topilmadi.\n\nIltimos, kodni to'g'ri kiritganingizga ishonch hosil qiling."

    await message.answer(msg, parse_mode="HTML")
