# Telegram Finance Tracker Bot (Multi-User)

A modular, production-ready personal finance tracking Telegram bot built with **Python 3.12+**, **aiogram 3.x**, and **SQLAlchemy 2.x**. Designed for Windows 11 local execution via Telegram Long Polling, and architected for easy future migration to Linux/VPS.

---

## 🌟 Fitur Utama

- **Multi-User Isolation**: Setiap pengguna Telegram memiliki ruang data terisolasi. Seluruh transaksi, kategori kustom, preferensi laporan, dan file ekspor terikat secara ketat pada `telegram_user_id`.
- **Private Chat Only**: Akses dari grup/supergroup/channel ditolak otomatis demi menjaga kerahasiaan finansial pengguna.
- **Pencatatan Transaksi Interaktif**:
  - Pemasukan (Income) & Pengeluaran (Expense).
  - Validasi nominal ketat berupa bilangan bulat Rupiah (integer positif, tanpa floating-point error).
  - Pemilih tanggal interaktif: *Hari Ini*, *Kalender Inline (Bahasa Indonesia)*, atau format manual `DD-MM-YYYY`.
  - Catatan transaksi opsional dengan tombol lewati (*Skip*).
  - Pratinjau (*Preview*) lengkap sebelum konfirmasi eksplisit (*Simpan*, *Perbaiki*, *Batalkan*).
- **Edit & Hapus Transaksi**:
  - Ubah nominal, kategori, tanggal, tipe transaksi, dan catatan.
  - Validasi kompatibilitas kategori saat tipe transaksi berganti.
  - Konfirmasi eksplisit sebelum penghapusan permanen (*Hard Delete*).
- **Kelola Kategori**:
  - Kategori bawaan (*Default*) terpisah untuk Pemasukan dan Pengeluaran.
  - Buat, ubah nama (*Rename*), dan hapus kategori kustom.
  - Pengecekan referensi: Kategori yang masih digunakan oleh transaksi tidak dapat dihapus sebelum transaksi terkait diselesaikan.
- **Dashboard Keuangan**:
  - Ringkasan Saldo Saat Ini (*Total Pemasukan - Total Pengeluaran*), Total Pemasukan, Total Pengeluaran, dan 5 transaksi terakhir.
  - Saldo awal Rp0 untuk setiap pengguna baru.
  - Pemformatan mata uang standar Indonesia (contoh: `Rp1.500.000`).
- **Riwayat Transaksi**:
  - Navigasi halaman (*Pagination* 5 transaksi per halaman).
  - Filter berdasarkan tipe (Semua, Pemasukan, Pengeluaran).
  - Filter berdasarkan periode (Semua Waktu, Hari Ini, Minggu Ini, Bulan Ini).
  - Tampilan rincian transaksi dengan tombol aksi cepat (*Ubah* / *Hapus*).
- **Laporan Keuangan Manual & Otomatis**:
  - Periode: Harian, Mingguan (Senin–Minggu), dan Bulanan (Bulan Kalender).
  - Rincian persentase dan nominal per kategori.
  - Penjadwal laporan otomatis (*APScheduler*) pada zona waktu `Asia/Jakarta` (WIB).
  - Pencegahan duplikasi pengiriman (*Duplicate Delivery Protection*) berbasis tabel `report_deliveries`.
  - Toleran terhadap restart aplikasi tanpa *catch-up spam*.
- **Ekspor Data Transaksi**:
  - Format CSV (`.csv` dengan UTF-8 BOM untuk Microsoft Excel).
  - Format Excel (`.xlsx` lengkap dengan gaya tabel dan baris ringkasan).
  - Filter ekspor: Semua, Hari Ini, Minggu Ini, Bulan Ini, atau Rentang Kustom (`DD-MM-YYYY`).
  - Pembersihan otomatis file sementara setelah dikirimkan ke chat pengguna.

---

## 🛠️ Arsitektur & Teknologi

| Komponen | Teknologi |
| :--- | :--- |
| **Bahasa Pemrograman** | Python 3.12+ |
| **Framework Bot** | [aiogram 3.x](https://docs.aiogram.dev/) (Asynchronous Telegram Bot API) |
| **Database & ORM** | [SQLAlchemy 2.x](https://docs.sqlalchemy.org/) + `aiosqlite` (SQLite WAL mode & Foreign Keys enabled) |
| **Scheduler** | [APScheduler 3.x](https://apscheduler.readthedocs.io/) (AsyncIOScheduler terintegrasi) |
| **Excel Exporter** | [openpyxl](https://openpyxl.readthedocs.io/) |
| **Zona Waktu** | `zoneinfo` (`Asia/Jakarta` - WIB) & `tzdata` |
| **Testing** | [pytest](https://docs.pytest.org/) & `pytest-asyncio` |

---

## 📁 Struktur Direktori

```text
FinanceTrackerBot/
├── .env.example                  # Template variabel lingkungan
├── .gitignore                    # Konfigurasi file yang diabaikan Git
├── requirements.txt              # Daftar dependensi aplikasi
├── pytest.ini                    # Konfigurasi automated testing
├── start.bat                     # Skrip peluncur cepat Windows 11
├── README.md                     # Dokumentasi teknis & panduan instalasi
├── app/
│   ├── __init__.py
│   ├── __main__.py               # Entry point untuk python -m app
│   ├── main.py                   # Setup bot, scheduler, dispatcher, dan polling
│   ├── core/
│   │   ├── config.py             # Parsing konfigurasi dan path
│   │   ├── constants.py          # Definisi Enum, kategori default, dan IDR formatter
│   │   ├── logging.py            # Konfigurasi structured logging
│   │   ├── timezone.py           # Utilitas zona waktu Asia/Jakarta (WIB)
│   │   └── scheduler.py          # Logika penjadwalan & pencegahan duplikasi
│   ├── db/
│   │   ├── base.py               # DeclarativeBase SQLAlchemy
│   │   ├── session.py            # SQLite async_engine & sessionmaker (WAL mode)
│   │   └── models.py             # Model User, Category, Transaction, ReportPreference, ReportDelivery
│   ├── services/
│   │   ├── user_service.py       # Registrasi otomatis & manajemen pengguna
│   │   ├── category_service.py   # Logika CRUD & isolasi kategori
│   │   ├── transaction_service.py# Logika CRUD transaksi, saldo, dan kalkulasi ringkasan
│   │   ├── report_service.py     # Perhitungan laporan & pelacakan pengiriman
│   │   └── export_service.py     # Generator file CSV & XLSX serta penghapusan temp file
│   ├── states/
│   │   └── form_states.py        # Aiogram FSM States (Add, Edit, Cat, Export, Settings)
│   ├── keyboards/
│   │   ├── reply_keyboards.py    # Persistent bottom reply keyboard
│   │   ├── inline_keyboards.py   # Menu navigasi, aksi, konfirmasi, dan filter
│   │   └── calendar_keyboard.py  # Kalender interaktif inline bahasa Indonesia
│   ├── middlewares/
│   │   ├── chat_type.py          # PrivateChatOnlyMiddleware (menolak grup/channel)
│   │   └── db_session.py         # SQLAlchemy AsyncSession lifecycle middleware
│   └── handlers/
│       ├── common.py             # /start, /help, /cancel, fallback
│       ├── dashboard.py          # Dashboard view & refresh
│       ├── transaction_add.py    # Alur tambah transaksi interaktif
│       ├── transaction_edit.py   # Alur ubah transaksi
│       ├── transaction_delete.py # Alur hapus transaksi dengan konfirmasi
│       ├── history.py            # Riwayat & paginasi transaksi
│       ├── category.py           # Kelola kategori kustom
│       ├── report.py             # Permintaan laporan manual
│       ├── export.py             # Generator & pengirim file ekspor
│       └── settings.py           # Pengaturan laporan otomatis
└── tests/
    ├── conftest.py               # Fixture database in-memory & isolasi user
    ├── test_users.py             # Pengujian registrasi & inisialisasi default
    ├── test_categories.py        # Pengujian CRUD & kepemilikan kategori
    ├── test_transactions.py      # Pengujian CRUD, validasi nominal, & edit transaksi
    ├── test_dashboard.py         # Pengujian kalkulasi saldo & update dashboard
    ├── test_reports.py           # Pengujian laporan harian, mingguan, bulanan, & proteksi duplikasi
    ├── test_export.py            # Pengujian ekspor CSV, Excel, & isolasi data ekspor
    └── test_security.py          # Pengujian pembatasan private chat
```

---

## 🚀 Panduan Instalasi (Windows 11)

### 1. Prasyarat
- Sistem Operasi: Windows 11.
- Python 3.11 atau lebih baru (disarankan Python 3.12).
- Akses internet untuk mengunduh dependensi dan menghubungkan ke Telegram Bot API.

### 2. Persiapan Virtual Environment
Buka terminal PowerShell atau Command Prompt di direktori project:

```powershell
# 1. Buat virtual environment
python -m venv .venv

# 2. Aktifkan virtual environment
.\.venv\Scripts\Activate.ps1
# (atau pada Command Prompt cmd.exe: .venv\Scripts\activate.bat)

# 3. Perbarui pip dan pasang dependensi
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

## 🔑 Mendapatkan Telegram Bot Token

1. Buka aplikasi Telegram dan cari akun resmi **[@BotFather](https://t.me/BotFather)**.
2. Kirim perintah `/newbot`.
3. Masukkan nama tampilan bot Anda (contoh: `DompetKu Finance Bot`).
4. Masukkan username bot (harus berakhiran `bot`, contoh: `dompetku_tracker_bot`).
5. `@BotFather` akan mengirimkan pesan berisi token otorisasi API seperti:
   `789123456:AAFlk_abcdef1234567890abcdef1234567`
6. Salin token tersebut untuk konfigurasi di bawah.

---

## ⚙️ Konfigurasi Environment (`.env`)

1. Salin template `.env.example` menjadi `.env`:
   ```powershell
   copy .env.example .env
   ```
2. Buka file `.env` menggunakan teks editor (Notepad atau VS Code) dan masukkan token bot Anda:
   ```env
   BOT_TOKEN=789123456:AAFlk_abcdef1234567890abcdef1234567
   DATABASE_URL=sqlite+aiosqlite:///data/finance_tracker.db
   LOG_LEVEL=INFO
   ```

---

## 🏃 Menjalankan Aplikasi

Anda dapat menjalankan bot dengan salah satu cara berikut:

### Opsi A: Menggunakan Command Line
```powershell
.\.venv\Scripts\python.exe -m app
```

### Opsi B: Menggunakan File Batch
Cukup klik ganda (*double-click*) file `start.bat` di Windows Explorer.

### Menghentikan Bot
Tekan kombinasi tombol `Ctrl + C` pada jendela terminal yang sedang menjalankan bot.

---

## 🧪 Menjalankan Automated Tests

Seluruh skenario pengujian diuji menggunakan database SQLite in-memory independen sehingga tidak memerlukan token Telegram asli.

Jalankan pengujian dengan perintah:
```powershell
.\.venv\Scripts\pytest.exe -v
```

Hasil uji coba:
```text
tests/test_categories.py::test_custom_category_creation PASSED           [  3%]
tests/test_categories.py::test_custom_category_ownership PASSED          [  7%]
tests/test_categories.py::test_delete_category_with_referenced_transactions PASSED [ 11%]
tests/test_dashboard.py::test_dashboard_initial_balance_is_zero PASSED   [ 15%]
tests/test_dashboard.py::test_dashboard_calculations_and_updates PASSED  [ 19%]
tests/test_export.py::test_export_csv PASSED                             [ 23%]
tests/test_export.py::test_export_excel PASSED                           [ 26%]
tests/test_export.py::test_export_ownership_isolation PASSED             [ 30%]
tests/test_reports.py::test_daily_report_calculations PASSED             [ 34%]
tests/test_reports.py::test_weekly_report_calculations PASSED            [ 38%]
tests/test_reports.py::test_monthly_report_calculations PASSED           [ 42%]
tests/test_reports.py::test_date_range_boundaries PASSED                 [ 46%]
tests/test_reports.py::test_report_preference_handling PASSED            [ 50%]
tests/test_reports.py::test_duplicate_report_delivery_prevention PASSED  [ 53%]
tests/test_security.py::test_private_chat_allowed PASSED                 [ 57%]
tests/test_security.py::test_group_chat_rejected PASSED                  [ 61%]
tests/test_security.py::test_supergroup_chat_rejected PASSED             [ 65%]
tests/test_transactions.py::test_income_creation PASSED                  [ 69%]
tests/test_transactions.py::test_expense_creation PASSED                 [ 73%]
tests/test_transactions.py::test_transaction_amount_validation PASSED    [ 76%]
tests/test_transactions.py::test_transaction_editing PASSED              [ 80%]
tests/test_transactions.py::test_transaction_deletion_logic PASSED       [ 84%]
tests/test_transactions.py::test_transaction_ownership_validation PASSED [ 88%]
tests/test_users.py::test_new_user_registration PASSED                   [ 92%]
tests/test_users.py::test_duplicate_registration PASSED                  [ 96%]
tests/test_users.py::test_default_category_initialization PASSED         [100%]

============================= 26 passed in 3.58s ==============================
```

---

## 📌 Batasan Prototipe Saat Ini

1. **Jadwal Laporan Otomatis Membutuhkan Proses Aktif**:
   Laporan otomatis dijadwalkan secara internal dalam proses Python. Apabila komputer Windows mati, dalam status *Sleep*, atau bot tidak sedang dijalankan, laporan otomatis tidak dapat terkirim pada jam tersebut. Setelah bot dinyalakan kembali, bot tidak akan mengirim *spam* laporan yang terlewat (*no unlimited catch-up*).
2. **Koneksi Telegram Long Polling**:
   Prototipe ini menggunakan polling langsung ke server Telegram. Untuk kebutuhan produksi berskala besar di server publik/cloud, disarankan berpindah ke mode Webhook dengan SSL.
3. **Penyimpanan SQLite Lokal**:
   File database disimpan secara lokal di path `data/finance_tracker.db`. Jangan menghapus folder `data/` secara manual agar riwayat transaksi pengguna tidak hilang.

---

## 🚀 Rekomendasi Langkah Pengembangan Selanjutnya

1. **Migrasi ke Server / VPS**:
   - Menjalankan bot sebagai `systemd service` atau menggunakan Docker container di Linux VPS agar berjalan 24/7.
   - Mengganti Telegram Long Polling dengan Webhook di balik reverse proxy (seperti Nginx atau Caddy).
2. **Database Cloud / PostgreSQL**:
   - Karena project telah menggunakan SQLAlchemy 2.x dengan arsitektur async repository terpisah, migrasi ke PostgreSQL dapat dilakukan hanya dengan mengubah connection string `DATABASE_URL=postgresql+asyncpg://...` tanpa merombak logika bisnis.
3. **Pencadangan Data Otomatis**:
   - Menambahkan fitur backup database terenkripsi berkala ke penyimpanan cloud pribadi (misal: S3 / Google Drive).
4. **Visualisasi Grafik**:
   - Menambahkan opsi pengiriman diagram pie (*pie chart*) per kategori menggunakan library visualisasi data seperti `matplotlib`.

