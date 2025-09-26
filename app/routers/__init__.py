from .auth import router as auth_router
from .convert import router as convert_router
from .history import router as history_router
from .favorites import router as favorites_router
from .profile import router as profile_router

__all__ = ["auth_router", "convert_router", "history_router", "favorites_router", "profile_router"]