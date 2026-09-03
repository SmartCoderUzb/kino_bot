from aiogram import Router
from .main import router as main_router
from .movies import router as movies_router
from .channels import router as channels_router
from .broadcast import router as broadcast_router
from .ads import router as ads_router
from .users import router as users_router
from .posts import router as posts_router
from .requests import router as requests_router
from .settings import router as settings_router

admin_router = Router(name="admin_root")
admin_router.include_routers(
    main_router,
    movies_router,
    channels_router,
    broadcast_router,
    ads_router,
    users_router,
    posts_router,
    requests_router,
    settings_router
)

__all__ = ["admin_router"]
