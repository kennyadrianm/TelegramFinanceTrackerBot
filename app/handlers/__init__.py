"""Aggregate all routers into a main router."""

from aiogram import Router

from app.handlers.category import router as category_router
from app.handlers.common import router as common_router
from app.handlers.dashboard import router as dashboard_router
from app.handlers.export import router as export_router
from app.handlers.history import router as history_router
from app.handlers.report import router as report_router
from app.handlers.settings import router as settings_router
from app.handlers.transaction_add import router as transaction_add_router
from app.handlers.transaction_delete import router as transaction_delete_router
from app.handlers.transaction_edit import router as transaction_edit_router


def get_main_router() -> Router:
    """Create root router registering all sub-routers in appropriate order."""
    root_router = Router(name="root_router")
    root_router.include_router(common_router)
    root_router.include_router(dashboard_router)
    root_router.include_router(transaction_add_router)
    root_router.include_router(transaction_edit_router)
    root_router.include_router(transaction_delete_router)
    root_router.include_router(history_router)
    root_router.include_router(category_router)
    root_router.include_router(report_router)
    root_router.include_router(export_router)
    root_router.include_router(settings_router)
    return root_router

