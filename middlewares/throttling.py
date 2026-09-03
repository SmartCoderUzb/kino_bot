from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from typing import Callable, Dict, Any, Awaitable
from redis.asyncio import Redis
import logging

logger = logging.getLogger(__name__)


class ThrottlingMiddleware(BaseMiddleware):
    def __init__(self, redis: Redis, rate_limit: float = 0.6):
        self.redis = redis
        self.rate_limit = rate_limit
        super().__init__()

    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Admins bypass throttling
        if data.get("is_admin", False):
            return await handler(event, data)

        user = None
        if isinstance(event, Message):
            user = event.from_user
        elif isinstance(event, CallbackQuery):
            user = event.from_user

        if not user or user.is_bot:
            return await handler(event, data)

        key = f"throttle:{user.id}"
        try:
            is_locked = await self.redis.get(key)
            if is_locked:
                if isinstance(event, Message):
                    await event.answer("⚠️ Iltimos, juda tez xabar yubormang!")
                elif isinstance(event, CallbackQuery):
                    await event.answer("⚠️ Juda ko'p so'rov! Biroz kuting.", show_alert=True)
                return

            await self.redis.set(key, "1", px=int(self.rate_limit * 1000))
        except Exception as e:
            logger.warning(f"Throttling error: {e}")

        return await handler(event, data)
