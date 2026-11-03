"""Application-wide constants, enums, and default configurations."""

from enum import Enum


class TransactionType(str, Enum):
    PEMASUKAN = "PEMASUKAN"
    PENGELUARAN = "PENGELUARAN"

    @property
    def label(self) -> str:
        if self == TransactionType.PEMASUKAN:
            return "Pemasukan"
        return "Pengeluaran"

    @property
    def emoji(self) -> str:
        if self == TransactionType.PEMASUKAN:
            return "🟢"
        return "🔴"


class ReportType(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"

    @property
    def label(self) -> str:
        if self == ReportType.DAILY:
            return "Harian"
        elif self == ReportType.WEEKLY:
            return "Mingguan"
        return "Bulanan"


class ExportFormat(str, Enum):
    CSV = "CSV"
    EXCEL = "EXCEL"


class ExportPeriod(str, Enum):
    ALL = "ALL"
    TODAY = "TODAY"
    THIS_WEEK = "THIS_WEEK"
    THIS_MONTH = "THIS_MONTH"
    CUSTOM = "CUSTOM"

    @property
    def label(self) -> str:
        mapping = {
            ExportPeriod.ALL: "Semua Transaksi",
            ExportPeriod.TODAY: "Hari Ini",
            ExportPeriod.THIS_WEEK: "Minggu Ini",
            ExportPeriod.THIS_MONTH: "Bulan Ini",
            ExportPeriod.CUSTOM: "Rentang Tanggal Kustom",
        }
        return mapping.get(self, self.value)


# Default categories as strictly requested in the prompt
DEFAULT_INCOME_CATEGORIES: list[str] = [
    "Gaji",
    "Bonus",
    "Freelance",
    "Bisnis",
    "Hadiah",
    "Lainnya",
]

DEFAULT_EXPENSE_CATEGORIES: list[str] = [
    "Makanan & Minuman",
    "Transportasi",
    "Belanja",
    "Tagihan",
    "Hiburan",
    "Kesehatan",
    "Pendidikan",
    "Kebutuhan Rumah",
    "Lainnya",
]

# Reply Keyboard button texts
BTN_DASHBOARD = "📊 Dashboard"
BTN_ADD_TX = "➕ Tambah Transaksi"
BTN_HISTORY = "📜 Riwayat"
BTN_REPORT = "📈 Laporan"
BTN_EXPORT = "📁 Ekspor Data"
BTN_CATEGORIES = "🏷️ Kelola Kategori"
BTN_SETTINGS = "⚙️ Pengaturan"

MAIN_MENU_BUTTONS = [
    [BTN_DASHBOARD, BTN_ADD_TX],
    [BTN_HISTORY, BTN_REPORT],
    [BTN_EXPORT, BTN_CATEGORIES],
    [BTN_SETTINGS],
]


def format_idr(amount: int) -> str:
    """Format an integer amount to Indonesian Rupiah representation.
    
    Examples:
        1500000 -> 'Rp1.500.000'
        0 -> 'Rp0'
        -50000 -> '-Rp50.000'
    """
    if amount < 0:
        formatted = f"{abs(amount):,}".replace(",", ".")
        return f"-Rp{formatted}"
    formatted = f"{amount:,}".replace(",", ".")
    return f"Rp{formatted}"

