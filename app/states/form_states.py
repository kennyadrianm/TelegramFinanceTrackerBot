"""FSM states for multi-step interactive Telegram menus."""

from aiogram.fsm.state import State, StatesGroup


class AddTransactionState(StatesGroup):
    waiting_for_type = State()
    waiting_for_amount = State()
    waiting_for_category = State()
    waiting_for_date = State()
    waiting_for_note = State()
    waiting_for_confirmation = State()


class EditTransactionState(StatesGroup):
    waiting_for_field_selection = State()
    waiting_for_new_type = State()
    waiting_for_new_amount = State()
    waiting_for_new_category = State()
    waiting_for_new_date = State()
    waiting_for_new_note = State()
    waiting_for_confirmation = State()


class CategoryState(StatesGroup):
    waiting_for_type_selection = State()
    waiting_for_category_name = State()
    waiting_for_rename_input = State()


class ExportState(StatesGroup):
    waiting_for_format = State()
    waiting_for_period = State()
    waiting_for_custom_start = State()
    waiting_for_custom_end = State()


class SettingsState(StatesGroup):
    waiting_for_daily_time = State()
    waiting_for_weekly_day = State()
    waiting_for_weekly_time = State()
    waiting_for_monthly_time = State()

