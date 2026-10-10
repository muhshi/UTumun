import os
import asyncio
from pathlib import Path
from playwright.async_api import BrowserContext, Page, async_playwright
from tuton.config import (
    SESSION_FILE,
    UT_USERNAME,
    UT_PASSWORD,
    CHROME_PATH
)

def is_session_expired_indicator(text: str) -> bool:
    if not text:
        return False
    lower = text.lower()
    return "sesi anda telah habis" in lower or "session has timed out" in lower

async def perform_login(context: BrowserContext, page: Page) -> bool:
    """Melakukan login otomatis melalui portal MyUT Tutor Eksternal."""
    if not UT_USERNAME or not UT_PASSWORD:
        raise ValueError("UT_USERNAME atau UT_PASSWORD belum diatur pada file .env")

    print("[AUTH] Memulai proses login MyUT...")
    await page.goto("https://elearning.ut.ac.id/login/index.php", wait_until="domcontentloaded")
    await page.wait_for_timeout(1500)

    # Klik tombol login MyUT
    login_btn = page.locator("#btnLoginMyUT")
    if await login_btn.count() > 0:
        await login_btn.click()
        await page.wait_for_timeout(1000)

    # Pilih Tutor Eksternal
    tutor_btn = page.locator("#btnTutorEksternal")
    if await tutor_btn.count() > 0:
        await tutor_btn.click()
        await page.wait_for_timeout(1000)

    # Isi credentials di modal
    await page.fill("#username_modal", UT_USERNAME)
    await page.fill("#password_modal", UT_PASSWORD)

    modal_submit = page.locator('#modalLogin, .modal-content, .modal-body').locator(
        'button[type="submit"], input[type="submit"], button:has-text("Masuk")'
    ).first

    if await modal_submit.count() > 0:
        await modal_submit.click()
    else:
        await page.locator("#password_modal").press("Enter")

    # Tunggu pengalihan ke dashboard /my/
    try:
        await page.wait_for_url(lambda u: "/my/" in u, timeout=30000)
    except Exception:
        # Fallback jika redirect lambat tapi URL sudah berubah
        await page.wait_for_timeout(5000)

    # Simpan state session yang valid
    Path(SESSION_FILE).parent.mkdir(parents=True, exist_ok=True)
    await context.storage_state(path=SESSION_FILE)
    print(f"[AUTH] Login berhasil! Sesi diperbarui dan disimpan di {SESSION_FILE}")
    return True

async def ensure_authenticated_page(context: BrowserContext, page: Page) -> bool:
    """
    Memeriksa validitas sesi saat ini.
    Jika sesi kedaluwarsa atau belum ada, lakukan login ulang secara otomatis.
    """
    print("[AUTH] Memeriksa validitas sesi di e-learning UT...")
    await page.goto("https://elearning.ut.ac.id/my/", wait_until="domcontentloaded")
    await page.wait_for_timeout(2000)

    needs_login = False
    current_url = page.url

    if "/login/" in current_url:
        needs_login = True
    elif await page.locator("#btnLoginMyUT").count() > 0:
        needs_login = True
    else:
        # Cek apakah ada pesan atau modal "Sesi Anda telah habis"
        body_text = await page.evaluate("() => document.body.innerText")
        if is_session_expired_indicator(body_text):
            needs_login = True

    if needs_login:
        print("[AUTH] Sesi tidak valid atau telah kedaluwarsa. Menjalankan auto-relogin...")
        return await perform_login(context, page)
    else:
        print("[AUTH] Sesi aktif dan valid!")
        return True
