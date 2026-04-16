from .users import router as users_router
from .shifts import router as shifts_router
from .swaps import router as swaps_router
from .medical_profiles import router as medical_profiles_router

__all__ = ["users_router", "shifts_router", "swaps_router", "medical_profiles_router"]
