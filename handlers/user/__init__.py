from aiogram import Router
from .start import router as start_router
from .movies import router as movies_router

user_router = Router(name="user_root")
user_router.include_routers(
    start_router,
    movies_router
)

__all__ = ["user_router"]
