"""Utility script to reset the database and start completely fresh."""

import asyncio
import os
import shutil
from pathlib import Path

from app.core.config import settings
from app.db.session import engine, init_db


async def reset_database() -> None:
    print("Menghentikan koneksi database...")
    await engine.dispose()

    # Lokasi folder data
    data_dir = settings.DATA_DIR

    print(f"Menghapus data lama di: {data_dir} ...")
    if data_dir.exists():
        try:
            shutil.rmtree(data_dir)
            print("Folder data dan file database berhasil dihapus.")
        except Exception as e:
            print(f"Gagal menghapus folder data: {e}")
            print("Pastikan bot sedang TIDAK berjalan (tekan Ctrl+C pada terminal bot).")
            return

    # Inisialisasi ulang database dan tabel fresh
    print("Membuat database dan tabel baru yang bersih...")
    await init_db()
    await engine.dispose()
    print("Database berhasil di-reset menjadi FRESH (bersih total)!")
    print("Anda sekarang dapat menjalankan bot kembali dengan: python -m app atau start.bat")


if __name__ == "__main__":
    asyncio.run(reset_database())

