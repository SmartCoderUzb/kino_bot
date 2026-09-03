from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from kino_bot.database.db import Database
from kino_bot.keyboards.user_kb import get_sub_channels_kb
import logging

logger = logging.getLogger(__name__)

async def is_user_subscribed(bot, user_id: int, channel_id: str, redis=None) -> bool:
    if not channel_id:
        return True
    if redis:
        try:
            cache_key = f"sub:{user_id}:{channel_id}"
            cached = await redis.get(cache_key)
            if cached is not None:
                return cached == b"1" or cached == "1"
        except Exception:
            pass

    try:
        member = await bot.get_chat_member(chat_id=channel_id, user_id=user_id)
        is_sub = member.status in ["member", "administrator", "creator", "restricted"]
        if is_sub and redis:
            try:
                await redis.set(f"sub:{user_id}:{channel_id}", "1", ex=300)  # 5 daqiqa kesh
            except Exception:
                pass
        return is_sub
    except Exception as e:
        logger.warning(f"Error checking sub for user {user_id} in {channel_id}: {e}")
        # If bot cannot check or not admin, don't hard block user
        return True

class CheckSubscriptionMiddleware(BaseMiddleware):
    def __init__(self, db: Database, redis=None):
        self.db = db
        self.redis = redis
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Admins bypass subscription check
        if data.get("is_admin", False):
            return await handler(event, data)

        bot = data.get("bot")
        redis = data.get("redis", self.redis)
        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user or user.is_bot:
            return await handler(event, data)

        # Allow check_sub callback to pass through so user can verify
        if isinstance(event, CallbackQuery) and event.data == "check_sub":
            return await handler(event, data)

        channels = await self.db.get_channels(active_only=True)
        if not channels:
            return await handler(event, data)

        unsubbed = []
        for ch in channels:
            # External channels (YouTube, Instagram) don't have Telegram get_chat_member verification
            if ch.get("channel_type") == "external":
                continue

            subbed = await is_user_subscribed(bot, user.id, ch["channel_id"], redis=redis)
            if not subbed:
                unsubbed.append(ch)

        if unsubbed:
            # Also include external channels in the buttons list so users see them
            all_display_channels = channels
            text = (
                "⚠️ <b>Botdan foydalanish uchun quyidagi homiy kanallarga a'zo bo'ling!</b>\n\n"
                "A'zo bo'lgach <b>«✅ Tekshirish»</b> tugmasini bosing."
            )
            kb = get_sub_channels_kb(all_display_channels)
            if isinstance(event, Message):
                await event.answer(text, reply_markup=kb, parse_mode="HTML")
            elif isinstance(event, CallbackQuery):
                await event.answer("⚠️ Iltimos, oldin kanallarga a'zo bo'ling!", show_alert=True)
                try:
                    await event.message.answer(text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass
            return

        return await handler(event, data)

